"""
Pydantic schemas for candidate profile endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────────────────────

class CandidateProfileUpdate(BaseModel):
    """Body for PUT /api/candidates/me — all fields optional."""
    phone: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=255)
    linkedin_url: Optional[str] = Field(None, max_length=512)
    github_url: Optional[str] = Field(None, max_length=512)
    portfolio_url: Optional[str] = Field(None, max_length=512)
    bio: Optional[str] = None

    # Education
    degree: Optional[str] = Field(None, max_length=255)
    branch: Optional[str] = Field(None, max_length=255)
    institution: Optional[str] = Field(None, max_length=255)
    cgpa: Optional[float] = Field(None, ge=0.0, le=10.0)
    graduation_year: Optional[int] = Field(None, ge=1990, le=2100)

    # Experience
    years_of_experience: Optional[float] = Field(None, ge=0.0, le=60.0)
    current_company: Optional[str] = Field(None, max_length=255)
    current_job_title: Optional[str] = Field(None, max_length=255)

    # Career preferences
    target_roles: Optional[list[str]] = None
    preferred_locations: Optional[list[str]] = None
    expected_salary: Optional[str] = Field(None, max_length=100)

    model_config = {
        "json_schema_extra": {
            "example": {
                "phone": "+91-9876543210",
                "location": "Bangalore, India",
                "degree": "B.Tech",
                "branch": "Computer Science",
                "institution": "IIT Bombay",
                "cgpa": 8.5,
                "graduation_year": 2024,
                "years_of_experience": 1.0,
                "target_roles": ["AI/ML Engineer", "Data Scientist"],
            }
        }
    }


# ── Response schemas ──────────────────────────────────────────────────────────

class SkillResponse(BaseModel):
    """A single skill with proficiency info."""
    id: int
    skill_name: str
    category: str
    proficiency_level: Optional[str]
    years_used: Optional[float]
    skill_source: str

    model_config = {"from_attributes": True}


class CandidateProfileResponse(BaseModel):
    """Full candidate profile response."""
    id: int
    user_id: int

    # Personal
    phone: Optional[str]
    location: Optional[str]
    linkedin_url: Optional[str]
    github_url: Optional[str]
    portfolio_url: Optional[str]
    bio: Optional[str]

    # Education
    degree: Optional[str]
    branch: Optional[str]
    institution: Optional[str]
    cgpa: Optional[float]
    graduation_year: Optional[int]

    # Experience
    years_of_experience: Optional[float]
    current_company: Optional[str]
    current_job_title: Optional[str]

    # Career
    target_roles: Optional[list]
    preferred_locations: Optional[list]
    expected_salary: Optional[str]

    # Scores
    profile_completion_pct: int
    resume_ats_score: Optional[int]

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CandidateProfileWithUserResponse(CandidateProfileResponse):
    """Profile + basic user info combined."""
    full_name: str
    email: str
