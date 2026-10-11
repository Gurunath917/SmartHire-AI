"""
Pydantic schemas for AI Mock Interview endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.interview import (
    ExperienceLevel, DifficultyLevel, QuestionType,
    InterviewStatus,
)


# ── Request schemas ───────────────────────────────────────────────────────────

class InterviewCreateRequest(BaseModel):
    """Body for POST /api/interviews"""
    target_role: str = Field(..., min_length=2, max_length=255)
    experience_level: ExperienceLevel = ExperienceLevel.FRESHER
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    total_questions: int = Field(default=10, ge=3, le=20)

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_role": "AI/ML Engineer",
                "experience_level": "FRESHER",
                "difficulty": "MEDIUM",
                "total_questions": 10,
            }
        }
    }


class AnswerSubmitRequest(BaseModel):
    """Body for POST /api/interviews/{id}/answer"""
    question_id: int
    answer_text: str = Field(..., min_length=1, max_length=5000)
    time_taken_seconds: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "question_id": 1,
                "answer_text": "Machine learning is a subset of AI that enables systems to learn from data...",
                "time_taken_seconds": 120,
            }
        }
    }


# ── Response schemas ──────────────────────────────────────────────────────────

class QuestionResponse(BaseModel):
    """A single interview question."""
    id: int
    question_number: int
    question_text: str
    question_type: Optional[QuestionType]
    difficulty: Optional[DifficultyLevel]
    expected_topics: Optional[list]

    model_config = {"from_attributes": True}


class AnswerResponse(BaseModel):
    """Evaluated answer for a single question."""
    id: int
    question_id: int
    answer_text: str
    technical_correctness: Optional[float]
    relevance_score: Optional[float]
    completeness_score: Optional[float]
    communication_score: Optional[float]
    missing_concepts: Optional[list]
    feedback: Optional[str]
    submitted_at: datetime

    model_config = {"from_attributes": True}


class InterviewResponse(BaseModel):
    """Full interview with questions."""
    id: int
    candidate_profile_id: int
    target_role: str
    experience_level: ExperienceLevel
    difficulty: DifficultyLevel
    total_questions: int
    interview_status: InterviewStatus
    technical_score: Optional[float]
    communication_score: Optional[float]
    overall_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InterviewWithQuestionsResponse(InterviewResponse):
    """Interview plus all questions."""
    questions: list[QuestionResponse] = []


class EvaluationResponse(BaseModel):
    """Complete interview evaluation report."""
    interview_id: int
    technical_score: float
    communication_score: float
    overall_score: float
    strengths: list[str]
    weaknesses: list[str]
    recommended_topics: list[str]
    summary: Optional[str]

    model_config = {"from_attributes": True}
