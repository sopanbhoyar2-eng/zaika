from datetime import datetime
from app.extensions import db


class Restaurant(db.Model):
    __tablename__ = 'restaurants'

    restaurant_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'),
                          nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    cuisine_type = db.Column(db.String(100))
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False, index=True)
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    fssai_license = db.Column(db.String(50))
    opening_time = db.Column(db.Time)
    closing_time = db.Column(db.Time)
    is_open = db.Column(db.Boolean, default=True, nullable=False)
    avg_rating = db.Column(db.Numeric(2, 1), default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    menu_items = db.relationship('MenuItem', backref='restaurant', lazy=True,
                                  cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='restaurant', lazy=True)

    def to_dict(self):
        return {
            'restaurant_id': self.restaurant_id,
            'name': self.name,
            'cuisine_type': self.cuisine_type,
            'city': self.city,
            'is_open': self.is_open,
            'avg_rating': float(self.avg_rating) if self.avg_rating else 0.0,
        }
