"""
Core module containing base classes, configurations, and utilities.
"""

from .config import Settings, get_settings
from .dependencies import validate_dependencies, check_ffmpeg
from .logger import logger

__all__ = [
    "Settings",
    "get_settings",
    "logger",
    "validate_dependencies",
    "check_ffmpeg",
]
