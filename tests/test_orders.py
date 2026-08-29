from tests.conftest import auth_header


def test_checkout_ignores_client_supplied_price(client, sample_restaurant, register_and_login):
    cust_token, _ = register_and_login('customer', 'cust1@test.com', '9800000060')
    r = client.post('/api/customer/orders', json={
        'restaurant_id': sample_restaurant['restaurant_id'],
        'items': [{'item_id': sample_restaurant['item_id'], 'quantity': 2, 'price': 1}],
        'delivery_address': 'Test', 'payment_method': 'cod',
    }, headers=auth_header(cust_token))
    assert r.status_code == 201
    assert float(r.get_json()['order']['grand_total']) > 100  # real price 50x2, not 1x2


def test_cannot_order_unavailable_item(client, sample_restaurant, register_and_login):
    client.patch(f"/api/restaurant/menu-item/{sample_restaurant['item_id']}/toggle",
                 headers=auth_header(sample_restaurant['owner_token']))
    cust_token, _ = register_and_login('customer', 'cust2@test.com', '9800000061')
    r = client.post('/api/customer/orders', json={
        'restaurant_id': sample_restaurant['restaurant_id'],
        'items': [{'item_id': sample_restaurant['item_id'], 'quantity': 1}],
        'delivery_address': 'x', 'payment_method': 'cod',
    }, headers=auth_header(cust_token))
    assert r.status_code == 400


def test_cannot_order_from_closed_restaurant(client, sample_restaurant, register_and_login):
    client.patch(f"/api/restaurant/profile/{sample_restaurant['restaurant_id']}/toggle",
                 headers=auth_header(sample_restaurant['owner_token']))
    cust_token, _ = register_and_login('customer', 'cust3@test.com', '9800000062')
    r = client.post('/api/customer/orders', json={
        'restaurant_id': sample_restaurant['restaurant_id'],
        'items': [{'item_id': sample_restaurant['item_id'], 'quantity': 1}],
        'delivery_address': 'x', 'payment_method': 'cod',
    }, headers=auth_header(cust_token))
    assert r.status_code == 400


def test_customer_cannot_view_others_order(client, sample_restaurant, place_test_order, register_and_login):
    order_id, _ = place_test_order(sample_restaurant)
    other_token, _ = register_and_login('customer', 'other@test.com', '9800000063')
    r = client.get(f'/api/customer/orders/{order_id}', headers=auth_header(other_token))
    assert r.status_code == 403


def test_cancel_only_while_placed(client, sample_restaurant, place_test_order):
    order_id, cust_token = place_test_order(sample_restaurant)
    client.patch(f'/api/restaurant/orders/{order_id}/status', json={'status': 'accepted'},
                 headers=auth_header(sample_restaurant['owner_token']))
    r = client.patch(f'/api/customer/orders/{order_id}/cancel', headers=auth_header(cust_token))
    assert r.status_code == 400


def test_cancel_while_placed_succeeds(client, sample_restaurant, place_test_order):
    order_id, cust_token = place_test_order(sample_restaurant)
    r = client.patch(f'/api/customer/orders/{order_id}/cancel', headers=auth_header(cust_token))
    assert r.status_code == 200
    assert r.get_json()['order']['order_status'] == 'cancelled'


def test_veg_only_filter_excludes_mixed_menu(client, sample_restaurant):
    client.post(f"/api/restaurant/{sample_restaurant['restaurant_id']}/menu",
                json={'name': 'Chicken', 'price': 100, 'is_veg': False},
                headers=auth_header(sample_restaurant['owner_token']))
    r = client.get('/api/customer/restaurants?veg_only=true')
    names = [x['name'] for x in r.get_json()['restaurants']]
    assert 'Test Diner' not in names
