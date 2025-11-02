"""
Service for keyword extraction business logic.
Implements Service Layer Pattern - orchestrates between repositories and messaging.
Follows Single Responsibility Principle - only handles keyword extraction business logic.
"""

from typing import Any, Dict, List, Optional

from core import logger
from core.messaging import get_queue_manager
from repositories import KeywordRepository
from .interfaces import IKeywordService


class KeywordService(IKeywordService):
    """
    Service handling keyword extraction business logic.
    Acts as a facade to simplify complex operations.
    """

    def __init__(self):
        self.repository = KeywordRepository()
        self.message_broker = get_queue_manager()

    async def extract_keywords_sync(
        self,
        text: str,
        method: str = "default",
        num_keywords: int = 10,
    ) -> Dict[str, Any]:
        """
        Extract keywords synchronously.

        Args:
            text: Text to extract keywords from
            method: Extraction method
            num_keywords: Number of keywords to extract

        Returns:
            Extraction result with keywords
        """
        try:
            # Check if we already have results for this text and method
            existing_result = await self.repository.find_by_text(text, method)

            if existing_result:
                logger.info(f"Found cached result for text with method {method}")
                return {
                    "status": "success",
                    "data": existing_result,
                    "cached": True,
                }

            # Perform extraction (placeholder - implement actual extraction logic)
            keywords = await self._perform_extraction(text, method, num_keywords)

            # Save results
            result_id = await self.repository.create_keyword_result(
                text=text,
                keywords=keywords,
                method=method,
                metadata={"num_keywords": num_keywords},
            )

            result = await self.repository.find_by_id(result_id)

            logger.info(f"Extracted {len(keywords)} keywords using {method}")

            return {
                "status": "success",
                "data": result,
                "cached": False,
            }
        except Exception as e:
            logger.error(f"Error in extract_keywords_sync: {e}")
            raise

    async def extract_keywords_async(
        self,
        text: str,
        method: str = "default",
        num_keywords: int = 10,
    ) -> Dict[str, Any]:
        """
        Extract keywords asynchronously via message queue.

        Args:
            text: Text to extract keywords from
            method: Extraction method
            num_keywords: Number of keywords to extract

        Returns:
            Task information
        """
        try:
            # Create message payload
            message = {
                "type": "keyword_extraction",
                "payload": {
                    "text": text,
                    "method": method,
                    "num_keywords": num_keywords,
                },
            }

            # Publish to queue
            await self.message_broker.publish(message)

            logger.info(f"Published keyword extraction task to queue")

            return {
                "status": "queued",
                "message": "Task has been queued for processing",
            }
        except Exception as e:
            logger.error(f"Error in extract_keywords_async: {e}")
            raise

    async def get_extraction_result(
        self,
        result_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get extraction result by ID.

        Args:
            result_id: Result ID

        Returns:
            Extraction result if found
        """
        try:
            result = await self.repository.find_by_id(result_id)
            return result
        except Exception as e:
            logger.error(f"Error in get_extraction_result: {e}")
            raise

    async def get_recent_results(
        self,
        limit: int = 10,
        method: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent extraction results.

        Args:
            limit: Maximum number of results
            method: Optional method filter

        Returns:
            List of recent results
        """
        try:
            results = await self.repository.find_recent_results(limit, method)
            return results
        except Exception as e:
            logger.error(f"Error in get_recent_results: {e}")
            raise

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get extraction statistics.

        Returns:
            Statistics dictionary
        """
        try:
            stats = await self.repository.get_statistics()
            return stats
        except Exception as e:
            logger.error(f"Error in get_statistics: {e}")
            raise

    async def _perform_extraction(
        self,
        text: str,
        method: str,
        num_keywords: int,
    ) -> List[Dict[str, Any]]:
        """
        Perform actual keyword extraction.
        This is a placeholder - implement actual extraction algorithms here.

        Args:
            text: Text to extract keywords from
            method: Extraction method
            num_keywords: Number of keywords to extract

        Returns:
            List of keywords with scores
        """
        # Placeholder implementation
        # TODO: Implement actual keyword extraction algorithms

        words = text.split()
        keywords = []

        for i, word in enumerate(words[:num_keywords]):
            keywords.append(
                {
                    "keyword": word.lower(),
                    "score": 1.0 - (i * 0.1),
                    "position": i,
                }
            )

        return keywords
