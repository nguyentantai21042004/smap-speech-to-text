"""
Common API schemas shared across different endpoints.
"""

from pydantic import BaseModel
from typing import Dict, Optional, Any


class StandardResponse(BaseModel):
    """
    Standard API response format for all endpoints.

    - error_code: 0 = success, 1 = error
    - message: Success or error message
    - data: Response data (optional, only present on success)
    """

    error_code: int = 0
    message: str
    data: Optional[Any] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "error_code": 0,
                    "message": "Success",
                    "data": {"job_id": "69073cc61dc7aa422463d537", "status": "PENDING"},
                },
                {"error_code": 1, "message": "Job not found", "data": None},
            ]
        }


class HealthResponse(BaseModel):
    """Response model for health check (internal use)."""

    status: str
    service: str
    version: str
    database: str
    message_broker: str

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "status": "healthy",
                    "service": "SMAP Service",
                    "version": "1.0.0",
                    "database": "connected",
                    "message_broker": "connected",
                }
            ]
        }
