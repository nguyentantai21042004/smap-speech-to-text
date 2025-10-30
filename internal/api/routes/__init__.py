"""
API Routes.
"""

from .keyword_routes import create_keyword_routes
from .task_routes import create_task_routes
from .health_routes import create_health_routes
from .sentiment_routes import create_sentiment_routes

__all__ = [
    "create_keyword_routes",
    "create_task_routes",
    "create_health_routes",
    "create_sentiment_routes",
]

