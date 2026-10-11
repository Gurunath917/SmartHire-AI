"""
AI Interview Answer Evaluator.

Evaluates a candidate's answer on:
  - technical_correctness (0–10): Is the answer factually correct?
  - relevance_score (0–10):       Does it answer the question asked?
  - completeness_score (0–10):    Does it cover the expected topics?
  - communication_score (0–10):   Is it clear and well-structured?
  - missing_concepts: list of key topics not mentioned

Primary: LLM evaluation with structured JSON output.
Fallback: Keyword-based scoring against expected_topics.
"""
from __future__ import annotations

from app.services.llm_client import call_llm, extract_json_from_response
from app.utils.logger import logger

_EVAL_SYSTEM_PROMPT = """You are an expert technical interviewer evaluating a candidate's answer.
Score the answer on these 4 dimensions (each 0.0 to 10.0):

1. technical_correctness: Is the answer factually accurate?
2. relevance_score: Does the answer address what was asked?
3. completeness_score: Does it cover the key expected topics?
4. communication_score: Is it clear, structured, and easy to understand?

Also identify:
- missing_concepts: list of key topics the candidate did NOT mention
- feedback: 1-2 sentences of constructive feedback

Return ONLY valid JSON. No prose outside JSON."""


def _build_eval_prompt(
    question_text: str,
    answer_text: str,
    expected_topics: list[str],
) -> str:
    topics_str = ", ".join(expected_topics) if expected_topics else "general understanding"
    return f"""Question: {question_text}

Expected key topics: {topics_str}

Candidate's Answer:
{answer_text}

Evaluate and return JSON with these exact keys:
{{
  "technical_correctness": <float 0-10>,
  "relevance_score": <float 0-10>,
  "completeness_score": <float 0-10>,
  "communication_score": <float 0-10>,
  "missing_concepts": [<list of strings>],
  "feedback": "<string>"
}}"""


def _keyword_fallback_score(
    answer_text: str,
    expected_topics: list[str],
) -> dict:
    """
    Simple keyword-based scoring when LLM is unavailable.
    Checks how many expected topics appear in the answer.
    """
    if not expected_topics:
        return {
            "technical_correctness": 5.0,
            "relevance_score":       6.0,
            "completeness_score":    5.0,
            "communication_score":   5.0,
            "missing_concepts":      [],
            "feedback": "Evaluation requires an LLM API key for detailed feedback.",
        }

    answer_lower = answer_text.lower()
    mentioned = [t for t in expected_topics if t.lower() in answer_lower]
    missing   = [t for t in expected_topics if t.lower() not in answer_lower]

    coverage = len(mentioned) / len(expected_topics)
    base = round(coverage * 10, 1)

    # Give partial credit for length (longer answers tend to be more complete)
    length_bonus = min(1.0, len(answer_text) / 500)
    adjusted = round(min(10.0, base + length_bonus), 1)

    return {
        "technical_correctness": adjusted,
        "relevance_score":       adjusted,
        "completeness_score":    base,
        "communication_score":   min(10.0, 5.0 + length_bonus * 3),
        "missing_concepts":      missing,
        "feedback": (
            f"You covered {len(mentioned)}/{len(expected_topics)} expected topics. "
            f"{'Good coverage!' if coverage >= 0.7 else 'Try to include more key concepts.'}"
            " (Note: Detailed AI feedback requires LLM API key.)"
        ),
    }


def evaluate_answer(
    question_text: str,
    answer_text: str,
    expected_topics: list[str],
) -> dict:
    """
    Evaluate a single interview answer.

    Returns:
        {
            technical_correctness : float 0–10
            relevance_score       : float 0–10
            completeness_score    : float 0–10
            communication_score   : float 0–10
            missing_concepts      : list[str]
            feedback              : str
        }
    """
    # Try LLM evaluation
    llm_response = call_llm(
        system_prompt=_EVAL_SYSTEM_PROMPT,
        user_prompt=_build_eval_prompt(question_text, answer_text, expected_topics),
        max_tokens=500,
        temperature=0.2,
        expect_json=True,
    )

    if llm_response:
        parsed = extract_json_from_response(llm_response)
        if isinstance(parsed, dict) and "technical_correctness" in parsed:
            # Clamp all scores to 0–10
            result = {
                "technical_correctness": float(min(10, max(0, parsed.get("technical_correctness", 5)))),
                "relevance_score":       float(min(10, max(0, parsed.get("relevance_score", 5)))),
                "completeness_score":    float(min(10, max(0, parsed.get("completeness_score", 5)))),
                "communication_score":   float(min(10, max(0, parsed.get("communication_score", 5)))),
                "missing_concepts":      list(parsed.get("missing_concepts", [])),
                "feedback":              str(parsed.get("feedback", "")),
            }
            logger.info("Answer evaluated via LLM.")
            return result

    # Fallback
    return _keyword_fallback_score(answer_text, expected_topics)


def generate_interview_evaluation(
    questions_and_answers: list[dict],
) -> dict:
    """
    Generate the final evaluation report for a completed interview.

    Args:
        questions_and_answers: list of {
            question_text, answer_text, expected_topics,
            technical_correctness, relevance_score,
            completeness_score, communication_score,
            missing_concepts, feedback
        }

    Returns:
        {
            technical_score:    float 0–100
            communication_score: float 0–100
            overall_score:      float 0–100
            strengths:          list[str]
            weaknesses:         list[str]
            recommended_topics: list[str]
            summary:            str
        }

    IMPORTANT: These scores are internal assessment scores only.
    They do NOT claim to predict job placement outcomes.
    """
    if not questions_and_answers:
        return {
            "technical_score": 0,
            "communication_score": 0,
            "overall_score": 0,
            "strengths": [],
            "weaknesses": ["No answers submitted"],
            "recommended_topics": [],
            "summary": "No answers were submitted for evaluation.",
        }

    # Aggregate per-answer scores
    tech_scores  = [qa.get("technical_correctness", 5) for qa in questions_and_answers]
    rel_scores   = [qa.get("relevance_score", 5) for qa in questions_and_answers]
    comp_scores  = [qa.get("completeness_score", 5) for qa in questions_and_answers]
    comm_scores  = [qa.get("communication_score", 5) for qa in questions_and_answers]

    avg_tech  = sum(tech_scores)  / len(tech_scores)
    avg_rel   = sum(rel_scores)   / len(rel_scores)
    avg_comp  = sum(comp_scores)  / len(comp_scores)
    avg_comm  = sum(comm_scores)  / len(comm_scores)

    # Scale to 0–100
    technical_score     = round(((avg_tech + avg_rel + avg_comp) / 3) * 10, 1)
    communication_score = round(avg_comm * 10, 1)
    overall_score       = round(0.70 * technical_score + 0.30 * communication_score, 1)

    # Collect all missing concepts across answers
    all_missing = []
    for qa in questions_and_answers:
        all_missing.extend(qa.get("missing_concepts", []))

    # De-duplicate and pick top recommended topics
    seen = set()
    recommended_topics = []
    for topic in all_missing:
        if topic.lower() not in seen:
            seen.add(topic.lower())
            recommended_topics.append(topic)
    recommended_topics = recommended_topics[:8]  # top 8

    # Strengths: high-scoring areas
    strengths = []
    if avg_tech >= 7:
        strengths.append("Strong technical knowledge demonstrated")
    if avg_comm >= 7:
        strengths.append("Clear and well-structured communication")
    if avg_comp >= 7:
        strengths.append("Good coverage of key concepts")
    if avg_rel >= 7:
        strengths.append("Answers were relevant and focused")
    if not strengths:
        strengths.append("Showed willingness to attempt all questions")

    # Weaknesses: low-scoring areas
    weaknesses = []
    if avg_tech < 5:
        weaknesses.append("Technical concepts need improvement")
    if avg_comp < 5:
        weaknesses.append("Answers lacked depth on key topics")
    if avg_comm < 5:
        weaknesses.append("Communication could be clearer and more structured")
    if avg_rel < 5:
        weaknesses.append("Some answers were not directly relevant to the questions")

    # Summary
    if overall_score >= 80:
        summary = "Excellent performance. Strong technical foundation and clear communication."
    elif overall_score >= 65:
        summary = "Good performance overall. Focus on the recommended topics to strengthen weak areas."
    elif overall_score >= 50:
        summary = "Moderate performance. Significant improvement needed in technical depth and coverage."
    else:
        summary = "More preparation needed. Study the recommended topics and practice explaining concepts clearly."

    return {
        "technical_score":    technical_score,
        "communication_score": communication_score,
        "overall_score":      overall_score,
        "strengths":          strengths,
        "weaknesses":         weaknesses,
        "recommended_topics": recommended_topics,
        "summary":            summary,
    }
