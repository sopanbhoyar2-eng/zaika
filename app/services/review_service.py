from app.extensions import db
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.models.review import Review


class ReviewError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _valid_rating(value, required=True):
    if value is None:
        return not required
    return isinstance(value, int) and 1 <= value <= 5


def create_review(customer_id, order_id, data):
    order = Order.query.get(order_id)
    if not order:
        raise ReviewError('Order not found.', 404)
    if order.customer_id != int(customer_id):
        raise ReviewError('This is not your order.', 403)
    if order.order_status != 'delivered':
        raise ReviewError('You can only review orders that have been delivered.')
    if Review.query.filter_by(order_id=order_id).first():
        raise ReviewError('You already reviewed this order.', 409)

    food_rating = data.get('food_rating')
    delivery_rating = data.get('delivery_rating')
    comment = (data.get('comment') or '').strip() or None

    if not _valid_rating(food_rating):
        raise ReviewError('food_rating is required and must be a whole number from 1 to 5.')
    if not _valid_rating(delivery_rating, required=False):
        raise ReviewError('delivery_rating must be a whole number from 1 to 5 if provided.')

    review = Review(order_id=order_id, customer_id=customer_id, restaurant_id=order.restaurant_id,
                     food_rating=food_rating, delivery_rating=delivery_rating, comment=comment)
    db.session.add(review)
    db.session.commit()

    _recompute_restaurant_rating(order.restaurant_id)
    return review


def _recompute_restaurant_rating(restaurant_id):
    reviews = Review.query.filter_by(restaurant_id=restaurant_id).all()
    if not reviews:
        return
    avg = sum(r.food_rating for r in reviews) / len(reviews)
    restaurant = Restaurant.query.get(restaurant_id)
    restaurant.avg_rating = round(avg, 1)
    db.session.commit()


def list_restaurant_reviews(restaurant_id):
    if not Restaurant.query.get(restaurant_id):
        raise ReviewError('Restaurant not found.', 404)
    return Review.query.filter_by(restaurant_id=restaurant_id).order_by(Review.created_at.desc()).all()
