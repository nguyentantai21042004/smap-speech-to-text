"""
RabbitMQ Message Queue Manager for async job processing.
Provides comprehensive logging and error handling for message queue operations.
"""

import json
from typing import Optional, Callable, Any, Dict
import asyncio

import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue, Message, DeliveryMode
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel

from core.config import get_settings
from core.logger import logger


class QueueManager:
    """
    RabbitMQ Queue Manager with comprehensive logging and error handling.
    Handles connection lifecycle, message publishing, and queue management.
    """

    def __init__(self):
        """Initialize RabbitMQ queue manager."""
        try:
            logger.debug("🔍 Initializing RabbitMQ QueueManager...")
            self.settings = get_settings()
            self.connection: Optional[AbstractRobustConnection] = None
            self.channel: Optional[AbstractRobustChannel] = None
            self.exchange: Optional[Exchange] = None
            self.queue: Optional[Queue] = None
            logger.debug("RabbitMQ QueueManager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize QueueManager: {e}")
            logger.exception("QueueManager initialization error:")
            raise

    async def connect(self) -> None:
        """
        Connect to RabbitMQ server with comprehensive error handling.

        Raises:
            Exception: If connection fails
        """
        try:
            logger.info("Connecting to RabbitMQ...")

            # Mask password in logs
            rabbitmq_url = self.settings.rabbitmq_url
            masked_url = rabbitmq_url.replace(
                f":{self.settings.rabbitmq_password}@",
                ":****@"
            )
            logger.debug(f"Connection URL: {masked_url}")

            # Create robust connection (auto-reconnect)
            logger.debug("Creating robust connection...")
            self.connection = await aio_pika.connect_robust(
                rabbitmq_url,
                timeout=10.0
            )
            logger.info(f"Connected to RabbitMQ at {self.settings.rabbitmq_host}:{self.settings.rabbitmq_port}")

            # Create channel
            logger.debug("Creating channel...")
            self.channel = await self.connection.channel()
            # Note: QoS will be set in consume_jobs() with proper prefetch_count
            logger.debug("Channel created")

            # Declare exchange
            logger.debug(f"Declaring exchange: {self.settings.rabbitmq_exchange_name}")
            self.exchange = await self.channel.declare_exchange(
                name=self.settings.rabbitmq_exchange_name,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True  # Survive broker restart
            )
            logger.info(f"Exchange declared: {self.settings.rabbitmq_exchange_name}")

            # Declare queue
            logger.debug(f"Declaring queue: {self.settings.rabbitmq_queue_name}")
            self.queue = await self.channel.declare_queue(
                name=self.settings.rabbitmq_queue_name,
                durable=True,  # Survive broker restart
                arguments={
                    "x-message-ttl": self.settings.job_timeout * 1000,  # Message TTL in ms
                    "x-max-priority": 10  # Enable priority queue
                }
            )
            logger.info(f"Queue declared: {self.settings.rabbitmq_queue_name}")

            # Bind queue to exchange
            logger.debug(f"Binding queue to exchange with routing key: {self.settings.rabbitmq_routing_key}")
            await self.queue.bind(
                exchange=self.exchange,
                routing_key=self.settings.rabbitmq_routing_key
            )
            logger.info(f"Queue bound to exchange")

            logger.info("RabbitMQ connection established successfully")

        except aio_pika.exceptions.AMQPConnectionError as e:
            logger.error(f"❌ RabbitMQ connection error: {e}")
            logger.error(f"Check if RabbitMQ is running at {self.settings.rabbitmq_host}:{self.settings.rabbitmq_port}")
            logger.exception("Connection error details:")
            raise

        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            logger.exception("RabbitMQ connection error details:")
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from RabbitMQ server with proper cleanup.
        """
        try:
            logger.info("Disconnecting from RabbitMQ...")

            if self.channel and not self.channel.is_closed:
                logger.debug("Closing channel...")
                await self.channel.close()
                logger.debug("Channel closed")

            if self.connection and not self.connection.is_closed:
                logger.debug("Closing connection...")
                await self.connection.close()
                logger.debug("Connection closed")

            logger.info("RabbitMQ disconnected successfully")

        except Exception as e:
            logger.error(f"❌ Error disconnecting from RabbitMQ: {e}")
            logger.exception("Disconnect error details:")

    async def publish_job(
        self,
        job_id: str,
        job_data: Dict[str, Any],
        priority: int = 5
    ) -> bool:
        """
        Publish a job message to the queue.

        Args:
            job_id: Job identifier
            job_data: Job data dictionary
            priority: Message priority (0-10, higher = more priority)

        Returns:
            True if published successfully, False otherwise

        Raises:
            Exception: If publishing fails
        """
        try:
            logger.info(f"Publishing job to queue: job_id={job_id}, priority={priority}")

            if not self.exchange:
                logger.error("❌ Exchange not initialized. Call connect() first.")
                raise RuntimeError("RabbitMQ not connected")

            # Prepare message
            message_body = {
                "job_id": job_id,
                **job_data
            }

            # Serialize to JSON
            message_bytes = json.dumps(message_body).encode("utf-8")
            logger.debug(f"Message size: {len(message_bytes)} bytes")

            # Create message with options
            message = Message(
                body=message_bytes,
                delivery_mode=DeliveryMode.PERSISTENT,  # Survive broker restart
                priority=priority,
                content_type="application/json",
                message_id=job_id,
                headers={
                    "x-job-id": job_id,
                    "x-published-at": str(asyncio.get_event_loop().time())
                }
            )

            # Publish message
            await self.exchange.publish(
                message=message,
                routing_key=self.settings.rabbitmq_routing_key
            )

            logger.info(f"Job published successfully: job_id={job_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to publish job {job_id}: {e}")
            logger.exception("Publish error details:")
            raise

    async def consume_jobs(
        self,
        callback: Callable,
        prefetch_count: int = 1
    ) -> None:
        """
        Start consuming jobs from the queue.

        Args:
            callback: Async callback function to process messages
            prefetch_count: Number of messages to prefetch

        Raises:
            Exception: If consumption fails
        """
        try:
            logger.info(f"Starting to consume jobs from queue: {self.settings.rabbitmq_queue_name}")

            if not self.queue:
                logger.error("❌ Queue not initialized. Call connect() first.")
                raise RuntimeError("RabbitMQ not connected")

            # Set QoS
            logger.debug(f"Setting prefetch_count={prefetch_count}")
            await self.channel.set_qos(prefetch_count=prefetch_count)

            # Start consuming
            logger.info("Started consuming messages...")
            logger.info("Press Ctrl+C to stop")

            await self.queue.consume(callback)

        except Exception as e:
            logger.error(f"❌ Error consuming jobs: {e}")
            logger.exception("Consume error details:")
            raise

    def health_check(self) -> bool:
        """
        Check if RabbitMQ connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.connection:
                logger.debug("Health check: No connection")
                return False

            if self.connection.is_closed:
                logger.debug("Health check: Connection is closed")
                return False

            if not self.channel or self.channel.is_closed:
                logger.debug("Health check: Channel is closed")
                return False

            logger.debug("Health check: RabbitMQ is healthy")
            return True

        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
            return False

    async def get_queue_size(self) -> Optional[int]:
        """
        Get the number of messages in the queue.

        Returns:
            Number of messages, or None on error
        """
        try:
            if not self.queue:
                logger.warning("Queue not initialized")
                return None

            # Declare queue passively to get status
            queue_info = await self.channel.declare_queue(
                name=self.settings.rabbitmq_queue_name,
                passive=True
            )

            message_count = queue_info.declaration_result.message_count
            logger.debug(f"Queue size: {message_count} messages")
            return message_count

        except Exception as e:
            logger.error(f"❌ Failed to get queue size: {e}")
            logger.exception("Queue size error:")
            return None

    async def purge_queue(self) -> bool:
        """
        Purge all messages from the queue.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.warning(f"⚠️ Purging queue: {self.settings.rabbitmq_queue_name}")

            if not self.queue:
                logger.error("Queue not initialized")
                return False

            await self.queue.purge()
            logger.info(f"Queue purged successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to purge queue: {e}")
            logger.exception("Purge error:")
            return False


# Singleton instance
_queue_manager: Optional[QueueManager] = None


def get_queue_manager() -> QueueManager:
    """
    Get QueueManager instance (singleton).

    Returns:
        QueueManager instance
    """
    global _queue_manager

    try:
        if _queue_manager is None:
            logger.debug("Creating new QueueManager instance")
            _queue_manager = QueueManager()

        return _queue_manager

    except Exception as e:
        logger.error(f"❌ Failed to get queue manager: {e}")
        logger.exception("Queue manager initialization error:")
        raise
