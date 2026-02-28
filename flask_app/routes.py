"""
Flask route definitions for telemetry API.

Defines HTTP endpoints for receiving and queuing telemetry data.
"""

import logging
from typing import Tuple, Dict, Any

from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest

from flask_app.tasks_with_batch import enqueue_telemetry

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
            
        Raises:
            BadRequest: If request data is invalid
        """
        try:
            # Validate content type
            if not request.is_json:
                logger.warning("Received non-JSON request")
                return jsonify({
                    "error": "Bad Request",
                    "message": "Content-Type must be application/json"
                }), 400
            
            data = request.json
            
            # Validate required fields
            if not data:
                logger.warning("Received empty request body")
                return jsonify({
                    "error": "Bad Request",
                    "message": "Request body cannot be empty"
                }), 400
            
            if "sensor_id" not in data:
                logger.warning("Missing sensor_id in request")
                return jsonify({
                    "error": "Bad Request",
                    "message": "Missing required field: sensor_id"
                }), 400
            
            if "temperature" not in data:
                logger.warning("Missing temperature in request")
                return jsonify({
                    "error": "Bad Request",
                    "message": "Missing required field: temperature"
                }), 400
            
            # Validate data types and values
            sensor_id = str(data["sensor_id"]).strip()
            if not sensor_id:
                return jsonify({
                    "error": "Bad Request",
                    "message": "sensor_id cannot be empty"
                }), 400
            
            try:
                temperature = float(data["temperature"])
            except (ValueError, TypeError):
                logger.warning(f"Invalid temperature value: {data['temperature']}")
                return jsonify({
                    "error": "Bad Request",
                    "message": "temperature must be a valid number"
                }), 400
            
            # Validate temperature range (optional but recommended)
            if temperature < -273.15:  # Absolute zero
                return jsonify({
                    "error": "Bad Request",
                    "message": "temperature cannot be below absolute zero (-273.15°C)"
                }), 400
            
            if temperature > 1000:  # Reasonable upper limit
                logger.warning(f"Unusually high temperature: {temperature}°C from {sensor_id}")
            
            # Enqueue the telemetry data
            task = enqueue_telemetry.delay(sensor_id, temperature)
            
            logger.info(f"Telemetry queued: sensor={sensor_id}, temp={temperature}°C, task_id={task.id}")
            
            return jsonify({
                "status": "queued",
                "message": "Telemetry data received and queued for processing",
                "task_id": task.id,
                "data": {
                    "sensor_id": sensor_id,
                    "temperature": temperature
                }
            }), 202
            
        except BadRequest as e:
            logger.warning(f"Bad request: {e}")
            return jsonify({
                "error": "Bad Request",
                "message": str(e)
            }), 400
        except Exception as e:
            logger.error(f"Error processing telemetry request: {e}", exc_info=True)
            return jsonify({
                "error": "Internal Server Error",
                "message": "Failed to process telemetry data"
            }), 500
    
    logger.info("All routes registered successfully")