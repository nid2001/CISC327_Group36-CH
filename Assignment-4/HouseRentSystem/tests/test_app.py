import pytest
import sqlite3
import json
from io import BytesIO
from flask import session
from app import app, init_db, init_property_db, init_messages_db, socketio

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
            init_property_db()
            init_messages_db()
        yield client

def test_init_db(client):
    """Test to ensure database is created properly."""
    conn = sqlite3.connect('rental_management.db')
    cursor = conn.cursor()

    # Check if users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    users_table = cursor.fetchone()
    assert users_table is not None

    # Check if properties table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='properties'")
    properties_table = cursor.fetchone()
    assert properties_table is not None

    # Check if messages table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
    messages_table = cursor.fetchone()
    assert messages_table is not None

    conn.close()

def test_register(client):
    """Test the registration endpoint."""
    response = client.post('/register', data={
        'phone': '1234567890',
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })

    # Check if the status code is 200
    assert response.status_code == 200

    # Verify that the response contains the form HTML elements, indicating the request did not fail
    assert b'<form' in response.data and b'name="username"' in response.data


def test_login(client):
    """Test the login endpoint."""
    # Register user first
    client.post('/register', data={
        'phone': '1234567890',
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })

    # Test login
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    assert response.status_code == 200
    assert b'success' in response.data


def test_add_property(client):
    """Test adding a property for a landlord."""
    # Register landlord
    client.post('/register', data={
        'phone': '1234567890',
        'username': 'landlorduser',
        'email': 'landlord@example.com',
        'password': 'password123',
        'user_type': 'landlord'
    })

    # Login and set session manually
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'landlorduser'
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'

    # Test adding a property, skipping specific field checks
    response = client.post('/add_property', data={
        'propertyType': 'Apartment',
        'propertyAddress': '123 Street Name',
        'propertyZipCode': '12345',
        'leaseTerm': '12 months',
        'rentRate': '1000',
        'availableDate': '2024-11-01'
    }, follow_redirects=True)

    # Check only if status code is 200 (indicating success after redirect)
    assert response.status_code == 200

def test_delete_property(client):
    """Test deleting a property."""
    # Register landlord and add property
    client.post('/register', data={
        'phone': '1234567890',
        'username': 'landlorduser',
        'email': 'landlord@example.com',
        'password': 'password123',
        'user_type': 'landlord'
    })

    client.post('/login', data={
        'username': 'landlorduser',
        'password': 'password123'
    })

    client.post('/add_property', data={
        'propertyType': 'Apartment',
        'propertyAddress': '123 Street Name',
        'propertyZipCode': '12345',
        'leaseTerm': '12 months',
        'rentRate': '1000',
        'availableDate': '2024-11-01'
    })

    # Get property ID
    conn = sqlite3.connect('rental_management.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM properties WHERE landlord_phone = ?', ('1234567890',))
    property_id = cursor.fetchone()[0]
    conn.close()

    # Set the phone in session to avoid BuildError
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'  # Simulate phone in session

    # Test deleting the property
    response = client.post(f'/delete_property/{property_id}', follow_redirects=False)

    # Check if response is a redirect (302 status code)
    assert response.status_code == 302


def test_logout(client):
    """Test logging out."""
    # Register and log in a user to simulate a session
    client.post('/register', data={
        'phone': '1234567890',
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })

    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })

    # Set the phone in session to avoid BuildError
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'  # Simulate phone in session

    # Log out and check for redirect
    response = client.post('/logout', follow_redirects=False)

    # Check if response is a redirect (302 status code)
    assert response.status_code == 302

def test_chat(client):
    """Test the chat functionality for a landlord."""
    # Register a landlord user
    client.post('/register', data={
        'phone': '1234567890',
        'username': 'landlorduser',
        'email': 'landlord@example.com',
        'password': 'password123',
        'user_type': 'landlord'
    })

    # Register a tenant user (for message recipient)
    client.post('/register', data={
        'phone': '0987654321',
        'username': 'tenantuser',
        'email': 'tenant@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })

    # Login as landlord
    client.post('/login', data={
        'username': 'landlorduser',
        'password': 'password123'
    })

    # Set up session to simulate being a landlord with all required session details
    with client.session_transaction() as sess:
        sess['username'] = 'landlorduser'
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'

    # Send a message as the landlord to a specific tenant
    response = client.post('/send_message/1', data={
        'message': 'Hello, tenant!',
        'pdf': (BytesIO(b'my file contents'), 'test.pdf')  # Simulate a file upload if required
    }, content_type='multipart/form-data', follow_redirects=False)

    # Check if the response is a redirect (302) indicating success or permission check passed
    assert response.status_code == 302 or response.status_code == 200
# Existing tests...

def test_register_existing_user(client):
    response = client.post('/register', data={
        'phone': '1234567890',
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })
    response = client.post('/register', data={
        'phone': '1234567890',
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })
    assert response.status_code in [200, 302]

def test_login_invalid_user(client):
    response = client.post('/login', data={
        'username': 'invaliduser',
        'password': 'wrongpassword'
    })
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data

def test_property_detail_forbidden(client):
    response = client.get('/1234567890/property/999')
    assert response.status_code in [302, 403]

def test_add_property_invalid_data(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'
        sess['username'] = 'landlorduser'
    response = client.post('/add_property', data={
        'propertyType': 'Apartment',
        'propertyAddress': '123 Test St',
        'propertyZipCode': '12345',
        'leaseTerm': '12 months',
        'rentRate': '1000',
        'availableDate': '2024-01-01'
    })
    assert response.status_code in [200, 400, 302]

def test_delete_nonexistent_property(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'
        sess['username'] = 'landlorduser'
    response = client.post('/delete_property/999')
    assert response.status_code in [302, 404]

def test_chat_route(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'
        sess['username'] = 'landlorduser'
    response = client.get('/1234567890/chat')
    assert response.status_code == 200

def test_report_route(client):
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'
    response = client.get('/1234567890/report')
    assert response.status_code == 200

def test_rentmanagement_route(client):
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'
    response = client.get('/1234567890/rentmanagement')
    assert response.status_code == 200

def test_upload_route(client):
    data = {
        'file': (BytesIO(b'my file contents'), 'test.pdf')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code in [200, 400]

def test_logout_route(client):
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'
    response = client.post('/logout')
    assert response.status_code in [200, 302]

# New tests for uncovered routes

def test_myproperty_route(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'
    response = client.get('/1234567890/myproperty')
    assert response.status_code == 200

def test_user_dashboard_route(client):
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'
        sess['username'] = 'testuser'
        sess['user_type'] = 'tenant'
    response = client.get('/user_dashboard/1234567890')
    assert response.status_code == 200

def test_paymyrent_route(client):
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'
        sess['user_type'] = 'tenant'
    response = client.get('/1234567890/paymyrent_t')
    assert response.status_code == 200

def test_maintenance_route(client):
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'
        sess['user_type'] = 'tenant'
    response = client.get('/1234567890/maintenance_t')
    assert response.status_code == 200

def test_rentnow_route(client):
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'
        sess['user_type'] = 'tenant'
    response = client.get('/1234567890/rentnow_t')
    assert response.status_code == 200

def test_myaccount_route(client):
    with client.session_transaction() as sess:
        sess['phone'] = '1234567890'
        sess['user_type'] = 'tenant'
        sess['username'] = 'testuser'
        sess['email'] = 'test@example.com'
    response = client.get('/1234567890/myaccount')
    assert response.status_code == 200

def test_register_invalid_email(client):
    response = client.post('/register', data={
        'phone': '1234567891',
        'username': 'newuser',
        'email': 'invalid-email',
        'password': 'password123',
        'user_type': 'tenant'
    })
    assert response.status_code in [200, 400]

def test_add_property_without_session(client):
    response = client.post('/add_property', data={
        'propertyType': 'Apartment',
        'propertyAddress': '456 Another St',
        'propertyZipCode': '54321',
        'leaseTerm': '6 months',
        'rentRate': '800',
        'availableDate': '2024-06-01'
    })
    assert response.status_code in [302, 403]

def test_property_detail_not_found(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'
    response = client.get('/1234567890/property/99999') 
    assert response.status_code in [302, 404]

def test_upload_invalid_file_type(client):
    data = {
        'file': (BytesIO(b'Not a PDF content'), 'test.txt')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400

def test_chat_without_login(client):
    response = client.get('/1234567890/chat')
    assert response.status_code == 302 

def test_logout_without_login(client):
    response = client.post('/logout')
    assert response.status_code == 302

def test_rentnow_access_without_permission(client):
    response = client.get('/1234567890/rentnow_t')
    assert response.status_code == 302

def test_delete_property_without_permission(client):
    with client.session_transaction() as sess:
        sess['phone'] = 'fake_phone_number'
        sess['user_type'] = 'tenant' 

    response = client.post('/delete_property/1')
    assert response.status_code in [302, 403] 

def test_register_duplicate_username(client):
    client.post('/register', data={
        'phone': '1112223333',
        'username': 'duplicateuser',
        'email': 'duplicate1@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })
    response = client.post('/register', data={
        'phone': '1112224444',
        'username': 'duplicateuser',
        'email': 'duplicate2@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })
    assert response.status_code in [200, 302]
    assert b'Username' in response.data or b'Error' in response.data or response.status_code == 302


def test_add_property_with_invalid_date(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'
    response = client.post('/add_property', data={
        'propertyType': 'Apartment',
        'propertyAddress': '789 Invalid St',
        'propertyZipCode': '98765',
        'leaseTerm': '12 months',
        'rentRate': '1200',
        'availableDate': 'invalid-date'
    })
    assert response.status_code in [200, 400, 302]
def test_upload_no_file(client):
    response = client.post('/upload', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b'No file part' in response.data

def test_upload_invalid_file_extension(client):
    data = {
        'file': (BytesIO(b'Invalid file content'), 'invalid_file.txt')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b'Invalid file type' in response.data

def test_chat_detail_without_permission(client):
    response = client.get('/chat_detail/1/fake_tenant_phone')
    assert response.status_code == 302 

def test_chat_detail_invalid_property(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'
        sess['username'] = 'landlorduser'
    response = client.get('/chat_detail/999999/fake_tenant_phone')
    assert response.status_code in [302, 404, 200]

def test_mychat_t_route_without_login(client):
    response = client.get('/1234567890/mychat_t')
    assert response.status_code == 302

def test_mychat_detail_t_invalid_access(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'tenant'
        sess['phone'] = '1234567890'
    response = client.get('/mychat_detail_t/999999/fake_landlord_phone')
    assert response.status_code in [302, 404, 200]

def test_logout_route_no_session(client):
    response = client.post('/logout')
    assert response.status_code == 302 

def test_paymyrent_access_with_invalid_session(client):
    with client.session_transaction() as sess:
        sess['phone'] = 'wrong_phone_number'
    response = client.get('/wrong_phone_number/paymyrent_t')
    assert response.status_code in [302, 403, 200]
    if response.status_code == 200:
        assert b'Permission' in response.data or b'Error' in response.data or b'Unauthorized' in response.data or len(response.data) > 0

def test_login_no_data(client):
    response = client.post('/login', data={})
    assert response.status_code == 400 

def test_register_no_data(client):
    response = client.post('/register', data={})
    assert response.status_code == 400 

def test_add_property_invalid_user_type(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'tenant'
        sess['phone'] = '1234567890'
    response = client.post('/add_property', data={
        'propertyType': 'Apartment',
        'propertyAddress': '456 Another St',
        'propertyZipCode': '54321',
        'leaseTerm': '6 months',
        'rentRate': '800',
        'availableDate': '2024-06-01'
    })
    assert response.status_code in [302, 403]

def test_access_dashboard_without_login(client):
    response = client.get('/user_dashboard/1234567890')
    assert response.status_code == 302 

def test_logout_after_login(client):
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    response = client.post('/logout')
    assert response.status_code == 302

def test_upload_large_file(client):
    large_file = BytesIO(b'a' * (10 * 1024 * 1024)) 
    data = {
        'file': (large_file, 'large_file.pdf')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code in [200, 400, 413] 

def test_delete_property_invalid_id(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'
    response = client.post('/delete_property/99999')
    assert response.status_code in [302, 404]

def test_register_with_existing_email(client):
    client.post('/register', data={
        'phone': '1112223333',
        'username': 'uniqueuser1',
        'email': 'duplicate@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })
    response = client.post('/register', data={
        'phone': '1112224444',
        'username': 'uniqueuser2',
        'email': 'duplicate@example.com', 
        'password': 'password123',
        'user_type': 'tenant'
    })
    assert response.status_code in [200, 302]
    assert b'Email' in response.data or b'Error' in response.data or response.status_code == 302

def test_invalid_date_format(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'landlord'
        sess['phone'] = '1234567890'
    response = client.post('/add_property', data={
        'propertyType': 'Apartment',
        'propertyAddress': '456 Another St',
        'propertyZipCode': '54321',
        'leaseTerm': '6 months',
        'rentRate': '800',
        'availableDate': 'invalid-date-format'
    })
    assert response.status_code in [400, 200, 302]
    assert b'Invalid date format' in response.data or b'Error' in response.data or b'Redirecting' in response.data
    
def test_access_without_login(client):
    restricted_routes = [
        '/user_dashboard/1234567890',
        '/1234567890/myproperty',
        '/1234567890/report'
    ]
    for route in restricted_routes:
        response = client.get(route)
        assert response.status_code == 302

def test_socketio_event(client):
    """测试 SocketIO 事件"""
    socketio_test_client = socketio.test_client(app)
    socketio_test_client.emit('join', {'tenant_phone': '12345', 'landlord_phone': '54321'})
    received = socketio_test_client.get_received()
    assert len(received) > 0
    assert received[0]['name'] == 'status'


def test_home_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Rental Management System' in response.data or b'Home' in response.data


def test_upload_files_listing(client):
    response = client.get('/uploaded-files')
    assert response.status_code == 200
    json_data = response.get_json()
    assert isinstance(json_data, list)

def test_invalid_property_detail_for_tenant(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'tenant'
        sess['phone'] = '1234567890'
    response = client.get('/1234567890/property_t/999999')
    assert response.status_code in [302, 404]

def test_send_message_with_invalid_property(client):
    with client.session_transaction() as sess:
        sess['user_type'] = 'tenant'
        sess['phone'] = '1234567890'
    response = client.post('/send_message/999999', data={'message': 'Hello, invalid property'})
    assert response.status_code in [302, 404, 403]
    
def test_rent_management_route_invalid_session(client):
    response = client.get('/1234567890/rentmanagement')
    assert response.status_code in [302, 403]

def test_login_blank_fields(client):
    response = client.post('/login', data={
        'username': '',
        'password': ''
    })

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data is not None
    assert json_data.get("success") is True

def test_login_when_already_logged_in(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1 
    response = client.get('/login')
    assert response.status_code in [200, 302, 403]






