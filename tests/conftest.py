import os
import tempfile
import pytest

from app.config import Config
from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    """Fresh SQLite file per test -- isolated, and avoids the in-memory
    SQLite + SQLAlchemy multi-connection gotcha of `:memory:`."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    Config.SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'

    application = create_app()
    application.config['TESTING'] = True

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def register_and_login(client):
    """register_and_login('customer', 'a@x.com', '9800000001') -> (token, user_id)
    Auto-approves restaurant/rider accounts so tests don't need an admin step
    unless they're specifically testing the approval flow."""
    def _do(role, email, phone, name='Test User', password='pass1234', auto_approve=True):
        resp = client.post('/api/auth/register', json={
            'full_name': name, 'email': email, 'phone': phone, 'password': password, 'role': role,
        })
        assert resp.status_code == 201, resp.get_json()
        user_id = resp.get_json()['user']['user_id']

        if role in ('restaurant', 'rider') and auto_approve:
            from app.models.user import User
            u = User.query.get(user_id)
            u.is_active = True
            _db.session.commit()

        login_resp = client.post('/api/auth/login', json={'email': email, 'password': password})
        token = login_resp.get_json().get('access_token')
        return token, user_id
    return _do


@pytest.fixture()
def sample_restaurant(client, register_and_login):
    """A ready-made approved restaurant with one ₹50 menu item."""
    owner_token, owner_id = register_and_login('restaurant', 'owner@test.com', '9800000001')
    r = client.post('/api/restaurant/profile', json={'name': 'Test Diner', 'address': 'Test St', 'city': 'TestCity'},
                     headers={'Authorization': f'Bearer {owner_token}'})
    restaurant_id = r.get_json()['restaurant']['restaurant_id']
    item_r = client.post(f'/api/restaurant/{restaurant_id}/menu', json={'name': 'Test Item', 'price': 50},
                          headers={'Authorization': f'Bearer {owner_token}'})
    item_id = item_r.get_json()['item']['item_id']
    return {'owner_token': owner_token, 'owner_id': owner_id, 'restaurant_id': restaurant_id, 'item_id': item_id}


@pytest.fixture()
def place_test_order(client):
    """place_test_order(sample_restaurant) -> (order_id, customer_token)"""
    def _do(restaurant_info, customer_email='cust@test.com', customer_phone='9800000050', quantity=1):
        cust_r = client.post('/api/auth/register', json={
            'full_name': 'Test Customer', 'email': customer_email, 'phone': customer_phone,
            'password': 'pass1234', 'role': 'customer',
        })
        cust_token = cust_r.get_json()['access_token']
        order_r = client.post('/api/customer/orders', json={
            'restaurant_id': restaurant_info['restaurant_id'],
            'items': [{'item_id': restaurant_info['item_id'], 'quantity': quantity}],
            'delivery_address': 'Test Address', 'payment_method': 'cod',
        }, headers={'Authorization': f'Bearer {cust_token}'})
        assert order_r.status_code == 201, order_r.get_json()
        return order_r.get_json()['order']['order_id'], cust_token
    return _do


def auth_header(token):
    return {'Authorization': f'Bearer {token}'}
