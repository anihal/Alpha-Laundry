"""
Pydantic schemas for Admin models
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from .base import BaseSchema, TimestampSchema


# =====================================================
# ADMIN SCHEMAS
# =====================================================

RoleType = Literal["admin", "super_admin", "operator"]


class AdminBase(BaseSchema):
    """Base admin schema"""

    username: str = Field(..., min_length=3, max_length=50, description="Admin username")
    email: Optional[EmailStr] = Field(None, description="Admin email")
    role: RoleType = Field("admin", description="Admin role")


class AdminCreate(AdminBase):
    """Schema for creating a new admin"""

    password: str = Field(..., min_length=8, description="Admin password (min 8 characters)")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class AdminUpdate(BaseSchema):
    """Schema for updating admin information"""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role: Optional[RoleType] = None
    is_active: Optional[bool] = None


class AdminResponse(AdminBase, TimestampSchema):
    """Schema for admin response"""

    id: int
    is_active: bool
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminPasswordChange(BaseSchema):
    """Schema for admin password change"""

    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class AdminDashboard(BaseSchema):
    """Schema for admin dashboard data"""

    pending_requests: list
    processing_requests: list
    total_pending: int
    total_processing: int
    total_completed_today: int


# =====================================================
# EXPORTS
# =====================================================

__all__ = [
    "AdminBase",
    "AdminCreate",
    "AdminUpdate",
    "AdminResponse",
    "AdminPasswordChange",
    "AdminDashboard",
    "RoleType",
]
