"""
Jobs API routes.

POST   /api/jobs                    — create job (recruiter only)
GET    /api/jobs                    — list all active jobs (public/candidate/recruiter)
GET    /api/jobs/{id}               — get job detail
PUT    /api/jobs/{id}               — update job (owner recruiter only)
DELETE /api/jobs/{id}               — delete job (owner recruiter only)
PATCH  /api/jobs/{id}/status        — activate / deactivate / close job
POST   /api/jobs/analyze            — AI analyze a job description (recruiter only)
GET    /api/jobs/{id}/applicants    — list applicants for a job (recruiter only)
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.job import Job, JobStatus, JobSkill
from app.models.skill import Skill
from app.models.recruiter_profile import RecruiterProfile
from app.schemas.job import (
    JobCreate, JobUpdate, JobStatusUpdate,
    JobResponse, JobListResponse, JobAnalyzeResponse,
)
from app.schemas.auth import MessageResponse
from app.services.job_analyzer import analyze_job_description
from app.utils.dependencies import get_current_user, get_current_recruiter, get_optional_user
from app.utils.errors import not_found, forbidden, bad_request
from app.utils.logger import logger

router = APIRouter()


def _get_recruiter_profile(user: User, db: Session) -> RecruiterProfile:
    """Get recruiter profile or raise 404."""
    profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == user.id
    ).first()
    if not profile:
        raise not_found("Recruiter profile")
    return profile


def _populate_job_skills(job: Job, required_skills: list[str], preferred_skills: list[str], db: Session) -> None:
    """
    Upsert job_skills rows for this job.
    Clears existing job_skills first, then inserts fresh rows
    based on the canonical required/preferred skill lists.
    Only inserts skills that exist in the master skills taxonomy table.
    """
    # Delete existing job_skills for this job
    db.query(JobSkill).filter(JobSkill.job_id == job.id).delete()

    # Build skill name → id lookup from taxonomy
    skill_rows = db.query(Skill).all()
    skill_lookup = {s.skill_name.lower(): s.id for s in skill_rows}

    added_skill_ids: set[int] = set()

    for skill_name in required_skills:
        skill_id = skill_lookup.get(skill_name.lower())
        if skill_id and skill_id not in added_skill_ids:
            added_skill_ids.add(skill_id)
            db.add(JobSkill(job_id=job.id, skill_id=skill_id, is_required=True))

    for skill_name in preferred_skills:
        skill_id = skill_lookup.get(skill_name.lower())
        if skill_id and skill_id not in added_skill_ids:
            added_skill_ids.add(skill_id)
            db.add(JobSkill(job_id=job.id, skill_id=skill_id, is_required=False))


# ── POST /api/jobs/analyze ────────────────────────────────────────────────────
# Note: this must come BEFORE /{id} routes to avoid "analyze" being treated as an ID
@router.post(
    "/analyze",
    response_model=JobAnalyzeResponse,
    summary="AI analyze a job description",
    description=(
        "Submit a job description text. "
        "The AI extracts required skills, preferred skills, experience, "
        "tools, technologies, and responsibilities. "
        "Recruiter can review and edit before saving the job."
    ),
)
def analyze_job(
    body: dict,
    current_user: User = Depends(get_current_recruiter),
):
    description = body.get("description", "").strip()
    if len(description) < 50:
        raise bad_request("Description must be at least 50 characters for meaningful analysis.")

    result = analyze_job_description(description)
    return JobAnalyzeResponse(**result)


# ── POST /api/jobs ────────────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=JobResponse,
    status_code=201,
    summary="Create a new job",
)
def create_job(
    body: JobCreate,
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    profile = _get_recruiter_profile(current_user, db)

    # Auto-analyze the job description
    analysis = analyze_job_description(body.description)

    # Merge recruiter-provided skills with AI-extracted ones
    required_skills = sorted(set(
        body.required_skills + analysis["required_skills"]
    ))
    preferred_skills = sorted(set(
        body.preferred_skills + analysis["preferred_skills"]
    ))

    logger.info(
        "Job create — NLP extracted required={} preferred={}",
        required_skills, preferred_skills
    )

    job = Job(
        recruiter_profile_id=profile.id,
        title=body.title,
        company=body.company,
        location=body.location,
        is_remote=body.is_remote,
        employment_type=body.employment_type,
        experience_level=body.experience_level,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        salary_currency=body.salary_currency,
        description=body.description,
        responsibilities=body.responsibilities or "\n".join(analysis["responsibilities"]),
        education_requirements=body.education_requirements or analysis.get("education"),
        ai_extracted_required_skills=required_skills,
        ai_extracted_preferred_skills=preferred_skills,
        ai_extracted_experience_years=analysis["experience_years"],
        ai_extracted_tools=analysis["tools"],
        ai_extracted_technologies=analysis["technologies"],
        job_status=JobStatus.DRAFT,
    )
    db.add(job)
    db.flush()  # get job.id before commit

    # Populate job_skills table (required and preferred)
    _populate_job_skills(job, required_skills, preferred_skills, db)

    db.commit()
    db.refresh(job)

    logger.info(
        "Job created: id={} title='{}' required_skills={} recruiter={}",
        job.id, job.title, required_skills, current_user.email
    )
    return job


# ── GET /api/jobs ─────────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[JobListResponse],
    summary="List jobs",
    description="List jobs. Candidates and public see only ACTIVE jobs. Recruiters see their own jobs in all statuses.",
)
def list_jobs(
    search: Optional[str] = Query(None, description="Search by title or company"),
    employment_type: Optional[str] = Query(None),
    experience_level: Optional[str] = Query(None),
    is_remote: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    query = db.query(Job)

    # Recruiters see their own jobs (all statuses)
    if current_user and current_user.user_role == UserRole.RECRUITER:
        profile = db.query(RecruiterProfile).filter(
            RecruiterProfile.user_id == current_user.id
        ).first()
        if profile:
            query = query.filter(Job.recruiter_profile_id == profile.id)
    else:
        # Everyone else sees only ACTIVE jobs
        query = query.filter(Job.job_status == JobStatus.ACTIVE)

    # Filters
    if search:
        query = query.filter(
            or_(
                Job.title.ilike(f"%{search}%"),
                Job.company.ilike(f"%{search}%"),
            )
        )
    if employment_type:
        query = query.filter(Job.employment_type == employment_type)
    if experience_level:
        query = query.filter(Job.experience_level == experience_level)
    if is_remote is not None:
        query = query.filter(Job.is_remote == is_remote)

    jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return jobs


# ── GET /api/jobs/{id} ────────────────────────────────────────────────────────
@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job detail",
)
def get_job(
    job_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise not_found("Job")

    # Candidates (or unauthenticated users) can only see ACTIVE jobs
    if not current_user or current_user.user_role == UserRole.CANDIDATE:
        if job.job_status != JobStatus.ACTIVE:
            raise not_found("Job")

    # Increment view count for candidates/unauthenticated
    if not current_user or current_user.user_role == UserRole.CANDIDATE:
        job.views_count += 1
        db.commit()
        db.refresh(job)

    return job


# ── PUT /api/jobs/{id} ────────────────────────────────────────────────────────
@router.put(
    "/{job_id}",
    response_model=JobResponse,
    summary="Update a job",
)
def update_job(
    job_id: int,
    body: JobUpdate,
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    profile = _get_recruiter_profile(current_user, db)
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise not_found("Job")
    if job.recruiter_profile_id != profile.id:
        raise forbidden("You can only edit your own jobs.")

    update_data = body.model_dump(exclude_unset=True)

    # If description is updated, re-run AI analysis and refresh job_skills
    if "description" in update_data:
        new_description = update_data.pop("description")
        # Persist the updated description text
        job.description = new_description

        analysis = analyze_job_description(new_description)

        # Merge existing recruiter-provided skills with freshly AI-extracted ones.
        # Preserve any manually set skills from ai_extracted_* fields already on the job,
        # then merge with the new AI analysis to avoid silently dropping recruiter edits.
        existing_required  = set(job.ai_extracted_required_skills  or [])
        existing_preferred = set(job.ai_extracted_preferred_skills or [])
        # Also honour explicit override from the request body
        body_required  = set(update_data.pop("ai_extracted_required_skills",  None) or [])
        body_preferred = set(update_data.pop("ai_extracted_preferred_skills", None) or [])

        new_required  = sorted(existing_required  | body_required  | set(analysis["required_skills"]))
        new_preferred = sorted(existing_preferred | body_preferred | set(analysis["preferred_skills"]))

        job.ai_extracted_required_skills  = new_required
        job.ai_extracted_preferred_skills = new_preferred
        job.ai_extracted_experience_years = analysis["experience_years"]
        job.ai_extracted_tools            = analysis["tools"]
        job.ai_extracted_technologies     = analysis["technologies"]

        logger.info(
            "Job update — NLP re-extracted required={} preferred={}",
            new_required, new_preferred
        )
        # Refresh job_skills table
        _populate_job_skills(job, new_required, new_preferred, db)

    for field, value in update_data.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)

    logger.info("Job updated: id={} recruiter={}", job_id, current_user.email)
    return job


# ── PATCH /api/jobs/{id}/status ───────────────────────────────────────────────
@router.patch(
    "/{job_id}/status",
    response_model=JobResponse,
    summary="Change job status (activate/deactivate/close)",
)
def update_job_status(
    job_id: int,
    body: JobStatusUpdate,
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    profile = _get_recruiter_profile(current_user, db)
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise not_found("Job")
    if job.recruiter_profile_id != profile.id:
        raise forbidden("You can only manage your own jobs.")

    job.job_status = body.job_status
    db.commit()
    db.refresh(job)

    logger.info(
        "Job status updated: id={} status={} recruiter={}",
        job_id, body.job_status.value, current_user.email
    )
    return job


# ── DELETE /api/jobs/{id} ─────────────────────────────────────────────────────
@router.delete(
    "/{job_id}",
    response_model=MessageResponse,
    summary="Delete a job",
)
def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    profile = _get_recruiter_profile(current_user, db)
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise not_found("Job")
    if job.recruiter_profile_id != profile.id:
        raise forbidden("You can only delete your own jobs.")

    db.delete(job)
    db.commit()

    logger.info("Job deleted: id={} recruiter={}", job_id, current_user.email)
    return MessageResponse(message=f"Job '{job.title}' deleted successfully.")


# ── GET /api/jobs/{id}/applicants ─────────────────────────────────────────────
@router.get(
    "/{job_id}/applicants",
    summary="List applicants for a job (recruiter only)",
)
def get_job_applicants(
    job_id: int,
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    profile = _get_recruiter_profile(current_user, db)
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise not_found("Job")
    if job.recruiter_profile_id != profile.id:
        raise forbidden("You can only view applicants for your own jobs.")

    from app.models.application import Application
    from app.models.candidate_profile import CandidateProfile
    from app.models.user import User as UserModel

    applicants = (
        db.query(Application, CandidateProfile, UserModel)
        .join(CandidateProfile, Application.candidate_profile_id == CandidateProfile.id)
        .join(UserModel, CandidateProfile.user_id == UserModel.id)
        .filter(Application.job_id == job_id)
        .all()
    )

    result = []
    for app, profile_obj, user in applicants:
        result.append({
            "application_id": app.id,
            "candidate_profile_id": profile_obj.id,
            "full_name": user.full_name,
            "email": user.email,
            "app_status": app.app_status.value,
            "applied_at": app.applied_at.isoformat(),
            "location": profile_obj.location,
            "years_of_experience": profile_obj.years_of_experience,
        })

    return result
