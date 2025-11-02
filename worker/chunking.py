"""
Audio chunking module for splitting audio files.
Includes detailed logging and comprehensive error handling.
"""

import os
from typing import List, Optional, Tuple
from pathlib import Path
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from core.config import get_settings
from core.logger import logger
from worker.errors import InvalidAudioFormatError, CorruptedFileError
from worker.constants import (
    SUPPORTED_FORMATS,
    MAX_CHUNK_SIZE_SECONDS,
    MIN_CHUNK_SIZE_SECONDS,
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
                f"📝 Starting audio chunking: file={audio_path}, strategy={strategy}"
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
                f"✅ Audio loaded: duration={duration_seconds:.2f}s, format={audio.frame_rate}Hz"
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

            logger.info(f"✅ Audio chunking complete: total_chunks={len(chunks)}")
            logger.debug(f"Chunk details: {chunks}")

            # Log statistics
            total_duration = sum(c["end_time"] - c["start_time"] for c in chunks)
            avg_duration = total_duration / len(chunks) if chunks else 0
            logger.info(
                f"📊 Chunk statistics: avg_duration={avg_duration:.2f}s, total_duration={total_duration:.2f}s"
            )

            return chunks

        except InvalidAudioFormatError as e:
            logger.error(f"❌ Invalid audio format: {e}")
            raise

        except CorruptedFileError as e:
            logger.error(f"❌ Corrupted audio file: {e}")
            raise

        except Exception as e:
            logger.error(f"❌ Audio chunking failed: {e}")
            logger.exception("Chunking error details:")
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
            logger.debug(f"🔍 Validating audio file: {audio_path}")

            # Check file exists
            if not os.path.exists(audio_path):
                error_msg = f"Audio file not found: {audio_path}"
                logger.error(f"❌ {error_msg}")
                raise FileNotFoundError(error_msg)

            # Check file extension
            file_ext = Path(audio_path).suffix.lower()
            if file_ext not in SUPPORTED_FORMATS:
                error_msg = f"Unsupported audio format: {file_ext}. Supported: {SUPPORTED_FORMATS}"
                logger.error(f"❌ {error_msg}")
                raise InvalidAudioFormatError(error_msg)

            logger.debug(f"✅ Audio file validation passed: format={file_ext}")

        except Exception as e:
            logger.error(f"❌ Audio validation failed: {e}")
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
            logger.debug(f"🔍 Loading audio file: {audio_path}")

            # Get file format
            file_ext = Path(audio_path).suffix.lower().replace(".", "")

            # Load audio
            audio = AudioSegment.from_file(audio_path, format=file_ext)

            logger.debug(
                f"✅ Audio loaded: channels={audio.channels}, frame_rate={audio.frame_rate}Hz, sample_width={audio.sample_width}"
            )

            return audio

        except Exception as e:
            error_msg = f"Failed to load audio (possibly corrupted): {e}"
            logger.error(f"❌ {error_msg}")
            logger.exception("Audio load error details:")
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
                f"📝 Chunking by silence: min_silence={min_silence_len}ms, thresh={silence_thresh}dB"
            )

            # Detect non-silent regions
            nonsilent_ranges = detect_nonsilent(
                audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh
            )

            logger.debug(f"Found {len(nonsilent_ranges)} non-silent regions")

            if not nonsilent_ranges:
                logger.warning(
                    "⚠️ No non-silent regions found, using fixed duration fallback"
                )
                return self._chunk_fixed_duration(
                    audio, output_dir, settings.chunk_duration
                )

            chunks = []
            for i, (start_ms, end_ms) in enumerate(nonsilent_ranges):
                try:
                    # Convert to seconds
                    start_sec = start_ms / 1000.0
                    end_sec = end_ms / 1000.0
                    duration_sec = end_sec - start_sec

                    logger.debug(
                        f"🔍 Processing chunk {i}: start={start_sec:.2f}s, end={end_sec:.2f}s, duration={duration_sec:.2f}s"
                    )

                    # Skip very short chunks
                    if duration_sec < MIN_CHUNK_SIZE_SECONDS:
                        logger.debug(
                            f"⚠️ Skipping short chunk {i}: {duration_sec:.2f}s < {MIN_CHUNK_SIZE_SECONDS}s"
                        )
                        continue

                    # Split long chunks
                    if duration_sec > MAX_CHUNK_SIZE_SECONDS:
                        logger.debug(
                            f"⚠️ Splitting long chunk {i}: {duration_sec:.2f}s > {MAX_CHUNK_SIZE_SECONDS}s"
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

                    logger.debug(f"✅ Chunk {i} saved: {chunk_path}")

                except Exception as e:
                    logger.error(f"❌ Failed to process chunk {i}: {e}")
                    logger.exception("Chunk processing error:")
                    # Continue with other chunks
                    continue

            logger.info(
                f"✅ Silence-based chunking complete: {len(chunks)} chunks created"
            )

            return chunks

        except Exception as e:
            logger.error(f"❌ Silence-based chunking failed: {e}")
            logger.exception("Silence chunking error details:")
            # Fallback to fixed duration
            logger.warning("⚠️ Falling back to fixed duration chunking")
            return self._chunk_fixed_duration(
                audio, output_dir, settings.chunk_duration
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
            logger.info(f"📝 Chunking by fixed duration: duration={chunk_duration}s")

            chunk_duration_ms = chunk_duration * 1000
            audio_length_ms = len(audio)
            chunks = []

            for i, start_ms in enumerate(range(0, audio_length_ms, chunk_duration_ms)):
                try:
                    end_ms = min(start_ms + chunk_duration_ms, audio_length_ms)

                    start_sec = start_ms / 1000.0
                    end_sec = end_ms / 1000.0

                    logger.debug(
                        f"🔍 Processing chunk {i}: {start_sec:.2f}s - {end_sec:.2f}s"
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

                    logger.debug(f"✅ Chunk {i} saved: {chunk_path}")

                except Exception as e:
                    logger.error(f"❌ Failed to process chunk {i}: {e}")
                    logger.exception("Chunk processing error:")
                    continue

            logger.info(
                f"✅ Fixed duration chunking complete: {len(chunks)} chunks created"
            )

            return chunks

        except Exception as e:
            logger.error(f"❌ Fixed duration chunking failed: {e}")
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
                f"🔍 Splitting long chunk: duration={len(chunk_audio)/1000.0:.2f}s"
            )

            sub_chunks = []
            chunk_duration_ms = MAX_CHUNK_SIZE_SECONDS * 1000
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
                    f"✅ Sub-chunk {i} created: {start_sec:.2f}s - {end_sec:.2f}s"
                )

            return sub_chunks

        except Exception as e:
            logger.error(f"❌ Failed to split chunk: {e}")
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
        logger.debug(f"🔍 Getting audio duration: {audio_path}")

        file_ext = Path(audio_path).suffix.lower().replace(".", "")
        audio = AudioSegment.from_file(audio_path, format=file_ext)
        duration = len(audio) / 1000.0

        logger.debug(f"✅ Audio duration: {duration:.2f}s")

        return duration

    except Exception as e:
        logger.error(f"❌ Failed to get audio duration: {e}")
        logger.exception("Duration retrieval error:")
        raise
