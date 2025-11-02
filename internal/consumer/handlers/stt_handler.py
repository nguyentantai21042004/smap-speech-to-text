"""
STT job handler for RabbitMQ consumer.
Includes comprehensive logging and error handling.
"""

import json
from typing import Dict, Any

from aio_pika import IncomingMessage
from aio_pika.abc import AbstractIncomingMessage

from core.logger import logger
from worker.processor import process_stt_job
from worker.errors import TransientError, PermanentError


async def handle_stt_message(message: AbstractIncomingMessage) -> None:
    """
    Handle an STT job message from RabbitMQ queue.

    This is the entry point for the RabbitMQ consumer.
    It processes the message, calls the STT processor, and handles acknowledgment.

    Args:
        message: RabbitMQ incoming message

    Raises:
        Exception: If message processing fails (message will be requeued)
    """
    job_id = None

    try:
        # Decode message body
        logger.info(f"📝 ========== HANDLER: Message received ==========")
        message_body = message.body.decode("utf-8")
        logger.debug(f"Message body: {message_body[:200]}...")  # Log first 200 chars

        # Parse JSON
        try:
            message_data = json.loads(message_body)
            job_id = message_data.get("job_id")
            logger.info(f"📝 Processing job: job_id={job_id}")
            logger.debug(f"Message data: {message_data}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ HANDLER: Failed to parse message JSON: {e}")
            logger.error(f"Invalid message body: {message_body}")
            # Reject message without requeue (invalid format)
            await message.reject(requeue=False)
            logger.warning(f"⚠️ Message rejected (invalid JSON)")
            return

        # Validate required fields
        if not job_id:
            logger.error(f"❌ HANDLER: Missing job_id in message")
            await message.reject(requeue=False)
            logger.warning(f"⚠️ Message rejected (missing job_id)")
            return

        # Process the STT job
        logger.info(f"📝 ========== HANDLER: Starting STT processing: job_id={job_id} ==========")
        result = await process_stt_job(job_id)
        logger.info(f"✅ ========== HANDLER: STT processing completed: job_id={job_id} ==========")
        logger.debug(f"Processing result: {result}")

        # Acknowledge message (successfully processed)
        await message.ack()
        logger.info(f"✅ HANDLER: Message acknowledged: job_id={job_id}")

    except TransientError as e:
        # Transient errors - requeue for retry
        logger.error(f"❌ HANDLER: Transient error for job {job_id}: {e}")
        logger.exception("Transient error details:")

        # Reject and requeue message for retry
        await message.reject(requeue=True)
        logger.warning(f"⚠️ HANDLER: Message requeued for retry: job_id={job_id}")

    except PermanentError as e:
        # Permanent errors - don't requeue
        logger.error(f"❌ HANDLER: Permanent error for job {job_id}: {e}")
        logger.exception("Permanent error details:")

        # Reject without requeue (permanent failure)
        await message.reject(requeue=False)
        logger.warning(f"⚠️ HANDLER: Message rejected (permanent error): job_id={job_id}")

        # Job status should already be updated to FAILED in the processor

    except Exception as e:
        # Unexpected errors - log and requeue
        logger.error(f"❌ HANDLER: Unexpected error for job {job_id}: {e}")
        logger.exception("Handler error details:")

        # Reject and requeue for retry (may be temporary issue)
        await message.reject(requeue=True)
        logger.warning(f"⚠️ HANDLER: Message requeued due to unexpected error: job_id={job_id}")
