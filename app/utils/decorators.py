from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def role_required(*allowed_roles):
    """Protects a route so only the given roles can access it.
    Usage: @role_required('restaurant') or @role_required('restaurant', 'admin')
    Must sit UNDER the @blueprint.route(...) decorator."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('role') not in allowed_roles:
                return jsonify({'error': 'Forbidden: you do not have permission for this action'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
