"""
API Routes.
"""

from .health_routes import create_health_routes
from .transcribe_routes import router as transcribe_router

__all__ = [
    "create_health_routes",
    "transcribe_router",
]
