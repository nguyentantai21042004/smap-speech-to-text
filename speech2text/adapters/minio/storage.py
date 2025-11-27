"""
MinIO Storage Adapter.
"""

import asyncio
from typing import BinaryIO
from ports.storage import StoragePort
from core.storage import get_minio_client


class MinioStorageAdapter(StoragePort):
    """Adapter for MinIO storage."""

    def __init__(self):
        self.client = get_minio_client()

    async def upload_file(
        self, file_data: BinaryIO, object_name: str, content_type: str
    ) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.client.upload_file, file_data, object_name, content_type
        )

    async def download_file(self, object_name: str, destination_path: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, self.client.download_file, object_name, destination_path
        )

    async def get_file_url(self, object_name: str) -> str:
        # This is fast enough to be sync usually, but let's be consistent if needed.
        # generate_presigned_url involves crypto but no network usually (unless checking bucket).
        return self.client.generate_presigned_url(object_name)
