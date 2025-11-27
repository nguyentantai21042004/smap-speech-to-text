"""
Repository Ports.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities import Job, JobStatus


class TaskRepositoryPort(ABC):
    """Abstract interface for Task Repository."""

    @abstractmethod
    async def create_job(self, job: Job) -> Job:
        """Save a new job."""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        pass

    @abstractmethod
    async def update_job(self, job: Job) -> bool:
        """Update an existing job."""
        pass

    @abstractmethod
    async def get_pending_jobs(self, limit: int = 10) -> List[Job]:
        """Get pending jobs."""
        pass

    @abstractmethod
    async def list_jobs(
        self, limit: int = 100, status: Optional[str] = None
    ) -> List[Job]:
        """List jobs with optional filter."""
        pass
