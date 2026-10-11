"""
Saved Jobs API routes.

POST   /api/saved-jobs/{job_id}  — save a job
DELETE /api/saved-jobs/{job_id}  — unsave a job
GET    /api/saved-jobs           — list saved jobs
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.job import Job, JobStatus
from app.models.misc import SavedJob
from app.schemas.auth import MessageResponse
from app.utils.dependencies import get_current_candidate
from app.utils.errors import not_found, conflict
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/{job_id}",
    response_model=MessageResponse,
    status_code=201,
    summary="Save a job",
)
def save_job(
    job_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise not_found("Job")

    existing = db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id,
        SavedJob.job_id == job_id,
    ).first()
    if existing:
        raise conflict("Job already saved.")

    db.add(SavedJob(user_id=current_user.id, job_id=job_id))
    db.commit()
    return MessageResponse(message=f"'{job.title}' saved successfully.")


@router.delete(
    "/{job_id}",
    response_model=MessageResponse,
    summary="Remove a saved job",
)
def unsave_job(
    job_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    saved = db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id,
        SavedJob.job_id == job_id,
    ).first()
    if not saved:
        raise not_found("Saved job")
    db.delete(saved)
    db.commit()
    return MessageResponse(message="Job removed from saved list.")


@router.get(
    "/",
    summary="List my saved jobs",
)
def list_saved_jobs(
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(SavedJob, Job)
        .join(Job, SavedJob.job_id == Job.id)
        .filter(SavedJob.user_id == current_user.id)
        .order_by(SavedJob.saved_at.desc())
        .all()
    )
    return [{
        "job_id":           job.id,
        "job_title":        job.title,
        "company":          job.company,
        "location":         job.location,
        "employment_type":  job.employment_type.value,
        "experience_level": job.experience_level.value,
        "job_status":       job.job_status.value,
        "saved_at":         sv.saved_at.isoformat(),
    } for sv, job in rows]
