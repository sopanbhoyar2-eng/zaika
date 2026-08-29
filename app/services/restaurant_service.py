from app.extensions import db
from app.models.restaurant import Restaurant
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.services.notification_service import notify


class RestaurantError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# What the RESTAURANT is allowed to do to an order. Rider-side transitions
# (picked_up, delivered) get added when we build the Rider Panel milestone.
RESTAURANT_STATUS_TRANSITIONS = {
    'placed': ['accepted', 'cancelled'],
    'accepted': ['preparing', 'cancelled'],
    'preparing': ['ready_for_pickup'],
}


def _get_owned_restaurant(owner_id, restaurant_id):
    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        raise RestaurantError('Restaurant not found.', 404)
    if restaurant.owner_id != int(owner_id):
        # Stops Restaurant A from editing Restaurant B's menu just by guessing
        # an ID in the URL — this class of bug is called IDOR (Insecure Direct
        # Object Reference). role_required only checks "are you a restaurant
        # owner"; this checks "do you own THIS specific restaurant."
        raise RestaurantError('You do not own this restaurant.', 403)
    return restaurant


def create_restaurant(owner_id, data):
    name = (data.get('name') or '').strip()
    address = (data.get('address') or '').strip()
    city = (data.get('city') or '').strip()

    if not name or len(name) < 2:
        raise RestaurantError('Restaurant name is required.')
    if not address:
        raise RestaurantError('Address is required.')
    if not city:
        raise RestaurantError('City is required.')

    restaurant = Restaurant(
        owner_id=owner_id,
        name=name,
        description=(data.get('description') or '').strip() or None,
        cuisine_type=(data.get('cuisine_type') or '').strip() or None,
        address=address,
        city=city,
        fssai_license=(data.get('fssai_license') or '').strip() or None,
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
    )
    db.session.add(restaurant)
    db.session.commit()
    return restaurant


def list_owned_restaurants(owner_id):
    return Restaurant.query.filter_by(owner_id=owner_id).all()


def update_restaurant(owner_id, restaurant_id, data):
    restaurant = _get_owned_restaurant(owner_id, restaurant_id)
    for field in ('name', 'description', 'cuisine_type', 'address', 'city', 'fssai_license'):
        if field in data and data[field] is not None:
            value = data[field]
            setattr(restaurant, field, value.strip() if isinstance(value, str) else value)
    if data.get('latitude') is not None:
        restaurant.latitude = data['latitude']
    if data.get('longitude') is not None:
        restaurant.longitude = data['longitude']
    db.session.commit()
    return restaurant


def toggle_restaurant_status(owner_id, restaurant_id):
    restaurant = _get_owned_restaurant(owner_id, restaurant_id)
    restaurant.is_open = not restaurant.is_open
    db.session.commit()
    return restaurant


def create_menu_item(owner_id, restaurant_id, data):
    _get_owned_restaurant(owner_id, restaurant_id)

    name = (data.get('name') or '').strip()
    price = data.get('price')

    if not name or len(name) < 2:
        raise RestaurantError('Item name is required.')
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise RestaurantError('Price must be a number.')
    if price <= 0:
        raise RestaurantError('Price must be greater than 0.')

    item = MenuItem(
        restaurant_id=restaurant_id,
        name=name,
        description=(data.get('description') or '').strip() or None,
        price=price,
        category=(data.get('category') or '').strip() or None,
        is_veg=bool(data.get('is_veg', True)),
    )
    db.session.add(item)
    db.session.commit()
    return item


def list_menu_items(owner_id, restaurant_id):
    _get_owned_restaurant(owner_id, restaurant_id)
    return MenuItem.query.filter_by(restaurant_id=restaurant_id).all()


def _get_owned_menu_item(owner_id, item_id):
    item = MenuItem.query.get(item_id)
    if not item:
        raise RestaurantError('Menu item not found.', 404)
    _get_owned_restaurant(owner_id, item.restaurant_id)
    return item


def update_menu_item(owner_id, item_id, data):
    item = _get_owned_menu_item(owner_id, item_id)

    if data.get('name'):
        item.name = data['name'].strip()
    if 'description' in data:
        item.description = (data['description'] or '').strip() or None
    if data.get('price') is not None:
        try:
            price = float(data['price'])
        except (TypeError, ValueError):
            raise RestaurantError('Price must be a number.')
        if price <= 0:
            raise RestaurantError('Price must be greater than 0.')
        item.price = price
    if 'category' in data:
        item.category = (data['category'] or '').strip() or None
    if 'is_veg' in data:
        item.is_veg = bool(data['is_veg'])

    db.session.commit()
    return item


def delete_menu_item(owner_id, item_id):
    item = _get_owned_menu_item(owner_id, item_id)
    db.session.delete(item)
    db.session.commit()


def toggle_menu_item_availability(owner_id, item_id):
    item = _get_owned_menu_item(owner_id, item_id)
    item.is_available = not item.is_available
    db.session.commit()
    return item


def upload_menu_item_photo(owner_id, item_id, file):
    import os as _os
    import cloudinary
    import cloudinary.uploader
    from flask import current_app

    item = _get_owned_menu_item(owner_id, item_id)

    if not file or file.filename == '':
        raise RestaurantError('No photo file provided.')
    ext = _os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        raise RestaurantError('Only JPG, PNG, or WEBP images are allowed.')

    cloud_name = current_app.config.get('CLOUDINARY_CLOUD_NAME')
    api_key = current_app.config.get('CLOUDINARY_API_KEY')
    api_secret = current_app.config.get('CLOUDINARY_API_SECRET')
    if not all([cloud_name, api_key, api_secret]):
        raise RestaurantError('Image upload is not configured. Add CLOUDINARY_* to .env.', 500)
    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)

    try:
        # Resized + compressed on Cloudinary's side so the customer app never
        # has to download a multi-MB phone photo just to show a menu thumbnail.
        result = cloudinary.uploader.upload(
            file, folder='zaika_menu_items',
            transformation=[{'width': 600, 'height': 600, 'crop': 'fill', 'quality': 'auto'}],
        )
    except Exception as e:
        raise RestaurantError(f'Image upload failed: {str(e)}', 502)

    item.image_url = result['secure_url']
    db.session.commit()
    return item


def list_restaurant_orders(owner_id, restaurant_id, status=None):
    _get_owned_restaurant(owner_id, restaurant_id)
    query = Order.query.filter_by(restaurant_id=restaurant_id)
    if status:
        query = query.filter_by(order_status=status)
    return query.order_by(Order.placed_at.desc()).all()


def get_restaurant_earnings(owner_id, restaurant_id):
    """MVP model: the restaurant earns item_total (food value) per delivered
    order. delivery_fee and taxes pass through to the rider/platform, not the
    restaurant — mirrors how the rider earnings model in Milestone 5 only
    counts delivery_fee, not the food price."""
    _get_owned_restaurant(owner_id, restaurant_id)
    all_orders = Order.query.filter_by(restaurant_id=restaurant_id).all()
    delivered = [o for o in all_orders if o.order_status == 'delivered']
    cancelled = [o for o in all_orders if o.order_status == 'cancelled']
    active = [o for o in all_orders if o.order_status not in ('delivered', 'cancelled')]
    return {
        'total_orders': len(all_orders),
        'delivered_orders': len(delivered),
        'active_orders': len(active),
        'cancelled_orders': len(cancelled),
        'total_revenue': round(sum(float(o.item_total) for o in delivered), 2),
    }


def update_order_status(owner_id, order_id, new_status):
    order = Order.query.get(order_id)
    if not order:
        raise RestaurantError('Order not found.', 404)
    _get_owned_restaurant(owner_id, order.restaurant_id)

    allowed_next = RESTAURANT_STATUS_TRANSITIONS.get(order.order_status, [])
    if new_status not in allowed_next:
        fallback = 'none, this order has already left the restaurant'
        raise RestaurantError(
            f"Cannot move an order from '{order.order_status}' to '{new_status}'. "
            f"Allowed next step(s): {allowed_next or fallback}."
        )

    order.order_status = new_status
    db.session.commit()

    notify(order.customer_id, 'Order update',
           f"Your order #{order.order_id} is now {new_status.replace('_', ' ')}",
           type='order_status', related_order_id=order.order_id)

    return order
