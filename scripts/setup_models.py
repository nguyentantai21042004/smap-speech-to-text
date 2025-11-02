#!/usr/bin/env python3
"""
Setup script to download Whisper models from MinIO private storage.
Run this script once to download all models or specific models.

Usage:
    python scripts/setup_models.py              # Download all models
    python scripts/setup_models.py medium       # Download specific model
    python scripts/setup_models.py medium large # Download multiple models

Environment Variables (required for MinIO connection):
    MINIO_ENDPOINT: MinIO server endpoint (e.g., minio:9000)
    MINIO_ACCESS_KEY: MinIO access key
    MINIO_SECRET_KEY: MinIO secret key
    MINIO_BUCKET_MODEL: MinIO bucket name for models (default: stt-whisper-models)
    MINIO_USE_SSL: Use SSL for MinIO connection (default: false)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.model_downloader import (
    get_model_downloader,
    MODEL_CONFIGS,
    get_minio_client_for_models,
)
from core.config import get_settings
from minio import Minio
from minio.error import S3Error


# ---- LOGGER SETUP ----
def setup_logger() -> logging.Logger:
    log_name = "setup_models"
    log = logging.getLogger(log_name)
    log.setLevel(logging.INFO)
    # Avoid repeated handlers in notebook/interactive
    if not log.handlers:
        ch = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(levelname)s | %(asctime)s | %(name)s | %(message)s"
        )
        ch.setFormatter(formatter)
        log.addHandler(ch)
    log.propagate = (
        False  # Avoid output duplication if root logger is configured elsewhere
    )
    return log


logger = setup_logger()


def validate_minio_connection() -> bool:
    """
    Validate MinIO connection before attempting downloads.

    Returns:
        True if connection is valid, False otherwise
    """
    try:
        settings = get_settings()

        # Check required environment variables
        required_vars = [
            ("MINIO_ENDPOINT", settings.minio_endpoint),
            ("MINIO_ACCESS_KEY", settings.minio_access_key),
            ("MINIO_SECRET_KEY", settings.minio_secret_key),
            ("MINIO_BUCKET_MODEL", settings.minio_bucket_model_name),
        ]

        missing_vars = [var for var, value in required_vars if not value]
        if missing_vars:
            logger.error(
                f"Missing required MinIO environment variables: {', '.join(missing_vars)}"
            )
            return False

        # Try to connect to MinIO models bucket (separate from audio files bucket)
        logger.info(f"Validating MinIO connection to: {settings.minio_endpoint}")
        minio_client = get_minio_client_for_models()
        models_bucket = settings.minio_bucket_model_name

        # Check if models bucket exists
        try:
            bucket_exists = minio_client.bucket_exists(models_bucket)
            if not bucket_exists:
                logger.error(f"MinIO models bucket '{models_bucket}' does not exist")
                logger.info(f"Please create the bucket or verify bucket name")
                return False
        except S3Error as e:
            logger.error(f"Failed to check bucket existence: {e}")
            return False

        logger.info(f"✓ MinIO connection validated successfully")
        logger.info(f"  Endpoint: {settings.minio_endpoint}")
        logger.info(f"  Bucket: {settings.minio_bucket_model_name}")
        logger.info(f"  SSL: {settings.minio_use_ssl}")

        return True

    except Exception as e:
        logger.error(f"Failed to validate MinIO connection: {e}")
        logger.info("Please check:")
        logger.info("  1. MinIO server is running and accessible")
        logger.info("  2. MINIO_ENDPOINT is correct (e.g., minio:9000)")
        logger.info("  3. MINIO_ACCESS_KEY and MINIO_SECRET_KEY are correct")
        logger.info("  4. Network connectivity to MinIO server")
        return False


def validate_model_name(model: str) -> bool:
    """
    Validate model name against known models.

    Args:
        model: Model name to validate

    Returns:
        True if valid, False otherwise
    """
    if model not in MODEL_CONFIGS:
        valid_models = ", ".join(MODEL_CONFIGS.keys())
        logger.error(f"Invalid model name: '{model}'")
        logger.info(f"Valid models: {valid_models}")
        return False
    return True


def download_model(model: str, downloader) -> bool:
    """
    Download a single model from MinIO.

    Args:
        model: Model name to download
        downloader: ModelDownloader instance

    Returns:
        True if successful, False otherwise
    """
    try:
        if not validate_model_name(model):
            return False

        config = MODEL_CONFIGS[model]
        logger.info(f"\nDownloading model: {model}")
        logger.info(f"   Size: {config['size_mb']:.0f}MB")
        logger.info(f"   MinIO path: {config['minio_path']}")

        model_path = downloader.ensure_model_exists(model)

        # Verify file was downloaded and exists
        if not Path(model_path).exists():
            logger.error(f"Downloaded model file not found: {model_path}")
            return False

        file_size_mb = Path(model_path).stat().st_size / (1024 * 1024)
        logger.info(f"✓ Model '{model}' downloaded successfully")
        logger.info(f"   Path: {model_path}")
        logger.info(f"   Size: {file_size_mb:.2f}MB")

        return True

    except Exception as e:
        logger.error(f"Failed to download model '{model}': {e}")
        logger.exception("Download error details:")
        return False


def download_all_models(downloader) -> dict:
    """
    Download all available models.

    Args:
        downloader: ModelDownloader instance

    Returns:
        Dictionary with download results for each model
    """
    results = {}
    total_models = len(MODEL_CONFIGS)
    total_size = sum(config["size_mb"] for config in MODEL_CONFIGS.values())

    logger.info(
        f"Downloading ALL models ({total_models} models, ~{total_size:.0f}MB total)"
    )
    logger.warning("This may take a while depending on network speed...")

    for model in MODEL_CONFIGS.keys():
        results[model] = download_model(model, downloader)

    return results


def show_model_status(downloader) -> None:
    """
    Show status of all models (downloaded or missing).

    Args:
        downloader: ModelDownloader instance
    """
    logger.info("\n" + "=" * 70)
    logger.info("Model Status:")
    logger.info("=" * 70)

    status = downloader.list_available_models()
    available_count = sum(1 for v in status.values() if v)
    total_count = len(status)

    for model, available in status.items():
        config = MODEL_CONFIGS[model]
        status_icon = "✓" if available else "✗"
        status_text = "Available" if available else "Missing"
        logger.info(
            f"{status_icon} {model:8s} - {config['size_mb']:6.0f}MB - {status_text}"
        )

    logger.info("=" * 70)
    logger.info(f"Summary: {available_count}/{total_count} models available")


def main():
    """Main entry point."""
    try:
        logger.info("=" * 70)
        logger.info("Whisper Model Setup - MinIO Download")
        logger.info("=" * 70)
        logger.info("")

        # Validate MinIO connection first
        if not validate_minio_connection():
            logger.error("MinIO connection validation failed")
            logger.info("Cannot proceed without valid MinIO connection")
            sys.exit(1)

        logger.info("")

        # Get model downloader
        downloader = get_model_downloader()

        # Parse arguments
        models_to_download = sys.argv[1:] if len(sys.argv) > 1 else None

        success_count = 0
        total_count = 0

        if models_to_download:
            # Download specific models
            total_count = len(models_to_download)
            logger.info(
                f"Downloading {total_count} specific model(s): {', '.join(models_to_download)}"
            )
            logger.info("")

            for model in models_to_download:
                if download_model(model, downloader):
                    success_count += 1
                else:
                    logger.warning(
                        f"Model '{model}' download failed, continuing with other models..."
                    )
        else:
            # Download all models
            results = download_all_models(downloader)
            total_count = len(results)
            success_count = sum(1 for success in results.values() if success)

        # Show final status
        show_model_status(downloader)

        logger.info("")
        if success_count == total_count:
            logger.info("=" * 70)
            logger.info(
                f"✓ Model setup complete! ({success_count}/{total_count} models)"
            )
            logger.info("=" * 70)
        else:
            logger.warning("=" * 70)
            logger.warning(
                f"Model setup partially complete ({success_count}/{total_count} models)"
            )
            logger.warning("=" * 70)
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("\nSetup interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"\nSetup failed: {e}")
        logger.exception("Setup error details:")
        sys.exit(1)


if __name__ == "__main__":
    main()
