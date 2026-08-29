from tests.conftest import auth_header


def test_menu_item_ownership_blocks_rival(client, register_and_login, sample_restaurant):
    rival_token, _ = register_and_login('restaurant', 'rival@test.com', '9800000099')
    r = client.post(f"/api/restaurant/{sample_restaurant['restaurant_id']}/menu",
                     json={'name': 'Hacked Item', 'price': 1}, headers=auth_header(rival_token))
    assert r.status_code == 403


def test_rival_cannot_edit_menu_item(client, register_and_login, sample_restaurant):
    rival_token, _ = register_and_login('restaurant', 'rival2@test.com', '9800000098')
    r = client.put(f"/api/restaurant/menu-item/{sample_restaurant['item_id']}",
                    json={'price': 1}, headers=auth_header(rival_token))
    assert r.status_code == 403


def test_order_status_cannot_skip_ahead(client, sample_restaurant, place_test_order):
    order_id, _ = place_test_order(sample_restaurant)
    headers = auth_header(sample_restaurant['owner_token'])
    r = client.patch(f'/api/restaurant/orders/{order_id}/status', json={'status': 'preparing'}, headers=headers)
    assert r.status_code == 400
    r = client.patch(f'/api/restaurant/orders/{order_id}/status', json={'status': 'accepted'}, headers=headers)
    assert r.status_code == 200


def test_rival_cannot_change_order_status(client, register_and_login, sample_restaurant, place_test_order):
    order_id, _ = place_test_order(sample_restaurant)
    rival_token, _ = register_and_login('restaurant', 'rival3@test.com', '9800000097')
    r = client.patch(f'/api/restaurant/orders/{order_id}/status', json={'status': 'accepted'}, headers=auth_header(rival_token))
    assert r.status_code == 403


def test_earnings_reflect_only_delivered_orders(client, sample_restaurant, place_test_order):
    order_id, _ = place_test_order(sample_restaurant)
    headers = auth_header(sample_restaurant['owner_token'])
    r = client.get(f"/api/restaurant/{sample_restaurant['restaurant_id']}/earnings", headers=headers)
    assert r.get_json()['delivered_orders'] == 0
    assert r.get_json()['total_revenue'] == 0


def test_toggle_menu_item_availability(client, sample_restaurant):
    headers = auth_header(sample_restaurant['owner_token'])
    r = client.patch(f"/api/restaurant/menu-item/{sample_restaurant['item_id']}/toggle", headers=headers)
    assert r.status_code == 200
    assert r.get_json()['item']['is_available'] is False
