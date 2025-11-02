"""
File upload service for handling file uploads to MinIO.
Separates file upload from STT processing.
"""

from typing import BinaryIO, Optional
from pathlib import Path

from core.logger import logger
from core.storage import get_minio_client
from repositories.objectid_utils import objectid_to_str
from core.database import get_database


class FileService:
    """Service for handling file uploads and management."""

    def __init__(self):
        """Initialize file service."""
        logger.debug("FileService initialized")

    async def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        file_size_mb: float,
    ) -> dict:
        """
        Upload file to MinIO and create file record.
        This is a separate service from STT processing.

        Args:
            file_data: File data
            filename: Original filename
            file_size_mb: File size in MB

        Returns:
            Dictionary with file_id and metadata

        Raises:
            Exception: If upload fails
        """
        try:
            logger.info(f"Uploading file: filename={filename}, size={file_size_mb:.2f}MB")

            # Validate file size
            if file_size_mb > 500:
                error_msg = f"File too large: {file_size_mb:.2f}MB (max 500MB)"
                logger.error(f"{error_msg}")
                raise ValueError(error_msg)

            # Upload to MinIO first (using temp UUID)
            import uuid
            temp_id = str(uuid.uuid4())

            logger.info(f"Uploading file to MinIO...")
            minio_path = await self._upload_to_minio(file_data, filename, temp_id)
            logger.info(f"File uploaded: {minio_path}")

            # Create file record in database (MongoDB will generate _id)
            from datetime import datetime

            db = await get_database()
            collection = await db.get_collection("file_records")

            file_record_data = {
                "original_filename": filename,
                "minio_path": minio_path,
                "file_size_mb": file_size_mb,
                "content_type": "audio/mpeg",  # Default for audio
                "created_at": datetime.utcnow(),
            }

            # Insert into MongoDB
            result = await collection.insert_one(file_record_data)

            # Get the inserted _id as file_id
            file_id = objectid_to_str(result.inserted_id)

            logger.info(f"File record created: file_id={file_id}")

            return {
                "status": "success",
                "file_id": file_id,
                "message": "File uploaded successfully",
                "details": {
                    "filename": filename,
                    "size_mb": file_size_mb,
                    "minio_path": minio_path,
                },
            }

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            logger.exception("File upload error details:")
            raise

    async def _upload_to_minio(
        self, file_data: BinaryIO, filename: str, file_id: str
    ) -> str:
        """
        Upload file to MinIO.

        Args:
            file_data: File data
            filename: Original filename
            file_id: File identifier for path

        Returns:
            MinIO object path
        """
        try:
            logger.debug(f"Uploading to MinIO: filename={filename}, file_id={file_id}")

            # Create MinIO path
            file_extension = Path(filename).suffix
            minio_filename = f"{file_id}{file_extension}"
            minio_path = f"uploads/{minio_filename}"

            # Get MinIO client
            minio_client = get_minio_client()

            # Upload file
            minio_client.upload_file(
                file_data=file_data, object_name=minio_path, content_type="audio/mpeg"
            )

            logger.debug(f"File uploaded to MinIO: {minio_path}")

            return minio_path

        except Exception as e:
            logger.error(f"MinIO upload failed: {e}")
            logger.exception("MinIO upload error details:")
            raise

    async def get_file(self, file_id: str) -> Optional[dict]:
        """
        Get file record by file_id.

        Args:
            file_id: File identifier

        Returns:
            File record dictionary or None if not found
        """
        try:
            from repositories.objectid_utils import str_to_objectid

            db = await get_database()
            collection = await db.get_collection("file_records")

            object_id = str_to_objectid(file_id)
            doc = await collection.find_one({"_id": object_id})

            if doc:
                from datetime import datetime

                created_at = doc.get("created_at")
                if isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                elif created_at:
                    created_at = str(created_at)

                return {
                    "file_id": file_id,
                    "original_filename": doc.get("original_filename"),
                    "minio_path": doc.get("minio_path"),
                    "file_size_mb": doc.get("file_size_mb"),
                    "created_at": created_at,
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get file {file_id}: {e}")
            logger.exception("Get file error details:")
            raise


# Singleton instance
_file_service: Optional[FileService] = None


def get_file_service() -> FileService:
    """Get file service instance (singleton)."""
    global _file_service

    try:
        if _file_service is None:
            logger.debug("Creating new FileService instance")
            _file_service = FileService()

        return _file_service

    except Exception as e:
        logger.error(f"Failed to get file service: {e}")
        logger.exception("File service initialization error:")
        raise

