"""
Flask route definitions for telemetry API.

Defines HTTP endpoints for receiving and queuing telemetry data.
"""

import logging
from typing import Tuple, Dict, Any

from flask import Flask, request, jsonify
from pydantic import ValidationError

from flask_app.tasks_with_batch import enqueue_telemetry
from flask_app.schemas import TelemetryRequest, TelemetryResponse, ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def register_routes(app: Flask) -> None:
    """
    Register all application routes.
    
    Args:
        app: Flask application instance
    """
    
    @app.route("/", methods=["GET"])
    def index() -> Tuple[Dict[str, Any], int]:
        """
        Health check endpoint.
        
        Returns:
            Tuple: JSON response and status code
        """
        return jsonify({
            "status": "ok",
            "service": "Telemetry Collection Service",
            "version": "1.0.0"
        }), 200
    
    @app.route("/health", methods=["GET"])
    def health() -> Tuple[Dict[str, Any], int]:
        """
        Detailed health check endpoint.
        
        Returns:
            Tuple: JSON response with service health and status code
        """
        try:
            # You can add more health checks here (DB, Redis, etc.)
            return jsonify({
                "status": "healthy",
                "checks": {
                    "api": "ok",
                    "database": "ok",  # Could check DB connection
                    "redis": "ok"      # Could check Redis connection
                }
            }), 200
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 503
    
    @app.route("/api/telemetry", methods=["POST"])
    def receive_telemetry() -> Tuple[Dict[str, Any], int]:
        """
        Receive telemetry data and queue for batch processing.
        
        Expected JSON payload:
            {
                "sensor_id": "room_24",
                "temperature": 22.5
            }
        
        Returns:
            Tuple: JSON response and status code
        """
        try:
            # Validate content type
            if not request.is_json:
                logger.warning("Received non-JSON request")
                error = ErrorResponse(
                    error="Bad Request",
                    message="Content-Type must be application/json"
                )
                return jsonify(error.model_dump()), 400
            
            # Validate and parse request data with Pydantic
            try:
                telemetry = TelemetryRequest(**request.json)
            except ValidationError as e:
                logger.warning(f"Validation error: {e}")
                error = ErrorResponse(
                    error="Validation Error",
                    message="Invalid request data",
                    details={"errors": e.errors()}
                )
                return jsonify(error.model_dump()), 400
            
            # Enqueue the telemetry data
            task = enqueue_telemetry.delay(
                telemetry.sensor_id, 
                telemetry.temperature
            )
            
            logger.info(
                f"Telemetry queued: sensor={telemetry.sensor_id}, "
                f"temp={telemetry.temperature}°C, task_id={task.id}"
            )
            
            # Create response using Pydantic model
            response = TelemetryResponse(
                status="queued",
                message="Telemetry data received and queued for processing",
                task_id=task.id,
                data={
                    "sensor_id": telemetry.sensor_id,
                    "temperature": telemetry.temperature
                }
            )
            
            return jsonify(response.model_dump()), 202
            
        except Exception as e:
            logger.error(f"Error processing telemetry request: {e}", exc_info=True)
            error = ErrorResponse(
                error="Internal Server Error",
                message="Failed to process telemetry data"
            )
            return jsonify(error.model_dump()), 500
    
    logger.info("All routes registered successfully")