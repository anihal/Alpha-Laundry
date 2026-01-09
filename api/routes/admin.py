"""
Admin routes for managing laundry requests and analytics
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database import get_db, User, Admin, LaundryJob
from ..schemas import (
    AdminDashboard,
    UpdateStatusRequest,
    UpdateStatusResponse,
    LaundryJobResponse,
    LaundryJobWithUser,
    LaundryJobStats,
)
from ..utils import extract_user_from_token

router = APIRouter(prefix="/admin", tags=["Admin"])


# =====================================================
# DEPENDENCY: Get Current Admin
# =====================================================


def get_current_admin(
    token: str = Query(..., description="JWT access token"), db: Session = Depends(get_db)
):
    """
    Dependency to get current authenticated admin from token
    """
    user_info = extract_user_from_token(token)

    if not user_info or user_info.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )

    admin = db.query(Admin).filter(Admin.id == user_info["user_id"]).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive",
        )

    return admin


# =====================================================
# DASHBOARD ENDPOINT
# =====================================================


@router.get("/dashboard", response_model=AdminDashboard)
def get_dashboard(
    admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)
):
    """
    Get admin dashboard with pending and processing requests

    Returns:
        AdminDashboard: Dashboard data with request counts
    """

    # Get pending requests with user info
    pending_jobs = (
        db.query(LaundryJob, User)
        .join(User, LaundryJob.user_id == User.id)
        .filter(LaundryJob.status == "submitted")
        .order_by(LaundryJob.submission_date.asc())
        .all()
    )

    pending_requests = [
        {
            "id": job.id,
            "student_id": job.student_id,
            "student_name": user.name,
            "num_clothes": job.num_clothes,
            "status": job.status,
            "priority": job.priority,
            "submission_date": job.submission_date.isoformat(),
            "notes": job.notes,
        }
        for job, user in pending_jobs
    ]

    # Get processing requests with user info
    processing_jobs = (
        db.query(LaundryJob, User)
        .join(User, LaundryJob.user_id == User.id)
        .filter(LaundryJob.status == "processing")
        .order_by(LaundryJob.started_date.asc())
        .all()
    )

    processing_requests = [
        {
            "id": job.id,
            "student_id": job.student_id,
            "student_name": user.name,
            "num_clothes": job.num_clothes,
            "status": job.status,
            "priority": job.priority,
            "submission_date": job.submission_date.isoformat(),
            "started_date": job.started_date.isoformat() if job.started_date else None,
            "notes": job.notes,
        }
        for job, user in processing_jobs
    ]

    # Get completed requests count for today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = (
        db.query(LaundryJob)
        .filter(
            LaundryJob.status == "completed",
            LaundryJob.completed_date >= today_start,
        )
        .count()
    )

    return AdminDashboard(
        pending_requests=pending_requests,
        processing_requests=processing_requests,
        total_pending=len(pending_requests),
        total_processing=len(processing_requests),
        total_completed_today=completed_today,
    )


# =====================================================
# UPDATE STATUS ENDPOINT (with logic for starting jobs)
# =====================================================


@router.patch("/update-status", response_model=UpdateStatusResponse)
def update_status(
    request_data: UpdateStatusRequest,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Update laundry job status

    **IMPORTANT**: When admin starts a job (changes status to 'processing'),
    the started_date is automatically set.

    - **request_id**: ID of the laundry job
    - **status**: New status (submitted, processing, completed, cancelled)

    Returns:
        UpdateStatusResponse: Updated job information
    """

    # Find the job
    job = db.query(LaundryJob).filter(LaundryJob.id == request_data.request_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {request_data.request_id} not found",
        )

    # Validate status transition
    valid_statuses = ["submitted", "processing", "completed", "cancelled"]
    if request_data.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    old_status = job.status
    new_status = request_data.status

    # Update status
    job.status = new_status

    # Set timestamps based on status transitions
    if new_status == "processing" and old_status == "submitted":
        # Admin is starting the job
        job.started_date = datetime.utcnow()

    elif new_status == "completed" and old_status in ["submitted", "processing"]:
        # Admin is completing the job
        if not job.started_date:
            job.started_date = datetime.utcnow()
        job.completed_date = datetime.utcnow()

    elif new_status == "cancelled":
        # Job is cancelled
        if not job.completed_date:
            job.completed_date = datetime.utcnow()

    # Commit changes
    try:
        db.commit()
        db.refresh(job)

        return UpdateStatusResponse(
            message=f"Job {job.id} status updated from '{old_status}' to '{new_status}'",
            job=LaundryJobResponse.model_validate(job),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job status: {str(e)}",
        )


# =====================================================
# ANALYTICS ENDPOINT
# =====================================================


@router.get("/analytics", response_model=LaundryJobStats)
def get_analytics(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Get analytics and statistics for laundry jobs

    - **days**: Number of days to include in analysis (default: 7)

    Returns:
        LaundryJobStats: Statistics including job counts and clothes processed
    """

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get total jobs
    total_jobs = db.query(LaundryJob).count()

    # Get jobs by status
    status_counts = (
        db.query(LaundryJob.status, func.count(LaundryJob.id))
        .group_by(LaundryJob.status)
        .all()
    )

    status_dict = {status: count for status, count in status_counts}

    # Get total clothes processed (completed jobs)
    total_clothes = (
        db.query(func.sum(LaundryJob.num_clothes))
        .filter(LaundryJob.status == "completed")
        .scalar()
    ) or 0

    return LaundryJobStats(
        total_jobs=total_jobs,
        submitted=status_dict.get("submitted", 0),
        processing=status_dict.get("processing", 0),
        completed=status_dict.get("completed", 0),
        cancelled=status_dict.get("cancelled", 0),
        total_clothes_processed=total_clothes,
    )


# =====================================================
# GET ALL JOBS ENDPOINT (with filters)
# =====================================================


@router.get("/jobs", response_model=List[LaundryJobWithUser])
def get_all_jobs(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Get all laundry jobs with optional filters

    - **status_filter**: Filter by status
    - **student_id**: Filter by student ID
    - **page**: Page number
    - **page_size**: Items per page

    Returns:
        List[LaundryJobWithUser]: List of jobs with user information
    """

    # Build query with join
    query = db.query(LaundryJob, User).join(User, LaundryJob.user_id == User.id)

    # Apply filters
    if status_filter:
        query = query.filter(LaundryJob.status == status_filter)

    if student_id:
        query = query.filter(LaundryJob.student_id == student_id)

    # Apply pagination
    offset = (page - 1) * page_size
    results = query.order_by(LaundryJob.submission_date.desc()).offset(offset).limit(page_size).all()

    # Format response
    jobs_with_users = []
    for job, user in results:
        job_dict = LaundryJobResponse.model_validate(job).model_dump()
        job_dict["student_name"] = user.name
        job_dict["remaining_quota"] = user.remaining_quota
        jobs_with_users.append(LaundryJobWithUser(**job_dict))

    return jobs_with_users


# =====================================================
# EXPORTS
# =====================================================

__all__ = ["router"]
