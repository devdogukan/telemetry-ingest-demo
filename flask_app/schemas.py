"""
Pydantic schemas for request/response validation.

Provides type-safe validation for API requests and responses.
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class TelemetryRequest(BaseModel):
    """Schema for telemetry data request."""
    
    sensor_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Unique identifier for the sensor"
    )
    temperature: float = Field(
        ..., 
        ge=-273.15,  # Greater than or equal to absolute zero
        le=1000.0,   # Less than or equal to 1000°C
        description="Temperature reading in Celsius"
    )
    
    @field_validator('sensor_id')
    @classmethod
    def validate_sensor_id(cls, v: str) -> str:
        """Validate and clean sensor_id."""
        v = v.strip()
        if not v:
            raise ValueError('sensor_id cannot be empty or whitespace')
        return v
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Additional temperature validation."""
        if v > 500:
            # Log warning for unusually high temps but allow
            logger.warning(f"Unusually high temperature: {v}°C")
        return round(v, 2)  # Round to 2 decimal places
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sensor_id": "room_24",
                    "temperature": 22.5
                }
            ]
        }
    }


class TelemetryResponse(BaseModel):
    """Schema for telemetry response."""
    
    status: str
    message: str
    task_id: str
    data: dict
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "queued",
                    "message": "Telemetry data received and queued for processing",
                    "task_id": "abc-123-def-456",
                    "data": {
                        "sensor_id": "room_24",
                        "temperature": 22.5
                    }
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    
    error: str
    message: str
    details: Optional[dict] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "Validation Error",
                    "message": "Invalid request data",
                    "details": {
                        "field": "temperature",
                        "issue": "Value out of range"
                    }
                }
            ]
        }
    }
