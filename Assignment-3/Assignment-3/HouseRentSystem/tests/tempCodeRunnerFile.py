def client():
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True

    with app.test_client() as client:
        with app.app_context():
            init_db()
            init_property_db()
            init_messages_db()
        yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])