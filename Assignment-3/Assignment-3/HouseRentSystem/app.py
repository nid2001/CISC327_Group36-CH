from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_socketio import SocketIO, send
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import uuid
import os
from flask_socketio import SocketIO, emit, join_room


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)


# Database setup
def init_db():
    conn = sqlite3.connect('rental_management.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            user_type TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def init_property_db():
    conn = sqlite3.connect('rental_management.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            landlord_phone TEXT NOT NULL,
            property_type TEXT NOT NULL,
            property_address TEXT NOT NULL,
            property_zip_code TEXT NOT NULL,
            lease_term TEXT NOT NULL,
            rent_rate TEXT NOT NULL,
            available_date TEXT NOT NULL,
            photos TEXT,
            tenant_phone TEXT,
            available_status TEXT NOT NULL,
            lease TEXT ,
            lease_status TEXT NOT NULL,
            original_lease_filename TEXT
        )
    ''')
    conn.commit()
    conn.close()

def init_messages_db():
    conn = sqlite3.connect('rental_management.db')
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys in SQLite
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER,
            tenant_phone TEXT,
            landlord_phone TEXT,
            message TEXT,
            sender TEXT NOT NULL,
            receiver TEXT,
            pdf_filename TEXT,  -- Column to store the PDF file path
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (property_id) REFERENCES properties(id)
        )
    ''')
    conn.commit()
    conn.close()


# Initialize both tables
init_db()  # Initialize users table
init_property_db()  # Initialize properties table
init_messages_db()

app.config['UPLOAD_FOLDER'] = 'static/uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# Home route
@app.route('/')
def home():
    return render_template('home.html')


# Login route with JSON response for AJAX handling
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Fetch user from database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[4], password):  # Password is in the 5th column (index 4)
            session['user_id'] = user[0]
            session['username'] = user[2]
            session['user_type'] = user[5]
            session ['email'] = user[3]
            session['phone'] = user[1]  # Save the user's phone number in the session

            return jsonify({'success': True, 'phone': user[1], 'username': user[2],
                            'user_type': user[5],'email':user[3]})  # JSON response on successful login
        else:
            return jsonify(
                {'success': False, 'message': 'Invalid username or password'})  # JSON response on failed login

    return render_template('login.html')


# User-specific dashboard route based on phone number
@app.route('/user_dashboard/<phone>')
def user_dashboard(phone):
    # Check if the phone number matches the logged-in user's phone
    if 'phone' in session and session['phone'] == phone:
        username = session.get('username')
        user_type = session.get('user_type')

        if user_type == 'landlord':
            return render_template('index.html', username=username, phone=phone)
        elif user_type == 'tenant':
            return render_template('Tenant/index_t.html', username=username, phone=phone)
    else:
        flash('Access denied or session expired. Please log in again.', 'error')
        return redirect(url_for('login'))



# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']  # 'landlord' or 'tenant'

        hashed_password = generate_password_hash(password)

        # Connect to database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email is already registered. Please use a different email.', 'error')
            conn.close()
            return redirect(url_for('register'))

        # Insert user into the database if email is not already registered
        try:
            cursor.execute('''
                INSERT INTO users (phone, username, email, password, user_type) 
                VALUES (?, ?, ?, ?, ?)
            ''', (phone, username, email, hashed_password, user_type))
            conn.commit()
            flash(f'Registration successful as {user_type}!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different username.', 'error')
        finally:
            conn.close()

    return render_template('register.html')


# Logout route
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('home'))






# My Property route (Landlord only)
@app.route('/<phone>/myproperty')
def myproperty(phone):
    if 'user_type' in session and session['user_type'] == 'landlord' and session.get('phone') == phone:
        # Fetch properties belonging to the logged-in landlord from the database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM properties WHERE landlord_phone = ?', (phone,))
        properties = cursor.fetchall()
        conn.close()

        # Convert properties to a list of dictionaries
        property_list = [
            {
                'id': property[0],
                'property_type': property[2],
                'property_address': property[3],
                'property_zip_code': property[4],
                'lease_term': property[5],
                'rent_rate': property[6],
                'available_date': property[7],
                'photos': property[8].split(',') if property[8] else []
            } for property in properties
        ]

        return render_template('myproperty.html', phone=phone, properties=property_list)
    else:
        flash('Access denied. This page is for landlords only.', 'error')
        return redirect(url_for('home'))



@app.route('/add_property', methods=['POST'])
def add_property():
    if 'user_type' in session and session['user_type'] == 'landlord':
        # Gather form data
        property_type = request.form.get('propertyType')
        property_address = request.form.get('propertyAddress')
        property_zip_code = request.form.get('propertyZipCode')
        lease_term = request.form.get('leaseTerm')
        rent_rate = request.form.get('rentRate')
        available_date = request.form.get('availableDate')
        landlord_phone = session.get('phone')

        # Default values for new properties
        available_status = "yes"
        lease_status = "no"

        # Process uploaded photos
        property_photos = request.files.getlist('propertyPhotos[]')
        photo_filenames = []
        for photo in property_photos:
            if photo and allowed_file(photo.filename):
                unique_filename = str(uuid.uuid4()) + "_" + secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                photo_filenames.append(unique_filename)
        photo_filenames_str = ",".join(photo_filenames)

        # Process lease file
        lease_file = request.files.get('lease')
        lease_filename = None
        original_lease_filename = None
        if lease_file and allowed_file(lease_file.filename):
            original_lease_filename = lease_file.filename  # Store the original filename
            lease_filename = str(uuid.uuid4()) + "_" + secure_filename(lease_file.filename)
            lease_file.save(os.path.join(app.config['LEASE_UPLOAD_FOLDER'], lease_filename))
            print("Saved lease filename:", lease_filename)  # Debugging
            print("Original lease filename:", original_lease_filename)  # Debugging

        # Insert property details into the database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO properties (landlord_phone, property_type, property_address, 
                                    property_zip_code, lease_term, rent_rate, 
                                    available_date, photos, available_status, lease,  lease_status, original_lease_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (landlord_phone, property_type, property_address, property_zip_code,
              lease_term, rent_rate, available_date, photo_filenames_str, available_status, lease_filename,
              original_lease_filename, lease_status))

        conn.commit()
        conn.close()

        flash("The property has been added successfully.")
        return redirect(url_for('myproperty', phone=landlord_phone))
    else:
        flash('Access denied. Only landlords can add properties.', 'error')
        return redirect(url_for('home'))




# Function to check if the uploaded file type is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif','pdf'}


@app.route('/<phone>/property/<int:property_id>')
def property_detail(phone, property_id):
    if 'user_type' in session and session['user_type'] == 'landlord' and session.get('phone') == phone:
        # Fetch the property details from the database and ensure it belongs to the landlord with this phone number
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM properties WHERE id = ? AND landlord_phone = ?', (property_id, phone))
        property = cursor.fetchone()
        conn.close()

        if property:
            property_dict = {
                'id': property[0],
                'landlord_phone': property[1],
                'property_type': property[2],
                'property_address': property[3],
                'property_zip_code': property[4],
                'lease_term': property[5],
                'rent_rate': property[6],
                'available_date': property[7],
                'photos': property[8].split(',') if property[8] else [],
                'available_status': property[10],
                'lease': property[11],
                'original_lease_filename':property[12]


            }
            return render_template('property_detail.html', property=property_dict)
        else:
            flash("Property not found or access denied.")
            return redirect(url_for('myproperty', phone=phone))
    else:
        flash('Access denied. This page is for landlords only.', 'error')
        return redirect(url_for('home'))



@app.route('/delete_property/<int:property_id>', methods=['POST'])
def delete_property(property_id):
    if 'user_type' in session and session['user_type'] == 'landlord':
        landlord_phone = session.get('phone')

        # Fetch the property from the database and ensure it belongs to the logged-in landlord
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM properties WHERE id = ? AND landlord_phone = ?', (property_id, landlord_phone))
        property = cursor.fetchone()

        if property:
            # Delete property photos from the upload folder
            if property[8]:  # Photos are stored in the 8th column (index 7)
                photo_filenames = property[8].split(',')
                for photo in photo_filenames:
                    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo)
                    if os.path.exists(photo_path):
                        os.remove(photo_path)

            # Delete lease PDF from the upload folder if it exists
                if property[11]:  # Assuming the lease PDF is stored in the 11th column (index 10)
                    lease_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], property[11])
                    if os.path.exists(lease_pdf_path):
                        os.remove(lease_pdf_path)

            # Delete the property from the database
            cursor.execute('DELETE FROM properties WHERE id = ?', (property_id,))
            conn.commit()
            flash("The property has been deleted successfully.")
        else:
            flash("Property not found or access denied.")

        conn.close()
    else:
        flash('Access denied. Only landlords can delete properties.', 'error')

    return redirect(url_for('myproperty', phone=session.get('phone')))


# Report route
@app.route('/<phone>/report')
def report(phone):
    if 'phone' in session and session['phone'] == phone:
        return render_template('report.html', phone=phone)
    else:
        flash('Unauthorized access or session expired.', 'error')
        return redirect(url_for('login'))


# Rent Management route
@app.route('/<phone>/rentmanagement')
def rentmanagement(phone):
    if 'phone' in session and session['phone'] == phone:

        return render_template('rentmanagement.html', phone=phone)
    else:
        flash('Unauthorized access or session expired.', 'error')
        return redirect(url_for('login'))





# Chat route
@app.route('/<phone>/chat')
def chat(phone):
    if 'user_type' in session and session['user_type'] == 'landlord' and session['phone'] == phone:
        # Retrieve unique conversations where the landlord has replied
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT property_id, tenant_phone
            FROM messages
            WHERE landlord_phone = ? AND sender = ?
            ORDER BY timestamp DESC
        ''', (phone, session['username']))

        active_chats = [
            {
                'property_id': row[0],
                'tenant_phone': row[1]
            }
            for row in cursor.fetchall()
        ]

        # Retrieve all messages for properties owned by this landlord (for display under messages section)
        cursor.execute('''
            SELECT property_id, tenant_phone, message, pdf_filename, timestamp 
            FROM messages 
            WHERE landlord_phone = ?
            ORDER BY timestamp DESC
        ''', (phone,))
        messages = [
            {
                'property_id': row[0],
                'tenant_phone': row[1],
                'message': row[2],
                'pdf_filename': row[3],
                'timestamp': row[4]
            }
            for row in cursor.fetchall()
        ]

        conn.close()

        # Render template with both active chats and all messages
        return render_template('chat.html', active_chats=active_chats, messages=messages, phone=phone)
    else:
        flash('Access denied. This page is for landlords only.', 'error')
        return redirect(url_for('home'))


@app.route('/chat_detail/<int:property_id>/<tenant_phone>', methods=['GET'])
def chat_detail(property_id, tenant_phone):
    if 'user_type' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for('login'))

    landlord_phone = session.get('phone')
    user_type = session.get('user_type')
    sender = session.get('username')

    # Determine the other participant (the person the user is chatting with)
    other_participant = tenant_phone if user_type == 'landlord' else landlord_phone

    # Retrieve conversation history for a specific property and tenant
    with sqlite3.connect('rental_management.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tenant_phone, landlord_phone, message, sender, pdf_filename, timestamp 
            FROM messages 
            WHERE property_id = ? AND ((landlord_phone = ? AND tenant_phone = ?) OR (landlord_phone = ? AND tenant_phone = ?))
            ORDER BY timestamp DESC
        ''', (property_id, landlord_phone, tenant_phone, tenant_phone, landlord_phone))
        chat_history = [
            {
                'tenant_phone': row[0],
                'landlord_phone': row[1],
                'message': row[2],
                'sender': row[3],
                'pdf_filename': row[4],
                'timestamp': row[5]
            }
            for row in cursor.fetchall()
        ]

    return render_template('chat_detail.html', chat_history=chat_history, tenant_phone=tenant_phone,
                           property_id=property_id, sender= sender, other_participant=other_participant)


@socketio.on('join')
def on_join(data):
    tenant_phone = data['tenant_phone']
    landlord_phone = data['landlord_phone']
    property_id = data.get('property_id')  # Use .get() to avoid KeyError if missing
    room = f"{landlord_phone}_{tenant_phone}_{property_id}" if property_id else f"{landlord_phone}_{tenant_phone}"
    join_room(room)
    emit('status', {'msg': 'User has entered the chat'}, room=room)


@socketio.on('send_message')
def handle_send_message(data):
    tenant_phone = data['tenant_phone']
    landlord_phone = data['landlord_phone']
    message = data['message']
    sender = session.get('username')  # The sender should be specified in the emitted data
    room = f"{landlord_phone}_{tenant_phone}_{data['property_id']}"






    # Save the message to the database
    with sqlite3.connect('rental_management.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (property_id, tenant_phone, landlord_phone, message, sender,  pdf_filename)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['property_id'], tenant_phone, landlord_phone, message, sender, None))
        conn.commit()

    # Broadcast the message to the room
    emit('receive_message', {
        'tenant_phone': tenant_phone,
        'landlord_phone': landlord_phone,
        'message': message,
        'sender': sender,  # Include the sender in the emitted data
        'timestamp': 'just now'
    }, room=room)



# Configure the upload folder for PDFs
app.config['LEASE_UPLOAD_FOLDER'] = os.path.join('static', 'lease')
if not os.path.exists(app.config['LEASE_UPLOAD_FOLDER']):
    os.makedirs(app.config['LEASE_UPLOAD_FOLDER'])


# Tenant Chat route
@app.route('/<phone>/mychat_t')
def mychat_t(phone):
    if 'user_type' in session and session['user_type'] == 'tenant' and session['phone'] == phone:
        # Retrieve unique conversations where the landlord has replied
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT property_id, landlord_phone
            FROM messages
            WHERE tenant_phone = ? AND sender = ?
            ORDER BY timestamp DESC
        ''', (phone, session['username']))

        active_chats = [
            {
                'property_id': row[0],
                'landlord_phone': row[1]
            }
            for row in cursor.fetchall()
        ]

        # Retrieve all messages for properties owned by this landlord (for display under messages section)
        cursor.execute('''
            SELECT property_id, tenant_phone, message, pdf_filename, timestamp 
            FROM messages 
            WHERE tenant_phone = ?
            ORDER BY timestamp DESC
        ''', (phone,))
        messages = [
            {
                'property_id': row[0],
                'tenant_phone': row[1],
                'message': row[2],
                'pdf_filename': row[3],
                'timestamp': row[4]
            }
            for row in cursor.fetchall()
        ]

        conn.close()

        # Render template with both active chats and all messages
        return render_template('Tenant/mychat_t.html', active_chats=active_chats, messages=messages, phone=phone)
    else:
        flash('Access denied. This page is for landlords only.', 'error')
        return redirect(url_for('home'))

@app.route('/mychat_detail_t/<int:property_id>/<landlord_phone>', methods=['GET'])
def mychat_detail_t(property_id, landlord_phone):
    if 'user_type' not in session:
        flash("Please log in to access this page.", "error")
        return redirect(url_for('login'))

    tenant_phone = session.get('phone')
    user_type = session.get('user_type')
    sender = session.get('username')

    # Determine the other participant (the person the user is chatting with)
    other_participant = landlord_phone if user_type == 'tenant' else tenant_phone

    # Retrieve conversation history for a specific property and tenant
    with sqlite3.connect('rental_management.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tenant_phone, landlord_phone, message, sender, pdf_filename, timestamp 
            FROM messages 
            WHERE property_id = ? AND ((landlord_phone = ? AND tenant_phone = ?) OR (landlord_phone = ? AND tenant_phone = ?))
            ORDER BY timestamp DESC
        ''', (property_id, landlord_phone, tenant_phone, tenant_phone, landlord_phone))
        chat_history = [
            {
                'tenant_phone': row[0],
                'landlord_phone': row[1],
                'message': row[2],
                'sender': row[3],
                'pdf_filename': row[4],
                'timestamp': row[5]
            }
            for row in cursor.fetchall()
        ]

    return render_template('Tenant/mychat_detail_t.html', chat_history=chat_history, landlord_phone=landlord_phone,
                           property_id=property_id, sender= sender, other_participant=other_participant)



# SocketIO message handling
@socketio.on('message')
def handle_message(msg):
    print('Message: ' + msg)
    send(msg, broadcast=True)


# Upload route for handling PDF file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.pdf'):
        return 'Invalid file type', 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['LEASE_UPLOAD_FOLDER'], filename)
    file.save(file_path)
    return 'File successfully uploaded', 200


@app.route('/uploaded-files')
def uploaded_files():
    files = os.listdir(app.config['LEASE_UPLOAD_FOLDER'])
    return jsonify(files)

# for tenant to leave message from property_detail_t
@app.route('/send_message/<int:property_id>', methods=['POST'])
def send_message(property_id):
    if 'user_type' in session and session['user_type'] == 'tenant':
        tenant_phone = session.get('phone')
        message_content = request.form.get('message')
        pdf_file = request.files.get('pdf')
        sender = session.get('username')

        # Set default pdf_filename to None
        pdf_filename = None

        # Process and save PDF file if uploaded
        if pdf_file and pdf_file.filename != '' and pdf_file.filename.endswith('.pdf'):
            pdf_filename = str(uuid.uuid4()) + "_" + secure_filename(pdf_file.filename)
            pdf_file.save(os.path.join(app.config['PDF_UPLOAD_FOLDER'], pdf_filename))

        # Connect to the database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()

        # Fetch the landlord's phone number for the specified property
        cursor.execute("SELECT landlord_phone FROM properties WHERE id = ?", (property_id,))
        result = cursor.fetchone()

        if result:
            landlord_phone = result[0]

            # Insert the message into the 'messages' table
            cursor.execute('''
                INSERT INTO messages (property_id, tenant_phone, landlord_phone, message, sender, pdf_filename)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (property_id, tenant_phone, landlord_phone, message_content, sender, pdf_filename))
            conn.commit()
            conn.close()

            flash("Message sent to the landlord successfully!", "success")
        else:
            conn.close()
            flash("Landlord not found for this property.", "error")

        return redirect(url_for('property_detail_t', property_id=property_id, phone=tenant_phone))
    else:
        flash("Access denied. Only tenants can send messages.", "error")
        return redirect(url_for('login'))


@app.route('/<phone>/paymyrent_t')
def paymyrent_t(phone):
    if 'phone' in session and session['phone'] == phone:
        # Render the paymyrent.html template with the phone variable
        return render_template('Tenant/paymyrent_t.html', phone=phone)
    else:
        flash('Unauthorized access or session expired.', 'error')
        return redirect(url_for('login'))

@app.route('/<phone>/maintenance_t')
def maintenance_t(phone):
    if 'phone' in session and session['phone'] == phone:
        # Render the maintenance_t.html template with the phone variable
        return render_template('Tenant/maintenance_t.html', phone=phone)
    else:
        flash('Unauthorized access or session expired.', 'error')
        return redirect(url_for('login'))

@app.route('/<phone>/rentnow_t')
def rentnow_t(phone):
    if 'user_type' in session and session['user_type'] == 'tenant' and session.get('phone') == phone:
        # Fetch all properties from the database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM properties')
        properties = cursor.fetchall()
        conn.close()

        # Convert the properties into a list of dictionaries for the template
        property_list = [
            {
                'id': property[0],
                'landlord_phone': property[1],
                'property_type': property[2],
                'property_address': property[3],
                'property_zip_code': property[4],
                'lease_term': property[5],
                'rent_rate': property[6],
                'available_date': property[7],
                'photos': property[8].split(',') if property[8] else []
            } for property in properties
        ]

        # Render the rentnow_t.html template with the phone and properties variables
        return render_template('Tenant/rentnow_t.html', phone=phone, properties=property_list)
    else:
        flash('Unauthorized access or session expired.', 'error')
        return redirect(url_for('login'))





@app.route('/<phone>/property_t/<int:property_id>')
def property_detail_t(phone, property_id):
    if 'user_type' in session and session['user_type'] == 'tenant' and session.get('phone') == phone:
        # Fetch the specific property by its property_id from the database
        conn = sqlite3.connect('rental_management.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM properties WHERE id = ?', (property_id,))
        property = cursor.fetchone()
        conn.close()

        if property:
            property_dict = {
                'id': property[0],
                'landlord_phone': property[1],
                'property_type': property[2],
                'property_address': property[3],
                'property_zip_code': property[4],
                'lease_term': property[5],
                'rent_rate': property[6],
                'available_date': property[7],
                'photos': property[8].split(',') if property[8] else [],
                'lease': property[11],
                'original_lease_filename': property[12]
            }
            return render_template('Tenant/property_detail_t.html', property=property_dict)
        else:
            flash("Property not found or access denied.")
            return redirect(url_for('rentnow_t', phone=phone))
    else:
        flash('Access denied. This page is for tenants only.', 'error')
        return redirect(url_for('login'))

@app.route('/<phone>/myaccount')
def myaccount(phone):
    if 'phone' in session and session['phone'] == phone:
        user_type = session.get('user_type')
        username = session.get('username')
        email = session.get('email')

        if user_type == 'tenant':
            return render_template('Tenant/myaccount_t.html', username=username, phone=phone, email=email)
        elif user_type == 'landlord':
            return render_template('myaccount.html', username=username, phone=phone, email=email)
        else:
            flash('Unknown user type.', 'error')
            return redirect(url_for('login'))
    else:
        flash('Unauthorized access or session expired.', 'error')
        return redirect(url_for('login'))







if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
