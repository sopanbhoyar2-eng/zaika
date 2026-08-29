from datetime import datetime
from app.extensions import db


class User(db.Model):
    """Single table for all 4 roles: customer, restaurant, rider, admin.
    The `role` column decides what a user can do; restaurant/order-specific
    details live in their own tables (Restaurant, Order) to keep this table lean."""
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('customer', 'restaurant', 'rider', 'admin', name='user_role'),
                      nullable=False, default='customer', index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # A user can own multiple restaurants (rare but possible for a small chain)
    restaurants = db.relationship('Restaurant', backref='owner', lazy=True,
                                   foreign_keys='Restaurant.owner_id')
    # Orders table has TWO foreign keys into users (customer_id and rider_id) —
    # foreign_keys= tells SQLAlchemy which column each relationship should follow.
    orders_as_customer = db.relationship('Order', backref='customer', lazy=True,
                                          foreign_keys='Order.customer_id')
    orders_as_rider = db.relationship('Order', backref='rider', lazy=True,
                                       foreign_keys='Order.rider_id')

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
