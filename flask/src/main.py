from flask import Flask
from flask_cors import CORS
from healthcheck import HealthCheck
from prometheus_client import generate_latest

from utils.logging import set_logging_configuration
from utils.config import DEBUG, PORT
from api_endpoints import api_endpoints
from user_handling import add_user_handling


set_logging_configuration()


def create_app():
    app = Flask(__name__, static_folder='dist')
    CORS(app)

    # Add user handling
    add_user_handling(app)

    health = HealthCheck()
    app.add_url_rule('/healthz', 'healthcheck', view_func=lambda: health.run())
    app.add_url_rule('/metrics', 'metrics', view_func=generate_latest)

    app.register_blueprint(api_endpoints)

    return app


app = create_app()


@app.route('/assets/<path:path>')
def static_file(path):
    return app.send_static_file('assets/' + path)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return app.send_static_file('index.html')


if __name__ == '__main__':  # pragma: no cover
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
