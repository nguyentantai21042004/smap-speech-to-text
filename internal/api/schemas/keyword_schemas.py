"""
Pydantic schemas for Keyword Extraction API.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class KeywordExtractionRequest(BaseModel):
    """Request model for keyword extraction."""

    text: str = Field(..., min_length=1, description="Text to extract keywords from")
    method: str = Field(default="default", description="Extraction method")
    num_keywords: int = Field(default=10, ge=1, le=50, description="Number of keywords")
    async_processing: bool = Field(
        default=False, description="Process asynchronously via queue"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "text": "Python là ngôn ngữ lập trình phổ biến cho phát triển web và machine learning",
                    "method": "default",
                    "num_keywords": 5,
                    "async_processing": False
                },
                {
                    "text": "FastAPI là framework hiện đại cho việc xây dựng API với hiệu suất cao",
                    "method": "tfidf",
                    "num_keywords": 10,
                    "async_processing": True
                }
            ]
        }


class KeywordExtractionResponse(BaseModel):
    """Response model for keyword extraction."""

    status: str
    data: Optional[Dict] = None
    message: Optional[str] = None
    cached: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "status": "success",
                    "data": {
                        "id": "kw_6541234abcdef",
                        "keywords": [
                            {"word": "python", "score": 0.95},
                            {"word": "machine learning", "score": 0.87},
                            {"word": "phát triển", "score": 0.82}
                        ],
                        "processing_time": 0.156
                    },
                    "cached": False,
                    "message": None
                },
                {
                    "status": "queued",
                    "data": {"task_id": "task_789xyz"},
                    "message": "Task queued for asynchronous processing",
                    "cached": None
                }
            ]
        }


class KeywordResult(BaseModel):
    """Model for keyword extraction result."""

    id: str
    text: str
    method: str
    keywords: List[Dict]
    num_keywords: int
    processing_time: Optional[float] = None
    cached: bool = False
    created_at: str


class KeywordStatistics(BaseModel):
    """Model for keyword extraction statistics."""

    total_extractions: int
    methods_used: Dict[str, int]
    average_processing_time: Optional[float] = None
    cache_hit_rate: Optional[float] = None

