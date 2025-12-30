"""Shared constants for DubWizard application."""

# File size limits
MAX_VIDEO_SIZE_MB = 100
MAX_VIDEO_SIZE_BYTES = MAX_VIDEO_SIZE_MB * 1024 * 1024  # 100MB in bytes

# Video duration limits
MAX_VIDEO_DURATION_SECONDS = 60  # 60 seconds for hackathon demo

# Supported formats
ALLOWED_VIDEO_EXTENSIONS = {".mp4"}
ALLOWED_CONTENT_TYPES = {"video/mp4"}

# Supported languages
SUPPORTED_SOURCE_LANGUAGES = ["english"]
SUPPORTED_TARGET_LANGUAGES = ["hindi"]

# S3 paths
S3_UPLOADS_PREFIX = "uploads/"
S3_OUTPUTS_PREFIX = "outputs/"
S3_SUBTITLES_PREFIX = "subtitles/"

# Presigned URL expiration times (in seconds)
UPLOAD_URL_EXPIRY = 900  # 15 minutes
DOWNLOAD_URL_EXPIRY = 3600  # 1 hour
