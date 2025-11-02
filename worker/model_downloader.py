"""
Whisper Model Downloader - Downloads models from MinIO if not present locally.
Includes checksum validation and comprehensive error handling.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Dict
import json

from core.config import get_settings
from core.logger import logger
from core.storage import get_minio_client

settings = get_settings()


# Model configurations with checksums (MD5)
MODEL_CONFIGS = {
    "tiny": {
        "filename": "ggml-tiny.bin",
        "minio_path": "whisper-models/ggml-tiny.bin",
        "size_mb": 75,
        "md5": None,  # Optional: Add MD5 checksum for validation
    },
    "base": {
        "filename": "ggml-base.bin",
        "minio_path": "whisper-models/ggml-base.bin",
        "size_mb": 142,
        "md5": None,
    },
    "small": {
        "filename": "ggml-small.bin",
        "minio_path": "whisper-models/ggml-small.bin",
        "size_mb": 466,
        "md5": None,
    },
    "medium": {
        "filename": "ggml-medium.bin",
        "minio_path": "whisper-models/ggml-medium.bin",
        "size_mb": 1500,
        "md5": None,
    },
    "large": {
        "filename": "ggml-large.bin",
        "minio_path": "whisper-models/ggml-large.bin",
        "size_mb": 2900,
        "md5": None,
    },
}


class ModelDownloader:
    """Downloads Whisper models from MinIO with validation."""

    def __init__(self):
        """Initialize model downloader."""
        self.models_dir = Path(settings.whisper_models_dir)
        self.cache_file = self.models_dir / ".model_cache.json"
        self._validated_models = set()  # In-memory cache for validated models (avoid redundant checks)
        logger.debug("ModelDownloader initialized")

    def ensure_model_exists(self, model: str) -> str:
        """
        Ensure model exists locally. Download from MinIO if missing.

        Args:
            model: Model name (tiny, base, small, medium, large)

        Returns:
            Path to model file

        Raises:
            ValueError: If model name is invalid
            Exception: If download fails
        """
        try:
            # Check in-memory cache first (fast path for parallel processing)
            if model in self._validated_models:
                config = MODEL_CONFIGS[model]
                model_path = self.models_dir / config["filename"]
                logger.debug(f"Model already validated in cache: {model}")
                return str(model_path)

            logger.info(f"Ensuring model exists: {model}")

            # Validate model name
            if model not in MODEL_CONFIGS:
                error_msg = f"Invalid model name: {model}. Valid models: {list(MODEL_CONFIGS.keys())}"
                logger.error(f"{error_msg}")
                raise ValueError(error_msg)

            config = MODEL_CONFIGS[model]
            model_path = self.models_dir / config["filename"]

            # Check if model exists and is valid
            if self._is_model_valid(model, model_path):
                logger.info(f"Model already exists and is valid: {model_path}")
                # Add to cache for future calls
                self._validated_models.add(model)
                return str(model_path)

            # Download model from MinIO
            logger.info(f"📥 Model not found or invalid, downloading from MinIO...")
            self._download_model(model, model_path, config)

            # Add to cache after successful download
            self._validated_models.add(model)

            logger.info(f"Model ready: {model_path}")
            return str(model_path)

        except Exception as e:
            logger.error(f"Failed to ensure model exists: {e}")
            logger.exception("Model download error details:")
            raise

    def _is_model_valid(self, model: str, model_path: Path) -> bool:
        """
        Check if model file exists and is valid.

        Args:
            model: Model name
            model_path: Path to model file

        Returns:
            True if model is valid
        """
        try:
            # Check if file exists
            if not model_path.exists():
                logger.debug(f"🔍 Model file not found: {model_path}")
                return False

            # Check file size (basic validation)
            file_size_mb = model_path.stat().st_size / (1024 * 1024)
            expected_size = MODEL_CONFIGS[model]["size_mb"]

            if file_size_mb < expected_size * 0.9:  # Allow 10% tolerance
                logger.warning(
                    f"Model file size mismatch: {file_size_mb:.2f}MB < {expected_size}MB"
                )
                return False

            # Check MD5 if provided
            expected_md5 = MODEL_CONFIGS[model].get("md5")
            if expected_md5:
                actual_md5 = self._calculate_md5(model_path)
                if actual_md5 != expected_md5:
                    logger.warning(
                        f"Model MD5 mismatch: {actual_md5} != {expected_md5}"
                    )
                    return False

            logger.debug(f"Model validation passed: {model}")
            return True

        except Exception as e:
            logger.error(f"Model validation error: {e}")
            return False

    def _download_model(self, model: str, model_path: Path, config: Dict) -> None:
        """
        Download model from MinIO.

        Args:
            model: Model name
            model_path: Local path to save model
            config: Model configuration

        Raises:
            Exception: If download fails
        """
        try:
            logger.info(
                f"Downloading model '{model}' from MinIO: {config['minio_path']}"
            )
            logger.info(f"Expected size: {config['size_mb']}MB")

            # Create models directory if not exists
            self.models_dir.mkdir(parents=True, exist_ok=True)

            # Get MinIO client
            minio_client = get_minio_client()

            # Check if model exists in MinIO
            if not minio_client.file_exists(config["minio_path"]):
                error_msg = f"Model not found in MinIO: {config['minio_path']}"
                logger.error(f"{error_msg}")
                raise FileNotFoundError(error_msg)

            # Download model
            logger.info(f"📥 Downloading to: {model_path}")
            minio_client.download_file(config["minio_path"], str(model_path))

            # Validate downloaded file
            file_size_mb = model_path.stat().st_size / (1024 * 1024)
            logger.info(f"Download complete: {file_size_mb:.2f}MB")

            # Verify size
            if file_size_mb < config["size_mb"] * 0.9:
                error_msg = f"Downloaded file size too small: {file_size_mb:.2f}MB < {config['size_mb']}MB"
                logger.error(f"{error_msg}")
                model_path.unlink()  # Delete corrupted file
                raise ValueError(error_msg)

            # Update cache
            self._update_cache(model, model_path)

            logger.info(f"Model downloaded and validated: {model}")

        except Exception as e:
            logger.error(f"Model download failed: {e}")
            logger.exception("Download error details:")
            # Cleanup partial download
            if model_path.exists():
                try:
                    model_path.unlink()
                    logger.debug("Cleaned up partial download")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup: {cleanup_error}")
            raise

    def _calculate_md5(self, file_path: Path) -> str:
        """
        Calculate MD5 checksum of file.

        Args:
            file_path: Path to file

        Returns:
            MD5 checksum as hex string
        """
        try:
            logger.debug(f"🔍 Calculating MD5 for: {file_path}")
            md5_hash = hashlib.md5()

            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    md5_hash.update(chunk)

            checksum = md5_hash.hexdigest()
            logger.debug(f"MD5: {checksum}")
            return checksum

        except Exception as e:
            logger.error(f"MD5 calculation failed: {e}")
            raise

    def _update_cache(self, model: str, model_path: Path) -> None:
        """
        Update model cache file.

        Args:
            model: Model name
            model_path: Path to model file
        """
        try:
            cache = {}
            if self.cache_file.exists():
                with open(self.cache_file, "r") as f:
                    cache = json.load(f)

            cache[model] = {
                "path": str(model_path),
                "size": model_path.stat().st_size,
                "timestamp": model_path.stat().st_mtime,
            }

            with open(self.cache_file, "w") as f:
                json.dump(cache, f, indent=2)

            logger.debug(f"Cache updated for model: {model}")

        except Exception as e:
            logger.warning(f"Failed to update cache: {e}")
            # Non-critical error, don't raise

    def download_all_models(self) -> None:
        """
        Download all available models from MinIO.
        Useful for initial setup or pre-warming.
        """
        try:
            logger.info("Downloading all Whisper models...")

            for model in MODEL_CONFIGS.keys():
                try:
                    self.ensure_model_exists(model)
                    logger.info(f"Model '{model}' ready")
                except Exception as e:
                    logger.error(f"Failed to download model '{model}': {e}")
                    # Continue with other models

            logger.info("All models download complete")

        except Exception as e:
            logger.error(f"Failed to download all models: {e}")
            raise

    def list_available_models(self) -> Dict[str, bool]:
        """
        List available models and their status.

        Returns:
            Dictionary mapping model name to availability status
        """
        try:
            status = {}
            for model, config in MODEL_CONFIGS.items():
                model_path = self.models_dir / config["filename"]
                status[model] = self._is_model_valid(model, model_path)

            return status

        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return {}


# Global singleton instance
_model_downloader: Optional[ModelDownloader] = None


def get_model_downloader() -> ModelDownloader:
    """
    Get or create global ModelDownloader instance (singleton).

    Returns:
        ModelDownloader instance
    """
    global _model_downloader

    try:
        if _model_downloader is None:
            logger.info("Creating ModelDownloader instance...")
            _model_downloader = ModelDownloader()

        return _model_downloader

    except Exception as e:
        logger.error(f"Failed to get model downloader: {e}")
        logger.exception("ModelDownloader initialization error:")
        raise
