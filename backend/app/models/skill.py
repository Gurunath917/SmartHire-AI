"""
Skill taxonomy model and candidate skill association.
Skills are normalized (e.g. ReactJS → React) before being stored.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Skill(Base):
    """Master skill taxonomy table — single source of truth for skill names."""
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    skill_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. programming_language, framework, database, cloud, ml, tool, soft_skill

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ─────────────────────────────────────────────────────
    candidate_skills: Mapped[list["CandidateSkill"]] = relationship(
        "CandidateSkill", back_populates="skill"
    )
    job_skills: Mapped[list["JobSkill"]] = relationship(
        "JobSkill", back_populates="skill"
    )

    def __repr__(self) -> str:
        return f"<Skill id={self.id} skill_name={self.skill_name} category={self.category}>"


class CandidateSkill(Base):
    """Association between a candidate profile and a skill with proficiency."""
    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("candidate_profile_id", "skill_id", name="uq_candidate_skill"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id"), index=True, nullable=False
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True, nullable=False)

    proficiency_level: Mapped[Optional[str]] = mapped_column(String(50))
    # beginner | intermediate | advanced | expert
    years_used: Mapped[Optional[float]] = mapped_column(Float)
    skill_source: Mapped[str] = mapped_column(String(50), default="ai_extracted")
    # ai_extracted | manually_added | verified

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="candidate_skills"
    )
    skill: Mapped["Skill"] = relationship("Skill", back_populates="candidate_skills")
