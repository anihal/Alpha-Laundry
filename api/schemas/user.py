"""
Pydantic schemas for User/Student models
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
import re

from .base import BaseSchema, TimestampSchema


# =====================================================
# USER SCHEMAS
# =====================================================


class UserBase(BaseSchema):
    """Base user schema with common fields"""

    student_id: str = Field(..., min_length=6, max_length=20, description="Student ID (e.g., STU001)")
    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    email: Optional[EmailStr] = Field(None, description="Email address")

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, v: str) -> str:
        """Validate student ID format"""
        if not re.match(r"^STU\d{3,}$", v):
            raise ValueError("Student ID must be in format STU### (e.g., STU001)")
        return v


class UserCreate(UserBase):
    """Schema for creating a new user"""

    password: Optional[str] = Field(None, min_length=6, description="Password (optional)")
    remaining_quota: int = Field(30, ge=0, description="Initial quota")


class UserUpdate(BaseSchema):
    """Schema for updating user information"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    remaining_quota: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class UserResponse(UserBase, TimestampSchema):
    """Schema for user response"""

    id: int
    remaining_quota: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserQuotaUpdate(BaseSchema):
    """Schema for updating user quota"""

    student_id: str
    remaining_quota: int = Field(..., ge=0)


class UserDashboard(BaseSchema):
    """Schema for user dashboard data"""

    id: int
    student_id: str
    name: str
    email: Optional[str]
    remaining_quota: int
    total_requests: int
    pending_requests: int
    completed_requests: int
    recent_jobs: list


class UserLogin(BaseSchema):
    """Schema for user login"""

    student_id: str = Field(..., description="Student ID")
    password: Optional[str] = Field(None, description="Password (if enabled)")


# =====================================================
# EXPORTS
# =====================================================

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserQuotaUpdate",
    "UserDashboard",
    "UserLogin",
]
