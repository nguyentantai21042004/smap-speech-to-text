"""
Sentiment Service Implementation.
Business logic for sentiment analysis operations.
"""

from typing import Dict, Any, List

from services.interfaces.sentiment_service_interface import ISentimentService
from core import logger


class SentimentService(ISentimentService):
    """
    Sentiment Analysis Service.
    Handles business logic for sentiment analysis operations.
    """

    def __init__(self) -> None:
        """
        Initialize sentiment service without any LLM model loaded.
        This stub preserves the interface but returns a not-available response.
        """
        logger.info("Initializing Sentiment Service (stub, no model loaded)...")

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a single text.

        Args:
            text: Input text

        Returns:
            Dict with sentiment analysis results
        """
        try:
            if not text or not text.strip():
                return {
                    "success": False,
                    "error": "Empty text provided",
                    "data": None
                }

            return {
                "success": False,
                "error": "Sentiment model is not available in this build",
                "data": None,
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    async def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment of multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of results
        """
        try:
            if not texts:
                return []

            return [
                {
                    "success": False,
                    "error": "Sentiment model is not available in this build",
                    "data": None,
                }
                for _ in texts
            ]

        except Exception as e:
            logger.error(f"Error analyzing batch sentiment: {e}", exc_info=True)
            return [
                {
                    "success": False,
                    "error": str(e),
                    "data": None
                }
                for _ in texts
            ]

    def get_model_info(self) -> Dict[str, Any]:
        """Return placeholder model metadata to keep API contract stable."""
        return {
            "name": "unavailable",
            "version": "-",
            "description": "No sentiment model bundled in this source",
            "labels": [],
            "framework": "none",
            "base_model": "-",
            "segmentation_enabled": False,
        }

