"""Test Job model."""

import pytest
from datetime import datetime
import uuid

from app.models.job import Job, JobStatus


@pytest.mark.unit
def test_create_job(db_session):
    """Test creating a job in database."""
    job_id = f"job_{uuid.uuid4()}"
    job = Job(
        id=job_id,
        status=JobStatus.CREATED,
        progress=0,
        input_s3_key="uploads/test.mp4",
        source_language="english",
        target_language="hindi",
        voice_id="test_voice_id",
    )

    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.id == job_id
    assert job.status == JobStatus.CREATED
    assert job.progress == 0
    assert job.input_s3_key == "uploads/test.mp4"
    assert job.source_language == "english"
    assert job.target_language == "hindi"
    assert job.voice_id == "test_voice_id"
    assert job.created_at is not None
    assert job.updated_at is not None
    assert job.completed_at is None


@pytest.mark.unit
def test_query_job(db_session):
    """Test querying a job from database."""
    job_id = f"job_{uuid.uuid4()}"
    job = Job(
        id=job_id,
        status=JobStatus.QUEUED,
        progress=0,
        input_s3_key="uploads/test.mp4",
        source_language="english",
        target_language="hindi",
        voice_id="test_voice_id",
    )

    db_session.add(job)
    db_session.commit()

    # Query the job
    retrieved_job = db_session.query(Job).filter(Job.id == job_id).first()

    assert retrieved_job is not None
    assert retrieved_job.id == job_id
    assert retrieved_job.status == JobStatus.QUEUED


@pytest.mark.unit
def test_update_job_status(db_session):
    """Test updating job status."""
    job_id = f"job_{uuid.uuid4()}"
    job = Job(
        id=job_id,
        status=JobStatus.CREATED,
        progress=0,
        input_s3_key="uploads/test.mp4",
        source_language="english",
        target_language="hindi",
        voice_id="test_voice_id",
    )

    db_session.add(job)
    db_session.commit()

    # Update status
    job.status = JobStatus.PROCESSING
    job.progress = 50
    db_session.commit()
    db_session.refresh(job)

    assert job.status == JobStatus.PROCESSING
    assert job.progress == 50


@pytest.mark.unit
def test_job_with_outputs(db_session):
    """Test job with output files."""
    job_id = f"job_{uuid.uuid4()}"
    job = Job(
        id=job_id,
        status=JobStatus.DONE,
        progress=100,
        input_s3_key="uploads/test.mp4",
        source_language="english",
        target_language="hindi",
        voice_id="test_voice_id",
        output_video_s3_key="outputs/test_dubbed.mp4",
        source_subtitle_s3_key="subtitles/test_en.srt",
        target_subtitle_s3_key="subtitles/test_hi.srt",
        video_duration_seconds=45.5,
        completed_at=datetime.utcnow(),
    )

    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.output_video_s3_key == "outputs/test_dubbed.mp4"
    assert job.source_subtitle_s3_key == "subtitles/test_en.srt"
    assert job.target_subtitle_s3_key == "subtitles/test_hi.srt"
    assert job.video_duration_seconds == 45.5
    assert job.completed_at is not None
