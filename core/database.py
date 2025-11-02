"""
MongoDB connection using Motor (async driver).
Includes detailed logging and comprehensive error handling.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import asyncio

from core.config import get_settings
from core.logger import logger

settings = get_settings()


class MongoDB:
    """MongoDB connection manager with async support."""

    def __init__(self):
        """Initialize MongoDB connection manager."""
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        logger.debug("MongoDB connection manager initialized")

    async def connect(self) -> None:
        """
        Establish connection to MongoDB.

        Raises:
            Exception: If connection fails
        """
        try:
            # Mask password in URL for logging
            masked_url = settings.mongodb_url
            if "@" in masked_url:
                parts = masked_url.split("@")
                if "://" in parts[0]:
                    protocol_user = parts[0].split("://")
                    if ":" in protocol_user[1]:
                        user = protocol_user[1].split(":")[0]
                        masked_url = f"{protocol_user[0]}://{user}:****@{parts[1]}"

            logger.info(f"📝 Connecting to MongoDB: {masked_url}")
            logger.debug(f"Database name: {settings.mongodb_database}")

            # Create client with connection pooling
            self.client = AsyncIOMotorClient(
                settings.mongodb_url,
                maxPoolSize=settings.mongodb_max_pool_size,
                minPoolSize=settings.mongodb_min_pool_size,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
            )

            # Test connection with ping
            await self.client.admin.command("ping")

            # Get database
            self.db = self.client[settings.mongodb_database]

            logger.info(
                f"✅ Connected to MongoDB database: {settings.mongodb_database}"
            )
            logger.debug(
                f"Connection pool: min={settings.mongodb_min_pool_size}, "
                f"max={settings.mongodb_max_pool_size}"
            )

        except ConnectionError as e:
            logger.error(f"❌ MongoDB connection error: {e}")
            logger.exception("Connection error details:")
            raise

        except TimeoutError as e:
            logger.error(f"❌ MongoDB connection timeout: {e}")
            logger.exception("Timeout error details:")
            raise

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            logger.exception("MongoDB connection error details:")
            raise

    async def disconnect(self) -> None:
        """
        Close MongoDB connection.

        This method gracefully closes the connection and is safe to call
        even if not connected.
        """
        try:
            if self.client:
                logger.info("📝 Disconnecting from MongoDB...")
                self.client.close()
                self.client = None
                self.db = None
                logger.info("✅ Disconnected from MongoDB")
            else:
                logger.debug("MongoDB client not initialized, nothing to disconnect")

        except Exception as e:
            logger.error(f"❌ Error disconnecting from MongoDB: {e}")
            logger.exception("MongoDB disconnection error details:")

    async def get_collection(self, collection_name: str):
        """
        Get a MongoDB collection.

        Args:
            collection_name: Name of the collection to access

        Returns:
            MongoDB collection object

        Raises:
            RuntimeError: If database is not connected
            Exception: If collection access fails
        """
        try:
            if not self.db:
                error_msg = "Database not connected. Call connect() first."
                logger.error(f"❌ {error_msg}")
                raise RuntimeError(error_msg)

            collection = self.db[collection_name]
            logger.debug(f"🔍 Accessed collection: {collection_name}")
            return collection

        except RuntimeError as e:
            # Re-raise RuntimeError without logging again
            raise

        except Exception as e:
            logger.error(f"❌ Failed to access collection {collection_name}: {e}")
            logger.exception("Collection access error details:")
            raise

    async def health_check(self) -> bool:
        """
        Check if MongoDB connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not self.client:
                logger.warning("⚠️ MongoDB client not initialized")
                return False

            # Ping the database
            await self.client.admin.command("ping")
            logger.debug("✅ MongoDB health check passed")
            return True

        except ConnectionError as e:
            logger.error(f"❌ MongoDB health check failed - connection error: {e}")
            return False

        except TimeoutError as e:
            logger.error(f"❌ MongoDB health check failed - timeout: {e}")
            return False

        except Exception as e:
            logger.error(f"❌ MongoDB health check failed: {e}")
            logger.exception("Health check error details:")
            return False

    async def create_indexes(self) -> None:
        """
        Create database indexes for optimal query performance.

        This should be called during application startup.
        """
        try:
            logger.info("📝 Creating MongoDB indexes...")

            if not self.db:
                raise RuntimeError("Database not connected")

            # Create indexes for stt_jobs collection
            jobs_collection = await self.get_collection("stt_jobs")

            # Index on job_id (unique)
            await jobs_collection.create_index("job_id", unique=True)
            logger.debug("✅ Created unique index on job_id")

            # Index on status for querying pending jobs
            await jobs_collection.create_index("status")
            logger.debug("✅ Created index on status")

            # Index on created_at for sorting
            await jobs_collection.create_index("created_at")
            logger.debug("✅ Created index on created_at")

            # Compound index for status + created_at (for efficient pending job queries)
            await jobs_collection.create_index([("status", 1), ("created_at", 1)])
            logger.debug("✅ Created compound index on status + created_at")

            logger.info("✅ MongoDB indexes created successfully")

        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
            logger.exception("Index creation error details:")
            # Don't raise - indexes are optional for functionality
            # but log the error for awareness


# Global instance
_mongodb: Optional[MongoDB] = None


async def get_database() -> MongoDB:
    """
    Get or create global MongoDB instance.

    Returns:
        MongoDB instance

    Raises:
        Exception: If database initialization fails
    """
    global _mongodb

    try:
        if _mongodb is None:
            logger.info("📝 Initializing MongoDB connection...")
            _mongodb = MongoDB()
            await _mongodb.connect()
            # Create indexes after connection
            await _mongodb.create_indexes()

        return _mongodb

    except Exception as e:
        logger.error(f"❌ Failed to get MongoDB instance: {e}")
        logger.exception("Database initialization error:")
        raise


async def close_database() -> None:
    """
    Close global MongoDB connection.

    This should be called during application shutdown.
    """
    global _mongodb

    try:
        if _mongodb:
            logger.info("📝 Closing global MongoDB connection...")
            await _mongodb.disconnect()
            _mongodb = None
            logger.info("✅ Global MongoDB connection closed")
        else:
            logger.debug("No global MongoDB connection to close")

    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")
        logger.exception("Database close error details:")


# Helper function for non-async contexts
def get_database_sync() -> MongoDB:
    """
    Get database instance in synchronous context.

    Note: This is a helper that creates an event loop if needed.
    Prefer using get_database() in async contexts.

    Returns:
        MongoDB instance
    """
    try:
        logger.debug("📝 Getting database in sync context")

        # Try to get current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.debug("Created new event loop for sync context")

        # Run the async function
        db = loop.run_until_complete(get_database())
        logger.debug("✅ Database retrieved in sync context")
        return db

    except Exception as e:
        logger.error(f"❌ Failed to get database in sync context: {e}")
        logger.exception("Sync database retrieval error:")
        raise
