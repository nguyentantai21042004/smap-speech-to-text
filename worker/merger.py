"""
Result merger for combining chunk transcriptions.
Includes detailed logging and comprehensive error handling.
"""
from typing import List, Dict, Any
import re

from core.logger import logger


class ResultMerger:
    """Merge transcription results from multiple chunks."""

    def __init__(self):
        """Initialize result merger."""
        logger.debug("ResultMerger initialized")

    def merge_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Merge transcriptions from multiple chunks.

        Args:
            chunks: List of chunk dictionaries with transcription data

        Returns:
            Merged transcription text

        Raises:
            Exception: If merging fails
        """
        try:
            logger.info(f"Starting chunk merge: total_chunks={len(chunks)}")

            if not chunks:
                logger.warning("⚠️ No chunks to merge")
                return ""

            # Sort chunks by index
            sorted_chunks = sorted(chunks, key=lambda x: x.get('chunk_index', 0))
            logger.debug(f"Chunks sorted by index: {[c.get('chunk_index') for c in sorted_chunks]}")

            # Extract transcriptions
            transcriptions = []
            for i, chunk in enumerate(sorted_chunks):
                try:
                    transcription = chunk.get('transcription', '')

                    if not transcription:
                        logger.warning(f"⚠️ Empty transcription for chunk {i}")
                        continue

                    # Clean transcription
                    transcription = self._clean_transcription(transcription)

                    transcriptions.append(transcription)
                    logger.debug(f"Chunk {i} transcription: length={len(transcription)} chars")

                except Exception as e:
                    logger.error(f"❌ Failed to process chunk {i}: {e}")
                    logger.exception("Chunk processing error:")
                    # Continue with other chunks
                    continue

            if not transcriptions:
                logger.warning("⚠️ No valid transcriptions found")
                return ""

            # Merge with overlap removal
            merged_text = self._merge_with_overlap_removal(transcriptions)

            # Final cleanup
            merged_text = self._final_cleanup(merged_text)

            logger.info(f"Merge complete: final_length={len(merged_text)} chars")
            logger.debug(f"Merged text preview: {merged_text[:200]}...")

            # Log statistics
            total_chars = sum(len(t) for t in transcriptions)
            reduction = ((total_chars - len(merged_text)) / total_chars * 100) if total_chars > 0 else 0
            logger.info(f"📊 Merge statistics: original={total_chars} chars, merged={len(merged_text)} chars, reduction={reduction:.1f}%")

            return merged_text

        except Exception as e:
            logger.error(f"❌ Chunk merge failed: {e}")
            logger.exception("Merge error details:")
            raise

    def _clean_transcription(self, text: str) -> str:
        """
        Clean individual transcription text.

        Args:
            text: Transcription text

        Returns:
            Cleaned text
        """
        try:
            # Remove leading/trailing whitespace
            text = text.strip()

            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text)

            # Remove multiple punctuation
            text = re.sub(r'([.!?])\1+', r'\1', text)

            return text

        except Exception as e:
            logger.error(f"❌ Text cleaning failed: {e}")
            return text  # Return original if cleaning fails

    def _merge_with_overlap_removal(self, transcriptions: List[str]) -> str:
        """
        Merge transcriptions with overlap detection and removal.

        Args:
            transcriptions: List of transcription strings

        Returns:
            Merged text
        """
        try:
            logger.debug("🔍 Merging with overlap removal...")

            if len(transcriptions) == 1:
                return transcriptions[0]

            merged = transcriptions[0]

            for i in range(1, len(transcriptions)):
                current = transcriptions[i]

                # Find overlap between end of merged and start of current
                overlap_len = self._find_overlap(merged, current)

                if overlap_len > 0:
                    logger.debug(f"🔍 Found overlap of {overlap_len} chars between chunks {i-1} and {i}")
                    # Remove overlap from current transcription
                    current = current[overlap_len:]

                # Add space if needed
                if merged and current and not merged.endswith(' ') and not current.startswith(' '):
                    merged += ' '

                merged += current

            logger.debug(f"Overlap removal complete")

            return merged

        except Exception as e:
            logger.error(f"❌ Overlap removal failed: {e}")
            logger.exception("Overlap removal error:")
            # Fallback: simple concatenation
            return ' '.join(transcriptions)

    def _find_overlap(self, text1: str, text2: str, min_overlap: int = 10) -> int:
        """
        Find overlapping text between end of text1 and start of text2.

        Args:
            text1: First text
            text2: Second text
            min_overlap: Minimum overlap length to consider

        Returns:
            Length of overlap
        """
        try:
            max_overlap = min(len(text1), len(text2), 100)  # Limit search to last 100 chars

            # Search for longest overlap
            for overlap_len in range(max_overlap, min_overlap - 1, -1):
                end_of_text1 = text1[-overlap_len:]
                start_of_text2 = text2[:overlap_len]

                if end_of_text1.lower() == start_of_text2.lower():
                    return overlap_len

            return 0

        except Exception as e:
            logger.error(f"❌ Overlap detection failed: {e}")
            return 0

    def _final_cleanup(self, text: str) -> str:
        """
        Final cleanup of merged text.

        Args:
            text: Merged text

        Returns:
            Cleaned text
        """
        try:
            logger.debug("🔍 Performing final cleanup...")

            # Remove multiple spaces
            text = re.sub(r' +', ' ', text)

            # Fix spacing around punctuation
            text = re.sub(r'\s+([.,!?])', r'\1', text)
            text = re.sub(r'([.,!?])([^\s])', r'\1 \2', text)

            # Remove spaces before closing brackets/quotes
            text = re.sub(r'\s+([)\]"}])', r'\1', text)

            # Add spaces after opening brackets/quotes
            text = re.sub(r'([(\["{])\s*', r'\1 ', text)

            # Fix multiple punctuation
            text = re.sub(r'([.!?])\1+', r'\1', text)

            # Capitalize first letter
            if text:
                text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

            # Strip final whitespace
            text = text.strip()

            logger.debug("Final cleanup complete")

            return text

        except Exception as e:
            logger.error(f"❌ Final cleanup failed: {e}")
            logger.exception("Cleanup error:")
            return text  # Return original if cleanup fails

    def add_timestamps(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add timestamp information to chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Chunks with timestamp information
        """
        try:
            logger.info(f"Adding timestamps to {len(chunks)} chunks")

            timestamped_chunks = []

            for chunk in chunks:
                try:
                    timestamped_chunk = {
                        "chunk_index": chunk.get('chunk_index', 0),
                        "start_time": chunk.get('start_time', 0.0),
                        "end_time": chunk.get('end_time', 0.0),
                        "transcription": chunk.get('transcription', ''),
                        "duration": chunk.get('end_time', 0.0) - chunk.get('start_time', 0.0)
                    }

                    timestamped_chunks.append(timestamped_chunk)

                    logger.debug(
                        f"Chunk {timestamped_chunk['chunk_index']}: "
                        f"{timestamped_chunk['start_time']:.2f}s - {timestamped_chunk['end_time']:.2f}s"
                    )

                except Exception as e:
                    logger.error(f"❌ Failed to add timestamp to chunk: {e}")
                    continue

            logger.info(f"Timestamps added to {len(timestamped_chunks)} chunks")

            return timestamped_chunks

        except Exception as e:
            logger.error(f"❌ Failed to add timestamps: {e}")
            logger.exception("Timestamp addition error:")
            return chunks  # Return original if adding timestamps fails
