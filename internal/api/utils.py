"""
API utility functions for response formatting.
"""

from typing import Any, Optional, Dict
from fastapi import HTTPException
from internal.api.schemas.common_schemas import StandardResponse


def success_response(message: str = "Success", data: Any = None) -> Dict:
    """
    Create a success response.

    Args:
        message: Success message
        data: Response data (optional)

    Returns:
        Standard response dictionary with error_code=0
    """
    return {"error_code": 0, "message": message, "data": data}


def error_response(message: str, error_code: int = 1, data: Any = None) -> Dict:
    """
    Create an error response.

    Args:
        message: Error message
        error_code: Error code (default: 1)
        data: Optional error data

    Returns:
        Standard response dictionary with error_code=1
    """
    return {"error_code": error_code, "message": message, "data": data}


async def handle_api_error(exception: Exception) -> Dict:
    """
    Convert exception to standard error response.

    Args:
        exception: Exception object

    Returns:
        Standard error response
    """
    if isinstance(exception, HTTPException):
        return error_response(message=exception.detail, error_code=1, data=None)
    else:
        return error_response(message=str(exception), error_code=1, data=None)
