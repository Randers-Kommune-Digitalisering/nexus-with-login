import logging
import math
import time
import requests

from flask import Blueprint, jsonify, redirect, url_for, request, session
from authlib.integrations.flask_client import OAuth
from flask_session import Session

from utils.config import COOKIE_SECRET, CLIENT_ID, CLIENT_SECRET, AUTH_URL, AUTH_PATH, AUTH_REALM, APP_URL

logger = logging.getLogger(__name__)
TOKEN_URL = f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}/protocol/openid-connect/token'


class TokenRefreshUnavailable(Exception):
    pass


def current_access_token():
    token = session.get('token')
    if not isinstance(token, dict) or not token.get('access_token'):
        session.clear()
        return None

    expires_at = token.get('expires_at')
    if not isinstance(expires_at, (int, float)) or not math.isfinite(expires_at):
        session.clear()
        return None
    if expires_at > time.time() + 30:
        return token['access_token']

    refresh_token = token.get('refresh_token')
    if not refresh_token:
        session.clear()
        return None

    started_at = time.time()
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
            },
            timeout=15,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        logger.warning('Token refresh request failed')
        raise TokenRefreshUnavailable from exc

    if response.status_code in (400, 401):
        session.clear()
        return None
    if response.status_code != 200:
        logger.warning('Token refresh endpoint returned status %s', response.status_code)
        raise TokenRefreshUnavailable

    try:
        refreshed = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        logger.warning('Token refresh response was not valid JSON')
        raise TokenRefreshUnavailable from exc

    if not isinstance(refreshed, dict):
        logger.warning('Token refresh response was missing required fields')
        raise TokenRefreshUnavailable

    access_token = refreshed.get('access_token')
    expires_in = refreshed.get('expires_in')
    valid_expiry = isinstance(expires_in, (int, float)) and not isinstance(expires_in, bool)
    if valid_expiry:
        valid_expiry = math.isfinite(expires_in) and expires_in > 0
    if not isinstance(access_token, str) or not access_token or not valid_expiry:
        logger.warning('Token refresh response was missing required fields')
        raise TokenRefreshUnavailable

    new_refresh_token = refreshed.get('refresh_token', refresh_token)
    if not isinstance(new_refresh_token, str) or not new_refresh_token:
        logger.warning('Token refresh response contained an invalid refresh token')
        raise TokenRefreshUnavailable

    session['token'] = {
        **token,
        **refreshed,
        'refresh_token': new_refresh_token,
        'expires_at': started_at + expires_in,
    }
    return access_token


def add_user_handling(app):
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_COOKIE_SECURE'] = APP_URL.startswith('https://')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    Session(app)

    app.secret_key = COOKIE_SECRET
    oauth = OAuth(app)

    oauth.register(
        name='openid',
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        client_kwargs={'scope': 'openid profile email'},
        api_base_url=f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}',
        access_token_url=TOKEN_URL,
        authorize_url=f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}/protocol/openid-connect/auth',
        jwks_uri=f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}/protocol/openid-connect/certs',
        logout_url=f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}/protocol/openid-connect/logout'
    )

    @app.before_request
    def check_authenticated():
        # Always allow access to assets (e.g. css, js, images)
        if request.path.startswith('/assets/'):
            pass
        elif 'token' not in session and request.path not in ['/user/login', '/user/auth', '/user/session', '/healthz', '/metrics', '/']:
            return {"error": "Unauthorized"}, 401

    user_endpoints = Blueprint('user', __name__, url_prefix='/user')

    @user_endpoints.route('/session', methods=['GET'])
    def session_status():
        if not session.get('token'):
            authenticated = False
        else:
            try:
                authenticated = bool(current_access_token())
            except TokenRefreshUnavailable:
                return jsonify(error='Authentication provider unavailable'), 502
        response = jsonify(authenticated=authenticated)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @user_endpoints.route('/login', methods=['GET'])
    def login():
        # Redirect to the OpenID provider for authorization - redirects to /user/auth
        redirect_uri = url_for('user.auth', _external=False)
        redirect_uri = APP_URL + redirect_uri
        print(redirect_uri)
        return oauth.openid.authorize_redirect(redirect_uri)

    @user_endpoints.route('/auth', methods=['GET'])
    def auth():
        # Handle the callback from the OpenID provider - adds token to session - then redirects to base url
        token = oauth.openid.authorize_access_token()
        session['token'] = token
        return redirect('/')

    # @user_endpoints.route('/profile', methods=['GET'])
    # def profile():
    #     # Endpoint to get user profile information
    #     # this is implemented as just parsing id token, alternative ideas:
    #     #   - could call openid userinfo endpoint to get more information
    #     #   - could extract specific information from the id token (e.g. email, name, etc.)
    #     user_info = session['token']['userinfo']
    #     return user_info

    @user_endpoints.route('/logout', methods=['GET'])
    def logout():
        refreshToken = session['token']['refresh_token']
        endSessionEndpoint = f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}/protocol/openid-connect/logout'

        requests.post(endSessionEndpoint, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refreshToken,
        })

        session.clear()
        return redirect('/')

    app.register_blueprint(user_endpoints)
