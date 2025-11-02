"""
Repository for keyword extraction results.
Follows Single Responsibility Principle - only handles keyword data access.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_repository import BaseRepository
from .interfaces import IKeywordRepository


class KeywordRepository(BaseRepository, IKeywordRepository):
    """Repository for managing keyword extraction results."""

    def __init__(self):
        super().__init__("keywords")

    async def create_keyword_result(
        self,
        text: str,
        keywords: List[Dict[str, Any]],
        method: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new keyword extraction result.

        Args:
            text: Original text
            keywords: Extracted keywords with scores
            method: Extraction method used
            metadata: Optional metadata

        Returns:
            ID of created result
        """
        document = {
            "text": text,
            "keywords": keywords,
            "method": method,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return await self.create(document)

    async def find_by_text(
        self,
        text: str,
        method: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find keyword result by text.

        Args:
            text: Text to search for
            method: Optional method filter

        Returns:
            Keyword result if found
        """
        filter_dict = {"text": text}
        if method:
            filter_dict["method"] = method

        return await self.find_one(filter_dict)

    async def find_recent_results(
        self,
        limit: int = 10,
        method: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find recent keyword extraction results.

        Args:
            limit: Maximum number of results
            method: Optional method filter

        Returns:
            List of recent results
        """
        filter_dict = {}
        if method:
            filter_dict["method"] = method

        return await self.find_many(
            filter_dict,
            limit=limit,
            sort=[("created_at", -1)],
        )

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about keyword extractions.

        Returns:
            Statistics dictionary
        """
        pipeline = [
            {
                "$group": {
                    "_id": "$method",
                    "count": {"$sum": 1},
                    "avg_keywords": {"$avg": {"$size": "$keywords"}},
                }
            }
        ]

        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)

        return {
            "total_extractions": await self.count(),
            "by_method": results,
        }

    # Implement interface methods
    async def find_by_text_hash(
        self, text_hash: str, method: str
    ) -> Optional[Dict[str, Any]]:
        """Find keyword result by text hash and method."""
        return await self.find_one({"text_hash": text_hash, "method": method})

    async def find_recent(
        self, limit: int = 10, method: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find recent keyword extraction results."""
        return await self.find_recent_results(limit=limit, method=method)

    async def update(self, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a keyword extraction record."""
        return await self.update_by_id(record_id, data)

    async def delete(self, record_id: str) -> bool:
        """Delete a keyword extraction record."""
        return await self.delete_by_id(record_id)

    async def count_by_method(self) -> Dict[str, int]:
        """Count records by extraction method."""
        pipeline = [
            {
                "$group": {
                    "_id": "$method",
                    "count": {"$sum": 1},
                }
            }
        ]

        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)

        return {item["_id"]: item["count"] for item in results}
