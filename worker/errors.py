"""Error definitions for STT processing."""


class STTError(Exception):
    """Base STT Error."""

    pass


class TransientError(STTError):
    """Errors that can be retried."""

    def __init__(self, message, retry_count=0):
        self.message = message
        self.retry_count = retry_count
        super().__init__(self.message)


class PermanentError(STTError):
    """Errors that should not be retried."""

    pass


# Transient errors
class OutOfMemoryError(TransientError):
    pass


class TimeoutError(TransientError):
    pass


class WhisperCrashError(TransientError):
    pass


class NetworkError(TransientError):
    pass


# Permanent errors
class InvalidAudioFormatError(PermanentError):
    pass


class UnsupportedLanguageError(PermanentError):
    pass


class FileTooLargeError(PermanentError):
    pass


class FileNotFoundError(PermanentError):
    pass


class CorruptedFileError(PermanentError):
    pass
