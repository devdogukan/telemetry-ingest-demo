"""
Flask application factory module.

Creates and configures the Flask application instance with all necessary
routes, error handlers, and middleware.
"""

import logging
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from flask_app.routes import register_routes
from flask_app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Create and configure Flask application.
    
    Returns:
        Flask: Configured Flask application instance
        
    Raises:
        Exception: If application creation fails
    """
    try:
        app = Flask(__name__)
        
        # Load configuration
        app.config['DEBUG'] = Config.FLASK_DEBUG
        app.config['ENV'] = Config.FLASK_ENV
        
        logger.info(f"Creating Flask app in {Config.FLASK_ENV} mode")
        
        # Register routes
        register_routes(app)
        logger.info("Routes registered successfully")
        
        # Register error handlers
        register_error_handlers(app)
        logger.info("Error handlers registered successfully")
        
        # Log startup
        Config.display_config()
        logger.info("Flask application started successfully")
        
        return app
        
    except Exception as e:
        logger.error(f"Failed to create Flask application: {e}", exc_info=True)
        raise


def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers for the Flask application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        logger.warning(f"404 error: {error}")
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found"
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"500 error: {error}", exc_info=True)
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle all other HTTP exceptions."""
        logger.warning(f"HTTP exception: {error.code} - {error.description}")
        return jsonify({
            "error": error.name,
            "message": error.description
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all unhandled exceptions."""
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }), 500