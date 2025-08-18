import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'図書館' in response.data  # Default library name

def test_get_location_by_serial(client):
    response = client.get('/api/get_location_by_serial')
    assert response.status_code == 200
    assert 'location' in response.get_json()

def test_check_lent_status(client):
    response = client.get('/api/check_lent_status')
    assert response.status_code == 200

def test_check_administrator_exists(client):
    gid = 'test_gid'
    response = client.get(f'/api/check_administrator_exists/{gid}')
    assert response.status_code == 200

def test_check_user_exists(client):
    gid = 'test_gid'
    response = client.get(f'/api/check_user_exists/{gid}')
    assert response.status_code == 200

def test_api_get_locations(client):
    response = client.get('/api/locations')
    assert response.status_code == 200
    assert 'locations' in response.get_json()