"""
STT Task API Routes.
Includes detailed logging and comprehensive error handling.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from typing import Optional
import time

from core.logger import logger
from services.task_service import get_task_service

router = APIRouter(prefix="/api/v1/tasks", tags=["STT Tasks"])


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload Audio for Transcription",
    description="Upload an audio file and create an STT job",
    responses={
        201: {
            "description": "Job created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "stt_6541234abcdef",
                        "status": "PENDING",
                        "message": "Job created successfully",
                        "filename": "audio.mp3",
                        "file_size_mb": 5.2,
                        "language": "vi",
                        "model": "medium",
                        "created_at": "2024-11-02T16:00:00Z",
                    }
                }
            },
        },
        400: {"description": "Bad request - invalid file or parameters"},
        413: {"description": "File too large (max 500MB)"},
        500: {"description": "Internal server error"},
    },
)
async def upload_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form(default="vi", description="Language code (en, vi, etc.)"),
    model: str = Form(
        default="medium", description="Whisper model (tiny, base, small, medium, large)"
    ),
):
    """
    Upload an audio file for speech-to-text transcription.

    **Parameters:**
    - **file**: Audio file (MP3, WAV, M4A, etc.)
    - **language**: Language code (default: vi for Vietnamese)
    - **model**: Whisper model to use (default: medium)

    **Returns:**
    - job_id: Unique identifier for the transcription job
    - status: Current job status
    - message: Success message

    **Supported formats:**
    MP3, WAV, M4A, MP4, AAC, OGG, FLAC, WMA, WEBM, MKV, AVI, MOV
    """
    start_time = time.time()

    try:
        logger.info(
            f"API: Upload request received: filename={file.filename}, language={language}, model={model}"
        )

        # Validate file
        if not file.filename:
            logger.error("❌ No filename provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided"
            )

        # Get file size
        file_content = await file.read()
        file_size_bytes = len(file_content)
        file_size_mb = file_size_bytes / (1024 * 1024)

        logger.debug(f"File size: {file_size_mb:.2f}MB")

        # Validate file size
        if file_size_mb > 500:
            logger.error(f"❌ File too large: {file_size_mb:.2f}MB")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large: {file_size_mb:.2f}MB. Maximum size is 500MB",
            )

        # Create task
        import io

        task_service = get_task_service()

        result = await task_service.create_stt_task(
            audio_file=io.BytesIO(file_content),
            filename=file.filename,
            file_size_mb=file_size_mb,
            language=language,
            model=model,
        )

        elapsed_time = time.time() - start_time
        logger.info(
            f"API: Upload successful: job_id={result['job_id']}, time={elapsed_time:.2f}s"
        )

        return result

    except HTTPException as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ API: HTTP error after {elapsed_time:.2f}s: {e.detail}")
        raise

    except ValueError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ API: Validation error after {elapsed_time:.2f}s: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"❌ API: Upload failed after {elapsed_time:.2f}s: {e}")
        logger.exception("API upload error details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transcription job: {str(e)}",
        )


@router.get(
    "/{job_id}/status",
    summary="Get Job Status",
    description="Get the current status of a transcription job",
    responses={
        200: {
            "description": "Job status retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "pending": {
                            "summary": "Job pending",
                            "value": {
                                "job_id": "stt_6541234abcdef",
                                "status": "PENDING",
                                "progress": 0,
                                "chunks_total": 5,
                                "chunks_completed": 0,
                                "created_at": "2024-11-02T16:00:00Z",
                            },
                        },
                        "processing": {
                            "summary": "Job processing",
                            "value": {
                                "job_id": "stt_6541234abcdef",
                                "status": "PROCESSING",
                                "progress": 60,
                                "chunks_total": 5,
                                "chunks_completed": 3,
                                "created_at": "2024-11-02T16:00:00Z",
                                "started_at": "2024-11-02T16:00:05Z",
                            },
                        },
                        "completed": {
                            "summary": "Job completed",
                            "value": {
                                "job_id": "stt_6541234abcdef",
                                "status": "COMPLETED",
                                "progress": 100,
                                "chunks_total": 5,
                                "chunks_completed": 5,
                                "created_at": "2024-11-02T16:00:00Z",
                                "started_at": "2024-11-02T16:00:05Z",
                                "completed_at": "2024-11-02T16:05:30Z",
                            },
                        },
                    }
                }
            },
        },
        404: {"description": "Job not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_job_status(job_id: str):
    """
    Get the status of a transcription job.

    **Parameters:**
    - **job_id**: Job identifier

    **Returns:**
    - job_id: Job identifier
    - status: Current status (PENDING, PROCESSING, COMPLETED, FAILED)
    - progress: Processing progress (0-100%)
    - chunks_total: Total number of audio chunks
    - chunks_completed: Number of completed chunks
    - created_at: Job creation timestamp
    - started_at: Job start timestamp (if started)
    - completed_at: Job completion timestamp (if completed)

    **Status values:**
    - PENDING: Job is queued, waiting to be processed
    - PROCESSING: Job is currently being processed
    - COMPLETED: Job completed successfully
    - FAILED: Job failed (check error_message)
    """
    try:
        logger.info(f"API: Status request for job_id={job_id}")

        task_service = get_task_service()
        result = await task_service.get_task_status(job_id)

        if not result:
            logger.warning(f"API: Job not found: job_id={job_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job not found: {job_id}"
            )

        logger.info(
            f"API: Status retrieved: job_id={job_id}, status={result['status']}"
        )

        return result

    except HTTPException as e:
        logger.error(f"❌ API: HTTP error: {e.detail}")
        raise

    except Exception as e:
        logger.error(f"❌ API: Failed to get status for {job_id}: {e}")
        logger.exception("API status error details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}",
        )


@router.get(
    "/{job_id}/result",
    summary="Get Transcription Result",
    description="Get the transcription result for a completed job",
    responses={
        200: {
            "description": "Result retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "stt_6541234abcdef",
                        "status": "COMPLETED",
                        "text": "Đây là nội dung được chuyển đổi từ audio sang văn bản.",
                        "transcription_url": "https://minio.tantai.dev/stt-results/stt_6541234abcdef.json",
                        "processing_time": 125.5,
                        "chunks_total": 5,
                        "chunks_completed": 5,
                        "created_at": "2024-11-02T16:00:00Z",
                        "completed_at": "2024-11-02T16:05:30Z",
                    }
                }
            },
        },
        400: {"description": "Job not completed yet - check status first"},
        404: {"description": "Job not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_job_result(job_id: str):
    """
    Get the transcription result for a completed job.

    **Parameters:**
    - **job_id**: Job identifier

    **Returns:**
    - job_id: Job identifier
    - status: Job status
    - transcription: Transcribed text
    - filename: Original filename
    - language: Language used
    - duration_seconds: Audio duration
    - processing_time_seconds: Processing time
    - download_url: URL to download result file (valid for 1 hour)

    **Note:**
    - Only available for COMPLETED jobs
    - For jobs still processing, returns status information
    """
    try:
        logger.info(f"API: Result request for job_id={job_id}")

        task_service = get_task_service()
        result = await task_service.get_task_result(job_id)

        if not result:
            logger.warning(f"API: Job not found: job_id={job_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job not found: {job_id}"
            )

        if result["status"] != "COMPLETED":
            logger.info(
                f"API: Job not completed: job_id={job_id}, status={result['status']}"
            )

        logger.info(
            f"API: Result retrieved: job_id={job_id}, status={result['status']}"
        )

        return result

    except HTTPException as e:
        logger.error(f"❌ API: HTTP error: {e.detail}")
        raise

    except Exception as e:
        logger.error(f"❌ API: Failed to get result for {job_id}: {e}")
        logger.exception("API result error details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job result: {str(e)}",
        )


@router.get(
    "",
    summary="List Jobs",
    description="List transcription jobs with optional status filter",
    responses={
        200: {
            "description": "Jobs retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "total": 10,
                        "limit": 10,
                        "status_filter": None,
                        "jobs": [
                            {
                                "job_id": "stt_6541234abcdef",
                                "status": "COMPLETED",
                                "filename": "audio.mp3",
                                "created_at": "2024-11-02T16:00:00Z",
                                "completed_at": "2024-11-02T16:05:30Z",
                            },
                            {
                                "job_id": "stt_6541234xyz",
                                "status": "PROCESSING",
                                "filename": "audio2.mp3",
                                "created_at": "2024-11-02T16:10:00Z",
                            },
                        ],
                    }
                }
            },
        },
        500: {"description": "Internal server error"},
    },
)
async def list_jobs(status: Optional[str] = None, limit: int = 10):
    """
    List transcription jobs.

    **Query Parameters:**
    - **status**: Filter by status (PENDING, PROCESSING, COMPLETED, FAILED)
    - **limit**: Maximum number of jobs to return (default: 10, max: 100)

    **Returns:**
    Array of job summaries with basic information.
    """
    try:
        logger.info(f"API: List jobs request: status={status}, limit={limit}")

        # Validate limit
        if limit > 100:
            limit = 100

        task_service = get_task_service()
        results = await task_service.list_tasks(limit=limit, status=status)

        logger.info(f"API: Jobs listed: count={len(results)}")

        return {"status": "success", "count": len(results), "jobs": results}

    except Exception as e:
        logger.error(f"❌ API: Failed to list jobs: {e}")
        logger.exception("API list error details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}",
        )


def create_task_routes() -> APIRouter:
    """
    Factory function to create task routes.

    Returns:
        APIRouter: Configured router with task endpoints
    """
    return router
