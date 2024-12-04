"""
Integration Test Suite for the Rental Management System

This script contains a set of integration tests to verify the end-to-end functionality of the Rental Management System.
The tests include:
- User registration and login.
- Landlord adding a property.
- Tenant viewing properties and sending messages to landlords.

Each test case performs a specific sequence of actions, including making HTTP requests, verifying database state, and managing session variables.
The tests utilize the Flask test client to simulate requests and manage the state.

Author: [Your Name]
Date: [Today's Date]
"""

import unittest
from app import app
import sqlite3

from werkzeug.security import generate_password_hash
from io import BytesIO
import uuid


class RentalManagementIntegrationTest(unittest.TestCase):
    """
    Integration tests for the Rental Management System.

    This class tests the main functionalities of the application, including:
    - User registration and login.
    - Landlord adding properties.
    - Tenant viewing properties and sending messages.

    The tests interact with the Flask application via HTTP requests, using the test client to simulate user actions.
    """

    def setUp(self):
        """
        Set up the test environment.

        This method is called before each test to configure the application for testing.
        It creates a test client to simulate requests to the application.
        """
        app.config['TESTING'] = True
        self.client = app.test_client()

    def generate_unique_data(self):
        """
        Generate a unique identifier for creating distinct test data.

        Returns:
            str: A unique identifier in the form of a UUID.
        """
        unique_id = str(uuid.uuid4())
        return unique_id

    def test_user_registration_and_login(self):
        """
        Test user registration and login process.

        This test registers a new user, verifies the user is added to the database,
        logs in the user, sets session variables, and accesses the user dashboard.
        """
        # Generate unique data
        unique_id = self.generate_unique_data()
        unique_username = f'test_user_{unique_id}'
        unique_email = f'test_user_{unique_id}@example.com'
        unique_phone = f'{uuid.uuid4().int % 10000000000:010d}'

        # Test user registration
        response = self.client.post('/register', data={
            'phone': unique_phone,
            'username': unique_username,
            'email': unique_email,
            'password': 'testpass',
            'user_type': 'tenant'
        }, follow_redirects=True)

        # Verify the user exists in the database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (unique_username,))
        user = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(user)

        # Test user login
        response = self.client.post('/login', data={
            'username': unique_username,
            'password': 'testpass'
        })

        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertTrue(data.get('success'))

        # Manually set session variables
        with self.client.session_transaction() as sess:
            sess['user_id'] = user[0]
            sess['username'] = unique_username
            sess['user_type'] = 'tenant'
            sess['email'] = unique_email
            sess['phone'] = unique_phone

        # Access user dashboard
        response = self.client.get(f'/user_dashboard/{sess["phone"]}')
        self.assertEqual(response.status_code, 200)

        # Clean up test user from database
        self.delete_test_user(unique_username)

    def test_landlord_add_property(self):
        """
        Test landlord registration, login, and adding a property.

        This test registers a new landlord, logs in, and adds a property with simulated file uploads.
        It verifies that the property is successfully added to the database.
        """
        # Generate unique data
        unique_id = self.generate_unique_data()
        unique_username = f'landlord_user_{unique_id}'
        unique_email = f'landlord_user_{unique_id}@example.com'
        unique_phone = f'{uuid.uuid4().int % 10000000000:010d}'

        # Register and log in as landlord
        self.register_user(unique_phone, unique_username, unique_email, 'landlordpass', 'landlord')

        response = self.client.post('/login', data={
            'username': unique_username,
            'password': 'landlordpass'
        })

        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertTrue(data.get('success'))

        # Manually set session variables
        with self.client.session_transaction() as sess:
            sess['user_id'] = data.get('user_id')
            sess['username'] = data.get('username')
            sess['user_type'] = data.get('user_type')
            sess['email'] = data.get('email')
            sess['phone'] = data.get('phone')

        # Add a property with simulated file uploads
        unique_address = f'123 Main St {unique_id}'

        property_data = {
            'propertyType': 'Apartment',
            'propertyAddress': unique_address,
            'propertyZipCode': '12345',
            'leaseTerm': '12 months',
            'rentRate': '1000',
            'availableDate': '2023-12-01',
            'propertyPhotos[]': (BytesIO(b'test image content'), 'test.jpg'),
            'lease': (BytesIO(b'test lease content'), 'lease.pdf')
        }
        response = self.client.post('/add_property', data=property_data, content_type='multipart/form-data')

        # Check for redirect to 'myproperty' page
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/{unique_phone}/myproperty', response.headers['Location'])

        # Verify the property was added to the database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM properties WHERE property_address = ?', (unique_address,))
        property = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(property)

        # Clean up test property and user from database
        self.delete_test_property(unique_address)
        self.delete_test_user(unique_username)

    def test_tenant_view_properties_and_send_message(self):
        """
        Test tenant viewing available properties and sending messages to landlords.

        This test registers a tenant and a landlord, adds a property, allows the tenant to view the property,
        and sends a message to the landlord. It verifies that the message is stored in the database.
        """
        # Generate unique data
        unique_id = self.generate_unique_data()
        tenant_username = f'tenant_user_{unique_id}'
        tenant_email = f'tenant_user_{unique_id}@example.com'
        tenant_phone = f'{uuid.uuid4().int % 10000000000:010d}'

        # Register and log in as tenant
        self.register_user(tenant_phone, tenant_username, tenant_email, 'tenantpass', 'tenant')

        response = self.client.post('/login', data={
            'username': tenant_username,
            'password': 'tenantpass'
        })

        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertTrue(data.get('success'))

        # Manually set session variables
        with self.client.session_transaction() as sess:
            sess['user_id'] = data.get('user_id')
            sess['username'] = data.get('username')
            sess['user_type'] = data.get('user_type')
            sess['email'] = data.get('email')
            sess['phone'] = data.get('phone')

        # Ensure there is a property to view
        unique_address = f'456 Elm St {unique_id}'
        landlord_username = f'landlord_user_{unique_id}'
        landlord_email = f'landlord_user_{unique_id}@example.com'
        landlord_phone = f'{uuid.uuid4().int % 10000000000:010d}'

        # Register landlord and add property
        self.register_user(landlord_phone, landlord_username, landlord_email, 'landlordpass', 'landlord')
        self.add_property(landlord_phone, unique_address)

        # Tenant views available properties
        response = self.client.get(f'/{tenant_phone}/rentnow_t')
        self.assertEqual(response.status_code, 200)
        self.assertIn(unique_address.encode(), response.data)

        # Get property ID
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM properties WHERE property_address = ?', (unique_address,))
        property_row = cursor.fetchone()
        conn.close()
        property_id = property_row[0]

        # Tenant views property details
        response = self.client.get(f'/{tenant_phone}/property_t/{property_id}')
        self.assertIn(unique_address.encode(), response.data)

        # Tenant sends a message to landlord
        response = self.client.post(f'/send_message/{property_id}', data={
            'message': 'I am interested in this property.'
        })

        # Check for redirect after sending message
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/{tenant_phone}/property_t/{property_id}', response.headers['Location'])

        # Verify the message is stored in the database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM messages WHERE tenant_phone = ? AND property_id = ?',
                       (tenant_phone, property_id))
        message = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(message)
        self.assertEqual(message[4], 'I am interested in this property.')

        # Clean up test data
        self.delete_test_message(message[0])
        self.delete_test_property(unique_address)
        self.delete_test_user(tenant_username)
        self.delete_test_user(landlord_username)

    # Helper methods to register users, add properties, and clean up test data

    def register_user(self, phone, username, email, password, user_type):
        """
        Register a user in the database.

        Args:
            phone (str): The user's phone number.
            username (str): The user's username.
            email (str): The user's email address.
            password (str): The user's password.
            user_type (str): The type of user ('tenant' or 'landlord').
        """
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        hashed_password = generate_password_hash(password)
        try:
            cursor.execute('''
                INSERT INTO users (phone, username, email, password, user_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (phone, username, email, hashed_password, user_type))
            conn.commit()
        except sqlite3.IntegrityError as e:
            self.fail(f'Failed to register user: {e}')
        finally:
            conn.close()

    def add_property(self, landlord_phone, property_address):
        """
        Add a property to the database.

        Args:
            landlord_phone (str): The landlord's phone number.
            property_address (str): The address of the property to add.
        """
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO properties (landlord_phone, property_type, property_address, 
                                        property_zip_code, lease_term, rent_rate, 
                                        available_date, available_status, lease_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (landlord_phone, 'Apartment', property_address, '67890', '6 months', '800',
                  '2023-11-01', 'yes', 'no'))
            conn.commit()
        except sqlite3.IntegrityError as e:
            self.fail(f'Failed to add property: {e}')
        finally:
            conn.close()

    def delete_test_user(self, username):
        """
        Delete a test user from the database.

        Args:
            username (str): The username of the user to delete.
        """
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
        conn.close()

    def delete_test_property(self, property_address):
        """
        Delete a test property from the database.

        Args:
            property_address (str): The address of the property to delete.
        """
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM properties WHERE property_address = ?', (property_address,))
        conn.commit()
        conn.close()

    def delete_test_message(self, message_id):
        """
        Delete a test message from the database.

        Args:
            message_id (int): The ID of the message to delete.
        """
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
        conn.commit()
        conn.close()


if __name__ == '__main__':
    unittest.main()
