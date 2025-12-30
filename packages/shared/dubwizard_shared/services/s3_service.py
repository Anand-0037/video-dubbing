"""S3 service for file storage and presigned URL generation shared across components."""

import logging
import time
import uuid
from typing import Optional
import boto3
from botocore.exceptions import ClientError

from dubwizard_shared.config import shared_settings as settings
from dubwizard_shared.constants import MAX_VIDEO_SIZE_MB, ALLOWED_CONTENT_TYPES, ALLOWED_VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


class S3ValidationError(Exception):
    """Custom exception for S3 validation errors."""
    pass


class S3Service:
    """Service for managing S3 operations and presigned URLs."""

    def __init__(self):
        """Initialize S3 client with credentials from settings."""
        self.is_dev = settings.USE_LOCAL_STORAGE
        if not self.is_dev:
            self.s3_client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        self.bucket_name = settings.S3_BUCKET_NAME
        self.local_storage_path = "/tmp/dubwizard_uploads"
        if self.is_dev:
            import os
            os.makedirs(self.local_storage_path, exist_ok=True)
        logger.info(f"S3Service initialized for bucket: {self.bucket_name} (Dev: {self.is_dev})")

    def generate_presigned_upload_url(
        self,
        filename: str,
        content_type: str = "video/mp4",
        file_size: int = 0,
        expires_in: int = 900,
    ) -> tuple[str, str]:
        """Generate presigned URL for uploading a file to S3."""
        # Validate file size
        max_size = MAX_VIDEO_SIZE_MB * 1024 * 1024  # Convert MB to bytes
        if file_size > max_size:
            raise S3ValidationError(
                f"File size exceeds maximum allowed size of {MAX_VIDEO_SIZE_MB}MB"
            )

        # Validate content type
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise S3ValidationError(
                f"Content type must be video/mp4. Received: {content_type}"
            )

        # Validate filename extension
        ext = filename.lower()[filename.rfind("."):] if "." in filename else ""
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise S3ValidationError(
                f"Filename must end with .mp4. Received: {filename}"
            )

        # Generate unique S3 key
        file_extension = filename.split(".")[-1] if "." in filename else "mp4"
        s3_key = f"uploads/{uuid.uuid4()}.{file_extension}"

        if self.is_dev:
            # Return local upload URL
            # Note: We use relative path /api/v1/... so it goes through proxy or direct based on frontend config
            # But the frontend axios client usage for upload might be direct axios, not the configured instance.
            # jobService.ts uses axios.put(presignedUrl).
            # If we return a relative URL, axios treats it relative to current page if not configured?
            # Actually jobService.ts uses `apiClient` for API calls but `axios.put` for upload.
            # Safest is to return full localhost URL for development.
            # Assuming backend is at localhost:8000
            host = f"http://localhost:8000"
            return f"{host}/api/v1/storage/upload/{s3_key}", s3_key

        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "ContentType": content_type,
                    "ContentLength": file_size,  # Enforce exact file size
                },
                ExpiresIn=expires_in,
            )

            logger.info(f"Generated presigned upload URL for: {s3_key} ({file_size} bytes)")
            return presigned_url, s3_key

        except ClientError as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            raise

    def generate_presigned_download_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
        filename: Optional[str] = None,
    ) -> str:
        """Generate presigned URL for downloading a file from S3."""
        if self.is_dev:
             host = f"http://localhost:8000"
             return f"{host}/api/v1/storage/download/{s3_key}"

        try:
            params = {
                "Bucket": self.bucket_name,
                "Key": s3_key,
            }

            # Add Content-Disposition header if filename provided
            if filename:
                params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )

            logger.info(f"Generated presigned download URL for: {s3_key}")
            return presigned_url

        except ClientError as e:
            logger.error(f"Failed to generate presigned download URL: {e}")
            raise

    def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3."""
        if self.is_dev:
            import os
            return os.path.exists(os.path.join(self.local_storage_path, s3_key))

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Error checking file existence: {e}")
            raise

    def get_file_size(self, s3_key: str) -> int:
        """Get file size in bytes."""
        if self.is_dev:
             import os
             try:
                return os.path.getsize(os.path.join(self.local_storage_path, s3_key))
             except OSError:
                return 0

        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return response["ContentLength"]
        except ClientError as e:
            logger.error(f"Failed to get file size for {s3_key}: {e}")
            raise

    def upload_file(self, file_path: str, s3_key: str) -> str:
        """Upload a file directly to S3."""
        if self.is_dev:
            import shutil
            import os
            dest_path = os.path.join(self.local_storage_path, s3_key)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(file_path, dest_path)
            logger.info(f"Uploaded file to Local Storage: {dest_path}")
            return s3_key

        self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
        logger.info(f"Uploaded file to S3: {s3_key}")
        return s3_key

    def download_file(self, s3_key: str, local_path: str) -> str:
        """Download a file from S3."""
        if self.is_dev:
            import shutil
            import os
            src_path = os.path.join(self.local_storage_path, s3_key)
            shutil.copy2(src_path, local_path)
            logger.info(f"Downloaded file from Local Storage: {src_path} to {local_path}")
            return local_path

        self.s3_client.download_file(self.bucket_name, s3_key, local_path)
        logger.info(f"Downloaded file from S3: {s3_key} to {local_path}")
        return local_path

    def upload_file_with_retry(self, file_path: str, s3_key: str, max_retries: int = 3) -> str:
        """Upload a file directly to S3 with retry logic."""
        if self.is_dev:
            return self.upload_file(file_path, s3_key)

        for attempt in range(max_retries + 1):
            try:
                self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
                logger.info(f"Uploaded file to S3: {s3_key} (attempt {attempt + 1})")
                return s3_key
            except ClientError as e:
                if attempt == max_retries:
                    logger.error(f"Failed to upload file to S3 after {max_retries + 1} attempts: {e}")
                    raise

                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Upload attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

    def download_file_with_retry(self, s3_key: str, local_path: str, max_retries: int = 3) -> str:
        """Download a file from S3 with retry logic."""
        if self.is_dev:
            return self.download_file(s3_key, local_path)

        for attempt in range(max_retries + 1):
            try:
                self.s3_client.download_file(self.bucket_name, s3_key, local_path)
                logger.info(f"Downloaded file from S3: {s3_key} to {local_path} (attempt {attempt + 1})")
                return local_path
            except ClientError as e:
                if attempt == max_retries:
                    logger.error(f"Failed to download file from S3 after {max_retries + 1} attempts: {e}")
                    raise

                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Download attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

    def generate_output_download_urls(
        self,
        job_id: str,
        expires_in: int = 3600,
    ) -> dict[str, str]:
        """Generate presigned download URLs for all output files of a job."""
        try:
            # Generate URLs for all output files
            video_url = self.generate_presigned_download_url(
                s3_key=f"outputs/{job_id}_dubbed.mp4",
                expires_in=expires_in,
                filename=f"{job_id}_dubbed.mp4"
            )

            source_subtitle_url = self.generate_presigned_download_url(
                s3_key=f"subtitles/{job_id}_source.srt",
                expires_in=expires_in,
                filename=f"{job_id}_english.srt"
            )

            target_subtitle_url = self.generate_presigned_download_url(
                s3_key=f"subtitles/{job_id}_target.srt",
                expires_in=expires_in,
                filename=f"{job_id}_hindi.srt"
            )

            return {
                "video": video_url,
                "source_subtitle": source_subtitle_url,
                "target_subtitle": target_subtitle_url,
            }

        except ClientError as e:
            logger.error(f"Failed to generate output download URLs for job {job_id}: {e}")
            raise

    def get_output_file_sizes(self, job_id: str) -> dict[str, int]:
        """Get file sizes for all output files of a job."""
        try:
            video_size = self.get_file_size(f"outputs/{job_id}_dubbed.mp4")
            source_subtitle_size = self.get_file_size(f"subtitles/{job_id}_source.srt")
            target_subtitle_size = self.get_file_size(f"subtitles/{job_id}_target.srt")

            return {
                "video": video_size,
                "source_subtitle": source_subtitle_size,
                "target_subtitle": target_subtitle_size,
            }

        except ClientError as e:
            logger.error(f"Failed to get output file sizes for job {job_id}: {e}")
            raise

    def delete_file(self, s3_key: str) -> None:
        """Delete a file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted file from S3: {s3_key}")
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise


# Singleton instance
_s3_service: Optional[S3Service] = None


def get_s3_service() -> S3Service:
    """Get or create S3Service singleton instance."""
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service
