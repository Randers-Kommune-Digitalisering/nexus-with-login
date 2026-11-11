import pytest
from unittest.mock import Mock, patch
from main import create_app


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
