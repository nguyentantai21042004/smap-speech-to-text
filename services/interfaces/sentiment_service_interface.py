"""
Sentiment Service Interface.
Defines the contract for sentiment analysis operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class ISentimentService(ABC):
    """Interface for sentiment analysis service."""

    @abstractmethod
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a single text.

        Args:
            text: Input text to analyze

        Returns:
            Dict containing sentiment analysis result
        """
        pass

    @abstractmethod
    async def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment of multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of sentiment analysis results
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the sentiment model.

        Returns:
            Dict with model metadata
        """
        pass

