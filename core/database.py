"""
Database connection manager for MongoDB.
Follows Single Responsibility Principle - only handles database connections.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import get_settings
from .logger import logger


class DatabaseManager:
    """
    Manages MongoDB database connections.
    Implements Singleton pattern through class-level attributes.
    """

    _client: Optional[AsyncIOMotorClient] = None
    _database: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> None:
        """Establish connection to MongoDB."""
        if cls._client is not None:
            logger.warning("Database already connected")
            return

        settings = get_settings()
        
        try:
            cls._client = AsyncIOMotorClient(
                settings.mongodb_url,
                minPoolSize=settings.mongodb_min_pool_size,
                maxPoolSize=settings.mongodb_max_pool_size,
            )
            cls._database = cls._client[settings.mongodb_database]
            
            # Test connection
            await cls._client.admin.command("ping")
            logger.info(f"Connected to MongoDB: {settings.mongodb_database}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def disconnect(cls) -> None:
        """Close MongoDB connection."""
        if cls._client is None:
            logger.warning("Database not connected")
            return

        try:
            cls._client.close()
            cls._client = None
            cls._database = None
            logger.info("Disconnected from MongoDB")
        except Exception as e:
            logger.error(f"Failed to disconnect from MongoDB: {e}")
            raise

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if cls._database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls._database

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """Get client instance."""
        if cls._client is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls._client

