"""
API Schemas (Request/Response Models).
"""

from .keyword_schemas import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    KeywordResult,
    KeywordStatistics,
)
from .task_schemas import (
    TaskCreateRequest,
    TaskResponse,
    TaskDetail,
    TaskStatistics,
)
from .common_schemas import (
    HealthResponse,
    ErrorResponse,
)

__all__ = [
    # Keyword schemas
    "KeywordExtractionRequest",
    "KeywordExtractionResponse",
    "KeywordResult",
    "KeywordStatistics",
    # Task schemas
    "TaskCreateRequest",
    "TaskResponse",
    "TaskDetail",
    "TaskStatistics",
    # Common schemas
    "HealthResponse",
    "ErrorResponse",
]

