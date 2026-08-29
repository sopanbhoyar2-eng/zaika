from app.extensions import db, bcrypt
from app.models.user import User
from app.utils.validators import is_valid_email, is_valid_phone, is_valid_password

# Admin is deliberately excluded — admin accounts must never be created through
# a public API. That's created by seeding the DB directly (see README).
PUBLIC_REGISTERABLE_ROLES = ('customer', 'restaurant', 'rider')


class AuthError(Exception):
    """Raised on any auth failure. The route layer catches this and converts
    it into the right HTTP status code, so validation logic stays out of routes."""
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_user(data):
    full_name = (data.get('full_name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    phone = (data.get('phone') or '').strip()
    password = data.get('password') or ''
    role = (data.get('role') or 'customer').strip().lower()

    if not full_name or len(full_name) < 2:
        raise AuthError('full_name is required (minimum 2 characters).')
    if not is_valid_email(email):
        raise AuthError('A valid email is required.')
    if not is_valid_phone(phone):
        raise AuthError('A valid 10-digit phone number is required.')
    if not is_valid_password(password):
        raise AuthError('Password must be at least 8 characters.')
    if role not in PUBLIC_REGISTERABLE_ROLES:
        raise AuthError('Invalid role. Choose customer, restaurant, or rider.')

    if User.query.filter_by(email=email).first():
        raise AuthError('An account with this email already exists.', status_code=409)
    if User.query.filter_by(phone=phone).first():
        raise AuthError('An account with this phone number already exists.', status_code=409)

    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    # Customers can order immediately. Restaurants and riders need an admin to
    # verify them first (FSSAI license / vehicle-KYC checks come in a later
    # milestone) — so their account is created but held inactive until approved.
    is_active = role == 'customer'

    user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )
    db.session.add(user)
    db.session.commit()
    return user


def authenticate_user(email, password):
    email = (email or '').strip().lower()
    password = password or ''

    if not email or not password:
        raise AuthError('Email and password are required.')

    user = User.query.filter_by(email=email).first()

    # Deliberately the SAME error whether the email doesn't exist or the
    # password is wrong. Telling attackers "email not found" vs "wrong
    # password" lets them discover which emails have accounts.
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        raise AuthError('Invalid email or password.', status_code=401)

    if not user.is_active:
        raise AuthError('Your account is pending admin approval.', status_code=403)

    return user
