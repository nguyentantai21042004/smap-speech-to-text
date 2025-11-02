"""
RabbitMQ Consumer Service - Main entry point for STT job processing.
Implements RabbitMQ async consumer with comprehensive logging and error handling:
- MongoDB connection for job persistence
- RabbitMQ for job queue management
- Graceful shutdown handling
- Message acknowledgment and retry logic
"""

import asyncio
import signal
import sys

from core.config import get_settings
from core.logger import logger
from core.database import get_database
from core.messaging import get_queue_manager
from core.dependencies import validate_dependencies
from internal.consumer.handlers.stt_handler import handle_stt_message
from worker.transcriber import get_whisper_transcriber
from worker.model_downloader import get_model_downloader


class ConsumerService:
    """
    Consumer Service manages the lifecycle of RabbitMQ consumer.
    Handles initialization, startup, and graceful shutdown.
    """

    def __init__(self):
        """Initialize consumer service."""
        try:
            logger.info("Initializing Consumer Service...")
            self.settings = get_settings()
            self.db = None
            self.queue_manager = None
            self.shutdown_event = asyncio.Event()
            logger.info("Consumer Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Consumer Service: {e}")
            logger.exception("Consumer Service initialization error:")
            raise

    async def startup(self):
        """
        Initialize and connect to required services.
        Sets up MongoDB and RabbitMQ connections.
        """
        try:
            logger.info(
                f"========== Starting {self.settings.app_name} Consumer Service =========="
            )
            logger.info(f"Environment: {self.settings.environment}")
            logger.info(f"Debug mode: {self.settings.debug}")
            logger.info(f"Max concurrent jobs: {self.settings.max_concurrent_jobs}")

            # Validate system dependencies (ffmpeg/ffprobe)
            try:
                validate_dependencies()
                logger.info("System dependencies validated")
            except Exception as e:
                logger.error(f"Dependency validation failed: {e}")
                raise

            # Connect to MongoDB
            try:
                logger.info("Connecting to MongoDB...")
                self.db = await get_database()
                await self.db.connect()
                logger.info("MongoDB connected successfully")

                # Create indexes
                logger.info("Creating database indexes...")
                await self.db.create_indexes()
                logger.info("Database indexes created")

                # Health check
                logger.info("Performing MongoDB health check...")
                db_healthy = await self.db.health_check()
                if db_healthy:
                    logger.info("MongoDB health check passed")
                else:
                    logger.warning("MongoDB health check failed")
                    raise Exception("MongoDB health check failed")

            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                logger.exception("MongoDB connection error details:")
                raise

            # Initialize RabbitMQ
            try:
                logger.info("Initializing RabbitMQ connection...")
                self.queue_manager = get_queue_manager()

                # Connect to RabbitMQ
                await self.queue_manager.connect()
                logger.info("RabbitMQ connected successfully")

                # Health check
                logger.info("Performing RabbitMQ health check...")
                rabbitmq_healthy = self.queue_manager.health_check()
                if rabbitmq_healthy:
                    logger.info("RabbitMQ health check passed")
                else:
                    logger.warning("RabbitMQ health check failed")
                    raise Exception("RabbitMQ health check failed")

            except Exception as e:
                logger.error(f"Failed to initialize RabbitMQ: {e}")
                logger.exception("RabbitMQ initialization error details:")
                raise

            # Initialize WhisperTranscriber (once for all jobs)
            try:
                logger.info("Initializing WhisperTranscriber singleton...")
                transcriber = get_whisper_transcriber()
                logger.info("WhisperTranscriber initialized successfully")

                # Pre-warm model downloader
                logger.info("Pre-warming model downloader...")
                model_downloader = get_model_downloader()
                logger.info("Model downloader initialized")

                # Pre-validate default model
                logger.info(
                    f"Pre-validating default model: {self.settings.default_whisper_model}"
                )
                model_downloader.ensure_model_exists(
                    self.settings.default_whisper_model
                )
                logger.info(
                    f"Default model ready: {self.settings.default_whisper_model}"
                )

            except Exception as e:
                logger.error(f"Failed to initialize transcriber: {e}")
                logger.exception("Transcriber initialization error details:")
                raise

            logger.info(f"========== Consumer Service startup complete ==========")

        except Exception as e:
            logger.error(f"Consumer Service startup failed: {e}")
            logger.exception("Startup error details:")
            raise

    async def shutdown(self):
        """
        Graceful shutdown of services.
        Closes RabbitMQ and MongoDB connections.
        """
        try:
            logger.info("========== Shutting down Consumer Service ==========")

            # Disconnect from RabbitMQ
            try:
                if self.queue_manager:
                    logger.info("Disconnecting from RabbitMQ...")
                    await self.queue_manager.disconnect()
                    logger.info("RabbitMQ disconnected successfully")
            except Exception as e:
                logger.error(f"Error disconnecting from RabbitMQ: {e}")
                logger.exception("RabbitMQ disconnect error details:")

            # Disconnect from MongoDB
            try:
                if self.db:
                    logger.info("Disconnecting from MongoDB...")
                    await self.db.disconnect()
                    logger.info("MongoDB disconnected successfully")
            except Exception as e:
                logger.error(f"Error disconnecting from MongoDB: {e}")
                logger.exception("MongoDB disconnect error details:")

            logger.info("========== Consumer Service stopped ==========")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            logger.exception("Shutdown error details:")

    async def start_consuming(self):
        """
        Start consuming messages from RabbitMQ queue.
        Uses the message handler to process STT jobs.
        """
        try:
            logger.info("========== Starting RabbitMQ Consumer ==========")
            logger.info(f"Queue: {self.settings.rabbitmq_queue_name}")
            logger.info(f"Prefetch: {self.settings.max_concurrent_jobs}")

            # Start consuming with our handler
            await self.queue_manager.consume_jobs(
                callback=handle_stt_message,
                prefetch_count=self.settings.max_concurrent_jobs,
            )

            logger.info("Consumer started successfully")
            logger.info("Press Ctrl+C to stop gracefully")

            # Wait for shutdown signal
            await self.shutdown_event.wait()

            logger.info("Shutdown signal received, stopping consumer...")

        except Exception as e:
            logger.error(f"Error in consumer: {e}")
            logger.exception("Consumer error details:")
            raise

    async def run(self):
        """
        Main service loop.
        Handles startup, consumption, and shutdown.
        """
        try:
            # Startup
            await self.startup()

            # Start consuming messages (blocks until shutdown)
            await self.start_consuming()

        except Exception as e:
            logger.error(f"Error in consumer service: {e}")
            logger.exception("Consumer service error:")
            raise
        finally:
            # Always cleanup on exit
            await self.shutdown()


async def main():
    """
    Main entry point for the consumer service.
    Handles async operations and signal handling for graceful shutdown.
    """
    service = None

    try:
        logger.info("========== SMAP STT Consumer Service ==========")

        # Create consumer service
        service = ConsumerService()

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()

        def handle_shutdown(signum):
            logger.info(f"Received shutdown signal: {signum}")
            service.shutdown_event.set()

        # Register signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: handle_shutdown(s))

        logger.info("Signal handlers registered (SIGTERM, SIGINT)")

        # Run the consumer
        await service.run()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")

    except Exception as e:
        logger.error(f"Fatal error in consumer service: {e}")
        logger.exception("Fatal error details:")
        sys.exit(1)

    finally:
        # Ensure cleanup
        if service:
            try:
                logger.info("Running final shutdown sequence...")
                await service.shutdown()
            except Exception as e:
                logger.error(f"Error during final shutdown: {e}")
                logger.exception("Final shutdown error details:")

        logger.info("Consumer service exited")


if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Failed to start consumer service: {e}")
        logger.exception("Startup error details:")
        sys.exit(1)
