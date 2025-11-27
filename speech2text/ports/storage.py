"""
Storage Ports.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Any


class StoragePort(ABC):
    """Abstract interface for Object Storage."""

    @abstractmethod
    async def upload_file(
        self, file_data: BinaryIO, object_name: str, content_type: str
    ) -> str:
        """Upload a file and return its path/url."""
        pass

    @abstractmethod
    async def download_file(self, object_name: str, destination_path: str) -> None:
        """Download a file to local path."""
        pass

    @abstractmethod
    async def get_file_url(self, object_name: str) -> str:
        """Get presigned URL or public URL."""
        pass
