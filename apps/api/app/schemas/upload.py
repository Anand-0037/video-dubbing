"""Upload-related Pydantic schemas."""

from pydantic import BaseModel, Field, validator


class UploadRequest(BaseModel):
    """Schema for requesting presigned upload URL."""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of file")
    file_size: int = Field(..., description="File size in bytes", gt=0)

    @validator("filename")
    def validate_filename(cls, v):
        """Validate filename ends with .mp4."""
        if not v.lower().endswith(".mp4"):
            raise ValueError("Only MP4 files are supported")
        return v

    @validator("content_type")
    def validate_content_type(cls, v):
        """Validate content type is video/mp4."""
        if v != "video/mp4":
            raise ValueError("Content type must be video/mp4")
        return v

    @validator("file_size")
    def validate_file_size(cls, v):
        """Validate file size is within limits."""
        max_size = 100 * 1024 * 1024  # 100MB in bytes
        if v > max_size:
            raise ValueError(f"File size exceeds maximum of 100MB")
        return v


class UploadResponse(BaseModel):
    """Schema for presigned upload URL response."""
    upload_url: str = Field(..., description="Presigned S3 upload URL")
    s3_key: str = Field(..., description="S3 key for the uploaded file")
    expires_in: int = Field(..., description="URL expiration time in seconds")


class DownloadFile(BaseModel):
    """Schema for a downloadable file."""
    url: str = Field(..., description="Presigned download URL")
    filename: str = Field(..., description="Suggested filename")
    size_bytes: int = Field(..., description="File size in bytes")
    expires_in: int = Field(..., description="URL expiration time in seconds")


class SubtitleFiles(BaseModel):
    """Schema for subtitle files."""
    source: DownloadFile
    target: DownloadFile


class DownloadResponse(BaseModel):
    """Schema for download URLs response."""
    video: DownloadFile
    subtitles: SubtitleFiles


class CreateJobRequest(BaseModel):
    """Combined schema for creating a job with upload info."""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of file")
    file_size: int = Field(..., description="File size in bytes", gt=0)
    target_language: str = Field(..., description="Target language for dubbing")
    voice_id: str = Field(..., description="ElevenLabs voice ID")
    source_language: str = Field(default="english", description="Source language of video")

    @validator("filename")
    def validate_filename(cls, v):
        """Validate filename ends with .mp4."""
        if not v.lower().endswith(".mp4"):
            raise ValueError("Only MP4 files are supported")
        return v

    @validator("content_type")
    def validate_content_type(cls, v):
        """Validate content type is video/mp4."""
        if v != "video/mp4":
            raise ValueError("Content type must be video/mp4")
        return v

    @validator("file_size")
    def validate_file_size(cls, v):
        """Validate file size is within limits."""
        max_size = 100 * 1024 * 1024  # 100MB in bytes
        if v > max_size:
            raise ValueError(f"File size exceeds maximum of 100MB")
        return v

    @validator("target_language")
    def validate_target_language(cls, v):
        """Validate target language is supported."""
        supported = ["hindi"]
        if v.lower() not in supported:
            raise ValueError(f"Target language must be one of: {', '.join(supported)}")
        return v.lower()

    @validator("source_language")
    def validate_source_language(cls, v):
        """Validate source language."""
        if v.lower() != "english":
            raise ValueError("Source language must be 'english' for MVP")
        return v.lower()
