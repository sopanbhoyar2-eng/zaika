from app.extensions import db
from app.models.notification import Notification


class NotificationError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def notify(user_id, title, message, type=None, related_order_id=None):
    """Called from other services whenever something notification-worthy
    happens (new order, status change, approval, etc). One place, so every
    trigger point behaves consistently."""
    n = Notification(user_id=user_id, title=title, message=message,
                      type=type, related_order_id=related_order_id)
    db.session.add(n)
    db.session.commit()
    return n


def list_notifications(user_id):
    return Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(50).all()


def unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_all_read(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
