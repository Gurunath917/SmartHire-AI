"""
Pydantic schemas for matching and skill gap endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Match Score Schemas ───────────────────────────────────────────────────────

class MatchScoreResponse(BaseModel):
    """Full match score result returned to client."""
    id: int
    candidate_profile_id: int
    job_id: int

    # Scores (all 0–100)
    overall_score: float
    skill_match_score: Optional[float]
    semantic_similarity_score: Optional[float]
    experience_match_score: Optional[float]
    education_match_score: Optional[float]
    tfidf_score: Optional[float]
    ml_rank_score: Optional[float]

    # Explanation
    explanation: Optional[dict]

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MatchScoreSummary(BaseModel):
    """Lightweight match score for job listings."""
    job_id: int
    overall_score: float
    skill_match_score: Optional[float]
    score_label: str  # "Excellent match", "Strong match", etc.
    matched_skills: list[str] = []
    missing_skills: list[str] = []


class AnalyzeMatchRequest(BaseModel):
    """Body for POST /api/matching/analyze"""
    job_id: int

    model_config = {
        "json_schema_extra": {
            "example": {"job_id": 1}
        }
    }


class CandidateRankItem(BaseModel):
    """Single item in a ranked candidate list (for recruiters)."""
    candidate_profile_id: int
    full_name: str
    email: str
    overall_score: float
    skill_match_score: Optional[float]
    experience_match_score: Optional[float]
    education_match_score: Optional[float]
    years_of_experience: Optional[float]
    location: Optional[str]
    explanation: Optional[dict]


# ── Skill Gap Schemas ─────────────────────────────────────────────────────────

class SkillGapResponse(BaseModel):
    """Full skill gap analysis result."""
    id: int
    candidate_profile_id: int
    job_id: int
    matched_skills: Optional[list]
    missing_skills: Optional[list]
    partial_skills: Optional[list]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillGapDetail(BaseModel):
    """Detailed skill gap with percentages — returned directly from analysis."""
    job_id: int
    job_title: str
    matched_skills: list[str]
    missing_skills: list[str]
    partial_skills: list[dict]
    preferred_gap: list[str]
    match_percentage: float
    total_required: int
    total_matched: int
