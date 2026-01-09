"""
Pydantic schemas for Subscription models
"""

from datetime import date, datetime
from typing import Optional, Literal
from pydantic import Field, field_validator, ConfigDict

from .base import BaseSchema, TimestampSchema


# =====================================================
# SUBSCRIPTION SCHEMAS
# =====================================================

PlanType = Literal["basic", "premium", "unlimited"]


class SubscriptionBase(BaseSchema):
    """Base subscription schema"""

    plan_type: PlanType = Field("basic", description="Subscription plan type")
    quota_limit: int = Field(..., ge=1, description="Quota limit for the plan")


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription"""

    user_id: int = Field(..., description="User ID")
    start_date: date = Field(default_factory=date.today, description="Subscription start date")
    end_date: Optional[date] = Field(None, description="Subscription end date")

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[date], info) -> Optional[date]:
        """Validate end date is after start date"""
        if v and "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class SubscriptionUpdate(BaseSchema):
    """Schema for updating subscription"""

    plan_type: Optional[PlanType] = None
    quota_limit: Optional[int] = Field(None, ge=1)
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class SubscriptionResponse(SubscriptionBase, TimestampSchema):
    """Schema for subscription response"""

    id: int
    user_id: int
    start_date: date
    end_date: Optional[date]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SubscriptionWithUser(SubscriptionResponse):
    """Schema for subscription with user information"""

    student_id: str
    student_name: str


# =====================================================
# EXPORTS
# =====================================================

__all__ = [
    "SubscriptionBase",
    "SubscriptionCreate",
    "SubscriptionUpdate",
    "SubscriptionResponse",
    "SubscriptionWithUser",
    "PlanType",
]
