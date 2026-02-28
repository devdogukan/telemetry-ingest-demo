"""
Database initialization script.

Creates the telemetries table and populates it with sample data.
This script should be run once during initial setup or when resetting the database.
"""

import sys
import logging
from typing import Optional

import psycopg
from psycopg import Connection

from flask_app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_tables(cur) -> None:
    """
    Create database tables.
    
    Args:
        cur: Database cursor
    """
    logger.info("Dropping existing telemetries table if exists...")
    cur.execute("DROP TABLE IF EXISTS telemetries;")
    
    logger.info("Creating telemetries table...")
    cur.execute("""
        CREATE TABLE telemetries (
            id SERIAL PRIMARY KEY,
            sensor_id VARCHAR(50) NOT NULL,
            temperature DOUBLE PRECISION NOT NULL,
            recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Create index for better query performance
    logger.info("Creating index on sensor_id...")
    cur.execute("""
        CREATE INDEX idx_telemetries_sensor_id ON telemetries(sensor_id);
    """)
    
    logger.info("Creating index on recorded_at...")
    cur.execute("""
        CREATE INDEX idx_telemetries_recorded_at ON telemetries(recorded_at DESC);
    """)
    
    logger.info("Tables created successfully")


def insert_sample_data(cur) -> None:
    """
    Insert sample telemetry records.
    
    Args:
        cur: Database cursor
    """
    logger.info("Inserting sample data...")
    
    sample_data = [
        ("room_24", 22.5),
        ("room_25", 23.1),
        ("room_26", 21.8),
        ("outdoor_1", 15.2),
        ("outdoor_2", 16.7),
    ]
    
    cur.executemany(
        "INSERT INTO telemetries (sensor_id, temperature) VALUES (%s, %s)",
        sample_data
    )
    
    logger.info(f"Inserted {len(sample_data)} sample records")


def init_db() -> bool:
    """
    Initialize the database with schema and sample data.
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn: Optional[Connection] = None
    cur = None
    
    try:
        logger.info("=" * 60)
        logger.info("Database Initialization Starting")
        logger.info("=" * 60)
        logger.info(f"Connecting to: {Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{Config.POSTGRES_DB}")
        
        # Connect to database
        conn = psycopg.connect(Config.DATABASE_URL)
        logger.info("Database connection established")
        
        cur = conn.cursor()
        
        # Create tables
        create_tables(cur)
        
        # Insert sample data
        insert_sample_data(cur)
        
        # Commit changes
        conn.commit()
        logger.info("All changes committed successfully")
        
        # Verify data
        cur.execute("SELECT COUNT(*) FROM telemetries;")
        count = cur.fetchone()[0]
        logger.info(f"Verification: {count} records in telemetries table")
        
        logger.info("=" * 60)
        logger.info("Database Initialization Completed Successfully")
        logger.info("=" * 60)
        
        return True
        
    except psycopg.OperationalError as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        logger.error("Please check your database configuration and ensure the database server is running")
        return False
        
    except psycopg.Error as e:
        logger.error(f"Database error during initialization: {e}", exc_info=True)
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}", exc_info=True)
        return False
        
    finally:
        # Clean up
        if cur:
            cur.close()
            logger.debug("Cursor closed")
        if conn:
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    logger.info("Running database initialization script...")
    
    # Validate configuration
    try:
        Config.validate()
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)
    
    # Initialize database
    success = init_db()
    
    if success:
        logger.info("Database is ready for use!")
        sys.exit(0)
    else:
        logger.error("Database initialization failed!")
        sys.exit(1)