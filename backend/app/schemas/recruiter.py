"""
Pydantic schemas for recruiter profile endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────────────────────

class RecruiterProfileUpdate(BaseModel):
    """Body for PUT /api/recruiters/me — all fields optional."""
    company_name: Optional[str] = Field(None, max_length=255)
    company_website: Optional[str] = Field(None, max_length=512)
    company_size: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=255)
    company_location: Optional[str] = Field(None, max_length=255)
    company_description: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    job_title: Optional[str] = Field(None, max_length=255)
    linkedin_url: Optional[str] = Field(None, max_length=512)

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_name": "TechCorp India",
                "company_website": "https://techcorp.in",
                "company_size": "200-500",
                "industry": "Technology",
                "company_location": "Bangalore, India",
                "job_title": "HR Manager",
                "phone": "+91-9876543210",
            }
        }
    }


# ── Response schemas ──────────────────────────────────────────────────────────

class RecruiterProfileResponse(BaseModel):
    """Full recruiter profile."""
    id: int
    user_id: int
    company_name: Optional[str]
    company_website: Optional[str]
    company_size: Optional[str]
    industry: Optional[str]
    company_location: Optional[str]
    company_description: Optional[str]
    phone: Optional[str]
    job_title: Optional[str]
    linkedin_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecruiterProfileWithUserResponse(RecruiterProfileResponse):
    """Profile + basic user info."""
    full_name: str
    email: str
