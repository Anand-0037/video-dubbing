
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dubwizard_shared.models.job import Job, JobStatus
from dubwizard_shared.config import shared_settings

engine = create_engine(shared_settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

print("--- Resetting Failed Jobs ---")
failed_jobs = session.query(Job).filter(Job.status.in_([JobStatus.FAILED, JobStatus.PROCESSING])).all()
for job in failed_jobs:
    print(f"Resetting Job {job.id} from {job.status} to QUEUED")
    job.status = JobStatus.QUEUED
    job.progress = 0
    job.error_message = None

session.commit()

print("--- Current Jobs ---")
jobs = session.query(Job).all()
for job in jobs:
    print(f"ID: {job.id}, Status: {job.status}")

session.close()
