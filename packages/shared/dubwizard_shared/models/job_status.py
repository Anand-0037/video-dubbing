from enum import Enum

class JobStatus(str, Enum):
    """Job status enumeration."""
    CREATED = "created"
    UPLOADING = "uploading"
    QUEUED = "queued"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    TRANSLATING = "translating"
    SYNTHESIZING = "synthesizing"
    PROCESSING_VIDEO = "processing_video"
    DONE = "done"
    FAILED = "failed"
