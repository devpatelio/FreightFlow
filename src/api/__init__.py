"""Flask application factory for the FreightFlow API."""

from flask import Flask, jsonify
from flask_cors import CORS

from .config import Config, ensure_dirs


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        origins=Config.CORS_ORIGINS,
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization'],
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    )

    ensure_dirs()

    # Register blueprints
    from .routes.customers import bp as customers_bp
    from .routes.addresses import bp as addresses_bp
    from .routes.sellers import bp as sellers_bp
    from .routes.products import bp as products_bp
    from .routes.organizations import bp as organizations_bp
    from .routes.documents import bp as documents_bp
    from .routes.templates import bp as templates_bp
    from .routes.schemas import bp as schemas_bp
    from .routes.pipelines import bp as pipelines_bp
    from .routes.profiles import bp as profiles_bp

    app.register_blueprint(customers_bp)
    app.register_blueprint(addresses_bp)
    app.register_blueprint(sellers_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(schemas_bp)
    app.register_blueprint(pipelines_bp)
    app.register_blueprint(profiles_bp)

    # Health check
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Resource not found'}}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': 'Internal server error'}}), 500

    return app
