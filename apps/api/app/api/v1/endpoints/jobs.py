"""Job management endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from dubwizard_shared import JobStatus
from app.schemas.job import JobCreate, JobResponse, JobStatusResponse
from app.schemas.upload import CreateJobRequest, UploadResponse, DownloadResponse, DownloadFile, SubtitleFiles
from app.schemas.response import StandardResponse, ErrorDetail
from app.services.job_service import JobService
from app.services.s3_service import get_s3_service, S3ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=StandardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new dubbing job",
    description="Create a new job and get presigned upload URL for video",
    responses={
        201: {
            "description": "Job created successfully",
            "content": {
                "application/json": {
                    "example": {
                   "success": True,
                        "data": {
                            "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
                            "upload_url": "https://s3.amazonaws.com/bucket/uploads/uuid.mp4?signature=...",
                            "s3_key": "uploads/550e8400-e29b-41d4-a716-446655440000.mp4",
                            "expires_in": 900,
                            "status": "created",
                        },
                        "error": None,
                    }
                }
            },
        },
        400: {"description": "Invalid input data"},
        422: {"description": "Validation error"},
    },
)
async def create_job(
    request: CreateJobRequest,
    db: Session = Depends(get_db),
):
    """
    Create a new dubbing job.

    This endpoint:
    1. Validates the upload request (file size, type, format)
    2. Generates a presigned S3 upload URL
    3. Creates a job record in the database
    4. Returns job ID and upload URL

    The client should:
    1. Call this endpoint to get upload URL
    2. Upload video directly to S3 using the presigned URL
    3. Call POST /jobs/{job_id}/enqueue to start processing
    """
    try:
        s3_service = get_s3_service()

        # Generate presigned upload URL with validation
        upload_url, s3_key = s3_service.generate_presigned_upload_url(
            filename=request.filename,
            content_type=request.content_type,
            file_size=request.file_size,
            expires_in=900,  # 15 minutes
        )

        # Create job data from request
        job_data = JobCreate(
            source_language=request.source_language,
            target_language=request.target_language,
            voice_id=request.voice_id,
        )

        # Create job in database
        job_service = JobService(db)
        job = job_service.create_job(job_data, s3_key)

        return {
            "success": True,
            "data": {
                "job_id": job.id,
                "upload_url": upload_url,
                "s3_key": s3_key,
                "expires_in": 900,
                "status": job.status,
            },
            "error": None,
        }

    except S3ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job",
        )


@router.post(
    "/{job_id}/enqueue",
    response_model=StandardResponse,
    summary="Enqueue job for processing",
    description="Mark job as queued to start dubbing process",
    responses={
        200: {
            "description": "Job enqueued successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
                            "status": "queued",
                            "message": "Job queued for processing",
                        },
                        "error": None,
                    }
                }
            },
        },
        404: {"description": "Job not found"},
    },
)
async def enqueue_job(job_id: str, db: Session = Depends(get_db)):
    """
    Enqueue a job for processing.

    Call this endpoint after successfully uploading the video to S3.
    The worker will pick up queued jobs and process them.
    """
    job_service = JobService(db)
    job = job_service.enqueue_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "data": None,
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job with ID {job_id} not found",
                    "details": None,
                },
            },
        )

    logger.info(f"Enqueued job: {job_id}")

    return {
        "success": True,
        "data": {
            "job_id": job.id,
            "status": job.status,
            "message": "Job queued for processing",
        },
        "error": None,
    }


@router.get(
    "/{job_id}",
    response_model=StandardResponse,
    summary="Get job status",
    description="Retrieve current status and progress of a dubbing job",
    responses={
        200: {
            "description": "Job status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
                            "status": "processing",
                            "progress": 50,
                            "source_language": "english",
                            "target_language": "hindi",
                            "voice_id": "21m00Tcm4TlvDq8ikWAM",
                            "video_duration_seconds": 45.5,
                            "error_message": None,
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:31:30Z",
                            "completed_at": None,
                        },
                        "error": None,
                    }
                }
            },
        },
        404: {"description": "Job not found"},
    },
)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get job status and progress.

    Poll this endpoint to track job progress. Status values:
    - created: Job created, waiting for upload
    - queued: Job queued for processing
    - processing: Job is being processed
    - transcribing: Transcribing audio (0-25%)
    - translating: Translating text (25-50%)
    - synthesizing: Generating speech (50-75%)
    - processing_video: Muxing audio (75-100%)
    - done: Job completed successfully
    - failed: Job failed (check error_message)
    """
    job_service = JobService(db)
    job = job_service.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "data": None,
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job with ID {job_id} not found",
                    "details": None,
                },
            },
        )

    return {
        "success": True,
        "data": {
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress,
            "source_language": job.source_language,
            "target_language": job.target_language,
            "voice_id": job.voice_id,
            "video_duration_seconds": job.video_duration_seconds,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
        "error": None,
    }


@router.get(
    "/{job_id}/download",
    response_model=StandardResponse,
    summary="Get download URLs",
    description="Get presigned download URLs for completed job outputs",
    responses={
        200: {
            "description": "Download URLs generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "video": {
                                "url": "https://s3.amazonaws.com/bucket/outputs/job_uuid_dubbed.mp4?signature=...",
                                "filename": "dubbed_video.mp4",
                                "size_bytes": 45678900,
                                "expires_in": 3600,
                            },
                            "subtitles": {
                                "source": {
                                    "url": "https://s3.amazonaws.com/bucket/subtitles/job_uuid_source.srt?signature=...",
                                    "filename": "subtitles_english.srt",
                                    "size_bytes": 2048,
                                    "expires_in": 3600,
                                },
                                "target": {
                                    "url": "https://s3.amazonaws.com/bucket/subtitles/job_uuid_target.srt?signature=...",
                                    "filename": "subtitles_hindi.srt",
                                    "size_bytes": 2156,
                                    "expires_in": 3600,
                                },
                            },
                        },
                        "error": None,
                    }
                }
            },
        },
        404: {"description": "Job not found"},
        400: {"description": "Job not completed yet"},
    },
)
async def get_download_urls(job_id: str, db: Session = Depends(get_db)):
    """
    Get presigned download URLs for job outputs.

    Only available when job status is 'done'.
    URLs expire after 1 hour.
    """
    job_service = JobService(db)
    job = job_service.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "data": None,
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job with ID {job_id} not found",
                    "details": None,
                },
            },
        )

    if job.status != JobStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed yet. Current status: {job.status}",
        )

    try:
        s3_service = get_s3_service()

        # Generate download URLs
        urls = s3_service.generate_output_download_urls(job_id, expires_in=3600)

        # Get file sizes
        sizes = s3_service.get_output_file_sizes(job_id)

        return {
            "success": True,
            "data": {
                "video": {
                    "url": urls["video"],
                    "filename": f"{job_id}_dubbed.mp4",
                    "size_bytes": sizes["video"],
                    "expires_in": 3600,
                },
                "subtitles": {
                    "source": {
                        "url": urls["source_subtitle"],
                        "filename": f"{job_id}_english.srt",
                        "size_bytes": sizes["source_subtitle"],
                        "expires_in": 3600,
                    },
                    "target": {
                        "url": urls["target_subtitle"],
                        "filename": f"{job_id}_hindi.srt",
                        "size_bytes": sizes["target_subtitle"],
                        "expires_in": 3600,
                    },
                },
            },
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to generate download URLs for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URLs",
        )


@router.delete(
    "/{job_id}",
    response_model=StandardResponse,
    summary="Delete job",
    description="Cancel or delete a job",
    responses={
        200: {
            "description": "Job deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {"job_id": "job_550e8400-e29b-41d4-a716-446655440000", "deleted": True},
                        "error": None,
                    }
                }
            },
        },
    },
)
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    """
    Delete a job.

    This endpoint is idempotent - returns success even if job doesn't exist.
    """
    job_service = JobService(db)
    deleted = job_service.delete_job(job_id)

    return {
        "success": True,
        "data": {"job_id": job_id, "deleted": deleted},
        "error": None,
    }
