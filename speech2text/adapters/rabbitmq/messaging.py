"""
RabbitMQ Messaging Adapter.
"""

from typing import Dict, Any
from ports.messaging import MessagingPort
from core.messaging import get_queue_manager


class RabbitMQAdapter(MessagingPort):
    """Adapter for RabbitMQ messaging."""

    def __init__(self):
        self.manager = get_queue_manager()

    async def publish(self, queue_name: str, message: Dict[str, Any]) -> bool:
        # Note: queue_name is currently managed by QueueManager settings
        job_id = message.get("job_id", "unknown")
        return await self.manager.publish_job(job_id, message)

    async def consume(self, queue_name: str, callback: Any) -> None:
        await self.manager.consume_jobs(callback)
