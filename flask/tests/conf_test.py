from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from unittest.mock import Mock, patch
from main import create_app
from utils.config import nexus_path


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_healthz(client):
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'success'


def test_session_status_anonymous_does_not_fetch_nexus(client):
    with patch('api_endpoints.requests.request') as nexus:
        response = client.get('/user/session')
        assert response.status_code == 200
        assert response.get_json() == {'authenticated': False}
        assert response.headers['Cache-Control'] == 'no-store'
        nexus.assert_not_called()


def test_citizen_list_config_exposes_runtime_paths(client):
    with client.session_transaction() as session:
        session['token'] = {'access_token': 'valid-access'}

    response = client.get('/api/citizen-list-config')

    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.get_json()['nexusPaths'] == {
        'formPrototype': 'patients/{patient_id}/example-prototype',
        'formAction': 'patients/{patient_id}/example-actions',
        'flatReferences': 'patients/{patient_id}/example-references',
        'citizenPage': '/example-citizen/{patient_id}',
        'orderPage': '/example-order/{patient_id}',
    }


def test_orders_use_configured_upstream_path(client):
    with client.session_transaction() as session:
        session['token'] = {'access_token': 'valid-access', 'expires_at': 1100}

    upstream = Mock(status_code=200, content=b'[]', headers={})
    with patch('user_handling.time.time', return_value=1000), \
            patch('api_endpoints.requests.request', return_value=upstream) as nexus:
        response = client.get('/api/hcl-depot/orders?patientId=123&inProgress=true')

    assert response.status_code == 200
    assert nexus.call_args.args == ('GET', 'https://example.com/api/example-orders')
    assert nexus.call_args.kwargs['params'] == [('patientId', '123'), ('inProgress', 'true')]


@pytest.mark.parametrize('path', (
    'https://other.example/orders',
    '//other.example/orders',
    '/api/orders?token=value',
))
def test_invalid_orders_api_path_fails_at_startup(monkeypatch, path):
    monkeypatch.setenv('NEXUS_ORDERS_API_PATH', path)

    with pytest.raises(ValueError, match='NEXUS_ORDERS_API_PATH'):
        nexus_path('NEXUS_ORDERS_API_PATH', absolute=True)


def test_patient_path_requires_placeholder(monkeypatch):
    monkeypatch.setenv('NEXUS_FORM_ACTION_PATH', 'patients/forms')

    with pytest.raises(ValueError, match='NEXUS_FORM_ACTION_PATH'):
        nexus_path('NEXUS_FORM_ACTION_PATH', patient=True)


def test_session_status_valid_token(client):
    with client.session_transaction() as session:
        session['token'] = {'access_token': 'valid-access', 'expires_at': 1100}

    with patch('user_handling.time.time', return_value=1000), \
            patch('api_endpoints.requests.request') as nexus:
        response = client.get('/user/session')
        assert response.get_json() == {'authenticated': True}
        nexus.assert_not_called()


def test_session_status_expired_refresh_token(client):
    with client.session_transaction() as session:
        session['token'] = {
            'access_token': 'old-access',
            'refresh_token': 'old-refresh',
            'expires_at': 1000,
        }

    with patch('user_handling.time.time', return_value=1000), \
            patch('user_handling.requests.post', return_value=Mock(status_code=400)), \
            patch('api_endpoints.requests.request') as nexus:
        response = client.get('/user/session')
        assert response.get_json() == {'authenticated': False}
        nexus.assert_not_called()


def test_nexus_refreshes_expiring_token(client):
    with client.session_transaction() as session:
        session['token'] = {
            'access_token': 'old-access',
            'refresh_token': 'old-refresh',
            'expires_at': 1020,
        }

    refreshed = Mock(status_code=200)
    refreshed.json.return_value = {
        'access_token': 'new-access',
        'refresh_token': 'new-refresh',
        'expires_in': 120,
    }
    upstream = Mock(status_code=200, content=b'{}', headers={'Content-Type': 'application/json'})
    with patch('user_handling.time.time', return_value=1000), \
            patch('user_handling.requests.post', return_value=refreshed) as refresh, \
            patch('api_endpoints.requests.request', return_value=upstream) as nexus:
        assert client.get('/api/home-ressource').status_code == 200
        refresh.assert_called_once()
        assert refresh.call_args.kwargs['data']['grant_type'] == 'refresh_token'
        assert refresh.call_args.kwargs['data']['refresh_token'] == 'old-refresh'
        assert refresh.call_args.kwargs['allow_redirects'] is False
        assert nexus.call_args.kwargs['headers']['Authorization'] == 'Bearer new-access'

    with client.session_transaction() as session:
        assert session['token']['refresh_token'] == 'new-refresh'
        assert session['token']['expires_at'] == 1120


def test_nexus_uses_valid_token_without_refresh(client):
    with client.session_transaction() as session:
        session['token'] = {'access_token': 'valid-access', 'expires_at': 1100}

    upstream = Mock(status_code=200, content=b'{}', headers={})
    with patch('user_handling.time.time', return_value=1000), \
            patch('user_handling.requests.post') as refresh, \
            patch('api_endpoints.requests.request', return_value=upstream) as nexus:
        assert client.get('/api/home-ressource').status_code == 200
        refresh.assert_not_called()
        assert nexus.call_args.kwargs['headers']['Authorization'] == 'Bearer valid-access'


def test_nexus_requires_login_when_refresh_rejected(client):
    with client.session_transaction() as session:
        session['token'] = {
            'access_token': 'old-access',
            'refresh_token': 'old-refresh',
            'expires_at': 1000,
        }

    with patch('user_handling.time.time', return_value=1000), \
            patch('user_handling.requests.post', return_value=Mock(status_code=400)), \
            patch('api_endpoints.requests.request') as nexus:
        assert client.get('/api/home-ressource').status_code == 401
        nexus.assert_not_called()

    with client.session_transaction() as session:
        assert 'token' not in session


def test_nexus_requires_login_without_refresh_token(client):
    with client.session_transaction() as session:
        session['token'] = {'access_token': 'old-access', 'expires_at': 1000}

    with patch('user_handling.time.time', return_value=1000), \
            patch('user_handling.requests.post') as refresh, \
            patch('api_endpoints.requests.request') as nexus:
        assert client.get('/api/home-ressource').status_code == 401
        refresh.assert_not_called()
        nexus.assert_not_called()


def test_nexus_does_not_send_request_on_transient_refresh_failure(client):
    with client.session_transaction() as session:
        session['token'] = {
            'access_token': 'old-access',
            'refresh_token': 'old-refresh',
            'expires_at': 1000,
        }

    with patch('user_handling.time.time', return_value=1000), \
            patch('user_handling.requests.post', return_value=Mock(status_code=503)), \
            patch('api_endpoints.requests.request') as nexus:
        assert client.get('/api/home-ressource').status_code == 502
        nexus.assert_not_called()

    with client.session_transaction() as session:
        assert session['token']['refresh_token'] == 'old-refresh'


def test_concurrent_requests_refresh_once_without_blocking_health(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session['token'] = {
            'access_token': 'old-access',
            'refresh_token': 'old-refresh',
            'expires_at': 1000,
        }
    sid = client.get_cookie('session').value
    other_client = app.test_client()
    with other_client.session_transaction() as session:
        session['token'] = {'access_token': 'other-access', 'expires_at': 1100}
    other_sid = other_client.get_cookie('session').value
    started = Event()
    release = Event()
    refreshed = Mock(status_code=200)
    refreshed.json.return_value = {
        'access_token': 'new-access',
        'refresh_token': 'new-refresh',
        'expires_in': 120,
    }

    def refresh(*args, **kwargs):
        started.set()
        assert release.wait(5)
        return refreshed

    def get_home(session_id):
        with app.test_client() as request_client:
            request_client.set_cookie('session', session_id)
            return request_client.get('/api/home-ressource')

    def get_health():
        with app.test_client() as request_client:
            request_client.set_cookie('session', sid)
            return request_client.get('/healthz')

    upstream = Mock(status_code=200, content=b'{}', headers={})
    with patch('user_handling.time.time', return_value=1000), \
            patch('user_handling.requests.post', side_effect=refresh) as token_request, \
            patch('api_endpoints.requests.request', return_value=upstream) as nexus, \
            ThreadPoolExecutor(max_workers=8) as executor:
        try:
            first = executor.submit(get_home, sid)
            assert started.wait(2)
            contenders = [executor.submit(get_home, sid) for _ in range(7)]
            health = executor.submit(get_health)
            other = executor.submit(get_home, other_sid)
            for contender in contenders:
                busy = contender.result(timeout=2)
                assert busy.status_code == 503
                assert busy.headers['Retry-After'] == '1'
                assert busy.headers['X-Session-Busy'] == '1'
                assert busy.headers['Cache-Control'] == 'no-store'
                assert busy.headers.get('Set-Cookie') is None
            assert health.result(timeout=2).status_code == 200
            assert other.result(timeout=2).status_code == 200
        finally:
            release.set()
        assert first.result(timeout=5).status_code == 200
        assert get_home(sid).status_code == 200

    token_request.assert_called_once()
    auth_headers = [call.kwargs['headers']['Authorization'] for call in nexus.call_args_list]
    assert auth_headers.count('Bearer new-access') == 2
    assert auth_headers.count('Bearer other-access') == 1


def test_concurrent_csrf_requests_share_token(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session['token'] = {'access_token': 'valid-access'}
    sid = client.get_cookie('session').value
    started = Event()
    release = Event()

    def create_token(*args, **kwargs):
        started.set()
        assert release.wait(5)
        return 'one-csrf-token'

    def get_csrf():
        with app.test_client() as request_client:
            request_client.set_cookie('session', sid)
            return request_client.get('/api/csrf')

    with patch('api_endpoints.secrets.token_urlsafe', side_effect=create_token) as generate, \
            ThreadPoolExecutor(max_workers=2) as executor:
        try:
            first = executor.submit(get_csrf)
            assert started.wait(2)
            second = executor.submit(get_csrf)
            assert second.result(timeout=2).status_code == 503
        finally:
            release.set()
        assert first.result(timeout=5).get_json()['token'] == get_csrf().get_json()['token'] == 'one-csrf-token'

    generate.assert_called_once()
