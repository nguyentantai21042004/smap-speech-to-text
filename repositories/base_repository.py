"""
Base repository with common CRUD operations.
Follows Single Responsibility Principle - only handles data access.
"""

from abc import ABC
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from core import DatabaseManager, logger


class BaseRepository(ABC):
    """
    Base repository providing common CRUD operations.
    All repositories should inherit from this class.
    """

    def __init__(self, collection_name: str):
        """
        Initialize repository with collection name.

        Args:
            collection_name: Name of MongoDB collection
        """
        self.collection_name = collection_name

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get MongoDB collection."""
        db = DatabaseManager.get_database()
        return db[self.collection_name]

    async def create(self, document: Dict[str, Any]) -> str:
        """
        Create a new document.

        Args:
            document: Document data

        Returns:
            ID of created document
        """
        try:
            result = await self.collection.insert_one(document)
            logger.debug(
                f"Created document in {self.collection_name}: {result.inserted_id}"
            )
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating document in {self.collection_name}: {e}")
            raise

    async def find_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Find document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document if found, None otherwise
        """
        try:
            document = await self.collection.find_one({"_id": ObjectId(document_id)})
            if document:
                document["_id"] = str(document["_id"])
            return document
        except Exception as e:
            logger.error(f"Error finding document by ID in {self.collection_name}: {e}")
            raise

    async def find_one(self, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find one document matching filter.

        Args:
            filter_dict: Query filter

        Returns:
            Document if found, None otherwise
        """
        try:
            document = await self.collection.find_one(filter_dict)
            if document:
                document["_id"] = str(document["_id"])
            return document
        except Exception as e:
            logger.error(f"Error finding document in {self.collection_name}: {e}")
            raise

    async def find_many(
        self,
        filter_dict: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        sort: Optional[List[tuple]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents matching filter.

        Args:
            filter_dict: Query filter
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: Sort specification

        Returns:
            List of documents
        """
        try:
            cursor = self.collection.find(filter_dict).skip(skip).limit(limit)

            if sort:
                cursor = cursor.sort(sort)

            documents = await cursor.to_list(length=limit)

            for doc in documents:
                doc["_id"] = str(doc["_id"])

            return documents
        except Exception as e:
            logger.error(f"Error finding documents in {self.collection_name}: {e}")
            raise

    async def update_by_id(
        self,
        document_id: str,
        update_data: Dict[str, Any],
    ) -> bool:
        """
        Update document by ID.

        Args:
            document_id: Document ID
            update_data: Data to update

        Returns:
            True if updated, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data},
            )
            logger.debug(f"Updated document in {self.collection_name}: {document_id}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating document in {self.collection_name}: {e}")
            raise

    async def update_many(
        self,
        filter_dict: Dict[str, Any],
        update_data: Dict[str, Any],
    ) -> int:
        """
        Update multiple documents matching filter.

        Args:
            filter_dict: Query filter
            update_data: Data to update

        Returns:
            Number of documents updated
        """
        try:
            result = await self.collection.update_many(
                filter_dict,
                {"$set": update_data},
            )
            logger.debug(
                f"Updated {result.modified_count} documents in {self.collection_name}"
            )
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating documents in {self.collection_name}: {e}")
            raise

    async def delete_by_id(self, document_id: str) -> bool:
        """
        Delete document by ID.

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(document_id)})
            logger.debug(f"Deleted document in {self.collection_name}: {document_id}")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document in {self.collection_name}: {e}")
            raise

    async def delete_many(self, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple documents matching filter.

        Args:
            filter_dict: Query filter

        Returns:
            Number of documents deleted
        """
        try:
            result = await self.collection.delete_many(filter_dict)
            logger.debug(
                f"Deleted {result.deleted_count} documents in {self.collection_name}"
            )
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting documents in {self.collection_name}: {e}")
            raise

    async def count(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents matching filter.

        Args:
            filter_dict: Query filter, if None counts all documents

        Returns:
            Number of documents
        """
        try:
            filter_dict = filter_dict or {}
            count = await self.collection.count_documents(filter_dict)
            return count
        except Exception as e:
            logger.error(f"Error counting documents in {self.collection_name}: {e}")
            raise

    async def exists(self, filter_dict: Dict[str, Any]) -> bool:
        """
        Check if document exists matching filter.

        Args:
            filter_dict: Query filter

        Returns:
            True if exists, False otherwise
        """
        try:
            count = await self.collection.count_documents(filter_dict, limit=1)
            return count > 0
        except Exception as e:
            logger.error(f"Error checking existence in {self.collection_name}: {e}")
            raise
