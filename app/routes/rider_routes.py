from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.utils.decorators import role_required
from app.models.user import User
from app.services.rider_service import (
    RiderError, list_available_orders, list_my_deliveries, claim_order,
    advance_checkpoint, cancel_delivery, get_earnings_summary, ping_location,
)

rider_bp = Blueprint('rider', __name__)


def _order_dict(order):
    data = order.to_dict()
    data['restaurant_name'] = order.restaurant.name if order.restaurant else None
    data['restaurant_address'] = order.restaurant.address if order.restaurant else None
    data['customer_name'] = order.customer.full_name if order.customer else None
    data['customer_phone'] = order.customer.phone if order.customer else None
    logs = sorted(order.delivery_logs, key=lambda l: l.logged_at)
    data['last_checkpoint'] = logs[-1].status if logs else None
    return data


@rider_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'blueprint': 'rider', 'status': 'ready'}), 200


@rider_bp.route('/dashboard', methods=['GET'])
@role_required('rider')
def dashboard():
    user = User.query.get(get_jwt_identity())
    return jsonify({'message': f'Welcome {user.full_name}'}), 200


@rider_bp.route('/available-orders', methods=['GET'])
@role_required('rider')
def available_orders():
    orders = list_available_orders()
    return jsonify({'available_orders': [_order_dict(o) for o in orders]}), 200


@rider_bp.route('/my-deliveries', methods=['GET'])
@role_required('rider')
def my_deliveries():
    orders = list_my_deliveries(get_jwt_identity())
    return jsonify({'deliveries': [_order_dict(o) for o in orders]}), 200


@rider_bp.route('/orders/<int:order_id>/claim', methods=['POST'])
@role_required('rider')
def claim(order_id):
    try:
        order = claim_order(get_jwt_identity(), order_id)
    except RiderError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Delivery claimed.', 'order': _order_dict(order)}), 200


@rider_bp.route('/orders/<int:order_id>/checkpoint', methods=['PATCH'])
@role_required('rider')
def checkpoint(order_id):
    data = request.get_json(silent=True) or {}
    try:
        order = advance_checkpoint(
            get_jwt_identity(), order_id,
            checkpoint=(data.get('checkpoint') or '').strip(),
            latitude=data.get('latitude'), longitude=data.get('longitude'),
            notes=data.get('notes'),
        )
    except RiderError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': f"Checkpoint logged. Order status: '{order.order_status}'.",
                     'order': _order_dict(order)}), 200


@rider_bp.route('/orders/<int:order_id>/location', methods=['POST'])
@role_required('rider')
def location_ping(order_id):
    data = request.get_json(silent=True) or {}
    lat, lng = data.get('latitude'), data.get('longitude')
    if lat is None or lng is None:
        return jsonify({'error': 'latitude and longitude are required.'}), 400
    try:
        ping_location(get_jwt_identity(), order_id, lat, lng)
    except RiderError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'status': 'ok'}), 200


@rider_bp.route('/orders/<int:order_id>/release', methods=['POST'])
@role_required('rider')
def release(order_id):
    data = request.get_json(silent=True) or {}
    try:
        order = cancel_delivery(get_jwt_identity(), order_id, notes=data.get('notes'))
    except RiderError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Delivery released back to the pool.', 'order': _order_dict(order)}), 200


@rider_bp.route('/earnings', methods=['GET'])
@role_required('rider')
def earnings():
    return jsonify(get_earnings_summary(get_jwt_identity())), 200
