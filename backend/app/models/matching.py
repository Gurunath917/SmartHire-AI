"""
Match score and skill gap models — AI matching results storage.
Scores are internal heuristics, NOT guaranteed hiring probabilities.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Float, ForeignKey, DateTime, JSON, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class MatchScore(Base):
    """Stores the multi-stage matching score between a candidate and a job."""
    __tablename__ = "match_scores"
    __table_args__ = (
        UniqueConstraint("candidate_profile_id", "job_id", name="uq_match_score"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id"), index=True, nullable=False
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True, nullable=False)

    # ── Score components ──────────────────────────────────────────────────
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)    # 0–100
    skill_match_score: Mapped[Optional[float]] = mapped_column(Float)       # 0–100
    semantic_similarity_score: Mapped[Optional[float]] = mapped_column(Float)  # 0–100
    experience_match_score: Mapped[Optional[float]] = mapped_column(Float)  # 0–100
    education_match_score: Mapped[Optional[float]] = mapped_column(Float)   # 0–100
    tfidf_score: Mapped[Optional[float]] = mapped_column(Float)             # raw cosine similarity

    # ── ML ranking score (from trained model) ────────────────────────────
    ml_rank_score: Mapped[Optional[float]] = mapped_column(Float)

    # ── Explainability (SHAP-style factors) ──────────────────────────────
    explanation: Mapped[Optional[dict]] = mapped_column(JSON)

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
        "CandidateProfile", back_populates="match_scores"
    )
    job: Mapped["Job"] = relationship("Job", back_populates="match_scores")


class SkillGap(Base):
    """Stores skill gap analysis results for a candidate vs a job."""
    __tablename__ = "skill_gaps"
    __table_args__ = (
        UniqueConstraint("candidate_profile_id", "job_id", name="uq_skill_gap"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id"), index=True, nullable=False
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True, nullable=False)

    matched_skills: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    missing_skills: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    partial_skills: Mapped[Optional[list]] = mapped_column(JSON, default=list)

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
        "CandidateProfile", back_populates="skill_gaps"
    )
    job: Mapped["Job"] = relationship("Job", back_populates="skill_gaps")
