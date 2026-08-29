from app.extensions import db
from app.models.restaurant import Restaurant
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services.notification_service import notify

DELIVERY_FEE = 30
TAX_RATE = 0.05


class OrderError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------- Browsing (public, no login required) ----------

def browse_restaurants(city=None, search=None, cuisine=None, veg_only=False, min_rating=None):
    query = Restaurant.query.filter_by(is_open=True)
    if city:
        query = query.filter(Restaurant.city.ilike(f'%{city}%'))
    if search:
        query = query.filter(Restaurant.name.ilike(f'%{search}%'))
    if cuisine:
        query = query.filter(Restaurant.cuisine_type.ilike(f'%{cuisine}%'))
    if min_rating:
        query = query.filter(Restaurant.avg_rating >= min_rating)
    if veg_only:
        # "Veg only" means every item on the menu is veg -- a restaurant with
        # even one non-veg item is excluded. Computed live from the current
        # menu rather than a separate flag, so it can never drift out of sync
        # with what the restaurant actually serves today.
        non_veg_exists = (
            db.session.query(MenuItem.item_id)
            .filter(MenuItem.restaurant_id == Restaurant.restaurant_id, MenuItem.is_veg.is_(False))
            .exists()
        )
        query = query.filter(~non_veg_exists)
    return query.all()


def get_restaurant_menu(restaurant_id):
    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        raise OrderError('Restaurant not found.', 404)
    items = MenuItem.query.filter_by(restaurant_id=restaurant_id, is_available=True).all()
    return restaurant, items


# ---------- Checkout ----------

def place_order(customer_id, data):
    restaurant_id = data.get('restaurant_id')
    items_input = data.get('items') or []
    delivery_address = (data.get('delivery_address') or '').strip()
    payment_method = (data.get('payment_method') or 'cod').strip().lower()

    if not restaurant_id:
        raise OrderError('restaurant_id is required.')
    if not items_input:
        raise OrderError('Cart cannot be empty.')
    if not delivery_address:
        raise OrderError('Delivery address is required.')
    if payment_method not in ('cod', 'upi', 'card'):
        raise OrderError('Invalid payment method.')

    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        raise OrderError('Restaurant not found.', 404)
    if not restaurant.is_open:
        raise OrderError('This restaurant is currently closed.')

    line_items = []
    item_total = 0.0

    for entry in items_input:
        item_id = entry.get('item_id')
        quantity = entry.get('quantity', 1)

        if not isinstance(quantity, int) or quantity < 1:
            raise OrderError('Quantity must be a positive whole number.')

        menu_item = MenuItem.query.get(item_id)
        if not menu_item or menu_item.restaurant_id != int(restaurant_id):
            raise OrderError(f'Item {item_id} does not belong to this restaurant.')
        if not menu_item.is_available:
            raise OrderError(f"'{menu_item.name}' is currently unavailable.")

        # SECURITY: price is read from the database, NEVER from the client's
        # request — even if the request body includes a "price" field, we
        # never look at it. Otherwise anyone could edit the request and buy a
        # ₹500 biryani for ₹1.
        subtotal = float(menu_item.price) * quantity
        item_total += subtotal
        line_items.append({
            'item_id': menu_item.item_id,
            'item_name_snapshot': menu_item.name,
            'price_snapshot': menu_item.price,
            'quantity': quantity,
            'subtotal': subtotal,
        })

    delivery_fee = DELIVERY_FEE
    taxes = round(item_total * TAX_RATE, 2)
    discount = 0
    grand_total = round(item_total + delivery_fee + taxes - discount, 2)

    order = Order(
        customer_id=customer_id,
        restaurant_id=restaurant_id,
        delivery_address=delivery_address,
        delivery_latitude=data.get('delivery_latitude'),
        delivery_longitude=data.get('delivery_longitude'),
        item_total=item_total,
        delivery_fee=delivery_fee,
        taxes=taxes,
        discount=discount,
        grand_total=grand_total,
        payment_method=payment_method,
        payment_status='pending',
        order_status='placed',
    )
    db.session.add(order)
    db.session.flush()  # assigns order.order_id without ending the transaction

    for li in line_items:
        db.session.add(OrderItem(order_id=order.order_id, **li))

    db.session.commit()

    notify(restaurant.owner_id, 'New order received',
           f'Order #{order.order_id} - Rs.{order.grand_total} - {delivery_address[:40]}',
           type='new_order', related_order_id=order.order_id)

    return order


# ---------- Customer order history / tracking ----------

def list_customer_orders(customer_id):
    return Order.query.filter_by(customer_id=customer_id).order_by(Order.placed_at.desc()).all()


def get_customer_order(customer_id, order_id):
    order = Order.query.get(order_id)
    if not order:
        raise OrderError('Order not found.', 404)
    if order.customer_id != int(customer_id):
        # Ownership check — stops customer A from tracking customer B's order
        # by guessing an order_id in the URL.
        raise OrderError('This is not your order.', 403)
    return order


def cancel_order(customer_id, order_id):
    order = get_customer_order(customer_id, order_id)
    if order.order_status != 'placed':
        raise OrderError(
            f"Cannot cancel — order is already '{order.order_status}'. "
            f"Once a restaurant accepts it, contact them directly."
        )
    order.order_status = 'cancelled'
    db.session.commit()
    return order
