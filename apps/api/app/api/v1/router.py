"""API v1 router configuration."""

from fastapi import APIRouter
from app.api.v1.endpoints import jobs, storage
from dubwizard_shared.config import shared_settings

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

# Include storage routes for local development or when USE_LOCAL_STORAGE is enabled
if shared_settings.USE_LOCAL_STORAGE or shared_settings.ENVIRONMENT == "development":
    api_router.include_router(storage.router, prefix="/storage", tags=["storage"])
