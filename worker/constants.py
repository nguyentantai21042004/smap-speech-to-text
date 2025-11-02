"""Constants for STT worker."""
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Language(str, Enum):
    ENGLISH = "en"
    VIETNAMESE = "vi"


# Supported audio formats
SUPPORTED_FORMATS = [
    '.mp3', '.wav', '.m4a', '.mp4',
    '.aac', '.ogg', '.flac', '.wma',
    '.webm', '.mkv', '.avi', '.mov'
]

# Queue names
QUEUE_HIGH_PRIORITY = "stt_jobs_high"
QUEUE_NORMAL = "stt_jobs"
QUEUE_LOW_PRIORITY = "stt_jobs_low"
QUEUE_DEAD_LETTER = "stt_jobs_dlq"

# Processing constants
MAX_CHUNK_SIZE_SECONDS = 60
MIN_CHUNK_SIZE_SECONDS = 5
DEFAULT_SAMPLE_RATE = 16000
