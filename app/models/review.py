from datetime import datetime
from app.extensions import db


class Review(db.Model):
    __tablename__ = 'reviews'

    review_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id', ondelete='CASCADE'),
                          nullable=False, unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.restaurant_id'),
                               nullable=False, index=True)
    food_rating = db.Column(db.SmallInteger, nullable=False)
    delivery_rating = db.Column(db.SmallInteger)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('User', foreign_keys=[customer_id])

    def to_dict(self):
        return {
            'review_id': self.review_id,
            'order_id': self.order_id,
            'food_rating': self.food_rating,
            'delivery_rating': self.delivery_rating,
            'comment': self.comment,
            'customer_name': self.customer.full_name if self.customer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
