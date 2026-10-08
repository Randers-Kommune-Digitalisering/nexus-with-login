import logging
import hmac
import secrets
import requests
from utils.config import MAX_WRITE_BYTES, BASE_URL, BASE_PATH

from flask import Blueprint, Response, jsonify, request, session

logger = logging.getLogger(__name__)
api_endpoints = Blueprint('api', __name__, url_prefix='/api')
NEXUS_BASE = f'{BASE_URL}/{BASE_PATH}/'


@api_endpoints.route('/status', methods=['GET'])
def status():
    return jsonify({"success": True, "message": "API is up and running"})


@api_endpoints.route('/home-ressource', methods=['GET'])
def home_ressource():
    return nexus_request('')


@api_endpoints.route('/csrf', methods=['GET'])
def csrf_token():
    token = session.setdefault('csrf_token', secrets.token_urlsafe(32))
    response = jsonify(token=token)
    response.headers['Cache-Control'] = 'no-store'
    return response


@api_endpoints.route('/nexus/', defaults={'resource': ''}, methods=['GET', 'POST', 'PUT'])
@api_endpoints.route('/nexus/<path:resource>', methods=['GET', 'POST', 'PUT'])
def nexus_resource(resource):
    return nexus_request(resource)


def nexus_request(resource):
    segments = resource.removesuffix('/').split('/') if resource else []
    if any(not segment or segment in ('.', '..') or not all(
        (character.isascii() and character.isalnum()) or character in '._~-' for character in segment
    ) for segment in segments):
        return jsonify(error='Invalid Nexus path'), 400

    token = session.get('token', {}).get('access_token')
    if not token:
        return jsonify(error='Unauthorized'), 401

    if request.method in ('POST', 'PUT'):
        expected = session.get('csrf_token', '')
        supplied = request.headers.get('X-CSRF-Token', '')
        if not expected or not hmac.compare_digest(expected, supplied):
            return jsonify(error='Invalid CSRF token'), 403
        if request.content_length is None or request.content_length > MAX_WRITE_BYTES:
            return jsonify(error='Invalid request size'), 413

    headers = {'Authorization': f'Bearer {token}'}
    for name in ('Accept', 'Content-Type', 'If-Match', 'If-None-Match'):
        if name in request.headers:
            headers[name] = request.headers[name]

    try:
        upstream = requests.request(
            request.method,
            NEXUS_BASE + resource,
            params=list(request.args.items(multi=True)),
            headers=headers,
            data=request.get_data() if request.method in ('POST', 'PUT') else None,
            timeout=15,
            allow_redirects=False,
        )
    except requests.RequestException:
        logger.warning('Nexus request failed')
        return jsonify(error='Nexus unavailable'), 502

    if 300 <= upstream.status_code < 400:
        return jsonify(error='Unexpected Nexus redirect'), 502

    response = Response(
        upstream.content,
        status=upstream.status_code,
        content_type=upstream.headers.get('Content-Type', 'application/octet-stream'),
    )
    for name in ('ETag', 'Location'):
        if name in upstream.headers:
            response.headers[name] = upstream.headers[name]
    response.headers['Cache-Control'] = 'no-store'
    return response
