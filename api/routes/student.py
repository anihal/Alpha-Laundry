"""
Student routes for laundry request management
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..database import get_db, User, LaundryJob
from ..schemas import (
    UserDashboard,
    SubmitRequestRequest,
    SubmitRequestResponse,
    LaundryJobResponse,
    LaundryJobList,
)
from ..utils import extract_user_from_token

router = APIRouter(prefix="/student", tags=["Student"])


# =====================================================
# DEPENDENCY: Get Current Student
# =====================================================


def get_current_student(
    token: str = Query(..., description="JWT access token"), db: Session = Depends(get_db)
):
    """
    Dependency to get current authenticated student from token
    """
    user_info = extract_user_from_token(token)

    if not user_info or user_info.get("user_type") != "student":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    student = db.query(User).filter(User.id == user_info["user_id"]).first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    if not student.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    return student


# =====================================================
# DASHBOARD ENDPOINT
# =====================================================


@router.get("/dashboard", response_model=UserDashboard)
def get_dashboard(
    student: User = Depends(get_current_student), db: Session = Depends(get_db)
):
    """
    Get student dashboard with quota and recent requests

    Returns:
        UserDashboard: Student information and request statistics
    """

    # Get request counts
    total_requests = db.query(LaundryJob).filter(LaundryJob.user_id == student.id).count()

    pending_requests = (
        db.query(LaundryJob)
        .filter(LaundryJob.user_id == student.id, LaundryJob.status == "submitted")
        .count()
    )

    completed_requests = (
        db.query(LaundryJob)
        .filter(LaundryJob.user_id == student.id, LaundryJob.status == "completed")
        .count()
    )

    # Get recent jobs (last 5)
    recent_jobs = (
        db.query(LaundryJob)
        .filter(LaundryJob.user_id == student.id)
        .order_by(LaundryJob.submission_date.desc())
        .limit(5)
        .all()
    )

    recent_jobs_data = [
        {
            "id": job.id,
            "num_clothes": job.num_clothes,
            "status": job.status,
            "submission_date": job.submission_date.isoformat(),
        }
        for job in recent_jobs
    ]

    return UserDashboard(
        id=student.id,
        student_id=student.student_id,
        name=student.name,
        email=student.email,
        remaining_quota=student.remaining_quota,
        total_requests=total_requests,
        pending_requests=pending_requests,
        completed_requests=completed_requests,
        recent_jobs=recent_jobs_data,
    )


# =====================================================
# SUBMIT REQUEST ENDPOINT (with transaction handling)
# =====================================================


@router.post("/submit", response_model=SubmitRequestResponse)
def submit_request(
    request_data: SubmitRequestRequest,
    student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """
    Submit a new laundry request

    **IMPORTANT**: This endpoint implements proper transaction handling to ensure
    the remaining_quota is correctly decremented atomically.

    - **num_clothes**: Number of clothes to launder (1-50)
    - **notes**: Optional notes for the request
    - **priority**: Request priority (low, normal, high, urgent)

    Returns:
        SubmitRequestResponse: Created job and updated quota information
    """

    try:
        # Start transaction (implicit with session)
        db.begin_nested()

        # Validate quota
        if student.remaining_quota < request_data.num_clothes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient quota. You have {student.remaining_quota} clothes remaining, "
                f"but requested {request_data.num_clothes}",
            )

        if request_data.num_clothes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of clothes must be greater than 0",
            )

        if request_data.num_clothes > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of clothes cannot exceed 50 per request",
            )

        # Create laundry job
        new_job = LaundryJob(
            user_id=student.id,
            student_id=student.student_id,
            num_clothes=request_data.num_clothes,
            status="submitted",
            priority=request_data.priority,
            notes=request_data.notes,
            submission_date=datetime.utcnow(),
        )

        db.add(new_job)

        # Decrement remaining quota - CRITICAL LOGIC
        # This happens atomically within the transaction
        student.remaining_quota -= request_data.num_clothes

        # Commit transaction
        db.commit()
        db.refresh(new_job)
        db.refresh(student)

        # Return response
        return SubmitRequestResponse(
            message=f"Request submitted successfully. {student.remaining_quota} clothes remaining in quota.",
            job_id=new_job.id,
            remaining_quota=student.remaining_quota,
            job=LaundryJobResponse.model_validate(new_job),
        )

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while submitting request: {str(e)}",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


# =====================================================
# HISTORY ENDPOINT
# =====================================================


@router.get("/history", response_model=LaundryJobList)
def get_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str = Query(None, description="Filter by status"),
    student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """
    Get student's laundry request history with pagination

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status_filter**: Optional status filter (submitted, processing, completed, cancelled)

    Returns:
        LaundryJobList: Paginated list of laundry jobs
    """

    # Build query
    query = db.query(LaundryJob).filter(LaundryJob.user_id == student.id)

    # Apply status filter if provided
    if status_filter:
        valid_statuses = ["submitted", "processing", "completed", "cancelled"]
        if status_filter not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            )
        query = query.filter(LaundryJob.status == status_filter)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    jobs = query.order_by(LaundryJob.submission_date.desc()).offset(offset).limit(page_size).all()

    # Convert to response models
    job_responses = [LaundryJobResponse.model_validate(job) for job in jobs]

    return LaundryJobList(
        total=total,
        page=page,
        page_size=page_size,
        jobs=job_responses,
    )


# =====================================================
# GET SINGLE JOB ENDPOINT
# =====================================================


@router.get("/job/{job_id}", response_model=LaundryJobResponse)
def get_job(
    job_id: int,
    student: User = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """
    Get details of a specific laundry job

    - **job_id**: ID of the laundry job

    Returns:
        LaundryJobResponse: Job details
    """

    job = (
        db.query(LaundryJob)
        .filter(LaundryJob.id == job_id, LaundryJob.user_id == student.id)
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return LaundryJobResponse.model_validate(job)


# =====================================================
# EXPORTS
# =====================================================

__all__ = ["router"]
