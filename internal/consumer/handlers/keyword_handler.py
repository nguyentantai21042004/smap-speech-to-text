"""
Keyword Extraction Handler.
Handles keyword extraction tasks from the message broker.
"""

import asyncio
from typing import Dict, Any, Optional

from core import logger
from core.messaging import QueueManager, get_queue_manager
from services.interfaces import IKeywordService, ITaskService


class KeywordHandler:
    """
    Handler for processing keyword extraction tasks.
    Implements the message handler pattern for asynchronous task processing.
    """

    def __init__(
        self,
        message_broker: QueueManager,
        keyword_service: IKeywordService,
        task_service: ITaskService,
        shutdown_event: Optional[asyncio.Event] = None,
    ):
        """
        Initialize KeywordHandler.

        Args:
            message_broker: QueueManager instance for handling messages
            keyword_service: Service for keyword extraction
            task_service: Service for task management
            shutdown_event: Optional event to signal shutdown
        """
        self.message_broker = message_broker
        self.keyword_service = keyword_service
        self.task_service = task_service
        self.shutdown_event = shutdown_event

    async def start_handling(self) -> None:
        """Start handling messages from the broker."""
        logger.info("Starting keyword extraction handler...")
        await self.message_broker.consume(
            self.process_message, shutdown_event=self.shutdown_event
        )

    async def process_message(self, message: Dict[str, Any]) -> None:
        """
        Process a single message from the broker.

        Args:
            message: Message data containing task information
        """
        task_id = message.get("task_id")
        task_type = message.get("task_type")

        if not task_id or not task_type:
            logger.error(f"Invalid message format: {message}")
            return

        logger.info(f"Processing task {task_id} of type {task_type}")

        try:
            # Update task status to processing
            await self.task_service.update_task_status(
                task_id=task_id,
                status="processing",
            )

            # Process based on task type
            if task_type == "keyword_extraction":
                result = await self._process_keyword_extraction(message)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            # Update task status to completed
            await self.task_service.update_task_status(
                task_id=task_id,
                status="completed",
                result=result,
            )

            logger.info(f"Successfully processed task {task_id}")

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            # Update task status to failed
            await self.task_service.update_task_status(
                task_id=task_id,
                status="failed",
                error=str(e),
            )

    async def _process_keyword_extraction(self, message: Dict[str, Any]) -> Dict:
        """
        Process keyword extraction task.

        Args:
            message: Message containing keyword extraction parameters

        Returns:
            Dict: Extraction result
        """
        payload = message.get("payload", {})
        text = payload.get("text")
        method = payload.get("method", "default")
        num_keywords = payload.get("num_keywords", 10)

        if not text:
            raise ValueError("Missing 'text' in payload")

        # Perform keyword extraction
        result = await self.keyword_service.extract_keywords_sync(
            text=text,
            method=method,
            num_keywords=num_keywords,
        )

        return result
