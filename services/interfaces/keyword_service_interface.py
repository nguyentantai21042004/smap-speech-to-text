"""
Interface for Keyword Service.
Defines the contract that all keyword services must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class IKeywordService(ABC):
    """Interface for keyword extraction service operations."""

    @abstractmethod
    async def extract_keywords_sync(
        self, text: str, method: str = "default", num_keywords: int = 10
    ) -> Dict:
        """
        Extract keywords synchronously.

        Args:
            text: Input text for keyword extraction
            method: Extraction method to use
            num_keywords: Number of keywords to extract

        Returns:
            Dict: Extraction result with status and data
        """
        pass

    @abstractmethod
    async def extract_keywords_async(
        self, text: str, method: str = "default", num_keywords: int = 10
    ) -> Dict:
        """
        Extract keywords asynchronously (via queue).

        Args:
            text: Input text for keyword extraction
            method: Extraction method to use
            num_keywords: Number of keywords to extract

        Returns:
            Dict: Task information including task_id
        """
        pass

    @abstractmethod
    async def get_extraction_result(self, result_id: str) -> Optional[Dict]:
        """
        Get keyword extraction result by ID.

        Args:
            result_id: ID of the extraction result

        Returns:
            Optional[Dict]: Result data if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_recent_results(
        self, limit: int = 10, method: Optional[str] = None
    ) -> List[Dict]:
        """
        Get recent keyword extraction results.

        Args:
            limit: Maximum number of results to return
            method: Optional filter by extraction method

        Returns:
            List[Dict]: List of recent results
        """
        pass

    @abstractmethod
    async def get_statistics(self) -> Dict:
        """
        Get keyword extraction statistics.

        Returns:
            Dict: Statistics data
        """
        pass
