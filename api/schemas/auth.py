"""
Pydantic schemas for Authentication
"""

from typing import Optional, Literal
from pydantic import Field, field_validator

from .base import BaseSchema


# =====================================================
# AUTHENTICATION SCHEMAS
# =====================================================

UserType = Literal["student", "admin"]


class LoginRequest(BaseSchema):
    """Schema for login request"""

    username: str = Field(..., description="Student ID or Admin username")
    password: str = Field(..., description="Password")
    user_type: UserType = Field(..., description="User type: 'student' or 'admin'")


class LoginResponse(BaseSchema):
    """Schema for login response"""

    success: bool = True
    message: str = "Login successful"
    access_token: str
    token_type: str = "bearer"
    user_type: UserType
    user_id: int
    username: str  # student_id for students, username for admins


class TokenData(BaseSchema):
    """Schema for JWT token data"""

    user_id: int
    username: str
    user_type: UserType
    exp: Optional[int] = None


class VerifyTokenResponse(BaseSchema):
    """Schema for token verification response"""

    valid: bool
    user_id: int
    username: str
    user_type: UserType


class RegisterAdminRequest(BaseSchema):
    """Schema for admin registration"""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[str] = None

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


class RegisterAdminResponse(BaseSchema):
    """Schema for admin registration response"""

    success: bool = True
    message: str
    admin_id: int
    username: str


class PasswordResetRequest(BaseSchema):
    """Schema for password reset request"""

    username: str
    user_type: UserType


class PasswordResetConfirm(BaseSchema):
    """Schema for password reset confirmation"""

    token: str
    new_password: str = Field(..., min_length=8)


# =====================================================
# EXPORTS
# =====================================================

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "TokenData",
    "VerifyTokenResponse",
    "RegisterAdminRequest",
    "RegisterAdminResponse",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "UserType",
]
