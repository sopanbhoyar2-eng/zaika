from datetime import datetime
from app.extensions import db


class Payment(db.Model):
    """One row per payment attempt against an order. Separate from
    orders.payment_status because an order can have more than one attempt
    (a failed try, a retry, a refund) — this is where the actual gateway IDs
    used to verify a transaction live."""
    __tablename__ = 'payments'

    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id', ondelete='CASCADE'),
                          nullable=False, index=True)
    gateway = db.Column(db.String(30), nullable=False, default='razorpay')
    gateway_order_id = db.Column(db.String(100), index=True)
    gateway_payment_id = db.Column(db.String(100))
    amount = db.Column(db.Numeric(8, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='INR')
    status = db.Column(db.Enum('created', 'paid', 'failed', 'refunded', name='payment_status_gateway_enum'),
                        nullable=False, default='created')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'payment_id': self.payment_id,
            'order_id': self.order_id,
            'gateway': self.gateway,
            'status': self.status,
            'amount': float(self.amount),
            'currency': self.currency,
        }
