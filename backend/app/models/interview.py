"""
Interview models — AI mock interview questions, answers, and evaluations.
"""
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Text, ForeignKey, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class InterviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EVALUATED = "EVALUATED"


class QuestionType(str, enum.Enum):
    TECHNICAL = "TECHNICAL"
    CODING = "CODING"
    BEHAVIORAL = "BEHAVIORAL"
    PROJECT = "PROJECT"


class DifficultyLevel(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class ExperienceLevel(str, enum.Enum):
    FRESHER = "FRESHER"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id"), index=True, nullable=False
    )

    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    experience_level: Mapped[ExperienceLevel] = mapped_column(
        SAEnum(ExperienceLevel), default=ExperienceLevel.FRESHER
    )
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SAEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM
    )
    total_questions: Mapped[int] = mapped_column(Integer, default=10)
    interview_status: Mapped[InterviewStatus] = mapped_column(
        SAEnum(InterviewStatus), default=InterviewStatus.PENDING, index=True
    )

    # ── Overall evaluation scores ─────────────────────────────────────────
    technical_score: Mapped[Optional[float]] = mapped_column(Float)
    communication_score: Mapped[Optional[float]] = mapped_column(Float)
    overall_score: Mapped[Optional[float]] = mapped_column(Float)

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
        "CandidateProfile", back_populates="interviews"
    )
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        "InterviewQuestion", back_populates="interview", cascade="all, delete-orphan"
    )
    evaluation: Mapped[Optional["InterviewEvaluation"]] = relationship(
        "InterviewEvaluation", back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True, nullable=False)

    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)


    question_type: Mapped[QuestionType] = mapped_column(
        SAEnum(QuestionType, name="question_type"),
        nullable=False,
    )

    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SAEnum(DifficultyLevel, name="difficulty_level"),
        nullable=False,
    )


    expected_topics: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ─────────────────────────────────────────────────────
    interview: Mapped["Interview"] = relationship("Interview", back_populates="questions")
    answer: Mapped[Optional["InterviewAnswer"]] = relationship(
        "InterviewAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("interview_questions.id"), unique=True, index=True, nullable=False
    )

    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    time_taken_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # ── Per-answer AI scores ──────────────────────────────────────────────
    technical_correctness: Mapped[Optional[float]] = mapped_column(Float)  # 0–10
    relevance_score: Mapped[Optional[float]] = mapped_column(Float)        # 0–10
    completeness_score: Mapped[Optional[float]] = mapped_column(Float)     # 0–10
    communication_score: Mapped[Optional[float]] = mapped_column(Float)    # 0–10
    missing_concepts: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    feedback: Mapped[Optional[str]] = mapped_column(Text)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ─────────────────────────────────────────────────────
    question: Mapped["InterviewQuestion"] = relationship(
        "InterviewQuestion", back_populates="answer"
    )


class InterviewEvaluation(Base):
    __tablename__ = "interview_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id"), unique=True, index=True, nullable=False
    )

    # ── Summary scores ────────────────────────────────────────────────────
    technical_score: Mapped[float] = mapped_column(Float)
    communication_score: Mapped[float] = mapped_column(Float)
    overall_score: Mapped[float] = mapped_column(Float)

    # ── Structured feedback ───────────────────────────────────────────────
    strengths: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    recommended_topics: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ─────────────────────────────────────────────────────
    interview: Mapped["Interview"] = relationship("Interview", back_populates="evaluation")
