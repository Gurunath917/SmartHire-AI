"""
Job model — recruiter-created job postings with AI-extracted requirements.
"""
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class EmploymentType(str, enum.Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    FREELANCE = "FREELANCE"


class ExperienceLevel(str, enum.Enum):
    FRESHER = "FRESHER"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    LEAD = "LEAD"
    MANAGER = "MANAGER"


class JobStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    PAUSED = "PAUSED"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    recruiter_profile_id: Mapped[int] = mapped_column(
        ForeignKey("recruiter_profiles.id"), index=True, nullable=False
    )

    # ── Basic Info ────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    employment_type: Mapped[EmploymentType] = mapped_column(
        SAEnum(EmploymentType), default=EmploymentType.FULL_TIME
    )
    experience_level: Mapped[ExperienceLevel] = mapped_column(
        SAEnum(ExperienceLevel), default=ExperienceLevel.MID
    )
    salary_min: Mapped[Optional[str]] = mapped_column(String(50))
    salary_max: Mapped[Optional[str]] = mapped_column(String(50))
    salary_currency: Mapped[str] = mapped_column(String(10), default="USD")

    # ── Content ───────────────────────────────────────────────────────────
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[Optional[str]] = mapped_column(Text)
    education_requirements: Mapped[Optional[str]] = mapped_column(Text)

    # ── AI-extracted requirements (editable by recruiter) ─────────────────
    ai_extracted_required_skills: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    ai_extracted_preferred_skills: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    ai_extracted_experience_years: Mapped[Optional[str]] = mapped_column(String(50))
    ai_extracted_tools: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    ai_extracted_technologies: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # ── Status ────────────────────────────────────────────────────────────
    job_status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus), default=JobStatus.DRAFT, index=True)
    views_count: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────
    recruiter_profile: Mapped["RecruiterProfile"] = relationship(
        "RecruiterProfile", back_populates="jobs"
    )
    job_skills: Mapped[list["JobSkill"]] = relationship(
        "JobSkill", back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )
    match_scores: Mapped[list["MatchScore"]] = relationship(
        "MatchScore", back_populates="job", cascade="all, delete-orphan"
    )
    skill_gaps: Mapped[list["SkillGap"]] = relationship(
        "SkillGap", back_populates="job", cascade="all, delete-orphan"
    )
    saved_by: Mapped[list["SavedJob"]] = relationship(
        "SavedJob", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title} status={self.job_status}>"


class JobSkill(Base):
    """Association between a job and a required/preferred skill."""
    __tablename__ = "job_skills"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True, nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True, nullable=False)

    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    # True = required, False = preferred

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ─────────────────────────────────────────────────────
    job: Mapped["Job"] = relationship("Job", back_populates="job_skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="job_skills")
