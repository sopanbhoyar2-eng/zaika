from datetime import datetime
from app.extensions import db


class Order(db.Model):
    __tablename__ = 'orders'

    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.restaurant_id'), nullable=False, index=True)
    rider_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'),
                          nullable=True, index=True)

    delivery_address = db.Column(db.String(255), nullable=False)
    delivery_latitude = db.Column(db.Numeric(10, 8))
    delivery_longitude = db.Column(db.Numeric(11, 8))

    item_total = db.Column(db.Numeric(8, 2), nullable=False)
    delivery_fee = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    taxes = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    discount = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    grand_total = db.Column(db.Numeric(8, 2), nullable=False)

    payment_method = db.Column(db.Enum('cod', 'upi', 'card', name='payment_method_enum'),
                                nullable=False, default='cod')
    payment_status = db.Column(db.Enum('pending', 'paid', 'failed', 'refunded', name='payment_status_enum'),
                                nullable=False, default='pending')
    order_status = db.Column(
        db.Enum('placed', 'accepted', 'preparing', 'ready_for_pickup', 'picked_up',
                'delivered', 'cancelled', name='order_status_enum'),
        nullable=False, default='placed', index=True
    )

    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    delivery_logs = db.relationship('DeliveryLog', backref='order', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'order_id': self.order_id,
            'customer_id': self.customer_id,
            'restaurant_id': self.restaurant_id,
            'rider_id': self.rider_id,
            'grand_total': float(self.grand_total),
            'order_status': self.order_status,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'placed_at': self.placed_at.isoformat() if self.placed_at else None,
        }
