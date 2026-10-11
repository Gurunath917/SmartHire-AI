"""
Pydantic schemas for dashboard analytics endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Candidate Dashboard ───────────────────────────────────────────────────────

class SkillBadge(BaseModel):
    skill_name: str
    category: str


class JobMatchSummary(BaseModel):
    job_id: int
    job_title: str
    company: str
    overall_score: float
    score_label: str


class ApplicationSummary(BaseModel):
    job_id: int
    job_title: str
    company: str
    app_status: str
    applied_at: datetime


class InterviewSummary(BaseModel):
    interview_id: int
    target_role: str
    overall_score: Optional[float]
    interview_status: str
    created_at: datetime


class CandidateDashboard(BaseModel):
    # Profile
    full_name: str
    profile_completion_pct: int
    resume_ats_score: Optional[int]
    # Skills
    top_skills: list[SkillBadge]
    total_skills: int
    # Job matching
    top_matches: list[JobMatchSummary]
    total_matches: int
    # Applications
    recent_applications: list[ApplicationSummary]
    total_applications: int
    applications_by_status: dict
    # Interviews
    recent_interviews: list[InterviewSummary]
    avg_interview_score: Optional[float]
    # Roadmaps
    active_roadmaps: int
    completed_roadmaps: int
    # Saved jobs
    saved_jobs_count: int


# ── Recruiter Dashboard ───────────────────────────────────────────────────────

class JobStatItem(BaseModel):
    job_id: int
    job_title: str
    applicant_count: int
    avg_match_score: Optional[float]
    job_status: str


class SkillDistributionItem(BaseModel):
    skill_name: str
    count: int


class RecruiterDashboard(BaseModel):
    # Company
    company_name: Optional[str]
    full_name: str
    # Job stats
    total_jobs: int
    active_jobs: int
    draft_jobs: int
    closed_jobs: int
    # Applicant stats
    total_applicants: int
    shortlisted: int
    avg_match_score: Optional[float]
    # Per-job breakdown
    jobs_with_stats: list[JobStatItem]
    # Skill distribution among applicants
    top_applicant_skills: list[SkillDistributionItem]
    # Applications by status
    applications_by_status: dict


# ── Admin Dashboard ───────────────────────────────────────────────────────────

class AdminDashboard(BaseModel):
    # User counts
    total_users: int
    total_candidates: int
    total_recruiters: int
    # Content counts
    total_jobs: int
    active_jobs: int
    total_applications: int
    total_resumes: int
    total_interviews: int
    total_roadmaps: int
    total_chat_sessions: int
    # Recent activity (last 7 days)
    new_users_7d: int
    new_jobs_7d: int
    new_applications_7d: int
    # AI usage
    parsed_resumes: int
    generated_roadmaps: int
    evaluated_interviews: int
