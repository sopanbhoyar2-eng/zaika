from app.extensions import db


class OrderItem(db.Model):
    """Line items for an order. item_name_snapshot / price_snapshot freeze the
    name and price at the moment of ordering, so a later menu price change never
    alters what a past order says the customer was charged."""
    __tablename__ = 'order_items'

    order_item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id', ondelete='CASCADE'),
                          nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.item_id'), nullable=False)

    item_name_snapshot = db.Column(db.String(150), nullable=False)
    price_snapshot = db.Column(db.Numeric(8, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Numeric(8, 2), nullable=False)

    def to_dict(self):
        return {
            'order_item_id': self.order_item_id,
            'item_name': self.item_name_snapshot,
            'price': float(self.price_snapshot),
            'quantity': self.quantity,
            'subtotal': float(self.subtotal),
        }
