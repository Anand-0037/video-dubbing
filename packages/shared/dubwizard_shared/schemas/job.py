"""Job-related Pydantic schemas shared across components."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from dubwizard_shared.models.job_status import JobStatus


class JobCreate(BaseModel):
    """Schema for creating a new job."""
    target_language: str = Field(..., description="Target language for dubbing")
    voice_id: str = Field(..., description="ElevenLabs voice ID")
    source_language: str = Field(default="english", description="Source language of video")

    @field_validator("target_language")
    @classmethod
    def validate_target_language(cls, v):
        """Validate target language is supported."""
        supported = ["hindi"]
        if v.lower() not in supported:
            raise ValueError(f"Target language must be one of: {', '.join(supported)}")
        return v.lower()

    @field_validator("source_language")
    @classmethod
    def validate_source_language(cls, v):
        """Validate source language."""
        if v.lower() != "english":
            raise ValueError("Source language must be 'english' for MVP")
        return v.lower()


class JobResponse(BaseModel):
    """Schema for job response."""
    job_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    source_language: str
    target_language: str
    voice_id: str
    video_duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    """Schema for job status response."""
    job_id: str
    status: JobStatus
    progress: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class JobDB(BaseModel):
    """Schema for job database model."""
    id: str
    status: JobStatus
    progress: int
    input_s3_key: str
    source_language: str
    target_language: str
    voice_id: str
    output_video_s3_key: Optional[str] = None
    source_subtitle_s3_key: Optional[str] = None
    target_subtitle_s3_key: Optional[str] = None
    video_duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
