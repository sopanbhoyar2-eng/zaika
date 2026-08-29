"""
One-time utility: creates an admin account directly in the database.

Why this exists as a separate script instead of an API endpoint: admin
accounts are deliberately NEVER created through the public /api/auth/register
endpoint (see Milestone 2's auth_service.py) -- exposing "become an admin" as
a public API call is one of the most common ways apps like this get hacked.
This script is the correct, safe way to create the first admin.

Usage (with your virtualenv active, same folder as run.py):
    python create_admin.py
"""
from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User
from app.utils.validators import is_valid_email, is_valid_phone, is_valid_password

app = create_app()

with app.app_context():
    print("--- Create admin account ---")
    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()
    phone = input("Admin phone (10 digits): ").strip()
    password = input("Admin password (min 8 chars): ").strip()

    if User.query.filter_by(email=email).first():
        print(f"A user with email '{email}' already exists. Aborting.")
        raise SystemExit(1)
    if not is_valid_email(email):
        print("That doesn't look like a valid email. Aborting.")
        raise SystemExit(1)
    if not is_valid_phone(phone):
        print("Phone must be a 10-digit number (optionally with 91/+91 prefix). Aborting.")
        raise SystemExit(1)
    if not is_valid_password(password):
        print("Password must be at least 8 characters. Aborting.")
        raise SystemExit(1)

    admin = User(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role="admin",
        is_active=True,
    )
    db.session.add(admin)
    db.session.commit()
    print(f"\nAdmin account created: {email}")
    print("Log in at http://localhost:5000/ with this email and password.")
