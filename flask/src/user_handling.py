import logging
import requests

from flask import Blueprint, redirect, url_for, request, session
from authlib.integrations.flask_client import OAuth
from flask_session import Session

from utils.config import COOKIE_SECRET, CLIENT_ID, CLIENT_SECRET, AUTH_URL, AUTH_PATH, AUTH_REALM, APP_URL

logger = logging.getLogger(__name__)


def add_user_handling(app):
    app.config['SESSION_TYPE'] = 'filesystem'
    Session(app)

    app.secret_key = COOKIE_SECRET
    oauth = OAuth(app)

    oauth.register(
        name='openid',
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        client_kwargs={'scope': 'openid profile email'},
        api_base_url=f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}',
        access_token_url=f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}/protocol/openid-connect/token',
        authorize_url=f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}/protocol/openid-connect/auth',
        jwks_uri=f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}/protocol/openid-connect/certs',
        logout_url=f'{AUTH_URL}/{AUTH_PATH.strip("/")}/realms/{AUTH_REALM}/protocol/openid-connect/logout'
    )

    @app.before_request
    def check_authenticated():
        # Always allow access to assets (e.g. css, js, images)
        if request.path.startswith('/assets/'):
            pass
        elif 'token' not in session and request.path not in ['/user/login', '/user/auth', '/healthz', '/metrics', '/']:
            return {"error": "Unauthorized"}, 401

    user_endpoints = Blueprint('user', __name__, url_prefix='/user')

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
        session['token'] = oauth.openid.authorize_access_token()
        return redirect('/')

    @user_endpoints.route('/profile', methods=['GET'])
    def profile():
        # Endpoint to get user profile information
        # this is implemented as just parsing id token, alternative ideas:
        #   - could call openid userinfo endpoint to get more information
        #   - could extract specific information from the id token (e.g. email, name, etc.)
        user_info = session['token']['userinfo']
        return user_info

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
