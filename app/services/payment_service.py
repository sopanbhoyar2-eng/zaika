import razorpay
from flask import current_app
from app.extensions import db
from app.models.order import Order
from app.models.payment import Payment


class PaymentError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _client():
    key_id = current_app.config.get('RAZORPAY_KEY_ID')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
    if not key_id or not key_secret:
        raise PaymentError('Payment gateway not configured. Add RAZORPAY_KEY_ID/SECRET to .env.', 500)
    return razorpay.Client(auth=(key_id, key_secret))


def create_payment_order(order):
    """Called right after our Order row exists, for upi/card orders only."""
    client = _client()
    amount_paise = int(round(float(order.grand_total) * 100))
    try:
        rp_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f'order_{order.order_id}',
            'notes': {'internal_order_id': str(order.order_id)},
        })
    except Exception as e:
        raise PaymentError(f'Could not create payment order: {str(e)}', 502)

    payment = Payment(order_id=order.order_id, gateway='razorpay',
                       gateway_order_id=rp_order['id'], amount=order.grand_total,
                       currency='INR', status='created')
    db.session.add(payment)
    db.session.commit()

    return {'razorpay_order_id': rp_order['id'], 'razorpay_key_id': current_app.config.get('RAZORPAY_KEY_ID'),
            'amount': amount_paise, 'currency': 'INR'}


def verify_payment(customer_id, order_id, razorpay_order_id, razorpay_payment_id, razorpay_signature):
    order = Order.query.get(order_id)
    if not order:
        raise PaymentError('Order not found.', 404)
    if order.customer_id != int(customer_id):
        raise PaymentError('This is not your order.', 403)

    payment = Payment.query.filter_by(order_id=order_id, gateway_order_id=razorpay_order_id).first()
    if not payment:
        raise PaymentError('No matching payment record for this order.', 404)

    client = _client()
    try:
        # The critical security step: proves this callback genuinely came from
        # Razorpay and the payment truly succeeded. Without this, anyone could
        # POST a fake "success" straight to our API and get a free order.
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        payment.status = 'failed'
        db.session.commit()
        raise PaymentError('Payment verification failed. Signature mismatch.', 400)

    payment.gateway_payment_id = razorpay_payment_id
    payment.status = 'paid'
    order.payment_status = 'paid'
    db.session.commit()
    return order


def handle_webhook(payload_body, signature_header):
    """Razorpay also calls this server-to-server, independent of the browser
    -- a safety net in case the frontend never gets to call verify-payment
    (closed tab, network drop, etc.) even though the payment succeeded."""
    import json
    webhook_secret = current_app.config.get('RAZORPAY_WEBHOOK_SECRET')
    if not webhook_secret:
        raise PaymentError('Webhook secret not configured.', 500)

    client = _client()
    try:
        client.utility.verify_webhook_signature(payload_body, signature_header, webhook_secret)
    except razorpay.errors.SignatureVerificationError:
        raise PaymentError('Invalid webhook signature.', 400)

    event = json.loads(payload_body)
    if event.get('event') == 'payment.captured':
        rp_payment = event['payload']['payment']['entity']
        payment = Payment.query.filter_by(gateway_order_id=rp_payment['order_id']).first()
        if payment and payment.status != 'paid':
            payment.gateway_payment_id = rp_payment['id']
            payment.status = 'paid'
            payment.order.payment_status = 'paid'
            db.session.commit()
    return True
