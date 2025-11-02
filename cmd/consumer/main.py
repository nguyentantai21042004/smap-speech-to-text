"""
Message Consumer Service - Main entry point (Refactored).
Implements clean separation of concerns:
- Handler logic is separated into dedicated classes
- Only initialization logic remains in this file
"""

import asyncio
import signal

from core import DatabaseManager, MessageBroker, get_settings, logger
from services import KeywordService, TaskService
from internal.consumer.handlers import KeywordHandler


class ConsumerService:
    """
    Consumer Service manages the lifecycle of message handlers.
    Handles graceful shutdown and resource cleanup.
    """

    def __init__(self):
        self.settings = get_settings()
        self.message_broker = None
        self.handler = None
        self.shutdown_event = asyncio.Event()

    async def startup(self):
        """Initialize and connect to required services."""
        logger.info(f"Starting {self.settings.app_name} Consumer service...")

        # Connect to database
        try:
            await DatabaseManager.connect()
            logger.info("Database connected")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

        # Connect to message broker
        try:
            self.message_broker = MessageBroker()
            await self.message_broker.connect()
            logger.info("Message broker connected")
        except Exception as e:
            logger.error(f"Failed to connect to message broker: {e}")
            raise

        # Initialize services
        keyword_service = KeywordService()
        task_service = TaskService()

        # Initialize handler with shutdown event
        self.handler = KeywordHandler(
            message_broker=self.message_broker,
            keyword_service=keyword_service,
            task_service=task_service,
            shutdown_event=self.shutdown_event,
        )

        logger.info("Consumer service started successfully")

    async def shutdown(self):
        """Graceful shutdown of services."""
        logger.info("Shutting down Consumer service...")

        # Disconnect from message broker
        try:
            if self.message_broker:
                await self.message_broker.disconnect()
            logger.info("Message broker disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting message broker: {e}")

        # Disconnect from database
        try:
            await DatabaseManager.disconnect()
            logger.info("Database disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting database: {e}")

        logger.info("Consumer service stopped")

    async def run(self):
        """Main service loop."""
        try:
            await self.startup()

            # Start handling messages
            logger.info("Starting to handle messages...")
            await self.handler.start_handling()

        except Exception as e:
            logger.error(f"Error in consumer service: {e}")
            raise
        finally:
            await self.shutdown()


async def main():
    """Main entry point for the consumer service."""
    service = ConsumerService()

    # Get the event loop
    loop = asyncio.get_running_loop()

    # Register signal handlers for graceful shutdown (asyncio-compatible)
    def handle_shutdown():
        logger.info("Received shutdown signal")
        service.shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_shutdown)

    try:
        await service.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
