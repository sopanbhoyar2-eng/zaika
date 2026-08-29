from tests.conftest import auth_header


def test_register_customer_returns_token(client):
    r = client.post('/api/auth/register', json={
        'full_name': 'Test User', 'email': 'test@test.com', 'phone': '9876543210',
        'password': 'pass1234', 'role': 'customer',
    })
    assert r.status_code == 201
    assert 'access_token' in r.get_json()


def test_register_restaurant_is_inactive_no_token(client):
    r = client.post('/api/auth/register', json={
        'full_name': 'Owner', 'email': 'owner@test.com', 'phone': '9876543211',
        'password': 'pass1234', 'role': 'restaurant',
    })
    assert r.status_code == 201
    assert 'access_token' not in r.get_json()
    assert r.get_json()['user']['is_active'] is False


def test_admin_cannot_self_register(client):
    r = client.post('/api/auth/register', json={
        'full_name': 'Hacker', 'email': 'hacker@test.com', 'phone': '9876543212',
        'password': 'pass1234', 'role': 'admin',
    })
    assert r.status_code == 400


def test_duplicate_email_rejected(client):
    payload = {'full_name': 'Dup Test', 'email': 'dup@test.com', 'phone': '9876543213', 'password': 'pass1234', 'role': 'customer'}
    r1 = client.post('/api/auth/register', json=payload)
    assert r1.status_code == 201
    r = client.post('/api/auth/register', json={**payload, 'phone': '9876543214'})
    assert r.status_code == 409


def test_login_wrong_password_gives_generic_error(client):
    reg = client.post('/api/auth/register', json={'full_name': 'Test User', 'email': 'a@test.com', 'phone': '9876543215',
                                                    'password': 'pass1234', 'role': 'customer'})
    assert reg.status_code == 201
    r = client.post('/api/auth/login', json={'email': 'a@test.com', 'password': 'wrongpass'})
    assert r.status_code == 401
    assert r.get_json()['error'] == 'Invalid email or password.'


def test_login_unknown_email_same_generic_error(client):
    """Same message as wrong-password -- stops attackers using login to find real emails."""
    r = client.post('/api/auth/login', json={'email': 'nobody@test.com', 'password': 'whatever1'})
    assert r.status_code == 401
    assert r.get_json()['error'] == 'Invalid email or password.'


def test_phone_validation_accepts_bare_10_digit(client):
    """Regression test: a broken regex (`^\\+?91?\\d{10}$`) once rejected every
    plain 10-digit number. Locking this in so it can't silently break again."""
    r = client.post('/api/auth/register', json={
        'full_name': 'Phone Test', 'email': 'phone@test.com', 'phone': '9876543216',
        'password': 'pass1234', 'role': 'customer',
    })
    assert r.status_code == 201


def test_protected_route_requires_token(client):
    r = client.get('/api/customer/profile')
    assert r.status_code == 401


def test_wrong_role_token_is_forbidden(client, register_and_login):
    cust_token, _ = register_and_login('customer', 'c2@test.com', '9876543217')
    r = client.get('/api/restaurant/dashboard', headers=auth_header(cust_token))
    assert r.status_code == 403
