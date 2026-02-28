"""
Celery tasks for batch processing telemetry data.

This module handles telemetry data collection and batch processing using:
- Celery for task queue management
- Redis as a buffer for incoming telemetry data
- PostgreSQL for persistent storage
- Batch processing to optimize database writes
"""

import json
import logging
from typing import Dict, List, Any, Optional

import redis
from celery import Celery
from psycopg_pool import ConnectionPool

from flask_app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Initialize connection pool
try:
    pool = ConnectionPool(
        Config.DATABASE_URL,
        min_size=Config.DB_POOL_MIN_SIZE,
        max_size=Config.DB_POOL_MAX_SIZE,
        timeout=30
    )
    logger.info("Database connection pool initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database connection pool: {e}")
    raise

# Initialize Redis connection
try:
    redis_client = redis.Redis(
        host=Config.REDIS_HOST,
        port=int(Config.REDIS_PORT),
        db=Config.REDIS_DB,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True
    )
    redis_client.ping()
    logger.info("Redis connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    raise


def insert_bulk(batch: List[Dict[str, Any]]) -> bool:
    """
    Insert a batch of telemetry records into the database.
    
    Args:
        batch: List of telemetry data dictionaries containing sensor_id and temperature
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not batch:
        logger.warning("Attempted to insert empty batch")
        return False
    
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                values = [
                    (item["sensor_id"], item["temperature"]) 
                    for item in batch
                ]
                cur.executemany(
                    "INSERT INTO telemetries (sensor_id, temperature) VALUES (%s, %s)",
                    values
                )
                conn.commit()
                logger.info(f"Successfully inserted batch of {len(batch)} telemetries")
                return True
                
    except KeyError as e:
        logger.error(f"Missing required field in telemetry data: {e}")
        return False
    except Exception as e:
        logger.error(f"Error inserting batch telemetry data: {e}", exc_info=True)
        return False


@celery_app.task(bind=True, max_retries=3)
def enqueue_telemetry(self, sensor_id: str, temperature: float) -> Optional[int]:
    """
    Enqueue telemetry data to Redis buffer for batch processing.
    
    Args:
        sensor_id: Unique identifier for the sensor
        temperature: Temperature reading from the sensor
        
    Returns:
        int: New length of the buffer, or None if failed
        
    Raises:
        Exception: Re-raises after max retries
    """
    try:
        telemetry_data = {
            "sensor_id": sensor_id,
            "temperature": temperature
        }
        buffer_len = redis_client.rpush(
            Config.REDIS_BUFFER_KEY,
            json.dumps(telemetry_data)
        )
        logger.debug(f"Enqueued telemetry from {sensor_id}, buffer length: {buffer_len}")
        return buffer_len
        
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
    except Exception as e:
        logger.error(f"Error enqueuing telemetry: {e}", exc_info=True)
        raise


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks for batch processing."""
    sender.add_periodic_task(
        Config.REDIS_BULK_INTERVAL,
        process_buffer.s(),
        name=f"Process telemetry buffer every {Config.REDIS_BULK_INTERVAL} seconds"
    )
    logger.info(f"Periodic task configured: process buffer every {Config.REDIS_BULK_INTERVAL} seconds")


@celery_app.task(bind=True)
def process_buffer(self) -> Dict[str, Any]:
    """
    Process telemetry buffer by reading batch from Redis and inserting into database.
    
    Returns:
        dict: Processing statistics including processed count and success status
    """
    try:
        buffer_len = redis_client.llen(Config.REDIS_BUFFER_KEY)
        
        if buffer_len == 0:
            logger.debug("Buffer is empty, nothing to process")
            return {"processed": 0, "status": "empty"}
        
        batch_size = min(Config.REDIS_BULK_SIZE, buffer_len)
        logger.info(f"Processing batch of {batch_size} items from buffer (total: {buffer_len})")
        
        # Read batch from Redis
        batch = []
        for _ in range(batch_size):
            item = redis_client.lpop(Config.REDIS_BUFFER_KEY)
            if item:
                try:
                    batch.append(json.loads(item))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON from buffer: {e}")
                    continue
        
        if not batch:
            logger.warning("No valid items in batch after JSON decode")
            return {"processed": 0, "status": "decode_error"}
        
        # Insert batch into database
        success = insert_bulk(batch)
        
        if success:
            return {
                "processed": len(batch),
                "status": "success",
                "remaining": redis_client.llen(Config.REDIS_BUFFER_KEY)
            }
        else:
            # Re-add failed items to buffer
            logger.warning("Batch insert failed, re-queuing items")
            for item in batch:
                redis_client.rpush(Config.REDIS_BUFFER_KEY, json.dumps(item))
            return {"processed": 0, "status": "failed", "re_queued": len(batch)}
            
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error in process_buffer: {e}")
        return {"processed": 0, "status": "redis_error"}
    except Exception as e:
        logger.error(f"Unexpected error in process_buffer: {e}", exc_info=True)
        return {"processed": 0, "status": "error"}