from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity
)

from app.models.user import User
from app.services.auth_service import register_user, authenticate_user, AuthError

auth_bp = Blueprint('auth', __name__)


def _issue_tokens(user):
    claims = {'role': user.role}
    access_token = create_access_token(identity=str(user.user_id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.user_id), additional_claims=claims)
    return access_token, refresh_token


@auth_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'blueprint': 'auth', 'status': 'ready'}), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    try:
        user = register_user(data)
    except AuthError as e:
        return jsonify({'error': e.message}), e.status_code

    if user.role == 'customer':
        access_token, refresh_token = _issue_tokens(user)
        return jsonify({
            'message': 'Account created successfully.',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token,
        }), 201

    return jsonify({
        'message': 'Account created. It will be reviewed by an admin before you can log in.',
        'user': user.to_dict(),
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    try:
        user = authenticate_user(data.get('email'), data.get('password'))
    except AuthError as e:
        return jsonify({'error': e.message}), e.status_code

    access_token, refresh_token = _issue_tokens(user)
    return jsonify({
        'message': 'Login successful.',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token,
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    access_token, _ = _issue_tokens(user)
    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    return jsonify({'user': user.to_dict()}), 200
