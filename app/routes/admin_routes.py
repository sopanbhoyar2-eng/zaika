from flask import Blueprint, jsonify
from app.utils.decorators import role_required
from app.models.user import User
from app.extensions import db
from app.services.notification_service import notify

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'blueprint': 'admin', 'status': 'ready'}), 200


@admin_bp.route('/pending-approvals', methods=['GET'])
@role_required('admin')
def pending_approvals():
    """Real query: every restaurant/rider account still waiting on approval."""
    pending = User.query.filter_by(is_active=False).all()
    return jsonify({'pending_approvals': [u.to_dict() for u in pending]}), 200


@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@role_required('admin')
def approve_user(user_id):
    """Activates a pending restaurant/rider account."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    if user.role not in ('restaurant', 'rider'):
        return jsonify({'error': 'Only restaurant and rider accounts require approval.'}), 400
    user.is_active = True
    db.session.commit()
    notify(user.user_id, 'Account approved', 'Your account has been approved. You can now log in.',
           type='account_approved')
    return jsonify({'message': f'{user.full_name} approved.', 'user': user.to_dict()}), 200


@admin_bp.route('/stats', methods=['GET'])
@role_required('admin')
def stats():
    """Platform-wide overview. Nothing here needs a new table — it's all
    aggregated from users/restaurants/orders, which is why we built Milestones
    1-8 with clean queryable relationships in the first place."""
    from app.models.restaurant import Restaurant
    from app.models.order import Order

    orders = Order.query.all()
    delivered = [o for o in orders if o.order_status == 'delivered']
    active = [o for o in orders if o.order_status not in ('delivered', 'cancelled')]

    return jsonify({
        'users': {
            'customers': User.query.filter_by(role='customer').count(),
            'restaurants': User.query.filter_by(role='restaurant').count(),
            'riders': User.query.filter_by(role='rider').count(),
            'pending_approval': User.query.filter_by(is_active=False).count(),
        },
        'restaurants': {
            'total': Restaurant.query.count(),
            'open_now': Restaurant.query.filter_by(is_open=True).count(),
        },
        'orders': {
            'total': len(orders),
            'delivered': len(delivered),
            'active': len(active),
            'gmv': round(sum(float(o.grand_total) for o in delivered), 2),
        },
    }), 200
