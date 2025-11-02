"""
Centralized logging configuration using Loguru.
Follows Single Responsibility Principle - only handles logging setup.
"""

import sys
from pathlib import Path

from loguru import logger


def setup_logger():
    """Configure logger handlers. Only configures once even if called multiple times."""
    from .config import get_settings
    settings = get_settings()
    
    # Get log level: LOG_LEVEL takes precedence over DEBUG flag
    # If LOG_LEVEL is set, use it; otherwise use DEBUG flag
    if settings.log_level:
        # Use LOG_LEVEL from config (from .env or default)
        log_level = settings.log_level.upper()
        # Validate log level
        if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            log_level = "INFO"
    else:
        # Fallback to DEBUG flag if LOG_LEVEL not set
        log_level = "DEBUG" if settings.debug else "INFO"
    
    # Check if logger already has our handlers configured
    # Loguru is a singleton, so handlers persist across module reloads
    handlers_count_before = len(logger._core.handlers.values())
    
    # If already configured (has 3 handlers: console + app.log + error.log)
    # We still need to update the console handler level if it changed
    if handlers_count_before >= 3:
        # Update console handler level if needed (for dynamic level changes)
        # Note: This requires removing and re-adding console handler
        # But since handlers are identified by ID and we can't easily update them,
        # we'll just return - user can restart to pick up new LOG_LEVEL
        return

    # Remove all existing handlers first
    logger.remove()

    # Now check if handlers were actually removed
    # If handlers still exist, they might be from previous config (shouldn't happen with remove())
    handlers_count_after_remove = len(logger._core.handlers.values())

    # Only configure if handlers were successfully removed
    if handlers_count_after_remove == 0:
        # Filter function to prevent duplicate logs from reloader processes
        def filter_reloader_logs(record):
            """Filter out logs from __main__ and __mp_main__ (reloader processes)."""
            module_name = record.get("name", "")

            # Only log from actual application code (cmd.* modules)
            # Block logs from __main__ and __mp_main__ (these are from uvicorn reloader)
            if module_name in ("__main__", "__mp_main__"):
                return False

            # Allow all other logs
            return True

        # Get log level: LOG_LEVEL takes precedence over DEBUG flag
        # If LOG_LEVEL is set, use it; otherwise use DEBUG flag
        if settings.log_level:
            # Use LOG_LEVEL from config (from .env or default)
            log_level = settings.log_level.upper()
            # Validate log level
            if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                log_level = "INFO"
        else:
            # Fallback to DEBUG flag if LOG_LEVEL not set
            log_level = "DEBUG" if settings.debug else "INFO"

        # Console handler with color - filter duplicate logs from reloader
        logger.add(
            sys.stdout,
            colorize=True,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            filter=filter_reloader_logs,
        )

        # File handler for all logs - always DEBUG level to capture everything
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logger.add(
            log_dir / "app.log",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",  # File logs always DEBUG to capture everything
        )

        # Error file handler
        logger.add(
            log_dir / "error.log",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="ERROR",
        )


# Configure logger on module import
setup_logger()

__all__ = ["logger"]
