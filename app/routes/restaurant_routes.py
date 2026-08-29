from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.utils.decorators import role_required
from app.models.user import User
from app.services.restaurant_service import (
    RestaurantError, create_restaurant, list_owned_restaurants, update_restaurant,
    toggle_restaurant_status, create_menu_item, list_menu_items, update_menu_item,
    delete_menu_item, toggle_menu_item_availability, list_restaurant_orders,
    update_order_status, get_restaurant_earnings, upload_menu_item_photo,
)

restaurant_bp = Blueprint('restaurant', __name__)


@restaurant_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'blueprint': 'restaurant', 'status': 'ready'}), 200


@restaurant_bp.route('/dashboard', methods=['GET'])
@role_required('restaurant')
def dashboard():
    user = User.query.get(get_jwt_identity())
    return jsonify({'message': f'Welcome {user.full_name}',
                     'restaurants': [r.to_dict() for r in user.restaurants]}), 200


# ---------- Restaurant profile ----------

@restaurant_bp.route('/profile', methods=['POST'])
@role_required('restaurant')
def create_profile():
    data = request.get_json(silent=True) or {}
    try:
        restaurant = create_restaurant(get_jwt_identity(), data)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Restaurant created.', 'restaurant': restaurant.to_dict()}), 201


@restaurant_bp.route('/profile', methods=['GET'])
@role_required('restaurant')
def get_profiles():
    restaurants = list_owned_restaurants(get_jwt_identity())
    return jsonify({'restaurants': [r.to_dict() for r in restaurants]}), 200


@restaurant_bp.route('/profile/<int:restaurant_id>', methods=['PUT'])
@role_required('restaurant')
def edit_profile(restaurant_id):
    data = request.get_json(silent=True) or {}
    try:
        restaurant = update_restaurant(get_jwt_identity(), restaurant_id, data)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Restaurant updated.', 'restaurant': restaurant.to_dict()}), 200


@restaurant_bp.route('/profile/<int:restaurant_id>/toggle', methods=['PATCH'])
@role_required('restaurant')
def toggle_profile(restaurant_id):
    try:
        restaurant = toggle_restaurant_status(get_jwt_identity(), restaurant_id)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    state = 'open' if restaurant.is_open else 'closed'
    return jsonify({'message': f'Restaurant is now {state}.', 'restaurant': restaurant.to_dict()}), 200


# ---------- Menu items ----------

@restaurant_bp.route('/<int:restaurant_id>/menu', methods=['POST'])
@role_required('restaurant')
def add_menu_item(restaurant_id):
    data = request.get_json(silent=True) or {}
    try:
        item = create_menu_item(get_jwt_identity(), restaurant_id, data)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Menu item added.', 'item': item.to_dict()}), 201


@restaurant_bp.route('/<int:restaurant_id>/menu', methods=['GET'])
@role_required('restaurant')
def get_menu_items(restaurant_id):
    try:
        items = list_menu_items(get_jwt_identity(), restaurant_id)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'menu_items': [i.to_dict() for i in items]}), 200


@restaurant_bp.route('/menu-item/<int:item_id>', methods=['PUT'])
@role_required('restaurant')
def edit_menu_item(item_id):
    data = request.get_json(silent=True) or {}
    try:
        item = update_menu_item(get_jwt_identity(), item_id, data)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Menu item updated.', 'item': item.to_dict()}), 200


@restaurant_bp.route('/menu-item/<int:item_id>', methods=['DELETE'])
@role_required('restaurant')
def remove_menu_item(item_id):
    try:
        delete_menu_item(get_jwt_identity(), item_id)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Menu item deleted.'}), 200


@restaurant_bp.route('/menu-item/<int:item_id>/toggle', methods=['PATCH'])
@role_required('restaurant')
def toggle_menu_item(item_id):
    try:
        item = toggle_menu_item_availability(get_jwt_identity(), item_id)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    state = 'available' if item.is_available else 'unavailable'
    return jsonify({'message': f"'{item.name}' is now {state}.", 'item': item.to_dict()}), 200


@restaurant_bp.route('/menu-item/<int:item_id>/photo', methods=['POST'])
@role_required('restaurant')
def upload_photo(item_id):
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo file provided.'}), 400
    try:
        item = upload_menu_item_photo(get_jwt_identity(), item_id, request.files['photo'])
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Photo uploaded.', 'item': item.to_dict()}), 200


# ---------- Orders ----------

def _order_detail_dict(order):
    data = order.to_dict()
    data['customer_name'] = order.customer.full_name if order.customer else None
    data['customer_phone'] = order.customer.phone if order.customer else None
    data['delivery_address'] = order.delivery_address
    data['items'] = [oi.to_dict() for oi in order.order_items]
    return data


@restaurant_bp.route('/<int:restaurant_id>/orders', methods=['GET'])
@role_required('restaurant')
def get_orders(restaurant_id):
    status = request.args.get('status')
    try:
        orders = list_restaurant_orders(get_jwt_identity(), restaurant_id, status)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'orders': [_order_detail_dict(o) for o in orders]}), 200


@restaurant_bp.route('/orders/<int:order_id>/status', methods=['PATCH'])
@role_required('restaurant')
def change_order_status(order_id):
    data = request.get_json(silent=True) or {}
    new_status = (data.get('status') or '').strip()
    try:
        order = update_order_status(get_jwt_identity(), order_id, new_status)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': f'Order #{order.order_id} is now {order.order_status}.',
                     'order': _order_detail_dict(order)}), 200


@restaurant_bp.route('/<int:restaurant_id>/earnings', methods=['GET'])
@role_required('restaurant')
def earnings(restaurant_id):
    try:
        summary = get_restaurant_earnings(get_jwt_identity(), restaurant_id)
    except RestaurantError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify(summary), 200
