from datetime import datetime
from app.extensions import db


class DeliveryLog(db.Model):
    """Append-only history of status changes for an order's delivery.
    orders.order_status holds the CURRENT state; this table holds every
    state the order has ever passed through, which is what a live tracking
    timeline UI queries (ORDER BY logged_at)."""
    __tablename__ = 'delivery_logs'

    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id', ondelete='CASCADE'),
                          nullable=False, index=True)
    rider_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'),
                          nullable=True, index=True)

    status = db.Column(
        db.Enum('assigned', 'accepted_by_rider', 'reached_restaurant', 'picked_up',
                'reached_customer', 'delivered', 'cancelled', name='delivery_status_enum'),
        nullable=False
    )
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    notes = db.Column(db.String(255))
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'order_id': self.order_id,
            'status': self.status,
            'logged_at': self.logged_at.isoformat() if self.logged_at else None,
        }
