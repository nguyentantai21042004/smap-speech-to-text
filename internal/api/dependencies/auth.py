"""
Authentication dependencies for internal API endpoints.
"""

from fastapi import Header, HTTPException, status
from core.config import get_settings
from core.logger import logger


async def verify_internal_api_key(
    x_api_key: str = Header(None, description="Internal API key for authentication")
) -> str:
    """
    Verify internal API key from request header.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    settings = get_settings()
    
    if not x_api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )
    
    if x_api_key != settings.internal_api_key:
        logger.warning(f"Invalid API key attempted: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return x_api_key

