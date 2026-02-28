"""
Celery tasks for direct database insertion (without batching).

This module provides a simple task for writing individual telemetry
records directly to the database. For high-throughput scenarios,
consider using tasks_with_batch.py instead.
"""

import logging
from typing import Dict, Any

from celery import Celery
from psycopg_pool import ConnectionPool

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
        timeout=Config.DB_POOL_TIMEOUT
    )
    logger.info("Database connection pool initialized for tasks")
except Exception as e:
    logger.error(f"Failed to initialize database connection pool: {e}")
    raise

# Initialize Celery app
celery_app = Celery(
    "tasks",
    broker=Config.BROKER_URL,
    backend=Config.BROKER_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(bind=True, max_retries=3)
def save_to_db_async(self, sensor_id: str, temperature: float) -> Dict[str, Any]:
    """
    Save telemetry data to database asynchronously.
    
    This task writes a single telemetry record directly to the database.
    For high-throughput scenarios, consider using batch processing instead.
    
    Args:
        sensor_id: Unique identifier for the sensor
        temperature: Temperature reading from the sensor
        
    Returns:
        dict: Result information including status and details
        
    Raises:
        Exception: Re-raises after max retries
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO telemetries (sensor_id, temperature) VALUES (%s, %s)",
                    (sensor_id, temperature)
                )
                conn.commit()
                
        logger.info(
            f"Telemetry data saved: sensor={sensor_id}, "
            f"temperature={temperature}°C, task_id={self.request.id}"
        )
        
        return {
            "status": "success",
            "sensor_id": sensor_id,
            "temperature": temperature,
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(
            f"Error saving telemetry data: sensor={sensor_id}, "
            f"temperature={temperature}, error={e}",
            exc_info=True
        )
        
        # Retry with exponential backoff
        try:
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except self.MaxRetriesExceededError:
            logger.error(
                f"Max retries exceeded for sensor {sensor_id}. "
                f"Data may be lost: temperature={temperature}"
            )
            return {
                "status": "failed",
                "sensor_id": sensor_id,
                "temperature": temperature,
                "error": str(e),
                "task_id": self.request.id
            }