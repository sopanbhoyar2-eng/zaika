from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.notification_service import list_notifications, unread_count, mark_all_read

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    return jsonify({
        'notifications': [n.to_dict() for n in list_notifications(user_id)],
        'unread_count': unread_count(user_id),
    }), 200


@notifications_bp.route('/read-all', methods=['POST'])
@jwt_required()
def read_all():
    mark_all_read(get_jwt_identity())
    return jsonify({'message': 'All notifications marked read.'}), 200
