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
    assert b'Home' in response.data  # Assuming the page contains the text "Home"

def test_login_success(client):
    """Simulate a successful login."""
    # Configure mock database with a sample user
    app.config['users_db'] = {
        'landlords': {'john': {'password': '1234'}},
        'tenants': {}
    }
    response = client.post('/login', data={'username': 'john', 'password': '1234'})
    assert response.status_code == 302  # Expect a redirect
    assert '/blank_page' in response.headers['Location']  # Check redirect target

def test_login_failure(client):
    """Simulate a failed login attempt."""
    response = client.post('/login', data={'username': 'wrong_user', 'password': 'wrong_pass'})
    assert response.status_code == 302  # Expect a redirect
    assert b'Invalid username or password' in response.data  # Verify error message

def test_register_success(client):
    """Simulate a successful user registration."""
    response = client.post('/register', data={
        'username': 'alice',
        'password': 'password123',
        'email': 'alice@example.com',
        'phone': '1234567890',
        'user_type': 'tenant'
    })
    assert response.status_code == 302  # Expect a redirect after registration

def test_file_upload_success(client):
    """Test successful PDF file upload."""
    data = {
        'file': (io.BytesIO(b'my file contents'), 'test.pdf')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200  # Upload should succeed
    assert b'File successfully uploaded' in response.data  # Verify success message

def test_file_upload_failure(client):
    """Test failed file upload with non-PDF file."""
    data = {
        'file': (io.BytesIO(b'not a pdf'), 'test.txt')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400  # Upload should fail
    assert b'Invalid file type. Please upload a PDF.' in response.data  # Verify error message
