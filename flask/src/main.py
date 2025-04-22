<<<<<<< HEAD
import os
from flask import Flask, send_from_directory
from healthcheck import HealthCheck
from prometheus_client import generate_latest
from utils.logging import set_logging_configuration, is_ready_gauge, last_updated_gauge
from utils.config import DEBUG, PORT, POD_NAME
from api_endpoints import api_endpoints
=======
from flask import Flask
from flask_cors import CORS
from healthcheck import HealthCheck
from prometheus_client import generate_latest

from utils.logging import set_logging_configuration
from utils.config import DEBUG, PORT
from api_endpoints import api_endpoints
from user_handling import add_user_handling

>>>>>>> develop

set_logging_configuration()


def create_app():
<<<<<<< HEAD
    app = Flask(__name__, static_folder='dist', static_url_path='/')
=======
    app = Flask(__name__, static_folder='dist')
    CORS(app)

    # Add user handling
    add_user_handling(app)

>>>>>>> develop
    health = HealthCheck()
    app.add_url_rule('/healthz', 'healthcheck', view_func=lambda: health.run())
    app.add_url_rule('/metrics', 'metrics', view_func=generate_latest)

    app.register_blueprint(api_endpoints)

<<<<<<< HEAD
    @app.before_request
    def set_ready():
        is_ready_gauge.labels(job_name=POD_NAME, error_type=None).set(1)
        last_updated_gauge.set_to_current_time()

=======
>>>>>>> develop
    return app


app = create_app()


<<<<<<< HEAD
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')
=======
@app.route('/assets/<path:path>')
def static_file(path):
    return app.send_static_file('assets/' + path)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return app.send_static_file('index.html')
>>>>>>> develop


if __name__ == '__main__':  # pragma: no cover
    app.run(debug=DEBUG, host='0.0.0.0', port=PORT)
