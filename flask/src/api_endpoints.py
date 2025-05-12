import logging
import requests

from flask import Blueprint, jsonify, session

logger = logging.getLogger(__name__)
api_endpoints = Blueprint('api', __name__, url_prefix='/api')


@api_endpoints.route('/status', methods=['GET'])
def status():
    return jsonify({"success": True, "message": "API is up and running"})


@api_endpoints.route('/home-ressource', methods=['GET'])
def home_ressource():
    headers = {"Authorization": "Bearer " + session['token']['access_token']}
    res = requests.get('https://randers.nexus-review.kmd.dk/api/core/mobile/randers/v2/', headers=headers)
    return res.json()
