"""
Resume API routes.

POST   /api/resumes/upload   — upload a PDF resume (candidate only)
GET    /api/resumes/         — list my resumes
GET    /api/resumes/{id}     — get a specific resume
DELETE /api/resumes/{id}     — delete a resume
"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.resume import Resume
from app.models.candidate_profile import CandidateProfile
from app.schemas.resume import ResumeResponse, ResumeListResponse
from app.schemas.auth import MessageResponse
from app.services.resume_storage import validate_and_store_resume, delete_resume_file
from app.services.resume_parser import parse_and_store_resume
from app.utils.dependencies import get_current_candidate
from app.utils.errors import not_found, forbidden
from app.utils.logger import logger

router = APIRouter()


# ── POST /api/resumes/upload ──────────────────────────────────────────────────
@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=201,
    summary="Upload a PDF resume",
    description=(
        "Upload a PDF resume. "
        "Validates file type (extension + magic bytes), size limit, "
        "and stores with a UUID-based safe filename. "
        "Only PDF files under 10 MB are accepted."
    ),
)
def upload_resume(
    file: UploadFile = File(..., description="PDF resume file"),
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    # Validate and store the file
    stored = validate_and_store_resume(file, current_user.id)

    # Mark any previous active resume as inactive (one active resume at a time)
    db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_active == True,
    ).update({"is_active": False})

    # Create resume record
    resume = Resume(
        user_id=current_user.id,
        original_filename=stored["original_filename"],
        stored_filename=stored["stored_filename"],
        file_path=stored["file_path"],
        file_size_bytes=stored["file_size_bytes"],
        mime_type=stored["mime_type"],
        is_parsed=False,
        is_active=True,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Update candidate profile ATS score placeholder (will be calculated in Phase 4 NLP)
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if profile:
        profile.resume_ats_score = None  # reset — will be recalculated after parsing
        db.commit()

    logger.info(
        "Resume uploaded: user_id={} resume_id={} file={}",
        current_user.id, resume.id, resume.original_filename
    )

    # Auto-parse the resume in the background (synchronous for now)
    # Phase 4: NLP pipeline runs immediately after upload
    try:
        parse_result = parse_and_store_resume(resume.id, db)
        if parse_result["success"]:
            logger.info(
                "Auto-parse complete: resume_id={} skills={}",
                resume.id, len(parse_result.get("skills_found", []))
            )
        else:
            logger.warning("Auto-parse failed: {}", parse_result.get("message"))
    except Exception as e:
        logger.warning("Auto-parse error (non-critical): {}", e)

    # Refresh to get updated parsed data
    db.refresh(resume)
    return resume


# ── GET /api/resumes/ ─────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[ResumeListResponse],
    summary="List my resumes",
)
def list_my_resumes(
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )
    return resumes


# ── GET /api/resumes/{id} ─────────────────────────────────────────────────────
@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Get a resume by ID",
)
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise not_found("Resume")

    # Candidates can only access their own resumes
    if resume.user_id != current_user.id:
        raise forbidden("You do not have access to this resume.")

    return resume


# ── DELETE /api/resumes/{id} ──────────────────────────────────────────────────
@router.delete(
    "/{resume_id}",
    response_model=MessageResponse,
    summary="Delete a resume",
)
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise not_found("Resume")

    if resume.user_id != current_user.id:
        raise forbidden("You do not have access to this resume.")

    # Delete file from disk
    delete_resume_file(resume.file_path)

    # Delete record from DB
    db.delete(resume)
    db.commit()

    logger.info(
        "Resume deleted: user_id={} resume_id={}",
        current_user.id, resume_id
    )
    return MessageResponse(message="Resume deleted successfully.")


# ── POST /api/resumes/{id}/parse ──────────────────────────────────────────────
@router.post(
    "/{resume_id}/parse",
    summary="Re-parse a resume",
    description="Trigger NLP parsing on an existing resume. Re-extracts text, sections, and skills.",
)
def parse_resume(
    resume_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise not_found("Resume")
    if resume.user_id != current_user.id:
        raise forbidden("You do not have access to this resume.")

    result = parse_and_store_resume(resume_id, db)

    return {
        "success": result["success"],
        "message": result["message"],
        "skills_found": result.get("skills_found", []),
        "sections_detected": result.get("sections", []),
        "contact": result.get("contact", {}),
        "ats_score": result.get("ats_score", 0),
    }
