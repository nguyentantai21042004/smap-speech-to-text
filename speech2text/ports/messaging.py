"""
Messaging Ports.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class MessagingPort(ABC):
    """Abstract interface for Messaging/Queue."""

    @abstractmethod
    async def publish(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a queue."""
        pass

    @abstractmethod
    async def consume(self, queue_name: str, callback: Any) -> None:
        """Consume messages from a queue."""
        pass
