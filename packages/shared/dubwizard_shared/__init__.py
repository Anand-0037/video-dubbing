"""DubWizard Shared Package - Common models, schemas, and services."""

from dubwizard_shared.models.job_status import JobStatus
from dubwizard_shared.models.job import Job, Base
from dubwizard_shared.models.segments import (
    TranscriptionSegment,
    TranslationSegment,
    SynthesizedSegment,
)
from dubwizard_shared.constants import (
    MAX_VIDEO_SIZE_MB,
    MAX_VIDEO_DURATION_SECONDS,
    ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_CONTENT_TYPES,
)
from dubwizard_shared.config import SharedSettings, shared_settings
from dubwizard_shared.schemas.job import JobCreate, JobResponse, JobStatusResponse, JobDB
from dubwizard_shared.services.s3_service import S3Service, get_s3_service, S3ValidationError
from dubwizard_shared.services.job_service import JobService

__all__ = [
    # Models
    "JobStatus",
    "Job",
    "Base",
    "TranscriptionSegment",
    "TranslationSegment",
    "SynthesizedSegment",
    # Constants
    "MAX_VIDEO_SIZE_MB",
    "MAX_VIDEO_DURATION_SECONDS",
    "ALLOWED_VIDEO_EXTENSIONS",
    "ALLOWED_CONTENT_TYPES",
    # Config
    "SharedSettings",
    "shared_settings",
    # Schemas
    "JobCreate",
    "JobResponse",
    "JobStatusResponse",
    "JobDB",
    # Services
    "S3Service",
    "get_s3_service",
    "S3ValidationError",
    "JobService",
]
