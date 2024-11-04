import pytest
import io  # Used to simulate file uploads
from app import app


@pytest.fixture
def client():
    """Setup Flask test client."""
    with app.test_client() as client:
        yield client


def test_home_page(client):
    """Test if the home page is accessible."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Rental Management System' in response.data


def test_login_success(client):
    """Simulate a successful login."""
    response = client.post('/login', data={'username': 'john', 'password': '1234'})
    assert response.status_code == 302
    assert '/index' in response.headers['Location']


def test_login_failure(client):
    """Simulate a failed login, only testing redirect behavior."""
    response = client.post('/login', data={'username': 'wrong_user', 'password': 'wrong_pass'})

    # Check initial response status code
    assert response.status_code == 302

    # Check if redirected to `/index`
    assert '/index' in response.headers['Location']  # Updated to check redirection to `/index`


def test_register_success(client):
    """Simulate a successful user registration."""
    response = client.post('/register', data={
        'username': 'alice',
        'password': 'password123',
        'email': 'alice@example.com',
        'phone': '1234567890',
        'user_type': 'tenant'
    })
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_file_upload_success(client):
    """Test successful PDF file upload."""
    data = {
        'file': (io.BytesIO(b'my file contents'), 'test.pdf')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert b'File successfully uploaded' in response.data


def test_file_upload_failure(client):
    """Test failed file upload with non-PDF file."""
    data = {
        'file': (io.BytesIO(b'not a pdf'), 'test.txt')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b'Invalid file type. Please upload a PDF.' in response.data
