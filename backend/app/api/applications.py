"""
Application API routes.

POST /api/applications              — apply to a job
GET  /api/applications              — list my applications (candidate)
DELETE /api/applications/{id}       — withdraw application
PATCH /api/applications/{id}/status — recruiter updates status
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.application import Application, ApplicationStatus
from app.models.job import Job, JobStatus
from app.models.candidate_profile import CandidateProfile
from app.models.recruiter_profile import RecruiterProfile
from app.schemas.auth import MessageResponse
from app.utils.dependencies import get_current_user, get_current_candidate, get_current_recruiter, get_current_admin
from app.utils.errors import not_found, forbidden, bad_request, conflict
from app.utils.logger import logger
from pydantic import BaseModel

router = APIRouter()


class ApplyRequest(BaseModel):
    job_id: int
    cover_letter: str = ""


class StatusUpdateRequest(BaseModel):
    app_status: ApplicationStatus


# ── POST /api/applications ────────────────────────────────────────────────────
@router.post(
    "/",
    status_code=201,
    summary="Apply to a job",
)
def apply_to_job(
    body: ApplyRequest,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Candidate profile")

    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise not_found("Job")
    if job.job_status != JobStatus.ACTIVE:
        raise bad_request("This job is not currently accepting applications.")

    # Check for duplicate application
    existing = db.query(Application).filter(
        Application.candidate_profile_id == profile.id,
        Application.job_id == body.job_id,
    ).first()
    if existing:
        raise conflict("You have already applied to this job.")

    application = Application(
        candidate_profile_id=profile.id,
        job_id=body.job_id,
        cover_letter=body.cover_letter or None,
        app_status=ApplicationStatus.APPLIED,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    logger.info(
        "Application submitted: candidate={} job={} id={}",
        profile.id, body.job_id, application.id
    )
    return {
        "message": f"Successfully applied to '{job.title}' at {job.company}.",
        "application_id": application.id,
        "app_status": application.app_status.value,
    }


# ── GET /api/applications ─────────────────────────────────────────────────────
@router.get(
    "/",
    summary="List my applications (candidate)",
)
def list_my_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Candidate profile")

    apps = (
        db.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.candidate_profile_id == profile.id)
        .order_by(Application.applied_at.desc())
        .offset(skip).limit(limit)
        .all()
    )

    return [{
        "application_id": app.id,
        "job_id":         job.id,
        "job_title":      job.title,
        "company":        job.company,
        "location":       job.location,
        "app_status":     app.app_status.value,
        "applied_at":     app.applied_at.isoformat(),
    } for app, job in apps]


# ── DELETE /api/applications/{id} ────────────────────────────────────────────
@router.delete(
    "/{application_id}",
    response_model=MessageResponse,
    summary="Withdraw an application",
)
def withdraw_application(
    application_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Candidate profile")

    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise not_found("Application")
    if app.candidate_profile_id != profile.id:
        raise forbidden("You can only withdraw your own applications.")

    app.app_status = ApplicationStatus.WITHDRAWN
    db.commit()

    return MessageResponse(message="Application withdrawn successfully.")


# ── PATCH /api/applications/{id}/status ──────────────────────────────────────
@router.patch(
    "/{application_id}/status",
    summary="Update application status (recruiter only)",
)
def update_application_status(
    application_id: int,
    body: StatusUpdateRequest,
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    rec_profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not rec_profile:
        raise not_found("Recruiter profile")

    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise not_found("Application")

    # Verify recruiter owns the job
    job = db.query(Job).filter(Job.id == app.job_id).first()
    if not job or job.recruiter_profile_id != rec_profile.id:
        raise forbidden("You can only manage applications for your own jobs.")

    # Recruiters cannot set WITHDRAWN (candidate-only) or APPLIED (initial state only)
    RECRUITER_FORBIDDEN_STATUSES = {ApplicationStatus.WITHDRAWN, ApplicationStatus.APPLIED}
    if body.app_status in RECRUITER_FORBIDDEN_STATUSES:
        raise bad_request(
            f"Recruiters cannot set status to '{body.app_status.value}'. "
            "WITHDRAWN is a candidate-only action; APPLIED is the initial state set on application."
        )

    app.app_status = body.app_status
    db.commit()

    logger.info(
        "Application status updated: id={} status={} recruiter={}",
        application_id, body.app_status.value, current_user.email
    )
    return {
        "application_id": application_id,
        "app_status":     body.app_status.value,
        "message":        f"Application status updated to {body.app_status.value}.",
    }


# ── GET /api/applications/admin ───────────────────────────────────────────────
@router.get(
    "/admin",
    summary="List all applications (admin only)",
    description="Paginated list of all applications across all jobs. Admin role required.",
)
def list_all_applications_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    app_status: str = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from app.models.candidate_profile import CandidateProfile
    from app.models.user import User as UserModel

    query = (
        db.query(Application, Job, CandidateProfile, UserModel)
        .join(Job, Application.job_id == Job.id)
        .join(CandidateProfile, Application.candidate_profile_id == CandidateProfile.id)
        .join(UserModel, CandidateProfile.user_id == UserModel.id)
    )

    if app_status:
        try:
            status_enum = ApplicationStatus[app_status.upper()]
            query = query.filter(Application.app_status == status_enum)
        except KeyError:
            raise bad_request(f"Invalid status '{app_status}'.")

    rows = query.order_by(Application.applied_at.desc()).offset(skip).limit(limit).all()

    return [{
        "application_id":       app.id,
        "candidate_name":       user.full_name,
        "candidate_email":      user.email,
        "job_id":               job.id,
        "job_title":            job.title,
        "company":              job.company,
        "app_status":           app.app_status.value,
        "applied_at":           app.applied_at.isoformat(),
        "cover_letter":         app.cover_letter,
        "recruiter_notes":      app.recruiter_notes,
    } for app, job, profile, user in rows]
