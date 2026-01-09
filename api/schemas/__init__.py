"""
Pydantic schemas for API request/response validation
"""

from .base import BaseSchema, TimestampSchema, ResponseBase, ErrorResponse
from .user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserQuotaUpdate,
    UserDashboard,
    UserLogin,
)
from .admin import (
    AdminBase,
    AdminCreate,
    AdminUpdate,
    AdminResponse,
    AdminPasswordChange,
    AdminDashboard,
    RoleType,
)
from .laundry_job import (
    LaundryJobBase,
    LaundryJobCreate,
    LaundryJobUpdate,
    LaundryJobStatusUpdate,
    LaundryJobResponse,
    LaundryJobWithUser,
    LaundryJobList,
    LaundryJobStats,
    SubmitRequestRequest,
    SubmitRequestResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
    StatusType,
    PriorityType,
)
from .subscription import (
    SubscriptionBase,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionWithUser,
    PlanType,
)
from .auth import (
    LoginRequest,
    LoginResponse,
    TokenData,
    VerifyTokenResponse,
    RegisterAdminRequest,
    RegisterAdminResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    UserType,
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampSchema",
    "ResponseBase",
    "ErrorResponse",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserQuotaUpdate",
    "UserDashboard",
    "UserLogin",
    # Admin
    "AdminBase",
    "AdminCreate",
    "AdminUpdate",
    "AdminResponse",
    "AdminPasswordChange",
    "AdminDashboard",
    "RoleType",
    # Laundry Job
    "LaundryJobBase",
    "LaundryJobCreate",
    "LaundryJobUpdate",
    "LaundryJobStatusUpdate",
    "LaundryJobResponse",
    "LaundryJobWithUser",
    "LaundryJobList",
    "LaundryJobStats",
    "SubmitRequestRequest",
    "SubmitRequestResponse",
    "UpdateStatusRequest",
    "UpdateStatusResponse",
    "StatusType",
    "PriorityType",
    # Subscription
    "SubscriptionBase",
    "SubscriptionCreate",
    "SubscriptionUpdate",
    "SubscriptionResponse",
    "SubscriptionWithUser",
    "PlanType",
    # Auth
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
