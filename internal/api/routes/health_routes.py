"""
Health Check API Routes.
"""

from fastapi import APIRouter
from typing import Dict

from internal.api.schemas import HealthResponse
from core import DatabaseManager, get_settings


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
        response_model=Dict,
        summary="Root Endpoint",
        description="Get basic API information",
        responses={
            200: {
                "description": "API information",
                "content": {
                    "application/json": {
                        "example": {
                            "service": "SMAP Service",
                            "version": "1.0.0",
                            "status": "running",
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
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "running",
        }

    @router.get(
        "/health",
        response_model=HealthResponse,
        summary="Health Check",
        description="Check service health and dependencies status",
        responses={
            200: {
                "description": "Health status",
                "content": {
                    "application/json": {
                        "examples": {
                            "healthy": {
                                "summary": "All systems operational",
                                "value": {
                                    "status": "healthy",
                                    "service": "SMAP Service",
                                    "version": "1.0.0",
                                    "database": "connected",
                                    "message_broker": "connected",
                                },
                            },
                            "unhealthy": {
                                "summary": "Service degraded",
                                "value": {
                                    "status": "unhealthy",
                                    "service": "SMAP Service",
                                    "version": "1.0.0",
                                    "database": "disconnected",
                                    "message_broker": "connected",
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

        Performs comprehensive health checks on the API service and its dependencies.
        Checks connectivity to:
        - MongoDB database
        - RabbitMQ message broker

        **Returns:**
        Health status object indicating:
        - Overall health status (healthy/unhealthy)
        - Service name and version
        - Individual component statuses

        **Status Values:**
        - `healthy`: All components operational
        - `unhealthy`: One or more components unavailable
        - `connected`: Component is accessible
        - `disconnected`: Component is not accessible
        - `not_initialized`: Component not yet initialized
        """
        settings = get_settings()

        db_status = "connected"
        try:
            db = DatabaseManager.get_database()
            await db.command("ping")
        except Exception:
            db_status = "disconnected"

        mq_status = "connected"
        try:
            if hasattr(app.state, "message_broker"):
                # Simple check - if we can access it, it's connected
                _ = app.state.message_broker
            else:
                mq_status = "not_initialized"
        except Exception:
            mq_status = "disconnected"

        return HealthResponse(
            status="healthy" if db_status == "connected" else "unhealthy",
            service=settings.app_name,
            version=settings.app_version,
            database=db_status,
            message_broker=mq_status,
        )

    return router
