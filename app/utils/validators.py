import re

EMAIL_REGEX = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
# Accepts a bare 10-digit number, or one prefixed with 91 / +91.
PHONE_REGEX = re.compile(r'^(\+91|91)?\d{10}$')


def is_valid_email(email):
    return bool(email) and bool(EMAIL_REGEX.match(email))


def is_valid_phone(phone):
    if not phone:
        return False
    return bool(PHONE_REGEX.match(phone.replace(' ', '')))


def is_valid_password(password):
    return bool(password) and len(password) >= 8
