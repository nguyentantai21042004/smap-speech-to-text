"""
Keyword Extraction API Routes.
"""

from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import Dict, List, Optional

from internal.api.schemas import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
)
from services.interfaces import IKeywordService
from core import logger


router = APIRouter(prefix="/api/v1/keywords", tags=["Keywords"])


def create_keyword_routes(keyword_service: IKeywordService) -> APIRouter:
    """
    Factory function to create keyword routes with dependency injection.
    
    Args:
        keyword_service: Implementation of IKeywordService
        
    Returns:
        APIRouter: Configured router with all keyword endpoints
    """

    @router.post(
        "/extract",
        response_model=KeywordExtractionResponse,
        status_code=status.HTTP_200_OK,
        summary="Extract Keywords",
        description="Extract keywords from Vietnamese text using various algorithms",
        responses={
            200: {
                "description": "Keywords extracted successfully",
                "content": {
                    "application/json": {
                        "examples": {
                            "sync_success": {
                                "summary": "Synchronous extraction",
                                "value": {
                                    "status": "success",
                                    "data": {
                                        "id": "keyword_123abc",
                                        "keywords": [
                                            {"word": "python", "score": 0.95},
                                            {"word": "fastapi", "score": 0.87}
                                        ],
                                        "processing_time": 0.234
                                    },
                                    "cached": False
                                }
                            },
                            "async_queued": {
                                "summary": "Async processing queued",
                                "value": {
                                    "status": "queued",
                                    "data": {"task_id": "task_456def"},
                                    "message": "Task queued for processing"
                                }
                            }
                        }
                    }
                }
            },
            500: {"description": "Internal server error"}
        }
    )
    async def extract_keywords(request: KeywordExtractionRequest):
        """
        Extract keywords from Vietnamese text.

        Supports two processing modes:
        - **Synchronous**: Immediate response with extracted keywords (async_processing=false)
        - **Asynchronous**: Returns task_id for later retrieval (async_processing=true)

        **Parameters:**
        - **text**: Input text to analyze (required, min 1 character)
        - **method**: Extraction algorithm to use (default: "default")
        - **num_keywords**: Number of keywords to extract (1-50, default: 10)
        - **async_processing**: Enable queue-based processing (default: false)

        **Returns:**
        - Synchronous: Extracted keywords with scores and processing time
        - Asynchronous: Task ID for status checking via /tasks/{task_id}

        Results are cached for improved performance on duplicate requests.
        """
        try:
            if request.async_processing:
                result = await keyword_service.extract_keywords_async(
                    text=request.text,
                    method=request.method,
                    num_keywords=request.num_keywords,
                )
            else:
                result = await keyword_service.extract_keywords_sync(
                    text=request.text,
                    method=request.method,
                    num_keywords=request.num_keywords,
                )
            return KeywordExtractionResponse(**result)
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error extracting keywords: {str(e)}",
            )

    @router.get(
        "/{result_id}",
        response_model=Dict,
        summary="Get Keyword Result",
        description="Retrieve a specific keyword extraction result by its ID",
        responses={
            200: {"description": "Result found and returned"},
            404: {"description": "Result not found"},
            500: {"description": "Internal server error"}
        }
    )
    async def get_keyword_result(result_id: str):
        """
        Get keyword extraction result by ID.

        Retrieve the complete result of a previous keyword extraction operation,
        including extracted keywords, scores, and metadata.

        **Parameters:**
        - **result_id**: Unique identifier of the keyword extraction result

        **Returns:**
        Complete extraction result with keywords, processing time, and caching info.
        """
        try:
            result = await keyword_service.get_extraction_result(result_id)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Result {result_id} not found",
                )
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting keyword result: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting result: {str(e)}",
            )

    @router.get(
        "",
        response_model=List[Dict],
        summary="Get Recent Extractions",
        description="Retrieve a list of recent keyword extraction results with optional filtering",
        responses={
            200: {"description": "List of recent extraction results"},
            500: {"description": "Internal server error"}
        }
    )
    async def get_recent_keywords(
        limit: int = Query(default=10, ge=1, le=100, description="Maximum number of results to return"),
        method: Optional[str] = Query(default=None, description="Filter by extraction method"),
    ):
        """
        Get recent keyword extraction results.

        Retrieve a paginated list of recent keyword extractions with optional
        filtering by extraction method.

        **Query Parameters:**
        - **limit**: Maximum number of results (1-100, default: 10)
        - **method**: Filter by extraction method (optional)

        **Returns:**
        Array of keyword extraction results sorted by creation time (newest first).
        """
        try:
            return await keyword_service.get_recent_results(limit, method)
        except Exception as e:
            logger.error(f"Error getting recent keywords: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting keywords: {str(e)}",
            )

    @router.get(
        "/stats/summary",
        response_model=Dict,
        summary="Get Statistics",
        description="Retrieve keyword extraction statistics and analytics",
        responses={
            200: {
                "description": "Statistics retrieved successfully",
                "content": {
                    "application/json": {
                        "example": {
                            "total_extractions": 1250,
                            "methods_used": {"default": 800, "tfidf": 450},
                            "average_processing_time": 0.234,
                            "cache_hit_rate": 0.67
                        }
                    }
                }
            },
            500: {"description": "Internal server error"}
        }
    )
    async def get_keyword_statistics():
        """
        Get keyword extraction statistics.

        Provides aggregate statistics about keyword extraction operations including:
        - Total number of extractions performed
        - Distribution of extraction methods used
        - Average processing time
        - Cache hit rate

        **Returns:**
        Statistics object with various metrics and analytics.
        """
        try:
            return await keyword_service.get_statistics()
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error getting statistics: {str(e)}",
            )

    return router

