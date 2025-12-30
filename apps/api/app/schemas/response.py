"""Standard API response schemas."""

from typing import Optional, Any, Dict
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Error detail schema."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class StandardResponse(BaseModel):
    """Standard API response format."""
    success: bool
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None


class SuccessResponse(StandardResponse):
    """Success response helper."""
    success: bool = True
    error: None = None


class ErrorResponse(StandardResponse):
    """Error response helper."""
    success: bool = False
    data: None = None
