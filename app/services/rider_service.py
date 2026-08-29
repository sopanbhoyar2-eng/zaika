from app.extensions import db
from app.models.order import Order
from app.models.delivery_log import DeliveryLog
from app.services.notification_service import notify


class RiderError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# The rider's journey is more fine-grained than orders.order_status. Every
# step gets its own delivery_logs row (full history / powers live tracking);
# only the two milestones customers/restaurants care about also update the
# order's headline order_status.
CHECKPOINT_SEQUENCE = ['assigned', 'accepted_by_rider', 'reached_restaurant',
                        'picked_up', 'reached_customer', 'delivered']
ORDER_STATUS_SYNC = {'picked_up': 'picked_up', 'delivered': 'delivered'}


def list_available_orders():
    """Food is ready and no rider has claimed it yet."""
    return (Order.query.filter_by(order_status='ready_for_pickup', rider_id=None)
            .order_by(Order.placed_at).all())


def list_my_deliveries(rider_id):
    return Order.query.filter_by(rider_id=rider_id).order_by(Order.placed_at.desc()).all()


def claim_order(rider_id, order_id):
    order = Order.query.get(order_id)
    if not order:
        raise RiderError('Order not found.', 404)
    if order.order_status != 'ready_for_pickup':
        raise RiderError(f"Order is '{order.order_status}', not ready for pickup yet.")
    if order.rider_id is not None:
        raise RiderError('Another rider has already claimed this order.', 409)

    order.rider_id = rider_id
    db.session.add(DeliveryLog(order_id=order.order_id, rider_id=rider_id,
                                status='assigned', notes='Claimed by rider'))
    db.session.commit()

    notify(order.customer_id, 'Rider assigned',
           f'A delivery partner has been assigned to order #{order.order_id}.',
           type='order_status', related_order_id=order.order_id)

    return order


def _get_own_delivery(rider_id, order_id):
    order = Order.query.get(order_id)
    if not order:
        raise RiderError('Order not found.', 404)
    if order.rider_id != int(rider_id):
        # Ownership check — stops Rider A from updating Rider B's delivery.
        raise RiderError('This delivery is not assigned to you.', 403)
    return order


def advance_checkpoint(rider_id, order_id, checkpoint, latitude=None, longitude=None, notes=None):
    order = _get_own_delivery(rider_id, order_id)

    last_log = (DeliveryLog.query.filter_by(order_id=order.order_id)
                .order_by(DeliveryLog.logged_at.desc()).first())
    current_index = (CHECKPOINT_SEQUENCE.index(last_log.status)
                      if last_log and last_log.status in CHECKPOINT_SEQUENCE else -1)

    if checkpoint not in CHECKPOINT_SEQUENCE:
        raise RiderError(f'Unknown checkpoint. Must be one of: {CHECKPOINT_SEQUENCE}')

    requested_index = CHECKPOINT_SEQUENCE.index(checkpoint)
    if requested_index != current_index + 1:
        next_expected = (CHECKPOINT_SEQUENCE[current_index + 1]
                          if current_index + 1 < len(CHECKPOINT_SEQUENCE) else None)
        raise RiderError(f"Checkpoints must be reported in order. Next expected: '{next_expected}'.")

    db.session.add(DeliveryLog(order_id=order.order_id, rider_id=rider_id, status=checkpoint,
                                latitude=latitude, longitude=longitude, notes=notes))

    if checkpoint in ORDER_STATUS_SYNC:
        order.order_status = ORDER_STATUS_SYNC[checkpoint]
        # COD is collected in person, so it's only "paid" once actually delivered.
        if checkpoint == 'delivered' and order.payment_method == 'cod':
            order.payment_status = 'paid'

    db.session.commit()

    if checkpoint in ORDER_STATUS_SYNC:
        notify(order.customer_id, 'Order update',
               f"Your order #{order.order_id} is now {order.order_status.replace('_', ' ')}",
               type='order_status', related_order_id=order.order_id)

    return order


def ping_location(rider_id, order_id, latitude, longitude):
    """Lightweight, frequent position update -- deliberately separate from
    advance_checkpoint's strict sequence rules. This just re-logs the rider's
    CURRENT status with a fresh lat/lng, so the customer's tracking map can
    show live movement without the rider having to 'complete a step' every
    time their phone reports a new GPS position."""
    order = _get_own_delivery(rider_id, order_id)
    last_log = (DeliveryLog.query.filter_by(order_id=order.order_id)
                .order_by(DeliveryLog.logged_at.desc()).first())
    current_status = last_log.status if last_log else 'assigned'
    db.session.add(DeliveryLog(order_id=order.order_id, rider_id=rider_id, status=current_status,
                                latitude=latitude, longitude=longitude, notes='location ping'))
    db.session.commit()
    return order


def cancel_delivery(rider_id, order_id, notes=None):
    """Rider can't complete it after all -- releases it back to the pool for another rider."""
    order = _get_own_delivery(rider_id, order_id)
    if order.order_status != 'ready_for_pickup':
        raise RiderError('Can only release a delivery before it has been picked up.')
    order.rider_id = None
    db.session.add(DeliveryLog(order_id=order.order_id, rider_id=rider_id, status='cancelled',
                                notes=notes or 'Rider released the delivery'))
    db.session.commit()
    return order


def get_earnings_summary(rider_id):
    """MVP model: rider earns the full delivery_fee per completed order.
    Incentives/surge/payout batching can refine this later."""
    delivered = Order.query.filter_by(rider_id=rider_id, order_status='delivered').all()
    return {
        'total_deliveries': len(delivered),
        'total_earnings': round(sum(float(o.delivery_fee) for o in delivered), 2),
    }
