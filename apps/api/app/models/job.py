"""Job database model wrapper - re-exports from shared package."""

from dubwizard_shared import Job, Base, JobStatus

__all__ = ["Job", "Base", "JobStatus"]
