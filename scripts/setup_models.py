#!/usr/bin/env python3
"""
Setup script to download Whisper models from MinIO.
Run this script once to download all models or specific models.

Usage:
    python scripts/setup_models.py              # Download all models
    python scripts/setup_models.py medium       # Download specific model
    python scripts/setup_models.py medium large # Download multiple models
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.model_downloader import get_model_downloader, MODEL_CONFIGS
from core.logger import logger


def main():
    """Main entry point."""
    try:
        logger.info("=" * 70)
        logger.info("Whisper Model Setup")
        logger.info("=" * 70)

        # Parse arguments
        models_to_download = sys.argv[1:] if len(sys.argv) > 1 else None

        # Get model downloader
        downloader = get_model_downloader()

        if models_to_download:
            # Download specific models
            logger.info(f"Downloading specific models: {models_to_download}")

            for model in models_to_download:
                if model not in MODEL_CONFIGS:
                    logger.error(
                        f"Invalid model: {model}. Valid models: {list(MODEL_CONFIGS.keys())}"
                    )
                    continue

                try:
                    logger.info(f"\n📥 Downloading model: {model}")
                    model_path = downloader.ensure_model_exists(model)
                    logger.info(f"Model ready: {model_path}")
                except Exception as e:
                    logger.error(f"Failed to download model '{model}': {e}")
        else:
            # Download all models
            logger.info("Downloading ALL models (this may take a while)...")
            downloader.download_all_models()

        # Show status
        logger.info("\n" + "=" * 70)
        logger.info("Model Status:")
        logger.info("=" * 70)

        status = downloader.list_available_models()
        for model, available in status.items():
            config = MODEL_CONFIGS[model]
            status_icon = "✅" if available else "❌"
            logger.info(
                f"{status_icon} {model:8s} - {config['size_mb']:6.0f}MB - {'Available' if available else 'Missing'}"
            )

        logger.info("\n" + "=" * 70)
        logger.info("Model setup complete!")
        logger.info("=" * 70)

    except KeyboardInterrupt:
        logger.warning("\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nSetup failed: {e}")
        logger.exception("Setup error details:")
        sys.exit(1)


if __name__ == "__main__":
    main()
