"""
Learning Roadmap API routes.

POST /api/roadmap/generate          — generate personalized roadmap
GET  /api/roadmap                   — list my roadmaps
GET  /api/roadmap/{id}              — get a specific roadmap
PATCH /api/roadmap/{id}/progress    — mark a week as complete/incomplete
DELETE /api/roadmap/{id}            — delete a roadmap
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database.connection import get_db
from app.models.user import User
from app.models.roadmap import LearningRoadmap, RoadmapStatus
from app.models.candidate_profile import CandidateProfile
from app.schemas.roadmap import (
    RoadmapGenerateRequest,
    RoadmapResponse,
    RoadmapSummary,
    WeekProgressUpdate,
)
from app.schemas.auth import MessageResponse
from app.services.roadmap_generator import generate_roadmap
from app.utils.dependencies import get_current_candidate
from app.utils.errors import not_found, forbidden, bad_request
from app.utils.logger import logger

router = APIRouter()


def _get_candidate_profile(current_user: User, db: Session) -> CandidateProfile:
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Candidate profile")
    return profile


# ── POST /api/roadmap/generate ────────────────────────────────────────────────
@router.post(
    "/generate",
    response_model=RoadmapResponse,
    status_code=201,
    summary="Generate a personalized learning roadmap",
    description=(
        "Generates a week-by-week learning roadmap based on missing skills. "
        "Uses LLM if configured, falls back to rule-based generation automatically. "
        "DISCLAIMER: This roadmap is a learning suggestion only — "
        "it does NOT guarantee job placement or any specific career outcome."
    ),
)
def generate_candidate_roadmap(
    body: RoadmapGenerateRequest,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_candidate_profile(current_user, db)

    if not body.missing_skills:
        raise bad_request(
            "No missing skills provided. "
            "Run skill gap analysis first: GET /api/matching/jobs/{id}/skill-gap"
        )

    # Create roadmap record in PENDING state
    roadmap = LearningRoadmap(
        candidate_profile_id=profile.id,
        target_role=body.target_role,
        missing_skills=body.missing_skills,
        roadmap_status=RoadmapStatus.PENDING,
    )
    db.add(roadmap)
    db.flush()  # get ID before generation

    logger.info(
        "Generating roadmap: candidate={} role='{}' skills={}",
        profile.id, body.target_role, body.missing_skills
    )

    try:
        result = generate_roadmap(
            target_role=body.target_role,
            missing_skills=body.missing_skills,
        )

        roadmap.roadmap_data    = result["roadmap_data"]
        roadmap.total_weeks     = result["total_weeks"]
        roadmap.roadmap_status  = RoadmapStatus.GENERATED
        roadmap.generation_error = None

        logger.info(
            "Roadmap generated: id={} weeks={} source={}",
            roadmap.id, result["total_weeks"], result["source"]
        )

    except Exception as e:
        roadmap.roadmap_status  = RoadmapStatus.PENDING
        roadmap.generation_error = str(e)
        logger.error("Roadmap generation failed: {}", e)
        db.commit()
        raise bad_request(f"Roadmap generation failed: {str(e)}")

    db.commit()
    db.refresh(roadmap)
    return roadmap


# ── GET /api/roadmap ──────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[RoadmapSummary],
    summary="List my learning roadmaps",
)
def list_my_roadmaps(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_candidate_profile(current_user, db)

    roadmaps = (
        db.query(LearningRoadmap)
        .filter(LearningRoadmap.candidate_profile_id == profile.id)
        .order_by(LearningRoadmap.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return roadmaps


# ── GET /api/roadmap/{id} ─────────────────────────────────────────────────────
@router.get(
    "/{roadmap_id}",
    response_model=RoadmapResponse,
    summary="Get a specific roadmap",
)
def get_roadmap(
    roadmap_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_candidate_profile(current_user, db)

    roadmap = db.query(LearningRoadmap).filter(
        LearningRoadmap.id == roadmap_id
    ).first()
    if not roadmap:
        raise not_found("Roadmap")
    if roadmap.candidate_profile_id != profile.id:
        raise forbidden("You can only view your own roadmaps.")

    return roadmap


# ── PATCH /api/roadmap/{id}/progress ─────────────────────────────────────────
@router.patch(
    "/{roadmap_id}/progress",
    response_model=RoadmapResponse,
    summary="Mark a week as completed or incomplete",
    description=(
        "Update the completion status of a specific week in the roadmap. "
        "When all weeks are completed, roadmap status is set to COMPLETED."
    ),
)
def update_week_progress(
    roadmap_id: int,
    body: WeekProgressUpdate,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_candidate_profile(current_user, db)

    roadmap = db.query(LearningRoadmap).filter(
        LearningRoadmap.id == roadmap_id
    ).first()
    if not roadmap:
        raise not_found("Roadmap")
    if roadmap.candidate_profile_id != profile.id:
        raise forbidden("You can only update your own roadmaps.")
    if roadmap.roadmap_status == RoadmapStatus.PENDING:
        raise bad_request("Roadmap has not been generated yet.")

    roadmap_data = roadmap.roadmap_data or []
    if not roadmap_data:
        raise bad_request("Roadmap has no weeks.")

    # Find the week and update its completion status
    week_found = False
    for week_item in roadmap_data:
        if week_item.get("week") == body.week_number:
            week_item["is_completed"] = body.is_completed
            flag_modified(roadmap, "roadmap_data")
            week_found = True
            break

    if not week_found:
        raise bad_request(
            f"Week {body.week_number} not found. "
            f"This roadmap has {len(roadmap_data)} weeks."
        )

    # Reassign to trigger SQLAlchemy JSON column change detection
    roadmap.roadmap_data = list(roadmap_data)

    # Auto-update roadmap status
    completed_weeks = sum(1 for w in roadmap_data if w.get("is_completed"))
    total_weeks = len(roadmap_data)

    if completed_weeks == total_weeks:
        roadmap.roadmap_status = RoadmapStatus.COMPLETED
    elif completed_weeks > 0:
        roadmap.roadmap_status = RoadmapStatus.IN_PROGRESS
    else:
        roadmap.roadmap_status = RoadmapStatus.GENERATED

    db.commit()
    db.refresh(roadmap)

    logger.info(
        "Roadmap progress: id={} week={} completed={} total_done={}/{}",
        roadmap_id, body.week_number, body.is_completed, completed_weeks, total_weeks
    )
    return roadmap


# ── DELETE /api/roadmap/{id} ──────────────────────────────────────────────────
@router.delete(
    "/{roadmap_id}",
    response_model=MessageResponse,
    summary="Delete a roadmap",
)
def delete_roadmap(
    roadmap_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_candidate_profile(current_user, db)

    roadmap = db.query(LearningRoadmap).filter(
        LearningRoadmap.id == roadmap_id
    ).first()
    if not roadmap:
        raise not_found("Roadmap")
    if roadmap.candidate_profile_id != profile.id:
        raise forbidden("You can only delete your own roadmaps.")

    db.delete(roadmap)
    db.commit()

    logger.info("Roadmap deleted: id={} candidate={}", roadmap_id, profile.id)
    return MessageResponse(
        message=f"Roadmap for '{roadmap.target_role}' deleted successfully."
    )
