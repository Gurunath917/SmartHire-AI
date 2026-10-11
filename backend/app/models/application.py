"""
Application model — candidate applies to a job.
"""
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Text, ForeignKey, DateTime, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class ApplicationStatus(str, enum.Enum):
    APPLIED = "APPLIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    OFFERED = "OFFERED"


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("candidate_profile_id", "job_id", name="uq_application"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id"), index=True, nullable=False
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True, nullable=False)

    app_status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus), default=ApplicationStatus.APPLIED, index=True
    )
    cover_letter: Mapped[Optional[str]] = mapped_column(Text)
    recruiter_notes: Mapped[Optional[str]] = mapped_column(Text)

    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="applications"
    )
    job: Mapped["Job"] = relationship("Job", back_populates="applications")

    def __repr__(self) -> str:
        return f"<Application id={self.id} candidate={self.candidate_profile_id} job={self.job_id} status={self.app_status}>"
