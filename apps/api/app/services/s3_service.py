"""S3 service wrapper - re-exports from shared package."""

from dubwizard_shared import S3Service, get_s3_service, S3ValidationError

__all__ = ["S3Service", "get_s3_service", "S3ValidationError"]
