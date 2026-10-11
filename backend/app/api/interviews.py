"""
AI Mock Interview API routes.

POST /api/interviews                      — start a new interview (generate questions)
GET  /api/interviews/{id}                 — get interview with questions
POST /api/interviews/{id}/answer          — submit an answer (auto-evaluated)
POST /api/interviews/{id}/evaluate        — generate final evaluation report
GET  /api/interviews/{id}/evaluation      — get saved evaluation report
GET  /api/interviews                      — list my interviews
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.interview import (
    Interview, InterviewQuestion, InterviewAnswer,
    InterviewEvaluation, InterviewStatus,
)
from app.models.candidate_profile import CandidateProfile
from app.schemas.interview import (
    InterviewCreateRequest,
    AnswerSubmitRequest,
    InterviewResponse,
    InterviewWithQuestionsResponse,
    QuestionResponse,
    AnswerResponse,
    EvaluationResponse,
)
from app.schemas.auth import MessageResponse
from app.services.interview_generator import generate_questions
from app.services.interview_evaluator import evaluate_answer, generate_interview_evaluation
from app.utils.dependencies import get_current_candidate
from app.utils.errors import not_found, forbidden, bad_request
from app.utils.logger import logger

router = APIRouter()


def _get_profile(current_user: User, db: Session) -> CandidateProfile:
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise not_found("Candidate profile")
    return profile


# ── POST /api/interviews ──────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=InterviewWithQuestionsResponse,
    status_code=201,
    summary="Start a new AI mock interview",
    description=(
        "Generates role-specific interview questions using AI. "
        "Questions are saved and returned immediately. "
        "Uses LLM if configured, falls back to a built-in question bank automatically."
    ),
)
def create_interview(
    body: InterviewCreateRequest,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_profile(current_user, db)

    # Create the interview record
    interview = Interview(
        candidate_profile_id=profile.id,
        target_role=body.target_role,
        experience_level=body.experience_level,
        difficulty=body.difficulty,
        total_questions=body.total_questions,
        interview_status=InterviewStatus.IN_PROGRESS,
    )
    db.add(interview)
    db.flush()  # get interview.id

    logger.info(
        "Interview started: id={} role='{}' level={} difficulty={} questions={}",
        interview.id, body.target_role, body.experience_level.value,
        body.difficulty.value, body.total_questions
    )

    # Generate questions
    questions_data = generate_questions(
        target_role=body.target_role,
        experience_level=body.experience_level.value,
        difficulty=body.difficulty.value,
        total_questions=body.total_questions,
    )

    # Persist questions
    question_objs = []
    for qdata in questions_data:
        q = InterviewQuestion(
            interview_id=interview.id,
            question_number=qdata["question_number"],
            question_text=qdata["question_text"],
            question_type=qdata.get("question_type"),
            difficulty=qdata.get("difficulty"),
            expected_topics=qdata.get("expected_topics", []),
        )
        db.add(q)
        question_objs.append(q)

    # Flush so DB assigns IDs to all question rows before we serialize them.
    # Without this, q.id is None and Pydantic raises a 422 validation error.
    db.flush()
    db.commit()
    db.refresh(interview)

    # Re-query questions after commit to avoid accessing expired ORM objects
    # (prevents N+1 lazy-load problem from post-commit expiry)
    refreshed_questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview.id)
        .order_by(InterviewQuestion.question_number)
        .all()
    )

    # Build response
    return InterviewWithQuestionsResponse(
        **InterviewResponse.model_validate(interview).model_dump(),
        questions=[QuestionResponse.model_validate(q) for q in refreshed_questions],
    )


# ── GET /api/interviews ───────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[InterviewResponse],
    summary="List my interviews",
)
def list_interviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_profile(current_user, db)

    interviews = (
        db.query(Interview)
        .filter(Interview.candidate_profile_id == profile.id)
        .order_by(Interview.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return interviews


# ── GET /api/interviews/{id} ──────────────────────────────────────────────────
@router.get(
    "/{interview_id}",
    response_model=InterviewWithQuestionsResponse,
    summary="Get an interview with all questions",
)
def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_profile(current_user, db)
    interview = db.query(Interview).filter(Interview.id == interview_id).first()

    if not interview:
        raise not_found("Interview")
    if interview.candidate_profile_id != profile.id:
        raise forbidden("You can only view your own interviews.")

    questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.question_number)
        .all()
    )

    return InterviewWithQuestionsResponse(
        **InterviewResponse.model_validate(interview).model_dump(),
        questions=[QuestionResponse.model_validate(q) for q in questions],
    )


# ── POST /api/interviews/{id}/answer ─────────────────────────────────────────
@router.post(
    "/{interview_id}/answer",
    response_model=AnswerResponse,
    summary="Submit and evaluate an answer",
    description=(
        "Submit an answer to a specific question. "
        "The AI evaluates it immediately on technical correctness, "
        "relevance, completeness, and communication. "
        "Re-submitting overwrites the previous answer."
    ),
)
def submit_answer(
    interview_id: int,
    body: AnswerSubmitRequest,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_profile(current_user, db)
    interview = db.query(Interview).filter(Interview.id == interview_id).first()

    if not interview:
        raise not_found("Interview")
    if interview.candidate_profile_id != profile.id:
        raise forbidden("You can only answer your own interviews.")
    if interview.interview_status == InterviewStatus.EVALUATED:
        raise bad_request("This interview is already evaluated. Start a new interview.")

    # Verify the question belongs to this interview
    question = db.query(InterviewQuestion).filter(
        InterviewQuestion.id == body.question_id,
        InterviewQuestion.interview_id == interview_id,
    ).first()
    if not question:
        raise not_found(f"Question {body.question_id} in this interview")

    # Evaluate the answer
    eval_result = evaluate_answer(
        question_text=question.question_text,
        answer_text=body.answer_text,
        expected_topics=question.expected_topics or [],
    )

    # Upsert answer (allow re-submission)
    existing = db.query(InterviewAnswer).filter(
        InterviewAnswer.question_id == body.question_id
    ).first()

    if existing:
        existing.answer_text            = body.answer_text
        existing.time_taken_seconds     = body.time_taken_seconds
        existing.technical_correctness  = eval_result["technical_correctness"]
        existing.relevance_score        = eval_result["relevance_score"]
        existing.completeness_score     = eval_result["completeness_score"]
        existing.communication_score    = eval_result["communication_score"]
        existing.missing_concepts       = eval_result["missing_concepts"]
        existing.feedback               = eval_result["feedback"]
        answer_obj = existing
    else:
        answer_obj = InterviewAnswer(
            question_id=body.question_id,
            answer_text=body.answer_text,
            time_taken_seconds=body.time_taken_seconds,
            technical_correctness=eval_result["technical_correctness"],
            relevance_score=eval_result["relevance_score"],
            completeness_score=eval_result["completeness_score"],
            communication_score=eval_result["communication_score"],
            missing_concepts=eval_result["missing_concepts"],
            feedback=eval_result["feedback"],
        )
        db.add(answer_obj)

    db.commit()
    db.refresh(answer_obj)

    logger.info(
        "Answer submitted: interview={} question={} tech_score={}",
        interview_id, body.question_id, eval_result["technical_correctness"]
    )
    return answer_obj


# ── POST /api/interviews/{id}/evaluate ───────────────────────────────────────
@router.post(
    "/{interview_id}/evaluate",
    response_model=EvaluationResponse,
    summary="Generate final evaluation report",
    description=(
        "Generate the overall interview evaluation report. "
        "Aggregates all answer scores into Technical, Communication, and Overall scores. "
        "Returns strengths, weaknesses, and recommended study topics. "
        "NOTE: These scores are internal assessments — not hiring decisions."
    ),
)
def evaluate_interview(
    interview_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_profile(current_user, db)
    interview = db.query(Interview).filter(Interview.id == interview_id).first()

    if not interview:
        raise not_found("Interview")
    if interview.candidate_profile_id != profile.id:
        raise forbidden("You can only evaluate your own interviews.")

    # Get all questions and their answers
    questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview_id)
        .all()
    )

    qa_pairs = []
    for q in questions:
        answer = db.query(InterviewAnswer).filter(
            InterviewAnswer.question_id == q.id
        ).first()
        if answer:
            qa_pairs.append({
                "question_text":         q.question_text,
                "answer_text":           answer.answer_text,
                "expected_topics":       q.expected_topics or [],
                "technical_correctness": answer.technical_correctness or 0,
                "relevance_score":       answer.relevance_score or 0,
                "completeness_score":    answer.completeness_score or 0,
                "communication_score":   answer.communication_score or 0,
                "missing_concepts":      answer.missing_concepts or [],
                "feedback":              answer.feedback or "",
            })

    if not qa_pairs:
        raise bad_request(
            "No answers submitted yet. "
            "Submit answers to at least a few questions before requesting evaluation."
        )

    # Generate evaluation
    eval_result = generate_interview_evaluation(qa_pairs)

    # Upsert evaluation record
    existing_eval = db.query(InterviewEvaluation).filter(
        InterviewEvaluation.interview_id == interview_id
    ).first()

    if existing_eval:
        existing_eval.technical_score     = eval_result["technical_score"]
        existing_eval.communication_score = eval_result["communication_score"]
        existing_eval.overall_score       = eval_result["overall_score"]
        existing_eval.strengths           = eval_result["strengths"]
        existing_eval.weaknesses          = eval_result["weaknesses"]
        existing_eval.recommended_topics  = eval_result["recommended_topics"]
        existing_eval.summary             = eval_result["summary"]
        eval_obj = existing_eval
    else:
        eval_obj = InterviewEvaluation(
            interview_id=interview_id,
            **eval_result,
        )
        db.add(eval_obj)

    # Update interview status and scores
    interview.interview_status  = InterviewStatus.EVALUATED
    interview.technical_score   = eval_result["technical_score"]
    interview.communication_score = eval_result["communication_score"]
    interview.overall_score     = eval_result["overall_score"]

    db.commit()
    db.refresh(eval_obj)

    logger.info(
        "Interview evaluated: id={} overall={} technical={} communication={}",
        interview_id, eval_result["overall_score"],
        eval_result["technical_score"], eval_result["communication_score"]
    )

    return EvaluationResponse(
        interview_id=interview_id,
        **eval_result,
    )


# ── GET /api/interviews/{id}/evaluation ──────────────────────────────────────
@router.get(
    "/{interview_id}/evaluation",
    response_model=EvaluationResponse,
    summary="Get saved evaluation report",
)
def get_evaluation(
    interview_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db),
):
    profile = _get_profile(current_user, db)
    interview = db.query(Interview).filter(Interview.id == interview_id).first()

    if not interview:
        raise not_found("Interview")
    if interview.candidate_profile_id != profile.id:
        raise forbidden("You can only view your own interview evaluations.")

    eval_obj = db.query(InterviewEvaluation).filter(
        InterviewEvaluation.interview_id == interview_id
    ).first()

    if not eval_obj:
        raise not_found(
            "Evaluation not found. "
            "POST /api/interviews/{id}/evaluate to generate the report first."
        )

    return EvaluationResponse(
        interview_id=interview_id,
        technical_score=eval_obj.technical_score,
        communication_score=eval_obj.communication_score,
        overall_score=eval_obj.overall_score,
        strengths=eval_obj.strengths or [],
        weaknesses=eval_obj.weaknesses or [],
        recommended_topics=eval_obj.recommended_topics or [],
        summary=eval_obj.summary,
    )
