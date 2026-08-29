from flask import Flask, render_template, jsonify
from whitenoise import WhiteNoise
from flask_cors import CORS

from app.config import Config
from app.extensions import db, bcrypt, jwt, migrate


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Serves /static reliably behind Railway's proxy -- Flask's own static
    # handler isn't reliable there for every asset type.
    app.wsgi_app = WhiteNoise(app.wsgi_app, root='app/static/', prefix='static/')

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    from app.routes.auth_routes import auth_bp
    from app.routes.customer_routes import customer_bp
    from app.routes.restaurant_routes import restaurant_bp
    from app.routes.rider_routes import rider_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.notification_routes import notifications_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(customer_bp, url_prefix='/api/customer')
    app.register_blueprint(restaurant_bp, url_prefix='/api/restaurant')
    app.register_blueprint(rider_bp, url_prefix='/api/rider')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')

    from app import models  # noqa: F401 -- registers all models with SQLAlchemy

    @app.route('/api/health')
    def health_check():
        return {'status': 'ok', 'message': 'Food delivery API is running'}, 200

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/payments/webhook', methods=['POST'])
    def razorpay_webhook():
        from flask import request as flask_request
        from app.services.payment_service import handle_webhook, PaymentError
        signature = flask_request.headers.get('X-Razorpay-Signature', '')
        try:
            handle_webhook(flask_request.get_data(as_text=True), signature)
        except PaymentError as e:
            return jsonify({'error': e.message}), e.status_code
        return jsonify({'status': 'ok'}), 200

    return app
