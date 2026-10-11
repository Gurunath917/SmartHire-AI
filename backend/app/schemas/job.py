"""
Pydantic schemas for job endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.job import EmploymentType, ExperienceLevel, JobStatus


# ── Request schemas ───────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    """Body for POST /api/jobs"""
    title: str = Field(..., min_length=2, max_length=255)
    company: str = Field(..., min_length=2, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    is_remote: bool = False
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    experience_level: ExperienceLevel = ExperienceLevel.MID
    salary_min: Optional[str] = Field(None, max_length=50)
    salary_max: Optional[str] = Field(None, max_length=50)
    salary_currency: str = Field("USD", max_length=10)
    description: str = Field(..., min_length=50)
    responsibilities: Optional[str] = None
    education_requirements: Optional[str] = None
    # Recruiter can optionally pre-fill required/preferred skills
    required_skills: Optional[list[str]] = []
    preferred_skills: Optional[list[str]] = []

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "AI/ML Engineer",
                "company": "TechCorp India",
                "location": "Bangalore, India",
                "is_remote": True,
                "employment_type": "FULL_TIME",
                "experience_level": "MID",
                "salary_min": "12 LPA",
                "salary_max": "20 LPA",
                "description": (
                    "Looking for an AI/ML Engineer with strong Python skills. "
                    "Experience with Scikit-learn, TensorFlow, FastAPI and SQL required. "
                    "Exposure to LLMs, RAG, and vector databases preferred."
                ),
            }
        }
    }


class JobUpdate(BaseModel):
    """Body for PUT /api/jobs/{id} — all fields optional."""
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    company: Optional[str] = Field(None, min_length=2, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    is_remote: Optional[bool] = None
    employment_type: Optional[EmploymentType] = None
    experience_level: Optional[ExperienceLevel] = None
    salary_min: Optional[str] = Field(None, max_length=50)
    salary_max: Optional[str] = Field(None, max_length=50)
    salary_currency: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, min_length=50)
    responsibilities: Optional[str] = None
    education_requirements: Optional[str] = None
    # Recruiter edits to AI-extracted fields
    ai_extracted_required_skills: Optional[list[str]] = None
    ai_extracted_preferred_skills: Optional[list[str]] = None
    ai_extracted_experience_years: Optional[str] = None
    ai_extracted_tools: Optional[list[str]] = None
    ai_extracted_technologies: Optional[list[str]] = None


class JobStatusUpdate(BaseModel):
    """Body for PATCH /api/jobs/{id}/status"""
    job_status: JobStatus

    model_config = {
        "json_schema_extra": {
            "example": {"job_status": "ACTIVE"}
        }
    }


# ── Response schemas ──────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    """Full job details."""
    id: int
    recruiter_profile_id: int
    title: str
    company: str
    location: Optional[str]
    is_remote: bool
    employment_type: EmploymentType
    experience_level: ExperienceLevel
    salary_min: Optional[str]
    salary_max: Optional[str]
    salary_currency: str
    description: str
    responsibilities: Optional[str]
    education_requirements: Optional[str]
    # AI-extracted fields
    ai_extracted_required_skills: Optional[list]
    ai_extracted_preferred_skills: Optional[list]
    ai_extracted_experience_years: Optional[str]
    ai_extracted_tools: Optional[list]
    ai_extracted_technologies: Optional[list]
    job_status: JobStatus
    views_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Minimal job info for listings."""
    id: int
    title: str
    company: str
    location: Optional[str]
    is_remote: bool
    employment_type: EmploymentType
    experience_level: ExperienceLevel
    salary_min: Optional[str]
    salary_max: Optional[str]
    job_status: JobStatus
    ai_extracted_required_skills: Optional[list]
    created_at: datetime

    model_config = {"from_attributes": True}


class JobAnalyzeResponse(BaseModel):
    """Returned by the AI job description analyzer."""
    required_skills: list[str]
    preferred_skills: list[str]
    experience_years: Optional[str]
    tools: list[str]
    technologies: list[str]
    responsibilities: list[str]
    education: Optional[str]
