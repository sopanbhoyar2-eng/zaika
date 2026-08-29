from tests.conftest import auth_header


def _ready_order(client, sample_restaurant, place_test_order):
    order_id, cust_token = place_test_order(sample_restaurant)
    headers = auth_header(sample_restaurant['owner_token'])
    for s in ['accepted', 'preparing', 'ready_for_pickup']:
        client.patch(f'/api/restaurant/orders/{order_id}/status', json={'status': s}, headers=headers)
    return order_id, cust_token


def test_double_claim_blocked(client, register_and_login, sample_restaurant, place_test_order):
    order_id, _ = _ready_order(client, sample_restaurant, place_test_order)
    r1_token, _ = register_and_login('rider', 'r1@test.com', '9800000070')
    r2_token, _ = register_and_login('rider', 'r2@test.com', '9800000071')
    assert client.post(f'/api/rider/orders/{order_id}/claim', headers=auth_header(r1_token)).status_code == 200
    r = client.post(f'/api/rider/orders/{order_id}/claim', headers=auth_header(r2_token))
    assert r.status_code == 409


def test_wrong_rider_cannot_update_delivery(client, register_and_login, sample_restaurant, place_test_order):
    order_id, _ = _ready_order(client, sample_restaurant, place_test_order)
    r1_token, _ = register_and_login('rider', 'r3@test.com', '9800000072')
    r2_token, _ = register_and_login('rider', 'r4@test.com', '9800000073')
    client.post(f'/api/rider/orders/{order_id}/claim', headers=auth_header(r1_token))
    r = client.patch(f'/api/rider/orders/{order_id}/checkpoint', json={'checkpoint': 'accepted_by_rider'},
                      headers=auth_header(r2_token))
    assert r.status_code == 403


def test_checkpoint_sequence_enforced(client, register_and_login, sample_restaurant, place_test_order):
    order_id, _ = _ready_order(client, sample_restaurant, place_test_order)
    rider_token, _ = register_and_login('rider', 'r5@test.com', '9800000074')
    client.post(f'/api/rider/orders/{order_id}/claim', headers=auth_header(rider_token))
    r = client.patch(f'/api/rider/orders/{order_id}/checkpoint', json={'checkpoint': 'picked_up'},
                      headers=auth_header(rider_token))
    assert r.status_code == 400


def test_cod_marked_paid_on_delivery(client, register_and_login, sample_restaurant, place_test_order):
    order_id, _ = _ready_order(client, sample_restaurant, place_test_order)
    rider_token, _ = register_and_login('rider', 'r6@test.com', '9800000075')
    headers = auth_header(rider_token)
    client.post(f'/api/rider/orders/{order_id}/claim', headers=headers)
    for cp in ['accepted_by_rider', 'reached_restaurant', 'picked_up', 'reached_customer', 'delivered']:
        r = client.patch(f'/api/rider/orders/{order_id}/checkpoint', json={'checkpoint': cp}, headers=headers)
        assert r.status_code == 200
    assert r.get_json()['order']['payment_status'] == 'paid'


def test_earnings_after_one_delivery(client, register_and_login, sample_restaurant, place_test_order):
    order_id, _ = _ready_order(client, sample_restaurant, place_test_order)
    rider_token, _ = register_and_login('rider', 'r7@test.com', '9800000076')
    headers = auth_header(rider_token)
    client.post(f'/api/rider/orders/{order_id}/claim', headers=headers)
    for cp in ['accepted_by_rider', 'reached_restaurant', 'picked_up', 'reached_customer', 'delivered']:
        client.patch(f'/api/rider/orders/{order_id}/checkpoint', json={'checkpoint': cp}, headers=headers)
    r = client.get('/api/rider/earnings', headers=headers)
    assert r.get_json()['total_deliveries'] == 1
    assert r.get_json()['total_earnings'] == 30.0
