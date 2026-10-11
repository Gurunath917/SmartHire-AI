"""
Import all ORM models here so SQLAlchemy's metadata knows about every table.
This file must be imported before calling Base.metadata.create_all().
"""
from app.models.user import User, UserRole
from app.models.candidate_profile import CandidateProfile
from app.models.recruiter_profile import RecruiterProfile
from app.models.resume import Resume
from app.models.skill import Skill, CandidateSkill
from app.models.job import Job, JobSkill, EmploymentType, ExperienceLevel, JobStatus
from app.models.application import Application, ApplicationStatus
from app.models.matching import MatchScore, SkillGap
from app.models.roadmap import LearningRoadmap, RoadmapStatus
from app.models.interview import (
    Interview, InterviewQuestion, InterviewAnswer, InterviewEvaluation,
    InterviewStatus, QuestionType, DifficultyLevel
)
from app.models.misc import (
    SavedJob, Notification, NotificationType, Document,
    ChatSession, ChatMessage, MessageRole
)

__all__ = [
    "User", "UserRole",
    "CandidateProfile",
    "RecruiterProfile",
    "Resume",
    "Skill", "CandidateSkill",
    "Job", "JobSkill", "EmploymentType", "ExperienceLevel", "JobStatus",
    "Application", "ApplicationStatus",
    "MatchScore", "SkillGap",
    "LearningRoadmap", "RoadmapStatus",
    "Interview", "InterviewQuestion", "InterviewAnswer", "InterviewEvaluation",
    "InterviewStatus", "QuestionType", "DifficultyLevel",
    "SavedJob", "Notification", "NotificationType", "Document",
    "ChatSession", "ChatMessage", "MessageRole",
]
