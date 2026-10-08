import os
from dotenv import load_dotenv


# loads .env file, will not overide already set enviroment variables (will do nothing when testing, building and deploying)
load_dotenv()


DEBUG = os.getenv('DEBUG', 'False') in ['True', 'true']
PORT = os.getenv('PORT', '8080')
POD_NAME = os.getenv('POD_NAME', 'pod_name_not_set')

MAX_WRITE_BYTES = 1024 * 1024
APP_URL = os.getenv('APP_URL', f'http://localhost:{PORT}').rstrip('/')
BASE_URL = os.getenv('BASE_URL', 'https://example.com').rstrip('/')
BASE_PATH = os.getenv('BASE_PATH', '/test/').strip('/')
AUTH_URL = os.getenv('AUTH_URL', 'https://keycloak.t0.hosting.kitkube.dk')
AUTH_PATH = os.getenv('AUTH_PATH', 'auth')
AUTH_REALM = os.getenv('AUTH_REALM', 'randers-kommune')
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
COOKIE_SECRET = os.environ['COOKIE_SECRET']
