"""
Analytics / Dashboard API routes.

GET /api/analytics/candidate   — candidate dashboard data
GET /api/analytics/recruiter   — recruiter dashboard data
GET /api/analytics/admin       — admin dashboard data (admin only)
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.candidate_profile import CandidateProfile
from app.models.recruiter_profile import RecruiterProfile
from app.models.job import Job, JobStatus
from app.models.skill import Skill, CandidateSkill
from app.models.application import Application, ApplicationStatus
from app.models.matching import MatchScore
from app.models.resume import Resume
from app.models.roadmap import LearningRoadmap, RoadmapStatus
from app.models.interview import Interview, InterviewStatus
from app.models.misc import SavedJob, ChatSession
from app.schemas.analytics import (
    CandidateDashboard, SkillBadge, JobMatchSummary,
    ApplicationSummary, InterviewSummary,
    RecruiterDashboard, JobStatItem, SkillDistributionItem,
    AdminDashboard,
)
from app.utils.dependencies import (
    get_current_user, get_current_candidate,
    get_current_recruiter, get_current_admin,
)
from app.utils.errors import not_found
from app.services.matching_engine import _score_label

router = APIRouter()


# ── GET /api/analytics/candidate ─────────────────────────────────────────────
@router.get(
    "/candidate",
    response_model=CandidateDashboard,
    summary="Candidate dashboard data",
)
def candidate_dashboard(
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Candidate profile")

    # ── Skills ────────────────────────────────────────────────────────────────
    skill_rows = (
        db.query(Skill.skill_name, Skill.category)
        .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
        .filter(CandidateSkill.candidate_profile_id == profile.id)
        .all()
    )
    top_skills = [
        SkillBadge(skill_name=r.skill_name, category=r.category)
        for r in skill_rows[:10]
    ]

    # ── Job matches ───────────────────────────────────────────────────────────
    match_rows = (
        db.query(MatchScore, Job)
        .join(Job, MatchScore.job_id == Job.id)
        .filter(MatchScore.candidate_profile_id == profile.id)
        .order_by(MatchScore.overall_score.desc())
        .limit(5)
        .all()
    )
    top_matches = [
        JobMatchSummary(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            overall_score=ms.overall_score,
            score_label=_score_label(ms.overall_score),
        )
        for ms, job in match_rows
    ]
    total_matches = db.query(MatchScore).filter(
        MatchScore.candidate_profile_id == profile.id
    ).count()

    # ── Applications ──────────────────────────────────────────────────────────
    app_rows = (
        db.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.candidate_profile_id == profile.id)
        .order_by(Application.applied_at.desc())
        .limit(5)
        .all()
    )
    recent_applications = [
        ApplicationSummary(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            app_status=app.app_status.value,
            applied_at=app.applied_at,
        )
        for app, job in app_rows
    ]
    total_applications = db.query(Application).filter(
        Application.candidate_profile_id == profile.id
    ).count()

    # Applications by status count
    status_counts = (
        db.query(Application.app_status, func.count(Application.id))
        .filter(Application.candidate_profile_id == profile.id)
        .group_by(Application.app_status)
        .all()
    )
    applications_by_status = {s.value: c for s, c in status_counts}

    # ── Interviews ────────────────────────────────────────────────────────────
    interview_rows = (
        db.query(Interview)
        .filter(Interview.candidate_profile_id == profile.id)
        .order_by(Interview.created_at.desc())
        .limit(3)
        .all()
    )
    recent_interviews = [
        InterviewSummary(
            interview_id=iv.id,
            target_role=iv.target_role,
            overall_score=iv.overall_score,
            interview_status=iv.interview_status.value,
            created_at=iv.created_at,
        )
        for iv in interview_rows
    ]
    avg_interview_score_row = (
        db.query(func.avg(Interview.overall_score))
        .filter(
            Interview.candidate_profile_id == profile.id,
            Interview.overall_score.isnot(None),
        )
        .scalar()
    )
    avg_interview_score = round(float(avg_interview_score_row), 1) if avg_interview_score_row else None

    # ── Roadmaps ──────────────────────────────────────────────────────────────
    active_roadmaps = db.query(LearningRoadmap).filter(
        LearningRoadmap.candidate_profile_id == profile.id,
        LearningRoadmap.roadmap_status.in_([RoadmapStatus.GENERATED, RoadmapStatus.IN_PROGRESS]),
    ).count()
    completed_roadmaps = db.query(LearningRoadmap).filter(
        LearningRoadmap.candidate_profile_id == profile.id,
        LearningRoadmap.roadmap_status == RoadmapStatus.COMPLETED,
    ).count()

    # ── Saved jobs ────────────────────────────────────────────────────────────
    saved_jobs_count = db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id
    ).count()

    return CandidateDashboard(
        full_name=current_user.full_name,
        profile_completion_pct=profile.profile_completion_pct or 0,
        resume_ats_score=profile.resume_ats_score,
        top_skills=top_skills,
        total_skills=len(skill_rows),
        top_matches=top_matches,
        total_matches=total_matches,
        recent_applications=recent_applications,
        total_applications=total_applications,
        applications_by_status=applications_by_status,
        recent_interviews=recent_interviews,
        avg_interview_score=avg_interview_score,
        active_roadmaps=active_roadmaps,
        completed_roadmaps=completed_roadmaps,
        saved_jobs_count=saved_jobs_count,
    )


# ── GET /api/analytics/recruiter ─────────────────────────────────────────────
@router.get(
    "/recruiter",
    response_model=RecruiterDashboard,
    summary="Recruiter dashboard data",
)
def recruiter_dashboard(
    current_user: User = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
):
    rec_profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not rec_profile:
        raise not_found("Recruiter profile")

    # ── Job stats ─────────────────────────────────────────────────────────────
    job_counts = (
        db.query(Job.job_status, func.count(Job.id))
        .filter(Job.recruiter_profile_id == rec_profile.id)
        .group_by(Job.job_status)
        .all()
    )
    jobs_by_status = {s.value: c for s, c in job_counts}
    total_jobs  = sum(jobs_by_status.values())
    active_jobs = jobs_by_status.get("ACTIVE", 0)
    draft_jobs  = jobs_by_status.get("DRAFT", 0)
    closed_jobs = jobs_by_status.get("CLOSED", 0)

    # ── Applicant stats ───────────────────────────────────────────────────────
    total_applicants = (
        db.query(func.count(Application.id))
        .join(Job, Application.job_id == Job.id)
        .filter(Job.recruiter_profile_id == rec_profile.id)
        .scalar()
    ) or 0

    shortlisted = (
        db.query(func.count(Application.id))
        .join(Job, Application.job_id == Job.id)
        .filter(
            Job.recruiter_profile_id == rec_profile.id,
            Application.app_status == ApplicationStatus.SHORTLISTED,
        )
        .scalar()
    ) or 0

    avg_score_row = (
        db.query(func.avg(MatchScore.overall_score))
        .join(Job, MatchScore.job_id == Job.id)
        .filter(Job.recruiter_profile_id == rec_profile.id)
        .scalar()
    )
    avg_match_score = round(float(avg_score_row), 1) if avg_score_row else None

    # ── Per-job breakdown ─────────────────────────────────────────────────────
    my_jobs = (
        db.query(Job)
        .filter(Job.recruiter_profile_id == rec_profile.id)
        .order_by(Job.created_at.desc())
        .limit(10)
        .all()
    )
    jobs_with_stats = []
    for job in my_jobs:
        app_count = db.query(func.count(Application.id)).filter(
            Application.job_id == job.id
        ).scalar() or 0

        avg_job_score = (
            db.query(func.avg(MatchScore.overall_score))
            .filter(MatchScore.job_id == job.id)
            .scalar()
        )
        jobs_with_stats.append(JobStatItem(
            job_id=job.id,
            job_title=job.title,
            applicant_count=app_count,
            avg_match_score=round(float(avg_job_score), 1) if avg_job_score else None,
            job_status=job.job_status.value,
        ))

    # ── Skill distribution among applicants ───────────────────────────────────
    skill_dist_rows = (
        db.query(Skill.skill_name, func.count(CandidateSkill.id).label("cnt"))
        .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
        .join(CandidateProfile, CandidateSkill.candidate_profile_id == CandidateProfile.id)
        .join(Application, Application.candidate_profile_id == CandidateProfile.id)
        .join(Job, Application.job_id == Job.id)
        .filter(Job.recruiter_profile_id == rec_profile.id)
        .group_by(Skill.skill_name)
        .order_by(func.count(CandidateSkill.id).desc())
        .limit(10)
        .all()
    )
    top_applicant_skills = [
        SkillDistributionItem(skill_name=r.skill_name, count=r.cnt)
        for r in skill_dist_rows
    ]

    # ── Applications by status ────────────────────────────────────────────────
    app_status_counts = (
        db.query(Application.app_status, func.count(Application.id))
        .join(Job, Application.job_id == Job.id)
        .filter(Job.recruiter_profile_id == rec_profile.id)
        .group_by(Application.app_status)
        .all()
    )
    applications_by_status = {s.value: c for s, c in app_status_counts}

    return RecruiterDashboard(
        company_name=rec_profile.company_name,
        full_name=current_user.full_name,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        draft_jobs=draft_jobs,
        closed_jobs=closed_jobs,
        total_applicants=total_applicants,
        shortlisted=shortlisted,
        avg_match_score=avg_match_score,
        jobs_with_stats=jobs_with_stats,
        top_applicant_skills=top_applicant_skills,
        applications_by_status=applications_by_status,
    )


# ── GET /api/analytics/admin ──────────────────────────────────────────────────
@router.get(
    "/admin",
    response_model=AdminDashboard,
    summary="Admin dashboard data (admin only)",
)
def admin_dashboard(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # ── User counts ───────────────────────────────────────────────────────────
    total_users      = db.query(func.count(User.id)).scalar() or 0
    total_candidates = db.query(func.count(User.id)).filter(
        User.user_role == UserRole.CANDIDATE
    ).scalar() or 0
    total_recruiters = db.query(func.count(User.id)).filter(
        User.user_role == UserRole.RECRUITER
    ).scalar() or 0

    # ── Content counts ────────────────────────────────────────────────────────
    total_jobs        = db.query(func.count(Job.id)).scalar() or 0
    active_jobs       = db.query(func.count(Job.id)).filter(
        Job.job_status == JobStatus.ACTIVE
    ).scalar() or 0
    total_applications = db.query(func.count(Application.id)).scalar() or 0
    total_resumes      = db.query(func.count(Resume.id)).scalar() or 0
    total_interviews   = db.query(func.count(Interview.id)).scalar() or 0
    total_roadmaps     = db.query(func.count(LearningRoadmap.id)).scalar() or 0
    total_chat_sessions = db.query(func.count(ChatSession.id)).scalar() or 0

    # ── 7-day activity ────────────────────────────────────────────────────────
    new_users_7d = db.query(func.count(User.id)).filter(
        User.created_at >= seven_days_ago
    ).scalar() or 0
    new_jobs_7d = db.query(func.count(Job.id)).filter(
        Job.created_at >= seven_days_ago
    ).scalar() or 0
    new_applications_7d = db.query(func.count(Application.id)).filter(
        Application.applied_at >= seven_days_ago
    ).scalar() or 0

    # ── AI usage stats ────────────────────────────────────────────────────────
    parsed_resumes = db.query(func.count(Resume.id)).filter(
        Resume.is_parsed == True
    ).scalar() or 0
    generated_roadmaps = db.query(func.count(LearningRoadmap.id)).filter(
        LearningRoadmap.roadmap_status != RoadmapStatus.PENDING
    ).scalar() or 0
    evaluated_interviews = db.query(func.count(Interview.id)).filter(
        Interview.interview_status == InterviewStatus.EVALUATED
    ).scalar() or 0

    return AdminDashboard(
        total_users=total_users,
        total_candidates=total_candidates,
        total_recruiters=total_recruiters,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_applications=total_applications,
        total_resumes=total_resumes,
        total_interviews=total_interviews,
        total_roadmaps=total_roadmaps,
        total_chat_sessions=total_chat_sessions,
        new_users_7d=new_users_7d,
        new_jobs_7d=new_jobs_7d,
        new_applications_7d=new_applications_7d,
        parsed_resumes=parsed_resumes,
        generated_roadmaps=generated_roadmaps,
        evaluated_interviews=evaluated_interviews,
    )
