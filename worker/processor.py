"""
Main STT processor orchestrating the complete transcription pipeline.
Includes extensive logging and comprehensive error handling.
"""
import os
import time
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from core.config import get_settings
from core.logger import logger
from core.storage import get_minio_client
from repositories.task_repository import get_task_repository
from repositories.models import JobStatus, JobUpdate, ChunkModel
from worker.chunking import AudioChunker, get_audio_duration
from worker.transcriber import WhisperTranscriber
from worker.merger import ResultMerger
from worker.errors import (
    TransientError, PermanentError,
    InvalidAudioFormatError, CorruptedFileError,
    WhisperCrashError, TimeoutError as STTTimeoutError
)

settings = get_settings()


async def process_stt_job(job_id: str) -> dict:
    """
    Main function to process an STT job.

    This orchestrates the entire pipeline:
    1. Download audio from MinIO
    2. Chunk the audio
    3. Transcribe each chunk
    4. Merge results
    5. Upload results to MinIO
    6. Update job status

    Args:
        job_id: Job ID to process

    Returns:
        Result dictionary with status and details

    Raises:
        Exception: If processing fails
    """
    start_time = time.time()
    temp_dir = None

    try:
        logger.info(f"📝 ========== Starting STT job processing: job_id={job_id} ==========")

        # Get repository
        repo = get_task_repository()

        # Get job from database
        logger.info(f"🔍 Fetching job from database...")
        job = await repo.get_job(job_id)

        if not job:
            error_msg = f"Job not found: {job_id}"
            logger.error(f"❌ {error_msg}")
            raise PermanentError(error_msg)

        logger.info(f"✅ Job found: file={job.original_filename}, language={job.language}, model={job.model_used}")

        # Update status to PROCESSING
        logger.info(f"📝 Updating job status to PROCESSING...")
        await repo.update_status(job_id, JobStatus.PROCESSING)

        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"stt_{job_id}_")
        logger.info(f"✅ Created temp directory: {temp_dir}")

        # Step 1: Download audio from MinIO
        logger.info(f"📝 Step 1: Downloading audio from MinIO...")
        audio_path = await _download_audio_from_minio(job, temp_dir)
        logger.info(f"✅ Audio downloaded: {audio_path}")

        # Get audio duration
        try:
            duration = get_audio_duration(audio_path)
            await repo.update_job(job_id, JobUpdate(audio_duration_seconds=duration))
            logger.info(f"✅ Audio duration: {duration:.2f}s")
        except Exception as e:
            logger.warning(f"⚠️ Failed to get audio duration: {e}")

        # Step 2: Chunk audio
        logger.info(f"📝 Step 2: Chunking audio...")
        chunks = await _chunk_audio(audio_path, temp_dir, job)
        logger.info(f"✅ Audio chunked: {len(chunks)} chunks created")

        # Update job with chunk info
        await repo.update_chunks(job_id, chunks)

        # Step 3: Transcribe chunks
        logger.info(f"📝 Step 3: Transcribing chunks...")
        transcribed_chunks = await _transcribe_chunks(chunks, job, repo, job_id)
        logger.info(f"✅ Chunks transcribed: {len(transcribed_chunks)} successful")

        # Step 4: Merge results
        logger.info(f"📝 Step 4: Merging results...")
        final_transcription = await _merge_results(transcribed_chunks)
        logger.info(f"✅ Results merged: {len(final_transcription)} chars")

        # Step 5: Upload results to MinIO
        logger.info(f"📝 Step 5: Uploading results to MinIO...")
        result_path = await _upload_results_to_minio(job_id, final_transcription)
        logger.info(f"✅ Results uploaded: {result_path}")

        # Step 6: Update job as completed
        logger.info(f"📝 Step 6: Updating job status to COMPLETED...")
        await repo.update_job(
            job_id,
            JobUpdate(
                status=JobStatus.COMPLETED,
                transcription_text=final_transcription,
                minio_result_path=result_path,
                chunks_completed=len(transcribed_chunks)
            )
        )

        elapsed_time = time.time() - start_time
        logger.info(f"✅ ========== STT job processing COMPLETED: job_id={job_id}, time={elapsed_time:.2f}s ==========")

        # Log performance metrics
        chars_per_second = len(final_transcription) / elapsed_time if elapsed_time > 0 else 0
        logger.info(f"📊 Performance metrics: chars/sec={chars_per_second:.2f}, chunks={len(chunks)}, time={elapsed_time:.2f}s")

        return {
            "status": "success",
            "job_id": job_id,
            "transcription": final_transcription,
            "chunks_processed": len(transcribed_chunks),
            "processing_time_seconds": elapsed_time
        }

    except PermanentError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ Permanent error processing job {job_id} after {elapsed_time:.2f}s: {e}")
        logger.exception("Permanent error details:")

        try:
            repo = get_task_repository()
            await repo.update_status(job_id, JobStatus.FAILED, str(e))
        except Exception as update_error:
            logger.error(f"❌ Failed to update job status: {update_error}")

        raise

    except TransientError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ Transient error processing job {job_id} after {elapsed_time:.2f}s: {e}")
        logger.exception("Transient error details:")

        try:
            repo = get_task_repository()
            await repo.increment_retry_count(job_id)
        except Exception as update_error:
            logger.error(f"❌ Failed to increment retry count: {update_error}")

        raise

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ Unexpected error processing job {job_id} after {elapsed_time:.2f}s: {e}")
        logger.exception("Processing error details:")

        try:
            repo = get_task_repository()
            await repo.update_status(job_id, JobStatus.FAILED, str(e))
        except Exception as update_error:
            logger.error(f"❌ Failed to update job status: {update_error}")

        raise

    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                logger.info(f"🧹 Cleaning up temp directory: {temp_dir}")
                shutil.rmtree(temp_dir)
                logger.debug(f"✅ Temp directory cleaned")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean temp directory: {e}")


async def _download_audio_from_minio(job, temp_dir: str) -> str:
    """
    Download audio file from MinIO.

    Args:
        job: Job model
        temp_dir: Temporary directory path

    Returns:
        Path to downloaded audio file

    Raises:
        Exception: If download fails
    """
    try:
        logger.debug(f"🔍 Downloading from MinIO: {job.minio_audio_path}")

        # Get MinIO client
        minio_client = get_minio_client()

        # Download file
        local_path = os.path.join(temp_dir, job.original_filename)
        minio_client.download_file(job.minio_audio_path, local_path)

        file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
        logger.debug(f"✅ Downloaded: {local_path}, size={file_size_mb:.2f}MB")

        return local_path

    except Exception as e:
        logger.error(f"❌ Failed to download audio from MinIO: {e}")
        logger.exception("MinIO download error details:")
        raise TransientError(f"MinIO download failed: {e}")


async def _chunk_audio(audio_path: str, temp_dir: str, job) -> list:
    """
    Chunk audio file.

    Args:
        audio_path: Path to audio file
        temp_dir: Temporary directory
        job: Job model

    Returns:
        List of chunk metadata

    Raises:
        Exception: If chunking fails
    """
    try:
        logger.debug(f"🔍 Chunking audio: strategy={job.chunk_strategy}")

        # Create chunks directory
        chunks_dir = os.path.join(temp_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)

        # Chunk audio
        chunker = AudioChunker()
        chunks = chunker.chunk_audio(
            audio_path=audio_path,
            output_dir=chunks_dir,
            strategy=job.chunk_strategy,
            chunk_duration=settings.chunk_duration,
            min_silence_len=int(settings.min_silence_duration * 1000),
            silence_thresh=settings.silence_threshold
        )

        logger.debug(f"✅ Chunking complete: {len(chunks)} chunks")

        return chunks

    except InvalidAudioFormatError as e:
        logger.error(f"❌ Invalid audio format: {e}")
        raise PermanentError(f"Invalid audio format: {e}")

    except CorruptedFileError as e:
        logger.error(f"❌ Corrupted audio file: {e}")
        raise PermanentError(f"Corrupted audio file: {e}")

    except Exception as e:
        logger.error(f"❌ Audio chunking failed: {e}")
        logger.exception("Chunking error details:")
        raise TransientError(f"Chunking failed: {e}")


async def _transcribe_chunks(chunks: list, job, repo, job_id: str) -> list:
    """
    Transcribe all chunks.

    Args:
        chunks: List of chunk metadata
        job: Job model
        repo: Task repository
        job_id: Job ID

    Returns:
        List of transcribed chunks

    Raises:
        Exception: If transcription fails
    """
    try:
        logger.debug(f"🔍 Transcribing {len(chunks)} chunks...")

        transcriber = WhisperTranscriber()
        transcribed_chunks = []

        for i, chunk in enumerate(chunks):
            try:
                logger.info(f"📝 Transcribing chunk {i+1}/{len(chunks)}: {chunk['file_path']}")

                # Transcribe with retry
                transcription = transcriber.transcribe_with_retry(
                    audio_path=chunk['file_path'],
                    language=job.language,
                    model=job.model_used,
                    max_retries=settings.max_retries
                )

                # Add transcription to chunk
                chunk['transcription'] = transcription
                chunk['status'] = JobStatus.COMPLETED
                chunk['processed_at'] = datetime.utcnow()

                transcribed_chunks.append(chunk)

                logger.info(f"✅ Chunk {i+1} transcribed: {len(transcription)} chars")

                # Update progress in database
                await repo.update_job(
                    job_id,
                    JobUpdate(chunks_completed=len(transcribed_chunks))
                )

            except STTTimeoutError as e:
                logger.error(f"❌ Timeout transcribing chunk {i}: {e}")
                chunk['status'] = JobStatus.FAILED
                chunk['error_message'] = str(e)
                # Continue with other chunks

            except WhisperCrashError as e:
                logger.error(f"❌ Whisper crash on chunk {i}: {e}")
                chunk['status'] = JobStatus.FAILED
                chunk['error_message'] = str(e)
                # Continue with other chunks

            except Exception as e:
                logger.error(f"❌ Failed to transcribe chunk {i}: {e}")
                logger.exception("Chunk transcription error:")
                chunk['status'] = JobStatus.FAILED
                chunk['error_message'] = str(e)
                # Continue with other chunks

        if not transcribed_chunks:
            raise PermanentError("All chunks failed to transcribe")

        success_rate = len(transcribed_chunks) / len(chunks) * 100
        logger.info(f"📊 Transcription success rate: {success_rate:.1f}% ({len(transcribed_chunks)}/{len(chunks)})")

        return transcribed_chunks

    except Exception as e:
        logger.error(f"❌ Chunk transcription failed: {e}")
        logger.exception("Transcription error details:")
        raise


async def _merge_results(chunks: list) -> str:
    """
    Merge transcription results.

    Args:
        chunks: List of transcribed chunks

    Returns:
        Merged transcription text

    Raises:
        Exception: If merging fails
    """
    try:
        logger.debug(f"🔍 Merging {len(chunks)} chunk transcriptions...")

        merger = ResultMerger()
        merged_text = merger.merge_chunks(chunks)

        logger.debug(f"✅ Merge complete: {len(merged_text)} chars")

        return merged_text

    except Exception as e:
        logger.error(f"❌ Result merging failed: {e}")
        logger.exception("Merge error details:")
        # Fallback: simple concatenation
        try:
            logger.warning("⚠️ Using fallback: simple concatenation")
            texts = [c.get('transcription', '') for c in chunks if c.get('transcription')]
            return ' '.join(texts)
        except Exception as fallback_error:
            logger.error(f"❌ Fallback merge also failed: {fallback_error}")
            raise PermanentError(f"Merge failed: {e}")


async def _upload_results_to_minio(job_id: str, transcription: str) -> str:
    """
    Upload results to MinIO.

    Args:
        job_id: Job ID
        transcription: Transcription text

    Returns:
        MinIO path to result file

    Raises:
        Exception: If upload fails
    """
    try:
        logger.debug(f"🔍 Uploading results to MinIO for job {job_id}...")

        # Create result filename
        result_filename = f"result_{job_id}.txt"
        minio_path = f"results/{result_filename}"

        # Convert to bytes
        content = transcription.encode('utf-8')

        # Get MinIO client
        minio_client = get_minio_client()

        # Upload
        import io
        minio_client.upload_file(
            file_data=io.BytesIO(content),
            object_name=minio_path,
            content_type="text/plain"
        )

        logger.debug(f"✅ Results uploaded: {minio_path}, size={len(content)} bytes")

        return minio_path

    except Exception as e:
        logger.error(f"❌ Failed to upload results to MinIO: {e}")
        logger.exception("MinIO upload error details:")
        raise TransientError(f"MinIO upload failed: {e}")
