"""
Pydantic schemas for Laundry Job models
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

from .base import BaseSchema, TimestampSchema


# =====================================================
# LAUNDRY JOB SCHEMAS
# =====================================================

# Type definitions for validation
StatusType = Literal["submitted", "processing", "completed", "cancelled"]
PriorityType = Literal["low", "normal", "high", "urgent"]


class LaundryJobBase(BaseSchema):
    """Base laundry job schema"""

    num_clothes: int = Field(..., ge=1, le=50, description="Number of clothes (1-50)")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")
    priority: PriorityType = Field("normal", description="Job priority")


class LaundryJobCreate(LaundryJobBase):
    """Schema for creating a new laundry job"""

    student_id: str = Field(..., description="Student ID submitting the request")

    @field_validator("num_clothes")
    @classmethod
    def validate_num_clothes(cls, v: int) -> int:
        """Validate number of clothes"""
        if v < 1:
            raise ValueError("Number of clothes must be at least 1")
        if v > 50:
            raise ValueError("Number of clothes cannot exceed 50")
        return v


class LaundryJobUpdate(BaseSchema):
    """Schema for updating laundry job"""

    status: Optional[StatusType] = None
    priority: Optional[PriorityType] = None
    notes: Optional[str] = Field(None, max_length=500)
    started_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None


class LaundryJobStatusUpdate(BaseSchema):
    """Schema for updating job status (admin action)"""

    status: StatusType = Field(..., description="New status")

    @field_validator("status")
    @classmethod
    def validate_status_transition(cls, v: str) -> str:
        """Validate status value"""
        valid_statuses = ["submitted", "processing", "completed", "cancelled"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class LaundryJobResponse(LaundryJobBase, TimestampSchema):
    """Schema for laundry job response"""

    id: int
    user_id: int
    student_id: str
    status: StatusType
    submission_date: datetime
    started_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LaundryJobWithUser(LaundryJobResponse):
    """Schema for laundry job with user information"""

    student_name: Optional[str] = None
    remaining_quota: Optional[int] = None


class LaundryJobList(BaseSchema):
    """Schema for paginated laundry job list"""

    total: int
    page: int
    page_size: int
    jobs: list[LaundryJobResponse]


class LaundryJobStats(BaseSchema):
    """Schema for laundry job statistics"""

    total_jobs: int
    submitted: int
    processing: int
    completed: int
    cancelled: int
    total_clothes_processed: int


# =====================================================
# REQUEST/RESPONSE SCHEMAS
# =====================================================


class SubmitRequestRequest(BaseSchema):
    """Schema for student submitting a laundry request"""

    num_clothes: int = Field(..., ge=1, le=50, description="Number of clothes")
    notes: Optional[str] = Field(None, max_length=500)
    priority: PriorityType = Field("normal", description="Request priority")


class SubmitRequestResponse(BaseSchema):
    """Schema for submit request response"""

    success: bool = True
    message: str
    job_id: int
    remaining_quota: int
    job: LaundryJobResponse


class UpdateStatusRequest(BaseSchema):
    """Schema for admin updating request status"""

    request_id: int = Field(..., description="Laundry job ID")
    status: StatusType = Field(..., description="New status")


class UpdateStatusResponse(BaseSchema):
    """Schema for update status response"""

    success: bool = True
    message: str
    job: LaundryJobResponse


# =====================================================
# EXPORTS
# =====================================================

__all__ = [
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
]
