"""
Common API schemas shared across different endpoints.
"""

from pydantic import BaseModel
from typing import Dict


class HealthResponse(BaseModel):
    """Response model for health check."""

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


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    detail: str
    status_code: int

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "error": "Not Found",
                    "detail": "The requested resource was not found",
                    "status_code": 404,
                },
                {
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred while processing your request",
                    "status_code": 500,
                },
            ]
        }
