"""Job service for managing dubbing jobs shared across components."""

import logging
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from dubwizard_shared.models.job import Job
from dubwizard_shared.models.job_status import JobStatus
from dubwizard_shared.schemas.job import JobCreate

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing job lifecycle and database operations."""

    def __init__(self, db: Session):
        """
        Initialize JobService with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_job(self, job_data: JobCreate, input_s3_key: str) -> Job:
        """Create a new dubbing job."""
        job_id = f"job_{uuid.uuid4()}"
        now = datetime.utcnow()

        job = Job(
            id=job_id,
            status=JobStatus.CREATED,
            progress=0,
            input_s3_key=input_s3_key,
            source_language=job_data.source_language,
            target_language=job_data.target_language,
            voice_id=job_data.voice_id,
            created_at=now,
            updated_at=now,
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info(f"Created job: {job_id}")
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Retrieve job by ID."""
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job:
            logger.debug(f"Retrieved job: {job_id}")
        else:
            logger.warning(f"Job not found: {job_id}")
        return job

    def update_job_status(
        self, job_id: str, status: JobStatus, progress: int
    ) -> Optional[Job]:
        """Update job status and progress."""
        job = self.get_job(job_id)
        if not job:
            return None

        job.status = status
        job.progress = progress
        job.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(job)

        logger.info(f"Updated job {job_id}: status={status}, progress={progress}")
        return job

    def enqueue_job(self, job_id: str) -> Optional[Job]:
        """Mark job as queued for processing."""
        return self.update_job_status(job_id, JobStatus.QUEUED, 0)

    def complete_job(
        self,
        job_id: str,
        output_video_key: str,
        source_subtitle_key: str,
        target_subtitle_key: str,
    ) -> Optional[Job]:
        """Mark job as completed with output keys."""
        job = self.get_job(job_id)
        if not job:
            return None

        job.status = JobStatus.DONE
        job.progress = 100
        job.output_video_s3_key = output_video_key
        job.source_subtitle_s3_key = source_subtitle_key
        job.target_subtitle_s3_key = target_subtitle_key
        job.completed_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(job)

        logger.info(f"Completed job: {job_id}")
        return job

    def fail_job(self, job_id: str, error_message: str) -> Optional[Job]:
        """Mark job as failed with error message."""
        job = self.get_job(job_id)
        if not job:
            return None

        job.status = JobStatus.FAILED
        job.error_message = error_message
        job.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(job)

        logger.error(f"Failed job {job_id}: {error_message}")
        return job

    def update_video_duration(self, job_id: str, duration: float) -> Optional[Job]:
        """Update video duration for a job."""
        job = self.get_job(job_id)
        if not job:
            return None

        job.video_duration_seconds = duration
        job.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(job)

        logger.info(f"Updated video duration for job {job_id}: {duration}s")
        return job

    def get_next_pending_job(self) -> Optional[Job]:
        """Get the oldest queued job for processing."""
        job = (
            self.db.query(Job)
            .filter(Job.status == JobStatus.QUEUED)
            .order_by(Job.created_at.asc())
            .first()
        )

        if job:
            logger.info(f"Found pending job: {job.id}")
        return job

    def list_jobs(
        self, status: Optional[JobStatus] = None, limit: int = 100
    ) -> List[Job]:
        """List jobs with optional status filter."""
        query = self.db.query(Job)

        if status:
            query = query.filter(Job.status == status)

        jobs = query.order_by(Job.created_at.desc()).limit(limit).all()

        logger.debug(f"Listed {len(jobs)} jobs")
        return jobs

    def delete_job(self, job_id: str) -> bool:
        """Delete a job from database."""
        job = self.get_job(job_id)
        if not job:
            return False

        self.db.delete(job)
        self.db.commit()

        logger.info(f"Deleted job: {job_id}")
        return True
