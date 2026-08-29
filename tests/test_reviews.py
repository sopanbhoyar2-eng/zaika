from tests.conftest import auth_header


def test_cannot_review_before_delivery(client, sample_restaurant, place_test_order):
    order_id, cust_token = place_test_order(sample_restaurant)
    r = client.post(f'/api/customer/orders/{order_id}/review', json={'food_rating': 5},
                     headers=auth_header(cust_token))
    assert r.status_code == 400


def test_review_updates_restaurant_avg_rating(client, register_and_login, sample_restaurant, place_test_order):
    order_id, cust_token = place_test_order(sample_restaurant)
    owner_headers = auth_header(sample_restaurant['owner_token'])
    for s in ['accepted', 'preparing', 'ready_for_pickup']:
        client.patch(f'/api/restaurant/orders/{order_id}/status', json={'status': s}, headers=owner_headers)
    rider_token, _ = register_and_login('rider', 'r8@test.com', '9800000080')
    client.post(f'/api/rider/orders/{order_id}/claim', headers=auth_header(rider_token))
    for cp in ['accepted_by_rider', 'reached_restaurant', 'picked_up', 'reached_customer', 'delivered']:
        client.patch(f'/api/rider/orders/{order_id}/checkpoint', json={'checkpoint': cp}, headers=auth_header(rider_token))

    r = client.post(f'/api/customer/orders/{order_id}/review', json={'food_rating': 5, 'comment': 'Great!'},
                     headers=auth_header(cust_token))
    assert r.status_code == 201

    listing = client.get('/api/customer/restaurants')
    diner = next(x for x in listing.get_json()['restaurants'] if x['restaurant_id'] == sample_restaurant['restaurant_id'])
    assert diner['avg_rating'] == 5.0


def test_duplicate_review_blocked(client, sample_restaurant, place_test_order):
    order_id, cust_token = place_test_order(sample_restaurant)
    owner_headers = auth_header(sample_restaurant['owner_token'])
    for s in ['accepted', 'preparing', 'ready_for_pickup']:
        client.patch(f'/api/restaurant/orders/{order_id}/status', json={'status': s}, headers=owner_headers)
    from app.models.order import Order
    from app.extensions import db
    order = Order.query.get(order_id)
    order.order_status = 'delivered'
    db.session.commit()

    client.post(f'/api/customer/orders/{order_id}/review', json={'food_rating': 4}, headers=auth_header(cust_token))
    r = client.post(f'/api/customer/orders/{order_id}/review', json={'food_rating': 3}, headers=auth_header(cust_token))
    assert r.status_code == 409


def test_invalid_rating_value_rejected(client, sample_restaurant, place_test_order):
    order_id, cust_token = place_test_order(sample_restaurant)
    from app.models.order import Order
    from app.extensions import db
    order = Order.query.get(order_id)
    order.order_status = 'delivered'
    db.session.commit()
    r = client.post(f'/api/customer/orders/{order_id}/review', json={'food_rating': 6}, headers=auth_header(cust_token))
    assert r.status_code == 400
