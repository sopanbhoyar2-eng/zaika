from datetime import datetime
from app.extensions import db


class MenuItem(db.Model):
    __tablename__ = 'menu_items'

    item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.restaurant_id', ondelete='CASCADE'),
                               nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(8, 2), nullable=False)
    category = db.Column(db.String(80), index=True)
    is_veg = db.Column(db.Boolean, default=True, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'item_id': self.item_id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'category': self.category,
            'is_veg': self.is_veg,
            'is_available': self.is_available,
            'image_url': self.image_url,
        }
