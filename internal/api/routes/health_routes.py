"""
Health Check API Routes.
"""

from fastapi import APIRouter
from typing import Dict

from internal.api.schemas import HealthResponse
from internal.api.schemas.common_schemas import StandardResponse
from internal.api.utils import success_response
from core import get_settings


router = APIRouter(tags=["Health"])


def create_health_routes(app) -> APIRouter:
    """
    Factory function to create health routes.

    Args:
        app: FastAPI application instance

    Returns:
        APIRouter: Configured router with health endpoints
    """

    @router.get(
        "/",
        response_model=StandardResponse,
        summary="Root Endpoint",
        description="Get basic API information",
        operation_id="get_root",
        responses={
            200: {
                "description": "API information",
                "content": {
                    "application/json": {
                        "example": {
                            "error_code": 0,
                            "message": "API service is running",
                            "data": {
                                "service": "Speech-to-Text API",
                                "version": "1.0.0",
                                "status": "running",
                            },
                        }
                    }
                },
            }
        },
    )
    async def root():
        """
        Root endpoint.

        Returns basic information about the API service including
        service name, version, and current status.

        **Returns:**
        Service metadata and status information.
        """
        settings = get_settings()
        return success_response(
            message="API service is running",
            data={
                "service": settings.app_name,
                "version": settings.app_version,
                "status": "running",
            },
        )

    @router.get(
        "/health",
        response_model=StandardResponse,
        summary="Health Check",
        description="Check service health",
        operation_id="health_check",
        responses={
            200: {
                "description": "Health status",
                "content": {
                    "application/json": {
                        "examples": {
                            "healthy": {
                                "summary": "Service operational",
                                "value": {
                                    "error_code": 0,
                                    "message": "Service is healthy",
                                    "data": {
                                        "status": "healthy",
                                        "service": "SMAP Service",
                                        "version": "1.0.0",
                                    },
                                },
                            },
                        }
                    }
                },
            }
        },
    )
    async def health_check():
        """
        Health check endpoint.

        **Returns:**
        Health status object indicating:
        - Overall health status (healthy)
        - Service name and version
        """
        settings = get_settings()

        health_data = HealthResponse(
            status="healthy",
            service=settings.app_name,
            version=settings.app_version,
        )

        # Convert Pydantic model to dict for response
        health_dict = health_data.model_dump()

        return success_response(message="Service is healthy", data=health_dict)

    return router
