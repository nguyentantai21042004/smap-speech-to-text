"""
File upload routes.
Separates file upload from STT processing.
"""

import time
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from core.logger import logger
from services.file_service import get_file_service

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload Audio File",
    description="Upload an audio file to MinIO and create a file record. Returns file_id for STT processing.",
    responses={
        201: {
            "description": "File uploaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "file_id": "69073cc61dc7aa422463d537",
                        "message": "File uploaded successfully",
                        "details": {
                            "filename": "audio.mp3",
                            "size_mb": 5.2,
                            "minio_path": "uploads/xxx-xxx-xxx.mp3",
                        },
                    }
                }
            },
        },
        400: {"description": "Bad request - invalid file or parameters"},
        413: {"description": "File too large (max 500MB)"},
        500: {"description": "Internal server error"},
    },
)
async def upload_file(
    file: UploadFile = File(..., description="Audio file to upload"),
):
    """
    Upload an audio file to MinIO and create a file record.

    **Parameters:**
    - **file**: Audio file (MP3, WAV, M4A, etc.)

    **Returns:**
    - **file_id**: Unique identifier for the uploaded file (use this for STT processing)
    - **details**: File metadata (filename, size, MinIO path)

    **Supported formats:**
    MP3, WAV, M4A, MP4, AAC, OGG, FLAC, WMA, WEBM, MKV, AVI, MOV

    **Note:**
    This endpoint only uploads the file and creates a record.
    Use the returned `file_id` with `/api/v1/tasks/create` to start STT processing.
    """
    start_time = time.time()

    try:
        logger.info(f"API: File upload request received: filename={file.filename}")

        # Validate file
        if not file.filename:
            logger.error("No filename provided")
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
            logger.error(f"File too large: {file_size_mb:.2f}MB")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large: {file_size_mb:.2f}MB. Maximum size is 500MB",
            )

        # Upload file
        import io

        file_service = get_file_service()

        result = await file_service.upload_file(
            file_data=io.BytesIO(file_content),
            filename=file.filename,
            file_size_mb=file_size_mb,
        )

        elapsed_time = time.time() - start_time
        logger.info(
            f"API: File upload successful: file_id={result['file_id']}, time={elapsed_time:.2f}s"
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"File upload failed after {elapsed_time:.2f}s: {e}")
        logger.exception("File upload error details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed",
        )
