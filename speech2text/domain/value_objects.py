"""
Domain value objects.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class JobId:
    """Job Identifier."""

    value: str

    def __str__(self):
        return self.value


@dataclass(frozen=True)
class FilePath:
    """File Path Value Object."""

    value: str

    def __str__(self):
        return self.value
