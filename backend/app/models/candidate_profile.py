"""
Candidate profile model — all candidate-specific information.
AI-extracted data is stored alongside manually verified data.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)

    # ── Personal Info ─────────────────────────────────────────────────────
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512))
    github_url: Mapped[Optional[str]] = mapped_column(String(512))
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(512))
    bio: Mapped[Optional[str]] = mapped_column(Text)

    # ── Education ─────────────────────────────────────────────────────────
    degree: Mapped[Optional[str]] = mapped_column(String(255))
    branch: Mapped[Optional[str]] = mapped_column(String(255))
    institution: Mapped[Optional[str]] = mapped_column(String(255))
    cgpa: Mapped[Optional[float]] = mapped_column(Float)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer)

    # ── Experience ────────────────────────────────────────────────────────
    years_of_experience: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    current_company: Mapped[Optional[str]] = mapped_column(String(255))
    current_job_title: Mapped[Optional[str]] = mapped_column(String(255))

    # ── Career ────────────────────────────────────────────────────────────
    target_roles: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    preferred_locations: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    expected_salary: Mapped[Optional[str]] = mapped_column(String(100))

    # ── Profile completeness ──────────────────────────────────────────────
    profile_completion_pct: Mapped[int] = mapped_column(Integer, default=0)
    resume_ats_score: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="candidate_profile")
    candidate_skills: Mapped[list["CandidateSkill"]] = relationship(
        "CandidateSkill", back_populates="candidate_profile", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="candidate_profile", cascade="all, delete-orphan"
    )
    match_scores: Mapped[list["MatchScore"]] = relationship(
        "MatchScore", back_populates="candidate_profile", cascade="all, delete-orphan"
    )
    skill_gaps: Mapped[list["SkillGap"]] = relationship(
        "SkillGap", back_populates="candidate_profile", cascade="all, delete-orphan"
    )
    learning_roadmaps: Mapped[list["LearningRoadmap"]] = relationship(
        "LearningRoadmap", back_populates="candidate_profile", cascade="all, delete-orphan"
    )
    interviews: Mapped[list["Interview"]] = relationship(
        "Interview", back_populates="candidate_profile", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CandidateProfile id={self.id} user_id={self.user_id}>"
