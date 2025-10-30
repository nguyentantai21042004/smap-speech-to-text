"""
Sentiment Analysis API Routes.
Handles HTTP requests for sentiment analysis endpoints.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List

from internal.api.schemas.sentiment_schemas import (
    SentimentRequest,
    BatchSentimentRequest,
    SentimentResponse,
    BatchSentimentResponse,
    ModelInfoResponse,
    SentimentResult
)
from services import SentimentService
from core import logger


def create_sentiment_routes(sentiment_service: SentimentService) -> APIRouter:
    """
    Factory function to create sentiment routes with injected service.
    Follows Dependency Injection pattern.
    
    Args:
        sentiment_service: Sentiment service instance
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(
        prefix="/api/v1/sentiment",
        tags=["Sentiment Analysis"]
    )

    @router.post(
        "/analyze",
        response_model=SentimentResponse,
        status_code=status.HTTP_200_OK,
        summary="Analyze Sentiment",
        description="Analyze sentiment of a single Vietnamese text"
    )
    async def analyze_sentiment(request: SentimentRequest):
        """
        Analyze sentiment of input text.
        
        Returns sentiment label (Positive/Neutral/Negative) with confidence scores.
        """
        try:
            result = await sentiment_service.analyze_sentiment(request.text)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("error", "Failed to analyze sentiment")
                )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in analyze_sentiment: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    @router.post(
        "/analyze/batch",
        response_model=BatchSentimentResponse,
        status_code=status.HTTP_200_OK,
        summary="Batch Sentiment Analysis",
        description="Analyze sentiment of multiple texts at once (max 100)"
    )
    async def analyze_batch(request: BatchSentimentRequest):
        """
        Analyze sentiment of multiple texts efficiently.
        
        Processes up to 100 texts in a single request.
        """
        try:
            results = await sentiment_service.analyze_batch(request.texts)
            
            # Extract data from results
            successful_results = [r["data"] for r in results if r["success"]]
            
            return {
                "success": len(successful_results) > 0,
                "data": successful_results if successful_results else None,
                "error": None if successful_results else "All texts failed to process",
                "count": len(successful_results)
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in analyze_batch: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    @router.get(
        "/model/info",
        response_model=ModelInfoResponse,
        status_code=status.HTTP_200_OK,
        summary="Get Model Information",
        description="Get information about the sentiment analysis model"
    )
    async def get_model_info():
        """
        Retrieve model metadata and configuration.
        """
        try:
            info = sentiment_service.get_model_info()
            return info
            
        except Exception as e:
            logger.error(f"Error getting model info: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve model information"
            )

    return router

