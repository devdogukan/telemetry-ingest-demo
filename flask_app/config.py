"""
Application configuration module.

Loads environment variables and provides configuration constants
for database, Redis, and application settings.
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class Config:
    """
    Application configuration class.
    
    Loads all configuration from environment variables and provides
    centralized access to application settings.
    """
    
    # PostgreSQL Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")

    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "1"))

    # Connection URLs
    DATABASE_URL: str = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    BROKER_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    # Redis Buffer Configuration
    REDIS_BUFFER_KEY: str = "telemetry_buffer"
    REDIS_BULK_SIZE: int = int(os.getenv("REDIS_BULK_SIZE", "100"))
    REDIS_BULK_INTERVAL: int = int(os.getenv("REDIS_BULK_INTERVAL", "5"))  # seconds
    
    # Database Connection Pool Configuration
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # seconds

    # Flask Configuration
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))

    @classmethod
    def validate(cls) -> None:
        """
        Validate that all required configuration values are set.
        
        Raises:
            ConfigError: If any required configuration is missing
        """
        required_vars = [
            ("POSTGRES_USER", cls.POSTGRES_USER),
            ("POSTGRES_PASSWORD", cls.POSTGRES_PASSWORD),
            ("POSTGRES_DB", cls.POSTGRES_DB),
            ("POSTGRES_HOST", cls.POSTGRES_HOST),
            ("REDIS_HOST", cls.REDIS_HOST),
        ]
        
        missing = [name for name, value in required_vars if not value]
        
        if missing:
            error_msg = f"Missing required configuration: {', '.join(missing)}"
            logger.error(error_msg)
            raise ConfigError(error_msg)
        
        logger.info("Configuration validated successfully")

    @classmethod
    def display_config(cls, hide_sensitive: bool = True) -> None:
        """
        Display current configuration (useful for debugging).
        
        Args:
            hide_sensitive: If True, masks sensitive values like passwords
        """
        logger.info("=" * 50)
        logger.info("Application Configuration:")
        logger.info(f"  Database: {cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}")
        logger.info(f"  Redis: {cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}")
        logger.info(f"  DB Pool: {cls.DB_POOL_MIN_SIZE}-{cls.DB_POOL_MAX_SIZE} connections")
        logger.info(f"  Batch Size: {cls.REDIS_BULK_SIZE}")
        logger.info(f"  Batch Interval: {cls.REDIS_BULK_INTERVAL}s")
        logger.info(f"  Flask: {cls.FLASK_HOST}:{cls.FLASK_PORT} (debug={cls.FLASK_DEBUG})")
        logger.info("=" * 50)


# Validate configuration on module import
try:
    Config.validate()
except ConfigError as e:
    logger.warning(f"Configuration validation failed: {e}")
    logger.warning("Application may not work correctly without proper configuration")
