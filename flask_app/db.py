"""
Database connection pool management module.

Provides a centralized connection pool for PostgreSQL database access
using psycopg3's ConnectionPool for efficient connection management.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from psycopg_pool import ConnectionPool
from psycopg import Connection

from flask_app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Initialize connection pool
try:
    pool = ConnectionPool(
        Config.DATABASE_URL,
        min_size=Config.DB_POOL_MIN_SIZE,
        max_size=Config.DB_POOL_MAX_SIZE,
        timeout=Config.DB_POOL_TIMEOUT,
        name="main_pool"
    )
    logger.info(
        f"Database connection pool initialized: "
        f"{Config.DB_POOL_MIN_SIZE}-{Config.DB_POOL_MAX_SIZE} connections"
    )
except Exception as e:
    logger.error(f"Failed to initialize database connection pool: {e}", exc_info=True)
    raise


@contextmanager
def get_db_connection() -> Generator[Connection, None, None]:
    """
    Get a database connection from the pool as a context manager.
    
    Usage:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM table")
                results = cur.fetchall()
    
    Yields:
        Connection: A PostgreSQL database connection
        
    Raises:
        Exception: If connection cannot be obtained from pool
    """
    conn = None
    try:
        conn = pool.connection()
        logger.debug("Database connection acquired from pool")
        yield conn
    except Exception as e:
        logger.error(f"Error getting database connection: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection returned to pool")


def check_pool_status() -> dict:
    """
    Get current connection pool statistics.
    
    Returns:
        dict: Pool statistics including size and available connections
    """
    try:
        stats = {
            "name": pool.name,
            "min_size": Config.DB_POOL_MIN_SIZE,
            "max_size": Config.DB_POOL_MAX_SIZE,
            "timeout": Config.DB_POOL_TIMEOUT,
        }
        logger.debug(f"Pool status: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error getting pool status: {e}")
        return {}


def close_pool() -> None:
    """
    Close the connection pool and all connections.
    
    Should be called during application shutdown.
    """
    try:
        pool.close()
        logger.info("Database connection pool closed successfully")
    except Exception as e:
        logger.error(f"Error closing connection pool: {e}", exc_info=True)