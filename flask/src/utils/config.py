import os
from dotenv import load_dotenv


# loads .env file, will not overide already set enviroment variables (will do nothing when testing, building and deploying)
load_dotenv()


DEBUG = os.getenv('DEBUG', 'False') in ['True', 'true']
PORT = os.getenv('PORT', '8080')
POD_NAME = os.getenv('POD_NAME', 'pod_name_not_set')

APP_URL = os.getenv('APP_URL', f'http://localhost:{PORT}').rstrip('/')
BASE_URL = os.getenv('BASE_URL', 'https://example.com').rstrip('/')
BASE_PATH = os.getenv('BASE_PATH', '/test/').strip('/')
AUTH_URL = os.getenv('AUTH_URL', 'https://keycloak.t0.hosting.kitkube.dk')
AUTH_PATH = os.getenv('AUTH_PATH', 'auth')
AUTH_REALM = os.getenv('AUTH_REALM', 'randers-kommune')
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
COOKIE_SECRET = os.environ['COOKIE_SECRET']

MAX_WRITE_BYTES = 1024 * 1024
ALLOWED_CITIZEN_LIST_IDS = os.getenv('ALLOWED_CITIZEN_LIST_IDS', '5327')


def nexus_path(name, *, absolute=False, patient=False):
    path = os.environ[name]
    valid = (
        bool(path),
        path.startswith('/') == absolute,
        not path.startswith('//'),
        all(segment not in ('', '.', '..') for segment in path.strip('/').split('/')),
        not any(character in path for character in '?#'),
        path.count('{patient_id}') == int(patient),
    )
    if not all(valid):
        raise ValueError(f'Invalid {name} path')
    return path


NEXUS_ORDERS_API_PATH = nexus_path('NEXUS_ORDERS_API_PATH', absolute=True)
NEXUS_FORM_PROTOTYPE_PATH = nexus_path('NEXUS_FORM_PROTOTYPE_PATH', patient=True)
NEXUS_FORM_ACTION_PATH = nexus_path('NEXUS_FORM_ACTION_PATH', patient=True)
NEXUS_FLAT_REFERENCES_PATH = nexus_path('NEXUS_FLAT_REFERENCES_PATH', patient=True)
NEXUS_CITIZEN_PAGE_PATH = nexus_path('NEXUS_CITIZEN_PAGE_PATH', absolute=True, patient=True)
NEXUS_ORDER_PAGE_PATH = nexus_path('NEXUS_ORDER_PAGE_PATH', absolute=True, patient=True)
