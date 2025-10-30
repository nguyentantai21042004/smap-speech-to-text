"""
Message broker for RabbitMQ.
Implements Producer-Consumer Pattern.
Follows Single Responsibility Principle - only handles messaging.
"""

import asyncio
import json
from typing import Any, Callable, Dict, Optional

import aio_pika
from aio_pika import Channel, Connection, Exchange, Queue, IncomingMessage
from aio_pika.pool import Pool

from .config import get_settings
from .logger import logger


class MessageBroker:
    """
    Manages RabbitMQ connections and implements Producer-Consumer pattern.
    Can act as both producer (publisher) and consumer.
    """

    def __init__(self):
        self.settings = get_settings()
        self._connection: Optional[Connection] = None
        self._channel: Optional[Channel] = None
        self._exchange: Optional[Exchange] = None
        self._queue: Optional[Queue] = None
        self._connection_pool: Optional[Pool] = None
        self._channel_pool: Optional[Pool] = None

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            self._connection = await aio_pika.connect_robust(
                self.settings.rabbitmq_url
            )
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)

            # Declare exchange
            self._exchange = await self._channel.declare_exchange(
                self.settings.rabbitmq_exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )

            # Declare queue
            self._queue = await self._channel.declare_queue(
                self.settings.rabbitmq_queue_name,
                durable=True,
            )

            # Bind queue to exchange
            await self._queue.bind(
                self._exchange,
                routing_key=self.settings.rabbitmq_routing_key,
            )

            logger.info(
                f"Connected to RabbitMQ - Exchange: {self.settings.rabbitmq_exchange_name}, "
                f"Queue: {self.settings.rabbitmq_queue_name}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        try:
            if self._channel:
                await self._channel.close()
            if self._connection:
                await self._connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to disconnect from RabbitMQ: {e}")
            raise

    async def publish(
        self,
        message: Dict[str, Any],
        routing_key: Optional[str] = None,
    ) -> None:
        """
        Publish a message to RabbitMQ (Producer role).
        
        Args:
            message: Dictionary message to publish
            routing_key: Optional routing key, defaults to configured routing key
        """
        if not self._exchange:
            raise RuntimeError("Not connected to RabbitMQ. Call connect() first.")

        routing_key = routing_key or self.settings.rabbitmq_routing_key

        try:
            await self._exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key=routing_key,
            )
            logger.debug(f"Published message to {routing_key}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    async def consume(
        self,
        callback: Callable[[Dict[str, Any]], Any],
        queue_name: Optional[str] = None,
        shutdown_event: Optional[asyncio.Event] = None,
    ) -> None:
        """
        Consume messages from RabbitMQ (Consumer role).
        
        Args:
            callback: Async function to process each message
            queue_name: Optional queue name, defaults to configured queue
            shutdown_event: Optional event to signal shutdown
        """
        if not self._channel:
            raise RuntimeError("Not connected to RabbitMQ. Call connect() first.")

        queue_name = queue_name or self.settings.rabbitmq_queue_name

        try:
            queue = await self._channel.declare_queue(
                queue_name,
                durable=True,
            )

            async def process_message(message: IncomingMessage) -> None:
                async with message.process():
                    try:
                        body = json.loads(message.body.decode())
                        logger.debug(f"Received message from {queue_name}: {body}")
                        await callback(body)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        raise

            consumer_tag = await queue.consume(process_message)
            logger.info(f"Started consuming from queue: {queue_name}")
            
            # Keep consuming until shutdown signal
            if shutdown_event:
                await shutdown_event.wait()
                logger.info("Shutdown signal received, stopping consumer...")
                await queue.cancel(consumer_tag)
            else:
                # Keep consuming forever if no shutdown event
                await asyncio.Future()
        except asyncio.CancelledError:
            logger.info("Consumer cancelled")
            raise
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")
            raise

    async def get_queue_size(self, queue_name: Optional[str] = None) -> int:
        """
        Get the number of messages in a queue.
        
        Args:
            queue_name: Optional queue name, defaults to configured queue
            
        Returns:
            Number of messages in queue
        """
        if not self._channel:
            raise RuntimeError("Not connected to RabbitMQ. Call connect() first.")

        queue_name = queue_name or self.settings.rabbitmq_queue_name

        try:
            queue = await self._channel.declare_queue(
                queue_name,
                durable=True,
                passive=True,
            )
            return queue.declaration_result.message_count
        except Exception as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0

