"""
Core module containing base classes, configurations, and utilities.
"""

from .config import Settings, get_settings
from .database import MongoDB, get_database
from .logger import logger
from .messaging import QueueManager, get_queue_manager

__all__ = [
    "Settings",
    "get_settings",
    "MongoDB",
    "get_database",
    "logger",
    "QueueManager",
    "get_queue_manager",
]

