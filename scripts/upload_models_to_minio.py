#!/usr/bin/env python3
"""
Upload Whisper models from local directory to MinIO.
Run this once to upload models to MinIO for the first time.

Usage:
    python scripts/upload_models_to_minio.py              # Upload all models
    python scripts/upload_models_to_minio.py medium       # Upload specific model
    python scripts/upload_models_to_minio.py medium large # Upload multiple models
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import get_settings
from core.logger import logger
from core.storage import get_minio_client
from worker.model_downloader import MODEL_CONFIGS


def upload_model(model_name: str, local_dir: Path) -> bool:
    """
    Upload a model file to MinIO.

    Args:
        model_name: Name of model (tiny, base, small, medium, large)
        local_dir: Local directory containing model files

    Returns:
        True if successful, False otherwise
    """
    try:
        if model_name not in MODEL_CONFIGS:
            logger.error(f"❌ Invalid model: {model_name}")
            return False

        config = MODEL_CONFIGS[model_name]
        local_path = local_dir / config["filename"]

        # Check if local file exists
        if not local_path.exists():
            logger.error(f"❌ Local model file not found: {local_path}")
            logger.info(
                f"💡 Please download the model first or place it in: {local_dir}"
            )
            return False

        # Check file size
        file_size_mb = local_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"Uploading {model_name} model: {file_size_mb:.2f}MB → {config['minio_path']}"
        )

        # Get MinIO client
        minio_client = get_minio_client()

        # Upload file
        with open(local_path, "rb") as f:
            minio_client.upload_file(
                file_data=f, object_name=config["minio_path"], content_type="application/octet-stream"
            )

        logger.info(f"Model uploaded successfully: {model_name}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to upload model {model_name}: {e}")
        logger.exception("Upload error details:")
        return False


def main():
    """Main entry point."""
    try:
        settings = get_settings()

        logger.info("=" * 70)
        logger.info("Upload Whisper Models to MinIO")
        logger.info("=" * 70)
        logger.info(f"MinIO Endpoint: {settings.minio_endpoint}")
        logger.info(f"Bucket: {settings.minio_bucket_name}")
        logger.info(f"Local models dir: {settings.whisper_models_dir}")
        logger.info("=" * 70)

        # Parse arguments
        models_to_upload = sys.argv[1:] if len(sys.argv) > 1 else None

        local_dir = Path(settings.whisper_models_dir)
        if not local_dir.exists():
            logger.error(f"❌ Local models directory not found: {local_dir}")
            logger.info(
                "💡 Please create the directory and place model files there first."
            )
            sys.exit(1)

        # Determine which models to upload
        if models_to_upload:
            models = models_to_upload
            logger.info(f"Uploading specific models: {models}")
        else:
            # Upload all models found in local directory
            models = []
            for model_name, config in MODEL_CONFIGS.items():
                local_path = local_dir / config["filename"]
                if local_path.exists():
                    models.append(model_name)

            if not models:
                logger.error(f"❌ No model files found in: {local_dir}")
                logger.info(
                    f"💡 Place model files (ggml-*.bin) in {local_dir} first"
                )
                sys.exit(1)

            logger.info(f"Found {len(models)} models to upload: {models}")

        # Upload each model
        success_count = 0
        for model in models:
            if model not in MODEL_CONFIGS:
                logger.error(
                    f"❌ Invalid model: {model}. Valid models: {list(MODEL_CONFIGS.keys())}"
                )
                continue

            if upload_model(model, local_dir):
                success_count += 1

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info(f"Upload Summary: {success_count}/{len(models)} successful")
        logger.info("=" * 70)

        if success_count == len(models):
            logger.info("All models uploaded successfully!")
            logger.info(
                "\n💡 Next steps:"
                "\n   1. Start worker service: docker-compose up worker"
                "\n   2. Models will be auto-downloaded from MinIO on first run"
                "\n   3. Models are cached and reused across restarts"
            )
        else:
            logger.warning(f"⚠️ Some models failed to upload")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Upload interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Upload failed: {e}")
        logger.exception("Upload error details:")
        sys.exit(1)


if __name__ == "__main__":
    main()

