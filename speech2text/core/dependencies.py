"""
System dependencies validation for STT processing.
Checks required tools (ffmpeg, ffprobe, whisper) are installed and accessible.
"""

import os
import shutil
from pathlib import Path
from typing import Tuple, Optional

from core.logger import logger
from core.config import get_settings
from core.errors import MissingDependencyError


def check_ffmpeg() -> Tuple[bool, Optional[str]]:
    """
    Check if ffmpeg or ffprobe is installed and accessible.

    Returns:
        Tuple of (is_available, path)
        - is_available: True if ffmpeg/ffprobe found
        - path: Path to executable, or None if not found
    """
    # Check ffprobe first (usually comes with ffmpeg)
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        logger.debug(f"ffprobe found at: {ffprobe_path}")
        return True, ffprobe_path

    # Check ffmpeg as fallback
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        logger.debug(f"ffmpeg found at: {ffmpeg_path}")
        return True, ffmpeg_path

    # Not found
    logger.warning("ffmpeg/ffprobe not found in PATH")
    return False, None


def validate_dependencies(should_check_ffmpeg: bool = True) -> None:
    """
    Validate all required system dependencies for STT processing.

    Args:
        should_check_ffmpeg: If True, check for ffmpeg/ffprobe (required for Consumer service).
                    If False, skip ffmpeg check (for API service which doesn't need it).

    Raises:
        MissingDependencyError: If required dependencies are missing
    """
    logger.info("Validating system dependencies...")

    # Check ffmpeg/ffprobe (only if requested)
    if should_check_ffmpeg:
        ffmpeg_available, ffmpeg_path = check_ffmpeg()

        if not ffmpeg_available:
            error_msg = (
                "ffmpeg/ffprobe not installed. "
                "Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
            )
            logger.error(f"{error_msg}")
            raise MissingDependencyError(error_msg)

        logger.info(f"All dependencies validated: ffmpeg/ffprobe={ffmpeg_path}")
    else:
        logger.debug("Skipping ffmpeg check (not required for this service)")

    # Check Whisper executable (optional - warn only, don't fail)
    # Whisper is required for transcription, but validation happens at runtime
    settings = get_settings()
    whisper_path = Path(settings.whisper_executable)

    # Convert to absolute path for better checking
    if not whisper_path.is_absolute():
        whisper_path = whisper_path.resolve()

    if whisper_path.exists() and whisper_path.is_file():
        if os.access(whisper_path, os.X_OK):
            logger.info(f"Whisper executable found: {whisper_path}")
        else:
            logger.warning(
                f"Whisper executable exists but not executable: {whisper_path}"
            )
    else:
        # Try alternative common paths
        alternative_paths = [
            Path("./whisper/bin/whisper-cli"),
            Path("./whisper/whisper.cpp/main"),
            Path("whisper/bin/whisper-cli"),
            Path("whisper/whisper.cpp/main"),
        ]

        found_alternative = None
        for alt_path in alternative_paths:
            alt_resolved = (
                alt_path.resolve() if not alt_path.is_absolute() else alt_path
            )
            if (
                alt_resolved.exists()
                and alt_resolved.is_file()
                and os.access(alt_resolved, os.X_OK)
            ):
                found_alternative = alt_resolved
                break

        if found_alternative:
            logger.warning(
                f"Whisper executable not found at configured path: {settings.whisper_executable}, "
                f"but found at: {found_alternative}. "
                f"Update .env: WHISPER_EXECUTABLE={found_alternative}"
            )
        else:
            logger.warning(
                f"Whisper executable not found: {settings.whisper_executable}. "
                "Transcription will fail at runtime. "
                "Build whisper.cpp or set WHISPER_EXECUTABLE environment variable to correct path."
            )

    logger.info("System dependencies check passed")
