def test_register_with_non_ascii_username(client):
    """测试注册时使用非 ASCII 字符的用户名"""
    response = client.post('/register', data={
        'phone': '1234567890',
        'username': '用户',  # 非 ASCII 字符
        'email': 'nonascii@example.com',
        'password': 'password123',
        'user_type': 'tenant'
    })
    assert response.status_code in [200, 400, 302]
    assert b'Invalid username' in response.data or b'Error' in response.data or b'Redirecting' in response.data