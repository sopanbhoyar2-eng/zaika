from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.utils.decorators import role_required
from app.models.user import User
from app.services.order_service import (
    OrderError, browse_restaurants, get_restaurant_menu, place_order,
    list_customer_orders, get_customer_order, cancel_order,
)
from app.services.payment_service import PaymentError, create_payment_order, verify_payment
from app.services.review_service import ReviewError, create_review, list_restaurant_reviews
from app.models.review import Review

customer_bp = Blueprint('customer', __name__)


def _order_dict(order):
    data = order.to_dict()
    data['restaurant_name'] = order.restaurant.name if order.restaurant else None
    data['delivery_address'] = order.delivery_address
    data['items'] = [oi.to_dict() for oi in order.order_items]
    data['has_review'] = Review.query.filter_by(order_id=order.order_id).first() is not None
    return data


@customer_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'blueprint': 'customer', 'status': 'ready'}), 200


@customer_bp.route('/profile', methods=['GET'])
@role_required('customer')
def profile():
    user = User.query.get(get_jwt_identity())
    return jsonify({'profile': user.to_dict()}), 200


# ---------- Browse — public, no login. People should see restaurants before
# being forced to make an account, same as Zomato/Swiggy. ----------

@customer_bp.route('/restaurants', methods=['GET'])
def get_restaurants():
    restaurants = browse_restaurants(
        city=request.args.get('city'),
        search=request.args.get('search'),
        cuisine=request.args.get('cuisine'),
        veg_only=request.args.get('veg_only') == 'true',
        min_rating=request.args.get('min_rating', type=float),
    )
    return jsonify({'restaurants': [r.to_dict() for r in restaurants]}), 200


@customer_bp.route('/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_menu(restaurant_id):
    try:
        restaurant, items = get_restaurant_menu(restaurant_id)
    except OrderError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'restaurant': restaurant.to_dict(), 'menu_items': [i.to_dict() for i in items]}), 200


# ---------- Orders — requires a logged-in customer ----------

@customer_bp.route('/orders', methods=['POST'])
@role_required('customer')
def checkout():
    data = request.get_json(silent=True) or {}
    try:
        order = place_order(get_jwt_identity(), data)
    except OrderError as e:
        return jsonify({'error': e.message}), e.status_code

    response = {'message': 'Order placed successfully.', 'order': _order_dict(order)}
    if order.payment_method in ('upi', 'card'):
        # Order already exists even if payment setup fails below -- we never
        # lose the order over a gateway hiccup, we just surface it separately
        # so the frontend can retry payment without re-placing everything.
        try:
            response['payment'] = create_payment_order(order)
        except PaymentError as e:
            response['payment_error'] = e.message
    return jsonify(response), 201


@customer_bp.route('/orders/<int:order_id>/verify-payment', methods=['POST'])
@role_required('customer')
def verify_payment_route(order_id):
    data = request.get_json(silent=True) or {}
    try:
        order = verify_payment(
            get_jwt_identity(), order_id,
            data.get('razorpay_order_id'), data.get('razorpay_payment_id'), data.get('razorpay_signature'),
        )
    except PaymentError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Payment verified.', 'order': _order_dict(order)}), 200


@customer_bp.route('/orders', methods=['GET'])
@role_required('customer')
def my_orders():
    orders = list_customer_orders(get_jwt_identity())
    return jsonify({'orders': [_order_dict(o) for o in orders]}), 200


@customer_bp.route('/orders/<int:order_id>', methods=['GET'])
@role_required('customer')
def order_detail(order_id):
    try:
        order = get_customer_order(get_jwt_identity(), order_id)
    except OrderError as e:
        return jsonify({'error': e.message}), e.status_code
    data = _order_dict(order)
    # Full rider-journey history for a live tracking screen — this is the
    # payoff of the delivery_logs table designed back in Milestone 1.
    logs_sorted = sorted(order.delivery_logs, key=lambda l: l.logged_at)
    data['tracking_timeline'] = [log.to_dict() for log in logs_sorted]

    r = order.restaurant
    data['restaurant_location'] = (
        {'lat': float(r.latitude), 'lng': float(r.longitude)}
        if r and r.latitude is not None and r.longitude is not None else None
    )
    data['delivery_location'] = (
        {'lat': float(order.delivery_latitude), 'lng': float(order.delivery_longitude)}
        if order.delivery_latitude is not None and order.delivery_longitude is not None else None
    )
    located_logs = [l for l in reversed(logs_sorted) if l.latitude is not None and l.longitude is not None]
    data['rider_location'] = (
        {'lat': float(located_logs[0].latitude), 'lng': float(located_logs[0].longitude)}
        if located_logs else None
    )
    return jsonify({'order': data}), 200


@customer_bp.route('/orders/<int:order_id>/cancel', methods=['PATCH'])
@role_required('customer')
def cancel(order_id):
    try:
        order = cancel_order(get_jwt_identity(), order_id)
    except OrderError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Order cancelled.', 'order': _order_dict(order)}), 200


@customer_bp.route('/orders/<int:order_id>/review', methods=['POST'])
@role_required('customer')
def review_order(order_id):
    data = request.get_json(silent=True) or {}
    try:
        review = create_review(get_jwt_identity(), order_id, data)
    except ReviewError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'message': 'Thanks for the review!', 'review': review.to_dict()}), 201


@customer_bp.route('/restaurants/<int:restaurant_id>/reviews', methods=['GET'])
def restaurant_reviews(restaurant_id):
    try:
        reviews = list_restaurant_reviews(restaurant_id)
    except ReviewError as e:
        return jsonify({'error': e.message}), e.status_code
    return jsonify({'reviews': [r.to_dict() for r in reviews]}), 200
