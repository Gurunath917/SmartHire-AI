"""
Recruiter profile model.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class RecruiterProfile(Base):
    __tablename__ = "recruiter_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)

    # ── Company Info ──────────────────────────────────────────────────────
    company_name: Mapped[Optional[str]] = mapped_column(String(255))
    company_website: Mapped[Optional[str]] = mapped_column(String(512))
    company_size: Mapped[Optional[str]] = mapped_column(String(100))  # e.g. "50-200"
    industry: Mapped[Optional[str]] = mapped_column(String(255))
    company_location: Mapped[Optional[str]] = mapped_column(String(255))
    company_description: Mapped[Optional[str]] = mapped_column(Text)

    # ── Recruiter Info ────────────────────────────────────────────────────
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    job_title: Mapped[Optional[str]] = mapped_column(String(255))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="recruiter_profile")
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="recruiter_profile", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RecruiterProfile id={self.id} company={self.company_name}>"
