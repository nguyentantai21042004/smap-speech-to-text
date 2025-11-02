#!/usr/bin/env python3
"""
Upload entire whisper folder to MinIO bucket.
This script will:
1. Validate MinIO connection
2. Check if bucket exists (for models)
3. Delete all existing objects in the models bucket
4. Upload entire whisper folder structure to MinIO

Usage:
    python scripts/upload_whisper_folder_to_minio.py

Environment Variables (required):
    MINIO_ENDPOINT: MinIO server endpoint (e.g., minio:9000)
    MINIO_ACCESS_KEY: MinIO access key
    MINIO_SECRET_KEY: MinIO secret key
    MINIO_BUCKET_MODEL: MinIO bucket name for models (default: stt-whisper-models)
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import get_settings
from core.logger import logger as core_logger  # In case preferred elsewhere
from minio import Minio
from minio.error import S3Error

# Setup logger for this script
logger = logging.getLogger("upload_whisper_to_minio")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s | %(asctime)s | %(name)s | %(message)s")
ch.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(ch)
logger.propagate = False  # Avoid duplicate logs if root logger is used elsewhere


def get_minio_client_direct() -> Minio:
    """
    Get MinIO client directly (not using wrapper).

    Returns:
        Minio client instance
    """
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )


def validate_minio_connection(client: Minio, bucket_name: str) -> bool:
    """
    Validate MinIO connection and bucket access.

    Args:
        client: MinIO client instance
        bucket_name: Bucket name to check

    Returns:
        True if connection is valid, False otherwise
    """
    try:
        # Check if bucket exists
        if not client.bucket_exists(bucket_name):
            logger.warning(f"Bucket '{bucket_name}' does not exist, creating it...")
            try:
                client.make_bucket(bucket_name)
                logger.info(f"✓ Created bucket: {bucket_name}")
            except S3Error as e:
                logger.error(f"Failed to create bucket: {e}")
                return False
        else:
            logger.info(f"✓ Bucket exists: {bucket_name}")

        return True

    except S3Error as e:
        logger.error(f"Failed to validate MinIO connection: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error validating MinIO: {e}")
        return False


def delete_all_objects_in_bucket(
    client: Minio, bucket_name: str, prefix: str = ""
) -> int:
    """
    Delete all objects in a bucket (optionally with a prefix).

    Args:
        client: MinIO client instance
        bucket_name: Bucket name
        prefix: Optional prefix to filter objects (e.g., "whisper-models/")

    Returns:
        Number of objects deleted
    """
    try:
        logger.info(
            f"🗑️  Deleting all objects in bucket '{bucket_name}' with prefix '{prefix}'..."
        )

        # List all objects with the prefix
        objects_to_delete = []
        try:
            objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)
            for obj in objects:
                objects_to_delete.append(obj.object_name)
        except S3Error as e:
            logger.warning(f"Failed to list objects: {e}")
            return 0

        if not objects_to_delete:
            logger.info("   No objects found to delete")
            return 0

        logger.info(f"   Found {len(objects_to_delete)} object(s) to delete")

        # Delete objects in batch
        deleted_count = 0
        errors = client.remove_objects(bucket_name, objects_to_delete)
        for error in errors:
            logger.error(f"   Error deleting object: {error}")
        else:
            deleted_count = len(objects_to_delete)

        logger.info(f"✓ Deleted {deleted_count} object(s)")
        return deleted_count

    except S3Error as e:
        logger.error(f"Failed to delete objects: {e}")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error deleting objects: {e}")
        return 0


def upload_file_to_minio(
    client: Minio,
    bucket_name: str,
    local_path: Path,
    object_name: str,
) -> bool:
    """
    Upload a single file to MinIO.

    Args:
        client: MinIO client instance
        bucket_name: Bucket name
        local_path: Local file path
        object_name: Object name (path) in MinIO

    Returns:
        True if successful, False otherwise
    """
    try:
        file_size = local_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        with open(local_path, "rb") as f:
            client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=f,
                length=file_size,
                content_type="application/octet-stream",
            )

        logger.debug(f"   ✓ {object_name} ({file_size_mb:.2f}MB)")
        return True

    except Exception as e:
        logger.error(f"   ✗ Failed to upload {object_name}: {e}")
        return False


def upload_folder_recursive(
    client: Minio,
    bucket_name: str,
    local_folder: Path,
    minio_prefix: str = "",
) -> Tuple[int, int]:
    """
    Upload entire folder recursively to MinIO.

    Args:
        client: MinIO client instance
        bucket_name: Bucket name
        local_folder: Local folder path to upload
        minio_prefix: Prefix for objects in MinIO (e.g., "whisper/")

    Returns:
        Tuple of (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0

    if not local_folder.exists():
        logger.error(f"Local folder does not exist: {local_folder}")
        return 0, 0

    if not local_folder.is_dir():
        logger.error(f"Path is not a directory: {local_folder}")
        return 0, 0

    logger.info(f"Uploading folder: {local_folder}")
    if minio_prefix:
        logger.info(f"   MinIO prefix: {minio_prefix}")
    else:
        logger.info(f"   MinIO prefix: (none - direct upload to bucket root)")

    # Walk through all files
    for root, dirs, files in os.walk(local_folder):
        root_path = Path(root)

        for file in files:
            local_file = root_path / file

            # Calculate relative path from local_folder
            relative_path = local_file.relative_to(local_folder)

            # Construct MinIO object name
            if minio_prefix:
                object_name = f"{minio_prefix}{relative_path}".replace("\\", "/")
            else:
                object_name = str(relative_path).replace("\\", "/")

            # Skip certain files
            if file.startswith(".") and file != ".gitkeep":
                logger.debug(f"   Skipping hidden file: {relative_path}")
                continue

            # Upload file
            if upload_file_to_minio(client, bucket_name, local_file, object_name):
                success_count += 1
            else:
                failure_count += 1

    return success_count, failure_count


def main():
    """Main entry point."""
    try:
        settings = get_settings()

        logger.info("=" * 70)
        logger.info("Upload Whisper Folder to MinIO")
        logger.info("=" * 70)
        logger.info("")
        logger.info(f"MinIO Endpoint: {settings.minio_endpoint}")
        logger.info(f"Bucket: {settings.minio_bucket_model_name}")
        logger.info(f"SSL: {settings.minio_use_ssl}")
        logger.info("")

        # Get MinIO client
        try:
            client = get_minio_client_direct()
        except Exception as e:
            logger.error(f"Failed to create MinIO client: {e}")
            sys.exit(1)

        # Validate connection
        if not validate_minio_connection(client, settings.minio_bucket_model_name):
            logger.error("MinIO connection validation failed")
            sys.exit(1)

        logger.info("")
        logger.info("=" * 70)
        logger.info("Step 1: Cleaning bucket")
        logger.info("=" * 70)

        # Delete all existing objects in bucket (clean entire bucket since it only contains models)
        # No prefix needed - this bucket only contains whisper models
        deleted_count = delete_all_objects_in_bucket(
            client, settings.minio_bucket_model_name, prefix=""
        )

        logger.info("")
        logger.info("=" * 70)
        logger.info("Step 2: Uploading whisper folder")
        logger.info("=" * 70)
        logger.info("")

        # Upload whisper folder
        whisper_folder = project_root / "whisper"

        if not whisper_folder.exists():
            logger.error(f"Whisper folder not found: {whisper_folder}")
            sys.exit(1)

        # Upload without prefix since bucket only contains models
        success_count, failure_count = upload_folder_recursive(
            client=client,
            bucket_name=settings.minio_bucket_model_name,
            local_folder=whisper_folder,
            minio_prefix="",  # No prefix - bucket only contains models
        )

        # Summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("Upload Summary")
        logger.info("=" * 70)
        logger.info(f"Objects deleted: {deleted_count}")
        logger.info(f"Files uploaded successfully: {success_count}")
        logger.info(f"Files failed: {failure_count}")
        logger.info("")

        if failure_count == 0:
            logger.info("=" * 70)
            logger.info("Upload complete! All files uploaded successfully")
            logger.info("=" * 70)
            logger.info("")
            logger.info("Next steps:")
            logger.info("   1. Models are now available in MinIO")
            logger.info(
                "   2. Consumer service will download models automatically on startup"
            )
            logger.info("   3. Models are cached locally after first download")
        else:
            logger.warning("=" * 70)
            logger.warning(
                f"Upload partially complete ({success_count} success, {failure_count} failed)"
            )
            logger.warning("=" * 70)
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("\nUpload interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"\nUpload failed: {e}")
        logger.exception("Upload error details:")
        sys.exit(1)


if __name__ == "__main__":
    main()
