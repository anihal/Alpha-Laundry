"""
Base Pydantic schemas for common patterns
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base schema with common configuration
    """

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """
    Schema for models with timestamp fields
    """

    created_at: datetime
    updated_at: datetime


class ResponseBase(BaseSchema):
    """
    Base response schema
    """

    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """
    Error response schema
    """

    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
