"""
MinIO Object Storage client for audio file management.
"""

from functools import lru_cache
from typing import Optional, BinaryIO
from pathlib import Path
import io

from minio import Minio
from minio.error import S3Error

from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class MinIOClient:
    """MinIO client for managing audio files and results."""

    def __init__(self):
        """Initialize MinIO client."""
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        self.bucket_name = settings.minio_bucket_name

        # Ensure bucket exists
        self._ensure_bucket_exists()

        logger.info(
            f"MinIO client initialized: {settings.minio_endpoint}/{self.bucket_name}"
        )

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                logger.debug(f"MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to check/create bucket: {e}")
            raise

    def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: str = "audio/mpeg",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            file_data: File-like object to upload
            object_name: Name of the object in MinIO (path)
            content_type: MIME type of the file
            metadata: Optional metadata dictionary

        Returns:
            Object name (path) in MinIO

        Example:
            >>> client.upload_file(file, "uploads/123-audio.mp3")
        """
        try:
            # Get file size
            file_data.seek(0, io.SEEK_END)
            file_size = file_data.tell()
            file_data.seek(0)

            # Upload
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=metadata or {},
            )

            logger.info(f"Uploaded file to MinIO: {object_name} ({file_size} bytes)")
            return object_name

        except S3Error as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            raise

    def download_file(self, object_name: str, local_path: str) -> str:
        """
        Download a file from MinIO to local filesystem.

        Args:
            object_name: Object name in MinIO
            local_path: Local file path to save to

        Returns:
            Local file path

        Example:
            >>> client.download_file("uploads/123-audio.mp3", "/tmp/audio.mp3")
        """
        try:
            # Ensure directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            # Download
            self.client.fget_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=local_path,
            )

            logger.info(f"Downloaded file from MinIO: {object_name} → {local_path}")
            return local_path

        except S3Error as e:
            logger.error(f"Failed to download file from MinIO: {e}")
            raise

    def get_file_stream(self, object_name: str) -> BinaryIO:
        """
        Get a file stream from MinIO (without saving to disk).

        Args:
            object_name: Object name in MinIO

        Returns:
            File-like object (stream)
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name, object_name=object_name
            )
            logger.debug(f"Got file stream from MinIO: {object_name}")
            return response

        except S3Error as e:
            logger.error(f"Failed to get file stream from MinIO: {e}")
            raise

    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO.

        Args:
            object_name: Object name in MinIO

        Returns:
            True if deleted successfully
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name, object_name=object_name
            )
            logger.info(f"Deleted file from MinIO: {object_name}")
            return True

        except S3Error as e:
            logger.error(f"Failed to delete file from MinIO: {e}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in MinIO.

        Args:
            object_name: Object name in MinIO

        Returns:
            True if file exists
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name, object_name=object_name
            )
            return True
        except S3Error:
            return False

    def get_file_info(self, object_name: str) -> Optional[dict]:
        """
        Get file metadata from MinIO.

        Args:
            object_name: Object name in MinIO

        Returns:
            Dictionary with file info (size, content_type, etc.)
        """
        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket_name, object_name=object_name
            )
            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "metadata": stat.metadata,
                "etag": stat.etag,
            }
        except S3Error as e:
            logger.error(f"Failed to get file info from MinIO: {e}")
            return None

    def generate_presigned_url(
        self, object_name: str, expiry_seconds: int = 3600
    ) -> str:
        """
        Generate a presigned URL for temporary access to a file.

        Args:
            object_name: Object name in MinIO
            expiry_seconds: URL expiry time in seconds (default: 1 hour)

        Returns:
            Presigned URL
        """
        try:
            from datetime import timedelta

            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expiry_seconds),
            )
            logger.debug(f"Generated presigned URL for: {object_name}")
            return url

        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise


# Global singleton instance
_minio_client: Optional[MinIOClient] = None


@lru_cache()
def get_minio_client() -> MinIOClient:
    """
    Get or create global MinIO client instance (singleton).

    Returns:
        MinIOClient instance
    """
    global _minio_client
    if _minio_client is None:
        _minio_client = MinIOClient()
    return _minio_client
