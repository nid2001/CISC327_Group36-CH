from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_socketio import SocketIO, send
from werkzeug.utils import secure_filename
from flask import session
import uuid
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)  # Initialize SocketIO with the Flask app

# Mock database to store user data (In-memory storage for simplicity)
users_db = {
    'landlords': {},
    'tenants': {}
}


# Home route
@app.route('/')
def home():
    return render_template('home.html')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        '''
        # Check if the user exists in either landlord or tenant
        user_type = 'landlords' if username in users_db['landlords'] else 'tenants'
        if username in users_db[user_type] and users_db[user_type][username]['password'] == password:
            session['username'] = username
            session['user_type'] = user_type
            flash(f'Login successful as {user_type[:-1]}!', 'success')
            return redirect(url_for('blank_page'))  # Redirect to blank page after successful login
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
        '''
        return redirect(url_for('index'))  # Redirect to blank page after login
    return render_template('login.html')


# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']  # 'landlord' or 'tenant'

        if username in users_db[user_type + 's']:
            flash('Username already taken', 'error')
            return redirect(url_for('register'))
        else:
            users_db[user_type + 's'][username] = {
                'phone': phone,
                'email': email,
                'password': password
            }
            flash(f'Registration successful as {user_type}!', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')



@app.route('/index')
def index():
    return render_template('index.html')


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('home'))

# Directory to store uploaded files
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')  # Directory where property photos will be stored

# Create the directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# In-memory storage for properties (for demonstration purposes)
properties = []



# Chat route
@app.route('/chat')
def chat():
    return render_template('chat.html')

from werkzeug.utils import secure_filename
import uuid

# My Property route
@app.route('/myproperty')
def myproperty():
    return render_template('myproperty.html', properties=properties)

# Route to handle property addition
@app.route('/add_property', methods=['POST'])
def add_property():
    property_type = request.form['propertyType']
    property_address = request.form['propertyAddress']
    property_zip_code = request.form['propertyZipCode']
    lease_term = request.form['leaseTerm']
    rent_rate = request.form['rentRate']
    property_photos = request.files.getlist('propertyPhotos')
    available_date = request.form['availableDate']

    if property_type and property_address and property_zip_code and lease_term and rent_rate and property_photos and available_date:
        photo_filenames = []

        # Save the photos to the upload folder
        for photo in property_photos:
            if photo and allowed_file(photo.filename):
                # Create a unique filename using UUID
                unique_filename = str(uuid.uuid4()) + "_" + secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                photo_filenames.append(unique_filename)

        # Add property details to the list
        property_id = len(properties)
        properties.append({
            'id': property_id,
            'type': property_type,
            'address': property_address,
            'zip_code': property_zip_code,
            'lease_term': lease_term,
            'rent_rate': rent_rate,
            'available_date': available_date,
            'photos': photo_filenames
        })

        # Flash a success message
        flash("The property has been added successfully.")
        return redirect(url_for('myproperty'))
    else:
        flash("Error: Missing type, address, zip code, lease term, rent rate, photos, or available date.")
        return redirect(url_for('myproperty'))

# Function to check if the uploaded file type is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# Property detail route
@app.route('/property/<int:property_id>')
def property_detail(property_id):
    if 0 <= property_id < len(properties):
        property = properties[property_id]
        return render_template('property_detail.html', property=property)
    else:
        flash("Property not found.")
        return redirect(url_for('myproperty'))

# Route to handle property deletion
@app.route('/delete_property/<int:property_id>', methods=['POST'])
def delete_property(property_id):
    if 0 <= property_id < len(properties):
        # Remove the property from the list
        property = properties.pop(property_id)

        # Delete the associated photos from the upload folder
        for photo in property['photos']:
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo)
            if os.path.exists(photo_path):
                os.remove(photo_path)

        # Flash a success message
        flash("The property has been deleted successfully.")
    else:
        flash("Property not found.")
    return redirect(url_for('myproperty'))

# Report route
@app.route('/report')
def report():
    return render_template('report.html')

# Rent Management route
@app.route('/rentmanagement')
def rentmanagement():
    return render_template('rentmanagement.html')

# Configure the upload folder for PDFs (lease agreements)
app.config['LEASE_UPLOAD_FOLDER'] = os.path.join('static', 'lease')

# Ensure the lease folder exists
if not os.path.exists(app.config['LEASE_UPLOAD_FOLDER']):
    os.makedirs(app.config['LEASE_UPLOAD_FOLDER'])


# Chatbox route
@app.route('/chatbox')
def chatbox():
    return render_template('chatbox.html')

# SocketIO message handling
@socketio.on('message')
def handle_message(msg):
    print('Message: ' + msg)  # Print the message to the console for debugging
    send(msg, broadcast=True)  # Broadcast the message to all connected clients

# Upload route for handling PDF file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400  # Return plain text error

    file = request.files['file']

    if file.filename == '':
        return 'No selected file', 400  # Return plain text error

    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['LEASE_UPLOAD_FOLDER'], filename)
        file.save(file_path)  # Save the PDF to the lease folder
        return 'File successfully uploaded', 200  # Return success as plain text

    return 'Invalid file type. Please upload a PDF.', 400  # Return plain text error


@app.route('/uploaded-files')
def uploaded_files():
    files = os.listdir(app.config['LEASE_UPLOAD_FOLDER'])
    return jsonify(files)




if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
