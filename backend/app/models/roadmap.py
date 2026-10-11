"""
Learning roadmap model — LLM-generated personalized learning plan.
"""
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class RoadmapStatus(str, enum.Enum):
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class LearningRoadmap(Base):
    __tablename__ = "learning_roadmaps"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id"), index=True, nullable=False
    )

    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    missing_skills: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # ── Generated roadmap ─────────────────────────────────────────────────
    # List of weekly items: {week, topic, objectives, time_estimate, practice_task, project_task, resources}
    roadmap_data: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    total_weeks: Mapped[Optional[int]] = mapped_column()
    roadmap_status: Mapped[RoadmapStatus] = mapped_column(
        SAEnum(RoadmapStatus), default=RoadmapStatus.PENDING
    )
    generation_error: Mapped[Optional[str]] = mapped_column(Text)

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
        "CandidateProfile", back_populates="learning_roadmaps"
    )

    def __repr__(self) -> str:
        return f"<LearningRoadmap id={self.id} role={self.target_role} status={self.roadmap_status}>"
