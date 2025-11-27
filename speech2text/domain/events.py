"""
Domain events.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DomainEvent:
    """Base domain event."""

    occurred_at: datetime = datetime.utcnow()


@dataclass
class JobCreated(DomainEvent):
    """Event raised when a job is created."""

    job_id: str
    filename: str


@dataclass
class JobCompleted(DomainEvent):
    """Event raised when a job is completed."""

    job_id: str
    transcription_length: int


@dataclass
class JobFailed(DomainEvent):
    """Event raised when a job fails."""

    job_id: str
    error: str
