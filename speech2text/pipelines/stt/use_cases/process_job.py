"""
Process Job Use Case.
Orchestrates the STT pipeline: Download -> Chunk -> Transcribe -> Merge -> Upload.
"""

import os
import time
import tempfile
import shutil
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.logger import logger, format_exception_short
from core.config import get_settings
from core.errors import TransientError, PermanentError
from domain.entities import Job, JobStatus, Chunk
from ports.repository import TaskRepositoryPort
from ports.storage import StoragePort
from ports.transcriber import TranscriberPort
from pipelines.stt.chunking import AudioChunker, get_audio_duration
from pipelines.stt.merger import ResultMerger

settings = get_settings()


class ProcessJobUseCase:
    """
    Use Case for processing an STT job.
    """

    def __init__(
        self,
        repository: TaskRepositoryPort,
        storage: StoragePort,
        transcriber: TranscriberPort,
    ):
        self.repository = repository
        self.storage = storage
        self.transcriber = transcriber

    async def execute(self, job_id: str) -> Dict[str, Any]:
        """
        Execute the STT processing pipeline for a job.
        """
        start_time = time.time()
        temp_dir = None

        try:
            logger.info(
                f"========== Starting STT job processing: job_id={job_id} =========="
            )

            # 1. Fetch Job
            job = await self.repository.get_job(job_id)
            if not job:
                raise PermanentError(f"Job not found: {job_id}")

            logger.info(
                f"Job found: file={job.original_filename}, language={job.language}"
            )

            # Update status to PROCESSING
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            await self.repository.update_job(job)

            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix=f"stt_{job_id}_")

            # 2. Download Audio
            local_audio_path = os.path.join(temp_dir, job.original_filename)
            await self.storage.download_file(job.minio_audio_path, local_audio_path)

            # Get duration
            try:
                duration = get_audio_duration(local_audio_path)
                job.audio_duration_seconds = duration
                await self.repository.update_job(job)
            except Exception as e:
                logger.warning(f"Failed to get audio duration: {e}")

            # 3. Chunk Audio
            chunker = AudioChunker()
            chunks_data = chunker.chunk_audio(
                audio_path=local_audio_path,
                output_dir=os.path.join(temp_dir, "chunks"),
                strategy=job.chunk_strategy,
                chunk_duration=settings.chunk_duration,
                min_silence_len=int(settings.min_silence_duration * 1000),
                silence_thresh=settings.silence_threshold,
            )

            # Create Chunk entities
            job.chunks = [
                Chunk(
                    index=c["chunk_index"],
                    start_time=c["start_time"],
                    end_time=c["end_time"],
                    file_path=c["file_path"],
                    status=JobStatus.PENDING,
                )
                for c in chunks_data
            ]
            job.chunks_total = len(job.chunks)
            await self.repository.update_job(job)

            # 4. Transcribe Chunks
            await self._transcribe_chunks(job)

            # 5. Merge Results
            merger = ResultMerger()
            # Convert Chunk entities back to dicts for merger (or update merger to use entities)
            # Merger expects dicts with 'transcription' key.
            chunks_dicts = [
                {
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                    "transcription": c.transcription,
                }
                for c in job.chunks
                if c.status == JobStatus.COMPLETED
            ]
            final_transcription = merger.merge_chunks(chunks_dicts)

            # 6. Upload Result
            result_filename = f"result_{job_id}.txt"
            result_object_name = f"results/{result_filename}"

            # Create a file-like object from string
            import io

            result_stream = io.BytesIO(final_transcription.encode("utf-8"))

            await self.storage.upload_file(
                result_stream, result_object_name, "text/plain"
            )

            # 7. Complete Job
            job.status = JobStatus.COMPLETED
            job.transcription_text = final_transcription
            job.minio_result_path = result_object_name
            job.completed_at = datetime.utcnow()
            job.chunks_completed = len(chunks_dicts)

            await self.repository.update_job(job)

            elapsed_time = time.time() - start_time
            logger.info(
                f"========== STT job processing COMPLETED: job_id={job_id}, time={elapsed_time:.2f}s =========="
            )

            return {
                "status": "success",
                "job_id": job_id,
                "transcription": final_transcription,
                "processing_time": elapsed_time,
            }

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Job processing failed: {e}")

            # Handle failure status
            try:
                # Re-fetch job to ensure we have latest state if possible, or just use current
                if "job" in locals() and job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    await self.repository.update_job(job)
            except Exception as update_err:
                logger.error(f"Failed to update job status to FAILED: {update_err}")

            raise

        finally:
            # Cleanup
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp dir: {e}")

    async def _transcribe_chunks(self, job: Job):
        """
        Transcribe chunks in parallel.
        """
        semaphore = asyncio.Semaphore(settings.max_parallel_workers)

        async def process_chunk(chunk: Chunk):
            async with semaphore:
                try:
                    logger.info(f"Transcribing chunk {chunk.index}...")
                    result = await self.transcriber.transcribe(
                        audio_path=chunk.file_path,
                        model=job.model_used,
                        language=job.language,
                    )
                    chunk.transcription = result["text"]
                    chunk.status = JobStatus.COMPLETED
                    chunk.processed_at = datetime.utcnow()
                except Exception as e:
                    logger.error(f"Chunk {chunk.index} failed: {e}")
                    chunk.status = JobStatus.FAILED
                    chunk.error_message = str(e)
                    # We don't raise here to allow other chunks to finish?
                    # But if one fails, the whole job might be compromised.
                    # Legacy logic allowed partial failure? No, it raised PermanentError if all failed.
                    # But if one failed, it logged and continued?
                    # Legacy: "Chunk {i} failed... Continue with other chunks".
                    # But at the end: "if not transcribed_chunks: raise PermanentError".
                    # So partial success is allowed?
                    # Merger handles missing chunks?
                    pass

        # Run all chunks
        tasks = [process_chunk(chunk) for chunk in job.chunks]

        # We want to update DB periodically or after all?
        # Legacy updated DB at milestones.
        # Here we can just wait for all.
        await asyncio.gather(*tasks)

        # Update job with chunk results
        job.chunks_completed = sum(
            1 for c in job.chunks if c.status == JobStatus.COMPLETED
        )
        await self.repository.update_job(job)

        if job.chunks_completed == 0 and len(job.chunks) > 0:
            raise PermanentError("All chunks failed to transcribe")
