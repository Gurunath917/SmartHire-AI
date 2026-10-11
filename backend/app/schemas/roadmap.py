"""
Pydantic schemas for learning roadmap endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Week item schema ──────────────────────────────────────────────────────────

class WeekItem(BaseModel):
    """A single week in the learning roadmap."""
    week: int
    topic: str
    objectives: list[str]
    time_estimate: str          # e.g. "8–10 hours"
    practice_task: str
    project_task: str
    resources: list[str]        # curated resource titles/links
    is_completed: bool = False  # candidate marks this as done


# ── Request schemas ───────────────────────────────────────────────────────────

class RoadmapGenerateRequest(BaseModel):
    """Body for POST /api/roadmap/generate"""
    target_role: str = Field(..., min_length=2, max_length=255)
    missing_skills: list[str] = Field(..., min_length=1)
    job_id: Optional[int] = None   # optional: tie roadmap to a specific job

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_role": "AI/ML Engineer",
                "missing_skills": ["PyTorch", "Docker", "AWS"],
                "job_id": 1,
            }
        }
    }


# ── Response schemas ──────────────────────────────────────────────────────────

class RoadmapResponse(BaseModel):
    """Full learning roadmap response."""
    id: int
    candidate_profile_id: int
    target_role: str
    missing_skills: Optional[list]
    roadmap_data: Optional[list]   # list of WeekItem dicts
    total_weeks: Optional[int]
    roadmap_status: str
    generation_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoadmapSummary(BaseModel):
    """Lightweight roadmap summary for listings."""
    id: int
    target_role: str
    total_weeks: Optional[int]
    roadmap_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WeekProgressUpdate(BaseModel):
    """Mark a specific week as completed or not."""
    week_number: int = Field(..., ge=1)
    is_completed: bool

    model_config = {
        "json_schema_extra": {
            "example": {"week_number": 1, "is_completed": True}
        }
    }
