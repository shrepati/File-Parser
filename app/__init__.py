"""
Flask Application Factory
Creates and configures the Flask application
"""

from flask import Flask, jsonify
from flask_cors import CORS

from config import settings, logging as log_config
from app.database import db_session, shutdown_session, init_db


def create_app(config=None):
    """
    Application factory pattern

    Args:
        config: Optional configuration override

    Returns:
        Flask: Configured Flask application
    """
    # Create Flask app
    app = Flask(__name__,
                template_folder='../frontend/templates',
                static_folder='../frontend/static')

    # Load configuration
    app.config['SECRET_KEY'] = settings.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = settings.MAX_UPLOAD_SIZE
    app.config['UPLOAD_FOLDER'] = settings.UPLOAD_FOLDER
    app.config['EXTRACT_FOLDER'] = settings.EXTRACT_FOLDER

    # Apply custom config if provided
    if config:
        app.config.update(config)

    # Setup CORS
    CORS(app, origins=settings.CORS_ORIGINS)

    # Setup logging
    logger = log_config.setup_logging('file-parser')
    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)

    # Initialize database
    with app.app_context():
        init_db()

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register teardown
    app.teardown_appcontext(shutdown_session)

    app.logger.info("File Extractor application initialized")

    return app


def register_blueprints(app):
    """Register all blueprints"""
    from app.blueprints.upload import upload_bp
    from app.blueprints.browse import browse_bp
    from app.blueprints.viewer import viewer_bp

    # Register with /api prefix
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(browse_bp, url_prefix='/api')
    app.register_blueprint(viewer_bp, url_prefix='/api')

    # Main route for serving frontend
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')


def register_error_handlers(app):
    """Register error handlers"""

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle file too large error"""
        from app.utils.security import get_file_size_human
        return jsonify({
            'error': 'File too large',
            'message': f'File size exceeds the maximum allowed size of {get_file_size_human(settings.MAX_UPLOAD_SIZE)}'
        }), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle internal server errors"""
        app.logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500

    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors"""
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404
