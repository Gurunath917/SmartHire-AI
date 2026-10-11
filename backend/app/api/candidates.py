"""
Candidate profile API routes.

GET  /api/candidates/me          — get my profile
PUT  /api/candidates/me          — update my profile
GET  /api/candidates/me/skills   — get my extracted skills
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.candidate_profile import CandidateProfile
from app.models.skill import CandidateSkill, Skill
from app.schemas.candidate import (
    CandidateProfileUpdate,
    CandidateProfileResponse,
    CandidateProfileWithUserResponse,
    SkillResponse,
)
from app.utils.dependencies import get_current_user, get_current_candidate
from app.utils.errors import not_found, forbidden
from app.utils.logger import logger

router = APIRouter()


def _calculate_completion(profile: CandidateProfile) -> int:
    """
    Calculate profile completion percentage based on filled fields.
    Returns 0–100.
    """
    fields = [
        profile.phone,
        profile.location,
        profile.bio,
        profile.degree,
        profile.branch,
        profile.institution,
        profile.cgpa,
        profile.graduation_year,
        profile.years_of_experience,
        profile.target_roles,
    ]
    filled = sum(1 for f in fields if f is not None and f != [] and f != "")
    return int((filled / len(fields)) * 100)


# ── GET /api/candidates/me ────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=CandidateProfileWithUserResponse,
    summary="Get my candidate profile",
)
def get_my_profile(
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise not_found("Candidate profile")

    # Build combined response
    data = CandidateProfileResponse.model_validate(profile)
    return CandidateProfileWithUserResponse(
        **data.model_dump(),
        full_name=current_user.full_name,
        email=current_user.email,
    )


# ── PUT /api/candidates/me ────────────────────────────────────────────────────
@router.put(
    "/me",
    response_model=CandidateProfileResponse,
    summary="Update my candidate profile",
)
def update_my_profile(
    body: CandidateProfileUpdate,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise not_found("Candidate profile")

    # Only update fields that were explicitly provided (not None)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    # Recalculate completion percentage
    profile.profile_completion_pct = _calculate_completion(profile)

    db.commit()
    db.refresh(profile)

    logger.info("Candidate profile updated: user_id={}", current_user.id)
    return profile


# ── GET /api/candidates/me/skills ─────────────────────────────────────────────
@router.get(
    "/me/skills",
    response_model=list[SkillResponse],
    summary="Get my skills",
    description="Returns all skills associated with the candidate profile.",
)
def get_my_skills(
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        raise not_found("Candidate profile")

    candidate_skills = (
        db.query(CandidateSkill)
        .join(Skill)
        .filter(CandidateSkill.candidate_profile_id == profile.id)
        .all()
    )

    result = []
    for cs in candidate_skills:
        result.append(
            SkillResponse(
                id=cs.id,
                skill_name=cs.skill.skill_name,
                category=cs.skill.category,
                proficiency_level=cs.proficiency_level,
                years_used=cs.years_used,
                skill_source=cs.skill_source,
            )
        )
    return result


# ── GET /api/candidates/{id} (recruiter view) ─────────────────────────────────
@router.get(
    "/{candidate_id}",
    response_model=CandidateProfileWithUserResponse,
    summary="Get a candidate profile (recruiter/admin only)",
)
def get_candidate_by_id(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Only recruiters and admins can view other candidate profiles
    if current_user.user_role == UserRole.CANDIDATE:
        raise forbidden("Candidates cannot view other candidate profiles.")

    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.id == candidate_id)
        .first()
    )
    if not profile:
        raise not_found("Candidate profile")

    user = db.query(User).filter(User.id == profile.user_id).first()
    data = CandidateProfileResponse.model_validate(profile)
    return CandidateProfileWithUserResponse(
        **data.model_dump(),
        full_name=user.full_name,
        email=user.email,
    )
