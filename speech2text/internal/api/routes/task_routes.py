"""
STT Task API Routes.
Includes detailed logging and comprehensive error handling.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status, Depends
from typing import Optional
import time

from core.logger import logger, format_exception_short
from internal.api.utils import success_response, error_response
from internal.api.schemas.common_schemas import StandardResponse
from internal.api.dependencies.task_dependencies import get_task_use_case
from services.task_use_case import ITaskUseCase
from services.file_service import get_file_service
from core.config import get_settings

router = APIRouter(prefix="/api/v1/tasks", tags=["STT Tasks"])


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    summary="Create STT Task from File ID",
    description="Create a speech-to-text job from an uploaded file_id. Model is determined by system, language defaults to 'vi' if not provided.",
    responses={
        201: {
            "description": "Job created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "job_id": "69073cc61dc7aa422463d537",
                        "id": "69073cc61dc7aa422463d537",
                        "message": "Task created and queued for processing",
                        "details": {
                            "file_id": "69073cc61dc7aa422463d537",
                            "filename": "audio.mp3",
                            "size_mb": 5.2,
                            "language": "vi",
                            "model": "medium",
                            "minio_path": "uploads/xxx-xxx-xxx.mp3",
                        },
                    }
                }
            },
        },
        400: {"description": "Bad request - invalid file_id or parameters"},
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    },
)
async def create_stt_task(
    file_id: str = Form(..., description="File ID from file upload endpoint"),
    language: str = Form(
        default=None,
        description="Optional language code (defaults to 'vi' if not provided)",
    ),
    use_case: ITaskUseCase = Depends(get_task_use_case),
):
    """
    Create a speech-to-text job from an uploaded file_id.
    """
    start_time = time.time()

    try:
        logger.info(
            f"API: Create STT task request: file_id={file_id}, language={language or 'default (vi)'}"
        )

        # Validate file_id
        if not file_id or file_id.strip() == "":
            logger.error("No file_id provided")
            return error_response(message="file_id is required", error_code=1)

        # Get file record
        file_service = get_file_service()
        file_record = await file_service.get_file(file_id)

        if not file_record:
            logger.error(f"File not found: file_id={file_id}")
            return error_response(message="File not found", error_code=1)

        filename = file_record["original_filename"]
        minio_path = file_record["minio_path"]
        file_size_mb = file_record["file_size_mb"]

        settings = get_settings()
        model = settings.default_whisper_model

        if not language:
            language = "vi"

        # Create job using Use Case
        job = await use_case.create_job_from_existing_file(
            filename=filename,
            minio_path=minio_path,
            file_size_mb=file_size_mb,
            language=language,
            model=model,
        )

        elapsed_time = time.time() - start_time
        logger.info(
            f"API: STT task created successfully: job_id={job.id}, time={elapsed_time:.2f}s"
        )

        result = {
            "status": "success",
            "job_id": job.id,
            "id": job.id,
            "message": "Task created and queued for processing",
            "details": {
                "file_id": file_id,
                "filename": filename,
                "size_mb": file_size_mb,
                "language": language,
                "model": model,
                "minio_path": minio_path,
            },
        }

        return success_response(
            message=result.get("message"),
            data=result,
        )

    except HTTPException as e:
        elapsed_time = time.time() - start_time
        logger.error(f"API: HTTP error after {elapsed_time:.2f}s: {e.detail}")
        return error_response(message=e.detail, error_code=1)

    except ValueError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"API: Validation error after {elapsed_time:.2f}s: {e}")
        return error_response(message=str(e), error_code=1)

    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = format_exception_short(
            e, f"API: Task creation failed after {elapsed_time:.2f}s"
        )
        logger.error(f"{error_msg}")
        return error_response(
            message=f"Failed to create transcription job: {str(e)}", error_code=1
        )


@router.get(
    "/{job_id}/status",
    summary="Get Job Status",
    description="Get the current status of a transcription job",
    responses={
        200: {"description": "Job status retrieved successfully"},
        404: {"description": "Job not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_job_status(
    job_id: str, use_case: ITaskUseCase = Depends(get_task_use_case)
):
    """
    Get the status of a transcription job.
    """
    try:
        logger.info(f"API: Status request for job_id={job_id}")

        job = await use_case.get_task_status(job_id)

        if not job:
            logger.warning(f"API: Job not found: job_id={job_id}")
            return error_response(message=f"Job not found: {job_id}", error_code=1)

        # Calculate progress
        progress = 0
        if job.chunks_total and job.chunks_total > 0:
            progress = (job.chunks_completed / job.chunks_total) * 100

        result = {
            "job_id": job.id,
            "id": job.id,
            "status": job.status.value,
            "filename": job.original_filename,
            "language": job.language,
            "model": job.model_used,
            "progress": round(progress, 2),
            "chunks_total": job.chunks_total,
            "chunks_completed": job.chunks_completed,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

        logger.info(
            f"API: Status retrieved: job_id={job_id}, status={job.status.value}"
        )

        return success_response(
            message="Job status retrieved successfully", data=result
        )

    except Exception as e:
        error_msg = format_exception_short(e, "API: Status check failed")
        logger.error(f"{error_msg}")
        return error_response(
            message=f"Failed to get job status: {str(e)}", error_code=1
        )


@router.get(
    "/{job_id}/result",
    summary="Get Transcription Result",
    description="Get the transcription result for a completed job",
    responses={
        200: {"description": "Result retrieved successfully"},
        400: {"description": "Job not completed yet"},
        404: {"description": "Job not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_job_result(
    job_id: str, use_case: ITaskUseCase = Depends(get_task_use_case)
):
    """
    Get the transcription result for a completed job.
    """
    try:
        logger.info(f"API: Result request for job_id={job_id}")

        result_data = await use_case.get_task_result(job_id)

        if not result_data:
            logger.warning(f"API: Job not found: job_id={job_id}")
            return error_response(message=f"Job not found: {job_id}", error_code=1)

        job = result_data["job"]
        download_url = result_data["download_url"]

        if job.status.value != "COMPLETED":
            logger.info(
                f"API: Job not completed: job_id={job_id}, status={job.status.value}"
            )
            # Return status info but indicate not completed?
            # Legacy returned 200 with message.
            # But let's follow legacy behavior if possible or improve.
            # Legacy: returns dict with status, message "Job not yet completed", transcription=None
            pass

        response_data = {
            "job_id": job.id,
            "id": job.id,
            "status": job.status.value,
            "filename": job.original_filename,
            "language": job.language,
            "transcription": job.transcription_text,
            "download_url": download_url,
            "duration_seconds": job.audio_duration_seconds,
            "processing_time_seconds": (
                (job.completed_at - job.started_at).total_seconds()
                if job.started_at and job.completed_at
                else None
            ),
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

        if job.status.value != "COMPLETED":
            response_data["message"] = "Job not yet completed"

        logger.info(
            f"API: Result retrieved: job_id={job_id}, status={job.status.value}"
        )

        return success_response(
            message="Job result retrieved successfully", data=response_data
        )

    except Exception as e:
        logger.error(f"API: Failed to get result for {job_id}: {e}")
        return error_response(
            message=f"Failed to get job result: {str(e)}", error_code=1
        )


@router.get(
    "",
    summary="List Jobs",
    description="List transcription jobs with optional status filter",
)
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 10,
    use_case: ITaskUseCase = Depends(get_task_use_case),
):
    """
    List transcription jobs.
    """
    try:
        logger.info(f"API: List jobs request: status={status}, limit={limit}")

        if limit > 100:
            limit = 100

        jobs = await use_case.list_tasks(limit=limit, status=status)

        results = [
            {
                "job_id": job.id,
                "id": job.id,
                "filename": job.original_filename,
                "status": job.status.value,
                "language": job.language,
                "created_at": job.created_at.isoformat(),
                "completed_at": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
            }
            for job in jobs
        ]

        logger.info(f"API: Jobs listed: count={len(results)}")

        return success_response(
            message=f"Retrieved {len(results)} jobs",
            data={"count": len(results), "jobs": results},
        )

    except Exception as e:
        logger.error(f"API: Failed to list jobs: {e}")
        return error_response(message=f"Failed to list jobs: {str(e)}", error_code=1)


def create_task_routes() -> APIRouter:
    return router
