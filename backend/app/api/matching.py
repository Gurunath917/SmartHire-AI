"""
Matching & Skill Gap API routes.

POST /api/matching/analyze              — run full match for candidate vs job
GET  /api/matching/jobs/{id}/matches    — ranked candidates for a job (recruiter)
GET  /api/matching/candidates/matches   — top job matches for candidate
GET  /api/matching/jobs/{id}/skill-gap  — skill gap for current candidate vs job
GET  /api/matching/candidates/skill-gap — all skill gaps for current candidate
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.job import Job, JobStatus
from app.models.candidate_profile import CandidateProfile
from app.models.recruiter_profile import RecruiterProfile
from app.models.skill import CandidateSkill, Skill
from app.models.matching import MatchScore, SkillGap
from app.schemas.matching import (
    MatchScoreResponse,
    MatchScoreSummary,
    AnalyzeMatchRequest,
    CandidateRankItem,
    SkillGapDetail,
)
from app.services.matching_engine import compute_match_score, _score_label
from app.services.skill_gap_service import analyze_skill_gap
from app.ml.ranking_service import rank_candidate, is_model_available, get_model_metadata
from app.utils.dependencies import get_current_user, get_current_candidate, get_current_recruiter
from app.utils.errors import not_found, forbidden, bad_request
from app.utils.logger import logger

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_job_skills(job: Job) -> tuple[list[str], list[str]]:
    """
    Get required and preferred skills for a job.
    Primary source: ai_extracted_required_skills / ai_extracted_preferred_skills.
    Fallback for legacy jobs (created before Phase 6 fix):
        if both lists are empty, use ai_extracted_technologies as required.
    This ensures skill matching works even for old job records.
    """
    required = job.ai_extracted_required_skills or []
    preferred = job.ai_extracted_preferred_skills or []

    if not required and not preferred:
        technologies = job.ai_extracted_technologies or []
        tools = job.ai_extracted_tools or []
        all_fallback = sorted(set(technologies + tools))
        if all_fallback:
            logger.warning(
                "Job id={} has empty required/preferred — using technologies as fallback: {}",
                job.id, all_fallback,
            )
            required = all_fallback

    return required, preferred


def _get_candidate_skills(profile_id: int, db: Session) -> list[str]:
    """Return list of canonical skill names for a candidate profile."""
    rows = (
        db.query(Skill.skill_name)
        .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
        .filter(CandidateSkill.candidate_profile_id == profile_id)
        .all()
    )
    return [r.skill_name for r in rows]


def _build_candidate_text(profile: CandidateProfile, skills: list[str]) -> str:
    """Build a text blob for TF-IDF/embedding from candidate profile."""
    parts = []
    if profile.current_job_title:
        parts.append(profile.current_job_title)
    if profile.degree:
        parts.append(f"{profile.degree} {profile.branch or ''}".strip())
    if skills:
        parts.append("Skills: " + ", ".join(skills))
    if profile.target_roles:
        parts.append("Target roles: " + ", ".join(profile.target_roles))
    return " ".join(parts)


def _build_job_text(job: Job) -> str:
    """Build a text blob for TF-IDF/embedding from job record."""
    parts = [job.title, job.description or ""]
    required, preferred = _get_job_skills(job)
    if required:
        parts.append("Required skills: " + ", ".join(required))
    if preferred:
        parts.append("Preferred skills: " + ", ".join(preferred))
    if job.responsibilities:
        parts.append(job.responsibilities)
    return " ".join(parts)


def _run_match(
    candidate_profile: CandidateProfile,
    job: Job,
    candidate_skills: list[str],
    db: Session,
) -> MatchScore:
    """
    Run the full matching pipeline and persist/upsert results.
    Returns the MatchScore ORM object.
    """
    candidate_text = _build_candidate_text(candidate_profile, candidate_skills)
    job_text = _build_job_text(job)

    required_skills, preferred_skills = _get_job_skills(job)

    logger.info(
        "_run_match: candidate_id={} job_id={} required_skills={} candidate_skills={}",
        candidate_profile.id, job.id, required_skills, candidate_skills,
    )

    scores = compute_match_score(
        candidate_text=candidate_text,
        job_text=job_text,
        candidate_skills=candidate_skills,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        candidate_years=float(candidate_profile.years_of_experience or 0),
        required_experience_str=job.ai_extracted_experience_years,
        candidate_degree=candidate_profile.degree,
        required_education=job.education_requirements,
    )

    # Run skill gap analysis using same skill lists
    gap = analyze_skill_gap(candidate_skills, required_skills, preferred_skills)

    # ── ML Ranking ────────────────────────────────────────────────────────────
    # Enrich the match with ML-based ranking score + SHAP explanation
    # Falls back gracefully if the model is not trained yet
    ml_rank_score = None
    shap_explanation = {}

    if is_model_available():
        try:
            num_skills = len(candidate_skills)
            num_req_matched = len(gap["matched_skills"]) + len(gap["partial_skills"])

            ml_result = rank_candidate(
                skill_match_score=scores["skill_match_score"],
                semantic_similarity_score=scores["semantic_similarity_score"],
                tfidf_score=scores["tfidf_score"],
                experience_match_score=scores["experience_match_score"],
                education_match_score=scores["education_match_score"],
                years_of_experience=float(candidate_profile.years_of_experience or 0),
                num_skills=num_skills,
                num_required_skills_matched=num_req_matched,
                num_projects=0,  # Phase 4 resume parsing can enrich this later
                has_certification=0,
                has_internship=0,
                cgpa=float(candidate_profile.cgpa or 0),
                include_shap=True,
            )
            ml_rank_score = ml_result["ml_rank_score"]
            shap_explanation = ml_result.get("explanation", {})
            logger.info(
                "ML rank: candidate={} job={} ml_score={}",
                candidate_profile.id, job.id, ml_rank_score
            )
        except Exception as e:
            logger.warning("ML ranking failed (non-critical): {}", e)

    # Merge SHAP explanation into the scores explanation
    explanation = scores.get("explanation", {})
    if shap_explanation:
        explanation["shap_positive"] = shap_explanation.get("positive_factors", [])
        explanation["shap_negative"] = shap_explanation.get("negative_factors", [])
        explanation["ml_rank_score"] = ml_rank_score
    # Always store skill gap results at the top level for easy retrieval
    explanation["matched_skills"] = gap.get("matched_skills", [])
    explanation["missing_skills"] = gap.get("missing_skills", [])
    scores["explanation"] = explanation
    scores["ml_rank_score"] = ml_rank_score

    # Upsert MatchScore
    existing_match = db.query(MatchScore).filter(
        MatchScore.candidate_profile_id == candidate_profile.id,
        MatchScore.job_id == job.id,
    ).first()

    if existing_match:
        for k, v in scores.items():
            setattr(existing_match, k, v)
        match_obj = existing_match
    else:
        match_obj = MatchScore(
            candidate_profile_id=candidate_profile.id,
            job_id=job.id,
            **scores,
        )
        db.add(match_obj)

    # Upsert SkillGap
    existing_gap = db.query(SkillGap).filter(
        SkillGap.candidate_profile_id == candidate_profile.id,
        SkillGap.job_id == job.id,
    ).first()

    if existing_gap:
        existing_gap.matched_skills = gap["matched_skills"]
        existing_gap.missing_skills = gap["missing_skills"]
        existing_gap.partial_skills = gap["partial_skills"]
    else:
        db.add(SkillGap(
            candidate_profile_id=candidate_profile.id,
            job_id=job.id,
            matched_skills=gap["matched_skills"],
            missing_skills=gap["missing_skills"],
            partial_skills=gap["partial_skills"],
        ))

    db.commit()
    db.refresh(match_obj)
    return match_obj


# ── POST /api/matching/analyze ────────────────────────────────────────────────
@router.post(
    "/analyze",
    response_model=MatchScoreResponse,
    summary="Run AI match score for current candidate vs a job",
    description=(
        "Computes TF-IDF + semantic + skill + experience + education scores. "
        "Results are stored. "
        "NOTE: This score is an internal heuristic — NOT a hiring probability."
    ),
)
def analyze_match(
    body: AnalyzeMatchRequest,
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
        raise bad_request("This job is not currently active.")

    candidate_skills = _get_candidate_skills(profile.id, db)
    if not candidate_skills:
        logger.warning(
            "Candidate id={} has no skills — upload and parse a resume first for best results.",
            profile.id,
        )

    match_obj = _run_match(profile, job, candidate_skills, db)
    logger.info(
        "Match analyzed: candidate={} job={} score={}",
        profile.id, job.id, match_obj.overall_score,
    )
    return match_obj


# ── GET /api/matching/jobs/{id}/matches ───────────────────────────────────────
@router.get(
    "/jobs/{job_id}/matches",
    response_model=list[CandidateRankItem],
    summary="Ranked candidates for a job (recruiter only)",
)
def get_job_matches(
    job_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    recruiter_profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not recruiter_profile:
        raise not_found("Recruiter profile")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise not_found("Job")
    if job.recruiter_profile_id != recruiter_profile.id:
        raise forbidden("You can only view matches for your own jobs.")

    matches = (
        db.query(MatchScore)
        .filter(MatchScore.job_id == job_id)
        .order_by(MatchScore.overall_score.desc())
        .limit(limit)
        .all()
    )

    result = []
    for m in matches:
        cprofile = db.query(CandidateProfile).filter(
            CandidateProfile.id == m.candidate_profile_id
        ).first()
        if not cprofile:
            continue
        cuser = db.query(User).filter(User.id == cprofile.user_id).first()
        if not cuser:
            continue
        result.append(CandidateRankItem(
            candidate_profile_id=cprofile.id,
            full_name=cuser.full_name,
            email=cuser.email,
            overall_score=m.overall_score,
            skill_match_score=m.skill_match_score,
            experience_match_score=m.experience_match_score,
            education_match_score=m.education_match_score,
            years_of_experience=cprofile.years_of_experience,
            location=cprofile.location,
            explanation=m.explanation,
        ))

    return result


# ── GET /api/matching/candidates/matches ──────────────────────────────────────
@router.get(
    "/candidates/matches",
    response_model=list[MatchScoreSummary],
    summary="Top job matches for the current candidate",
)
def get_candidate_matches(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Candidate profile")

    matches = (
        db.query(MatchScore)
        .filter(MatchScore.candidate_profile_id == profile.id)
        .order_by(MatchScore.overall_score.desc())
        .limit(limit)
        .all()
    )

    result = []
    for m in matches:
        explanation = m.explanation or {}
        # matched/missing skills are stored directly in the explanation by _run_match
        # fallback to shap explanation keys if present
        matched = (
            explanation.get("matched_skills")
            or explanation.get("factors", [{}])[0].get("matched_skills", [])
            or []
        )
        missing = (
            explanation.get("missing_skills")
            or []
        )
        result.append(MatchScoreSummary(
            job_id=m.job_id,
            overall_score=m.overall_score,
            skill_match_score=m.skill_match_score,
            score_label=_score_label(m.overall_score),
            matched_skills=matched,
            missing_skills=missing,
        ))

    return result


# ── GET /api/matching/jobs/{id}/skill-gap ─────────────────────────────────────
@router.get(
    "/jobs/{job_id}/skill-gap",
    response_model=SkillGapDetail,
    summary="Skill gap analysis for current candidate vs a specific job",
)
def get_skill_gap_for_job(
    job_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Candidate profile")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise not_found("Job")

    candidate_skills = _get_candidate_skills(profile.id, db)
    required_skills, preferred_skills = _get_job_skills(job)

    gap = analyze_skill_gap(candidate_skills, required_skills, preferred_skills)

    # Persist/update skill gap record
    existing = db.query(SkillGap).filter(
        SkillGap.candidate_profile_id == profile.id,
        SkillGap.job_id == job_id,
    ).first()

    if existing:
        existing.matched_skills = gap["matched_skills"]
        existing.missing_skills = gap["missing_skills"]
        existing.partial_skills = gap["partial_skills"]
    else:
        db.add(SkillGap(
            candidate_profile_id=profile.id,
            job_id=job_id,
            matched_skills=gap["matched_skills"],
            missing_skills=gap["missing_skills"],
            partial_skills=gap["partial_skills"],
        ))
    db.commit()

    return SkillGapDetail(
        job_id=job_id,
        job_title=job.title,
        **gap,
    )


# ── GET /api/matching/candidates/skill-gap ────────────────────────────────────
@router.get(
    "/candidates/skill-gap",
    summary="All skill gaps for the current candidate (across analyzed jobs)",
)
def get_all_skill_gaps(
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Candidate profile")

    gaps = (
        db.query(SkillGap)
        .filter(SkillGap.candidate_profile_id == profile.id)
        .all()
    )

    result = []
    for g in gaps:
        job = db.query(Job).filter(Job.id == g.job_id).first()
        result.append({
            "job_id": g.job_id,
            "job_title": job.title if job else "Unknown",
            "matched_skills": g.matched_skills or [],
            "missing_skills": g.missing_skills or [],
            "partial_skills": g.partial_skills or [],
        })

    return result


# ── GET /api/matching/model-info ──────────────────────────────────────────────
@router.get(
    "/model-info",
    summary="ML ranking model metadata",
    description=(
        "Returns information about the trained ML ranking model: "
        "model type, feature importances, evaluation metrics on demo data. "
        "NOTE: Metrics are from synthetic demo data only."
    ),
)
def get_ranking_model_info(
    current_user: User = Depends(get_current_user),
):
    if not is_model_available():
        return {
            "available": False,
            "message": "ML model not trained yet. Run ml/training/train_ranker.py.",
        }
    meta = get_model_metadata()
    return {
        "available": True,
        "model_name": meta.get("model_name"),
        "n_features": meta.get("n_features"),
        "feature_names": meta.get("feature_names"),
        "feature_importances": meta.get("feature_importances"),
        "test_metrics": meta.get("test_metrics"),
        "warning": meta.get("warning"),
        "dataset": meta.get("dataset"),
    }
