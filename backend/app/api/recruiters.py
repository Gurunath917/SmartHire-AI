"""
Recruiter profile API routes.

GET  /api/recruiters/me        — get my recruiter profile
PUT  /api/recruiters/me        — update my recruiter profile
GET  /api/recruiters/me/jobs   — list my posted jobs
GET  /api/recruiters/{id}      — get recruiter profile by id (admin only)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.recruiter_profile import RecruiterProfile
from app.models.job import Job, JobStatus
from app.schemas.recruiter import (
    RecruiterProfileUpdate,
    RecruiterProfileResponse,
    RecruiterProfileWithUserResponse,
)
from app.schemas.job import JobListResponse
from app.utils.dependencies import get_current_user, get_current_recruiter
from app.utils.errors import not_found, forbidden
from app.utils.logger import logger

router = APIRouter()


# ── GET /api/recruiters/me ────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=RecruiterProfileWithUserResponse,
    summary="Get my recruiter profile",
)
def get_my_profile(
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Recruiter profile")

    data = RecruiterProfileResponse.model_validate(profile)
    return RecruiterProfileWithUserResponse(
        **data.model_dump(),
        full_name=current_user.full_name,
        email=current_user.email,
    )


# ── PUT /api/recruiters/me ────────────────────────────────────────────────────
@router.put(
    "/me",
    response_model=RecruiterProfileResponse,
    summary="Update my recruiter profile",
)
def update_my_profile(
    body: RecruiterProfileUpdate,
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Recruiter profile")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    logger.info("Recruiter profile updated: user_id={}", current_user.id)
    return profile


# ── GET /api/recruiters/me/jobs ───────────────────────────────────────────────
@router.get(
    "/me/jobs",
    response_model=list[JobListResponse],
    summary="List my posted jobs",
    description="Returns all jobs posted by the current recruiter (all statuses).",
)
def get_my_jobs(
    status: str = Query(None, description="Filter by status: DRAFT, ACTIVE, CLOSED, PAUSED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Recruiter profile")

    query = db.query(Job).filter(Job.recruiter_profile_id == profile.id)

    if status:
        try:
            status_enum = JobStatus[status.upper()]
            query = query.filter(Job.job_status == status_enum)
        except KeyError:
            pass

    jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return jobs


# ── GET /api/recruiters/me/stats ──────────────────────────────────────────────
@router.get(
    "/me/stats",
    summary="Get my recruitment stats",
    description="Returns summary stats: job counts, total applicants, active jobs.",
)
def get_my_stats(
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Recruiter profile")

    from app.models.application import Application
    from sqlalchemy import func

    # Job counts by status
    job_counts = (
        db.query(Job.job_status, func.count(Job.id))
        .filter(Job.recruiter_profile_id == profile.id)
        .group_by(Job.job_status)
        .all()
    )
    jobs_by_status = {str(s.value): c for s, c in job_counts}

    # Total applicants across all jobs
    total_applicants = (
        db.query(func.count(Application.id))
        .join(Job, Application.job_id == Job.id)
        .filter(Job.recruiter_profile_id == profile.id)
        .scalar()
    )

    return {
        "total_jobs": sum(jobs_by_status.values()),
        "active_jobs": jobs_by_status.get("ACTIVE", 0),
        "draft_jobs": jobs_by_status.get("DRAFT", 0),
        "closed_jobs": jobs_by_status.get("CLOSED", 0),
        "total_applicants": total_applicants or 0,
        "company": profile.company_name,
    }


# ── GET /api/recruiters/{id} (admin only) ─────────────────────────────────────
@router.get(
    "/{recruiter_id}",
    response_model=RecruiterProfileWithUserResponse,
    summary="Get recruiter profile by ID (admin only)",
)
def get_recruiter_by_id(
    recruiter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_role != UserRole.ADMIN:
        raise forbidden("Admin access required.")

    profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.id == recruiter_id
    ).first()
    if not profile:
        raise not_found("Recruiter profile")

    user = db.query(User).filter(User.id == profile.user_id).first()
    data = RecruiterProfileResponse.model_validate(profile)
    return RecruiterProfileWithUserResponse(
        **data.model_dump(),
        full_name=user.full_name,
        email=user.email,
    )
