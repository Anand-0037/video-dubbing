"""Worker main loop for processing dubbing jobs."""

import logging
import os
import sys
import signal
import time
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dubwizard_shared import JobStatus, Job, Base, JobService, get_s3_service

from worker.services.ai_service import AIService
from worker.tasks.process_job import JobProcessor, JobProcessingError
from dubwizard_shared.config import shared_settings as settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class Worker:
    """Background worker for processing dubbing jobs."""

    # Polling interval in seconds
    POLL_INTERVAL = 5

    def __init__(self):
        """Initialize worker with services."""
        self.running = False

        # Database setup
        database_url = os.getenv("DATABASE_URL", "sqlite:///./dubwizard.db")
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # S3 service
        self.s3_service = get_s3_service()

        # AI service
        self.ai_service = AIService()

        logger.info("Worker initialized")

    def get_db_session(self):
        """Get a new database session."""
        return self.SessionLocal()

    def process_next_job(self) -> bool:
        """
        Process the next pending job.

        Returns:
            True if a job was processed, False if no jobs available
        """
        db = self.get_db_session()

        try:
            job_service = JobService(db)

            # Get next pending job
            job = job_service.get_next_pending_job()

            if not job:
                return False

            logger.info(f"Processing job: {job.id}")

            # Mark job as processing
            job_service.update_job_status(job.id, JobStatus.PROCESSING, 0)

            # Create processor and process job
            processor = JobProcessor(
                s3_service=self.s3_service,
                job_service=job_service,
                ai_service=self.ai_service,
            )

            try:
                processor.process_job(job.id)
                return True

            except JobProcessingError as e:
                logger.error(f"Job {job.id} failed: {e}")
                # Job is already marked as failed by processor
                return True

        finally:
            db.close()

    def run(self):
        """Run the worker main loop."""
        logger.info("Starting worker...")
        self.running = True

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        while self.running:
            try:
                # Process next job
                job_processed = self.process_next_job()

                if not job_processed:
                    # No jobs available, wait before polling again
                    logger.debug(f"No pending jobs, waiting {self.POLL_INTERVAL}s...")
                    time.sleep(self.POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                # Wait before retrying
                time.sleep(self.POLL_INTERVAL)

        logger.info("Worker stopped")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def stop(self):
        """Stop the worker."""
        self.running = False


def main():
    """Main entry point for worker."""
    logger.info("DubWizard Worker starting...")

    # Validate required environment variables via settings
    # Pydantic will have already validated presence if they are not Optional
    # but we can do a quick check here if we want to be explicit.
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Create and run worker
    worker = Worker()
    worker.run()


if __name__ == "__main__":
    main()
