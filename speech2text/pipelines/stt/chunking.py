"""
Audio chunking module for splitting audio files.
Includes detailed logging and comprehensive error handling.
"""

import os
import re
import subprocess
import warnings
from typing import List, Optional, Tuple
from pathlib import Path

# Suppress pydub ffmpeg warning - it's expected if ffmpeg is not installed
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message=".*ffmpeg.*", category=RuntimeWarning)
    warnings.filterwarnings("ignore", message=".*avconv.*", category=RuntimeWarning)
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent

from core.config import get_settings
from core.logger import logger, format_exception_short
from core.errors import (
    InvalidAudioFormatError,
    CorruptedFileError,
    MissingDependencyError,
)
from core.constants import (
    SUPPORTED_FORMATS,
)

settings = get_settings()


class AudioChunker:
    """Audio chunking with silence detection and fallback strategies."""

    def __init__(self):
        """Initialize audio chunker."""
        logger.debug("AudioChunker initialized")

    def chunk_audio(
        self,
        audio_path: str,
        output_dir: str,
        strategy: str = "silence_based",
        chunk_duration: int = 30,
        min_silence_len: int = 1000,
        silence_thresh: int = -40,
    ) -> List[dict]:
        """
        Chunk audio file using specified strategy.

        Args:
            audio_path: Path to input audio file
            output_dir: Directory to save chunks
            strategy: Chunking strategy ('silence_based' or 'fixed_duration')
            chunk_duration: Duration of each chunk in seconds (for fixed strategy)
            min_silence_len: Minimum silence length in ms (for silence strategy)
            silence_thresh: Silence threshold in dBFS

        Returns:
            List of chunk metadata dictionaries

        Raises:
            InvalidAudioFormatError: If audio format is not supported
            CorruptedFileError: If audio file is corrupted
            Exception: For other errors
        """
        try:
            logger.info(
                f"Starting audio chunking: file={audio_path}, strategy={strategy}"
            )
            logger.debug(
                f"Parameters: chunk_duration={chunk_duration}s, min_silence={min_silence_len}ms, thresh={silence_thresh}dB"
            )

            # Validate audio file
            self._validate_audio_file(audio_path)

            # Load audio
            audio = self._load_audio(audio_path)

            # Get audio info
            duration_seconds = len(audio) / 1000.0
            logger.info(
                f"Audio loaded: duration={duration_seconds:.2f}s, format={audio.frame_rate}Hz"
            )

            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Output directory: {output_dir}")

            # Choose chunking strategy
            if strategy == "silence_based":
                chunks = self._chunk_by_silence(
                    audio, output_dir, min_silence_len, silence_thresh
                )
            else:
                chunks = self._chunk_fixed_duration(audio, output_dir, chunk_duration)

            logger.info(f"Audio chunking complete: total_chunks={len(chunks)}")
            logger.debug(f"Chunk details: {chunks}")

            # Log statistics
            total_duration = sum(c["end_time"] - c["start_time"] for c in chunks)
            avg_duration = total_duration / len(chunks) if chunks else 0
            logger.info(
                f"Chunk statistics: avg_duration={avg_duration:.2f}s, total_duration={total_duration:.2f}s"
            )

            return chunks

        except MissingDependencyError as e:
            # Missing dependencies are permanent - don't retry
            logger.error(f"Missing dependency: {e}")
            raise

        except InvalidAudioFormatError as e:
            logger.error(f"Invalid audio format: {e}")
            raise

        except CorruptedFileError as e:
            logger.error(f"Corrupted audio file: {e}")
            raise

        except Exception as e:
            error_formatted = format_exception_short(e, "Audio chunking failed")
            logger.error(f"{error_formatted}")
            raise

    def _validate_audio_file(self, audio_path: str) -> None:
        """
        Validate audio file exists and has supported format.

        Args:
            audio_path: Path to audio file

        Raises:
            FileNotFoundError: If file doesn't exist
            InvalidAudioFormatError: If format not supported
        """
        try:
            logger.debug(f"Validating audio file: {audio_path}")

            # Check file exists
            if not os.path.exists(audio_path):
                error_msg = f"Audio file not found: {audio_path}"
                logger.error(f"{error_msg}")
                raise FileNotFoundError(error_msg)

            # Check file extension
            file_ext = Path(audio_path).suffix.lower()
            if file_ext not in SUPPORTED_FORMATS:
                error_msg = f"Unsupported audio format: {file_ext}. Supported: {SUPPORTED_FORMATS}"
                logger.error(f"{error_msg}")
                raise InvalidAudioFormatError(error_msg)

            logger.debug(f"Audio file validation passed: format={file_ext}")

        except Exception as e:
            logger.error(f"Audio validation failed: {e}")
            raise

    def _load_audio(self, audio_path: str) -> AudioSegment:
        """
        Load audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            AudioSegment object

        Raises:
            CorruptedFileError: If file is corrupted
        """
        try:
            logger.debug(f"Loading audio file: {audio_path}")

            # Get file format
            file_ext = Path(audio_path).suffix.lower().replace(".", "")

            # Load audio
            audio = AudioSegment.from_file(audio_path, format=file_ext)

            logger.debug(
                f"Audio loaded: channels={audio.channels}, frame_rate={audio.frame_rate}Hz, sample_width={audio.sample_width}"
            )

            return audio

        except FileNotFoundError as e:
            # Check if it's ffmpeg/ffprobe missing
            error_str = str(e)
            if (
                "ffprobe" in error_str
                or "ffmpeg" in error_str
                or "avprobe" in error_str
            ):
                error_msg = "ffmpeg/ffprobe not installed. Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
                logger.error(f"{error_msg}")
                raise MissingDependencyError(error_msg)
            else:
                error_msg = f"Audio file not found: {e}"
                logger.error(f"{error_msg}")
                raise

        except Exception as e:
            # Check if underlying error is ffmpeg missing
            error_str = str(e)
            if (
                "ffprobe" in error_str
                or "ffmpeg" in error_str
                or "avprobe" in error_str
                or "No such file or directory: 'ffprobe'" in error_str
            ):
                error_msg = "ffmpeg/ffprobe not installed. Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
                logger.error(f"{error_msg}")
                raise MissingDependencyError(error_msg)

            error_msg = f"Failed to load audio (possibly corrupted): {e}"
            error_formatted = format_exception_short(e, "Audio load failed")
            logger.error(f"{error_formatted}")
            raise CorruptedFileError(error_msg)

    def _chunk_by_silence(
        self,
        audio: AudioSegment,
        output_dir: str,
        min_silence_len: int = 1000,
        silence_thresh: int = -40,
    ) -> List[dict]:
        """
        Chunk audio by detecting silence.

        Args:
            audio: AudioSegment to chunk
            output_dir: Output directory
            min_silence_len: Minimum silence length in ms
            silence_thresh: Silence threshold in dBFS

        Returns:
            List of chunk metadata
        """
        try:
            logger.info(
                f"Chunking by silence: min_silence={min_silence_len}ms, thresh={silence_thresh}dB"
            )

            # OPTIMIZATION: Use ffmpeg silencedetect for large files (much faster than pydub)
            # For files > 60 seconds, use ffmpeg directly; otherwise use pydub (simpler)
            audio_duration_ms = len(audio)

            if audio_duration_ms > 60000:  # 60 seconds
                logger.debug("Using ffmpeg silencedetect (optimized for large files)")
                nonsilent_ranges = self._detect_silence_ffmpeg_fast(
                    audio, min_silence_len, silence_thresh
                )
            else:
                logger.debug("Using pydub detect_nonsilent (good for small files)")
                # Detect non-silent regions using pydub (for smaller files)
                nonsilent_ranges = detect_nonsilent(
                    audio,
                    min_silence_len=min_silence_len,
                    silence_thresh=silence_thresh,
                )

            logger.debug(f"Found {len(nonsilent_ranges)} non-silent regions")

            if not nonsilent_ranges:
                logger.warning(
                    "No non-silent regions found, using fixed duration fallback"
                )
                return self._chunk_fixed_duration(
                    audio, output_dir, settings.chunk_duration
                )

            # Get audio duration for filtering intro/outro
            audio_duration_sec = len(audio) / 1000.0
            intro_threshold = 5.0  # First 5 seconds
            outro_threshold = 5.0  # Last 5 seconds

            # Filter intro/outro if enabled
            filtered_ranges = []
            if settings.filter_intro_outro:
                logger.debug(
                    f"Filtering intro/outro: intro_threshold={intro_threshold}s, outro_threshold={outro_threshold}s"
                )
                for start_ms, end_ms in nonsilent_ranges:
                    start_sec = start_ms / 1000.0
                    end_sec = end_ms / 1000.0

                    # Skip if entirely within intro/outro zones
                    if (start_sec < intro_threshold and end_sec < intro_threshold) or (
                        start_sec > audio_duration_sec - outro_threshold
                        and end_sec > audio_duration_sec - outro_threshold
                    ):
                        logger.debug(
                            f"Skipping chunk in intro/outro zone: {start_sec:.2f}s - {end_sec:.2f}s"
                        )
                        continue

                    # Clip start/end if partially in intro/outro
                    if start_sec < intro_threshold:
                        start_ms = int(intro_threshold * 1000)
                        logger.debug(
                            f"Clip chunk start from intro: {start_sec:.2f}s -> {intro_threshold:.2f}s"
                        )
                    if end_sec > audio_duration_sec - outro_threshold:
                        end_ms = int((audio_duration_sec - outro_threshold) * 1000)
                        logger.debug(
                            f"Clip chunk end from outro: {end_sec:.2f}s -> {audio_duration_sec - outro_threshold:.2f}s"
                        )

                    if end_ms > start_ms:  # Only add if still valid after clipping
                        filtered_ranges.append((start_ms, end_ms))
                logger.info(
                    f"After intro/outro filter: {len(filtered_ranges)}/{len(nonsilent_ranges)} chunks remain"
                )
            else:
                filtered_ranges = nonsilent_ranges

            chunks = []
            for i, (start_ms, end_ms) in enumerate(filtered_ranges):
                try:
                    # Convert to seconds
                    start_sec = start_ms / 1000.0
                    end_sec = end_ms / 1000.0
                    duration_sec = end_sec - start_sec

                    logger.debug(
                        f"Processing chunk {i}: start={start_sec:.2f}s, end={end_sec:.2f}s, duration={duration_sec:.2f}s"
                    )

                    # Validate chunk duration using config settings
                    min_duration = settings.min_chunk_duration
                    max_duration = settings.max_chunk_duration

                    # Skip very short chunks
                    if duration_sec < min_duration:
                        logger.debug(
                            f"Skipping short chunk {i}: {duration_sec:.2f}s < {min_duration}s"
                        )
                        continue

                    # Split long chunks
                    if duration_sec > max_duration:
                        logger.debug(
                            f"Splitting long chunk {i}: {duration_sec:.2f}s > {max_duration}s"
                        )
                        sub_chunks = self._split_chunk(
                            audio[start_ms:end_ms],
                            output_dir,
                            start_sec,
                            i * 100,  # Offset for sub-chunk indices
                        )
                        chunks.extend(sub_chunks)
                        continue

                    # Extract and save chunk
                    chunk_audio = audio[start_ms:end_ms]
                    chunk_path = os.path.join(output_dir, f"chunk_{i:04d}.wav")
                    chunk_audio.export(chunk_path, format="wav")

                    chunk_info = {
                        "chunk_index": i,
                        "start_time": start_sec,
                        "end_time": end_sec,
                        "file_path": chunk_path,
                    }
                    chunks.append(chunk_info)

                    logger.debug(f"Chunk {i} saved: {chunk_path}")

                except Exception as e:
                    logger.error(f"Failed to process chunk {i}: {e}")
                    logger.exception("Chunk processing error:")
                    # Continue with other chunks
                    continue

            logger.info(
                f"Silence-based chunking complete: {len(chunks)} chunks created"
            )

            return chunks

        except Exception as e:
            logger.error(f"Silence-based chunking failed: {e}")
            logger.exception("Silence chunking error details:")
            # Fallback to fixed duration
            logger.warning("Falling back to fixed duration chunking")
            return self._chunk_fixed_duration(
                audio, output_dir, settings.chunk_duration
            )

    def _detect_silence_ffmpeg_fast(
        self,
        audio: AudioSegment,
        min_silence_len: int,
        silence_thresh: int,
    ) -> List[Tuple[int, int]]:
        """
        Fast silence detection using ffmpeg silencedetect filter.
        Much faster than pydub for large files (doesn't load entire audio into memory).

        Args:
            audio: AudioSegment (used to get source file path)
            min_silence_len: Minimum silence length in ms
            silence_thresh: Silence threshold in dBFS

        Returns:
            List of (start_ms, end_ms) tuples for non-silent regions
        """
        try:
            # Convert dBFS to dB (ffmpeg uses different scale)
            # pydub uses dBFS, ffmpeg silencedetect uses dB relative to peak
            # For -40 dBFS, we use approximately -50 dB in ffmpeg
            ffmpeg_thresh = silence_thresh - 10  # Adjust threshold

            min_silence_sec = min_silence_len / 1000.0

            # Save audio to temp file for ffmpeg (if audio is in-memory)
            # If audio was loaded from file, we need the original file path
            # For now, save to temp and use that
            import tempfile

            temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_audio_path = temp_audio.name
            temp_audio.close()

            try:
                # Export audio to temp file
                audio.export(temp_audio_path, format="wav")

                # Run ffmpeg silencedetect
                # Format: silencedetect=n=-50dB:d=1.0
                # Output format: silence_start: X.XXX | silence_end: Y.YYY | silence_duration: Z.ZZZ
                cmd = [
                    "ffmpeg",
                    "-i",
                    temp_audio_path,
                    "-af",
                    f"silencedetect=n={ffmpeg_thresh}dB:d={min_silence_sec}",
                    "-f",
                    "null",
                    "-",
                ]

                logger.debug(f"Running ffmpeg silencedetect: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,  # Timeout after 30s
                    check=False,
                )

                if result.returncode != 0:
                    logger.warning(f"ffmpeg silencedetect failed: {result.stderr}")
                    # Fallback to pydub
                    logger.debug("Falling back to pydub detect_nonsilent")
                    from pydub.silence import detect_nonsilent

                    return detect_nonsilent(
                        audio,
                        min_silence_len=min_silence_len,
                        silence_thresh=silence_thresh,
                    )

                # Parse ffmpeg output to find silence periods
                # Example output:
                # [silencedetect @ 0x...] silence_start: 5.234
                # [silencedetect @ 0x...] silence_end: 8.456 | silence_duration: 3.222
                silence_periods = []
                silence_start = None

                for line in result.stderr.split("\n"):
                    if "silence_start:" in line:
                        try:
                            silence_start = float(
                                line.split("silence_start:")[1].strip()
                            )
                        except (ValueError, IndexError):
                            continue
                    elif "silence_end:" in line and silence_start is not None:
                        try:
                            silence_end_str = (
                                line.split("silence_end:")[1].split("|")[0].strip()
                            )
                            silence_end = float(silence_end_str)
                            silence_periods.append((silence_start, silence_end))
                            silence_start = None
                        except (ValueError, IndexError):
                            continue

                # Convert silence periods to non-silent regions
                audio_duration_sec = len(audio) / 1000.0
                nonsilent_ranges = []
                last_end = 0.0

                for silence_start, silence_end in silence_periods:
                    if silence_start > last_end:
                        # There's a non-silent region before this silence
                        nonsilent_ranges.append(
                            (int(last_end * 1000), int(silence_start * 1000))
                        )
                    last_end = silence_end

                # Add final non-silent region if exists
                if last_end < audio_duration_sec:
                    nonsilent_ranges.append(
                        (int(last_end * 1000), int(audio_duration_sec * 1000))
                    )

                # If no silence detected, entire audio is non-silent
                if not silence_periods:
                    nonsilent_ranges = [(0, len(audio))]

                logger.debug(
                    f"ffmpeg detected {len(nonsilent_ranges)} non-silent regions"
                )
                return nonsilent_ranges

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_audio_path)
                except Exception:
                    pass

        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg silencedetect timed out, falling back to pydub")
            from pydub.silence import detect_nonsilent

            return detect_nonsilent(
                audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh
            )
        except Exception as e:
            logger.warning(f"ffmpeg silencedetect failed: {e}, falling back to pydub")
            from pydub.silence import detect_nonsilent

            return detect_nonsilent(
                audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh
            )

    def _chunk_fixed_duration(
        self, audio: AudioSegment, output_dir: str, chunk_duration: int = 30
    ) -> List[dict]:
        """
        Chunk audio into fixed duration segments.

        Args:
            audio: AudioSegment to chunk
            output_dir: Output directory
            chunk_duration: Duration in seconds

        Returns:
            List of chunk metadata
        """
        try:
            logger.info(f"Chunking by fixed duration: duration={chunk_duration}s")

            chunk_duration_ms = chunk_duration * 1000
            audio_length_ms = len(audio)
            chunks = []

            for i, start_ms in enumerate(range(0, audio_length_ms, chunk_duration_ms)):
                try:
                    end_ms = min(start_ms + chunk_duration_ms, audio_length_ms)

                    start_sec = start_ms / 1000.0
                    end_sec = end_ms / 1000.0

                    logger.debug(
                        f"Processing chunk {i}: {start_sec:.2f}s - {end_sec:.2f}s"
                    )

                    # Extract and save chunk
                    chunk_audio = audio[start_ms:end_ms]
                    chunk_path = os.path.join(output_dir, f"chunk_{i:04d}.wav")
                    chunk_audio.export(chunk_path, format="wav")

                    chunk_info = {
                        "chunk_index": i,
                        "start_time": start_sec,
                        "end_time": end_sec,
                        "file_path": chunk_path,
                    }
                    chunks.append(chunk_info)

                    logger.debug(f"Chunk {i} saved: {chunk_path}")

                except Exception as e:
                    logger.error(f"Failed to process chunk {i}: {e}")
                    logger.exception("Chunk processing error:")
                    continue

            logger.info(
                f"Fixed duration chunking complete: {len(chunks)} chunks created"
            )

            return chunks

        except Exception as e:
            logger.error(f"Fixed duration chunking failed: {e}")
            logger.exception("Fixed chunking error details:")
            raise

    def _split_chunk(
        self,
        chunk_audio: AudioSegment,
        output_dir: str,
        start_offset: float,
        index_offset: int,
    ) -> List[dict]:
        """
        Split a long chunk into smaller sub-chunks.

        Args:
            chunk_audio: AudioSegment to split
            output_dir: Output directory
            start_offset: Time offset for the chunk
            index_offset: Index offset for sub-chunks

        Returns:
            List of sub-chunk metadata
        """
        try:
            logger.debug(
                f"Splitting long chunk: duration={len(chunk_audio)/1000.0:.2f}s"
            )

            sub_chunks = []
            chunk_duration_ms = int(settings.max_chunk_duration * 1000)
            chunk_length_ms = len(chunk_audio)

            for i, start_ms in enumerate(range(0, chunk_length_ms, chunk_duration_ms)):
                end_ms = min(start_ms + chunk_duration_ms, chunk_length_ms)

                start_sec = start_offset + (start_ms / 1000.0)
                end_sec = start_offset + (end_ms / 1000.0)

                # Extract and save sub-chunk
                sub_chunk_audio = chunk_audio[start_ms:end_ms]
                chunk_index = index_offset + i
                chunk_path = os.path.join(output_dir, f"chunk_{chunk_index:04d}.wav")
                sub_chunk_audio.export(chunk_path, format="wav")

                chunk_info = {
                    "chunk_index": chunk_index,
                    "start_time": start_sec,
                    "end_time": end_sec,
                    "file_path": chunk_path,
                }
                sub_chunks.append(chunk_info)

                logger.debug(
                    f"Sub-chunk {i} created: {start_sec:.2f}s - {end_sec:.2f}s"
                )

            return sub_chunks

        except Exception as e:
            logger.error(f"Failed to split chunk: {e}")
            logger.exception("Chunk split error details:")
            raise


def get_audio_duration(audio_path: str) -> float:
    """
    Get audio file duration in seconds.

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds

    Raises:
        Exception: If duration cannot be determined
    """
    try:
        logger.debug(f"Getting audio duration: {audio_path}")

        file_ext = Path(audio_path).suffix.lower().replace(".", "")
        audio = AudioSegment.from_file(audio_path, format=file_ext)
        duration = len(audio) / 1000.0

        logger.debug(f"Audio duration: {duration:.2f}s")

        return duration

    except FileNotFoundError as e:
        error_str = str(e)
        if "ffprobe" in error_str or "ffmpeg" in error_str or "avprobe" in error_str:
            error_msg = "ffmpeg/ffprobe not installed. Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
            logger.error(f"{error_msg}")
            raise MissingDependencyError(error_msg)
        else:
            error_formatted = format_exception_short(e, "Duration retrieval failed")
            logger.error(f"{error_formatted}")
            raise

    except Exception as e:
        error_str = str(e)
        if (
            "ffprobe" in error_str
            or "ffmpeg" in error_str
            or "avprobe" in error_str
            or "No such file or directory: 'ffprobe'" in error_str
        ):
            error_msg = "ffmpeg/ffprobe not installed. Install with: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
            logger.error(f"{error_msg}")
            raise MissingDependencyError(error_msg)

        error_formatted = format_exception_short(e, "Duration retrieval failed")
        logger.error(f"{error_formatted}")
        raise
