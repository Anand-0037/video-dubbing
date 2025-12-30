"""Job database model shared across components."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.orm import declarative_base

# Shared declarative base
Base = declarative_base()

from dubwizard_shared.models.job_status import JobStatus

class Job(Base):
    """Job model for tracking dubbing jobs."""

    __tablename__ = "jobs"

    # Primary key
    id = Column(String, primary_key=True, index=True)

    # Status and progress
    status = Column(String, nullable=False, default=JobStatus.CREATED, index=True)
    progress = Column(Integer, nullable=False, default=0)

    # Input configuration
    input_s3_key = Column(String, nullable=False)
    source_language = Column(String, nullable=False, default="english")
    target_language = Column(String, nullable=False)
    voice_id = Column(String, nullable=False)

    # Output files
    output_video_s3_key = Column(String, nullable=True)
    source_subtitle_s3_key = Column(String, nullable=True)
    target_subtitle_s3_key = Column(String, nullable=True)

    # Metadata
    video_duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Job(id={self.id}, status={self.status}, progress={self.progress})>"
