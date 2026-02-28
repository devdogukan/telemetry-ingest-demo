"""
Flask application entry point.

This script creates and runs the Flask development server.
For production deployment, use a WSGI server like Gunicorn or uWSGI.

Usage:
    python run.py
    
    or with custom host/port:
    
    HOST=0.0.0.0 PORT=8000 python run.py
"""

import sys
import logging

from flask_app import create_app
from flask_app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    Create and run the Flask application.
    
    Raises:
        SystemExit: If configuration validation fails
    """
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        Config.validate()
        
        # Create Flask app
        logger.info("Creating Flask application...")
        app = create_app()
        
        # Display configuration
        Config.display_config()
        
        # Production warning
        if Config.FLASK_DEBUG:
            logger.warning("=" * 60)
            logger.warning("WARNING: Running in DEBUG mode!")
            logger.warning("This is NOT suitable for production use.")
            logger.warning("Set FLASK_DEBUG=False for production deployment.")
            logger.warning("=" * 60)
        
        # Run the application
        logger.info(f"Starting Flask server on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
        logger.info("Press CTRL+C to quit")
        
        app.run(
            host=Config.FLASK_HOST,
            port=Config.FLASK_PORT,
            debug=Config.FLASK_DEBUG,
            use_reloader=Config.FLASK_DEBUG,  # Only reload in debug mode
            threaded=True  # Handle multiple requests concurrently
        )
        
    except Exception as e:
        logger.error(f"Failed to start Flask application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
