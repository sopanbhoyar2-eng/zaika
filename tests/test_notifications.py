from tests.conftest import auth_header


def test_restaurant_notified_on_new_order(client, sample_restaurant, place_test_order):
    place_test_order(sample_restaurant)
    r = client.get('/api/notifications', headers=auth_header(sample_restaurant['owner_token']))
    titles = [n['title'] for n in r.get_json()['notifications']]
    assert 'New order received' in titles


def test_customer_notified_on_status_change(client, sample_restaurant, place_test_order):
    order_id, cust_token = place_test_order(sample_restaurant)
    client.patch(f'/api/restaurant/orders/{order_id}/status', json={'status': 'accepted'},
                 headers=auth_header(sample_restaurant['owner_token']))
    r = client.get('/api/notifications', headers=auth_header(cust_token))
    assert any('accepted' in n['message'] for n in r.get_json()['notifications'])


def test_mark_all_read_clears_unread_count(client, sample_restaurant, place_test_order):
    _, cust_token = place_test_order(sample_restaurant)
    headers = auth_header(sample_restaurant['owner_token'])
    assert client.get('/api/notifications', headers=headers).get_json()['unread_count'] >= 1
    client.post('/api/notifications/read-all', headers=headers)
    assert client.get('/api/notifications', headers=headers).get_json()['unread_count'] == 0
