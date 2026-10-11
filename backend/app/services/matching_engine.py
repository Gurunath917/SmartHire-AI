"""
AI Job Matching Engine — 3-stage pipeline.

Stage 1: TF-IDF + Cosine Similarity
Stage 2: Sentence Transformer semantic embeddings
Stage 3: Weighted final score

Weights (configurable constants):
    WEIGHT_SEMANTIC   = 0.40
    WEIGHT_SKILL      = 0.35
    WEIGHT_EXPERIENCE = 0.15
    WEIGHT_EDUCATION  = 0.10

All scores are normalized to 0–100.
IMPORTANT: Scores are internal heuristics — NOT guaranteed hiring probabilities.
"""
from __future__ import annotations

import re
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from app.utils.logger import logger

# ── Configurable weights ──────────────────────────────────────────────────────
WEIGHT_SEMANTIC   = 0.40
WEIGHT_SKILL      = 0.35
WEIGHT_EXPERIENCE = 0.15
WEIGHT_EDUCATION  = 0.10

# Fallback score when a component cannot be computed meaningfully
# (e.g. no required skills specified — neutral, not perfect)
NEUTRAL_SCORE = 0.5

# ── Model loading (lazy, cached) ─────────────────────────────────────────────
_embedding_model: Optional[SentenceTransformer] = None
_MODEL_NAME = "all-MiniLM-L6-v2"  # Fast, lightweight, good quality


def _get_embedding_model() -> SentenceTransformer:
    """Load the sentence transformer model once and cache it."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading sentence transformer model: {}", _MODEL_NAME)
        _embedding_model = SentenceTransformer(_MODEL_NAME)
        logger.info("Sentence transformer model loaded.")
    return _embedding_model


# ── Stage 1: TF-IDF Cosine Similarity ────────────────────────────────────────

def compute_tfidf_similarity(text1: str, text2: str) -> float:
    """
    Compute cosine similarity between two texts using TF-IDF.

    Returns:
        float between 0.0 and 1.0
    """
    if not text1.strip() or not text2.strip():
        return 0.0

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
        )
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(np.clip(score, 0.0, 1.0))
    except Exception as e:
        logger.warning("TF-IDF similarity failed: {}", e)
        return 0.0


# ── Stage 2: Semantic Embedding Similarity ────────────────────────────────────

def compute_semantic_similarity(text1: str, text2: str) -> float:
    """
    Compute semantic similarity using sentence transformers.

    Returns:
        float between 0.0 and 1.0
    """
    if not text1.strip() or not text2.strip():
        return 0.0

    try:
        model = _get_embedding_model()
        # Truncate to avoid token limit issues
        t1 = text1[:2000]
        t2 = text2[:2000]
        embeddings = model.encode([t1, t2], convert_to_numpy=True, show_progress_bar=False)
        # Cosine similarity via dot product of normalized vectors
        norm1 = embeddings[0] / (np.linalg.norm(embeddings[0]) + 1e-9)
        norm2 = embeddings[1] / (np.linalg.norm(embeddings[1]) + 1e-9)
        score = float(np.dot(norm1, norm2))
        return float(np.clip(score, 0.0, 1.0))
    except Exception as e:
        logger.warning("Semantic similarity failed: {}", e)
        return 0.0


# ── Stage 3: Skill Match Score ────────────────────────────────────────────────

def compute_skill_match_score(
    candidate_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str] = None,
) -> float:
    """
    Compute skill match score (0.0–1.0).

    Edge cases handled explicitly:
    - No required AND no preferred skills → NEUTRAL_SCORE (0.5), not 1.0
      A job with no specified skills cannot be assumed a perfect match.
    - No candidate skills → based on required skills only (0 matches = 0)
    - All required skills matched → 1.0
    - Required skills carry weight 0.7, preferred 0.3

    Returns float 0.0–1.0.
    """
    preferred_skills = preferred_skills or []
    candidate_set = {s.lower().strip() for s in candidate_skills}

    # Guard: no requirements at all → neutral score (not a perfect match)
    if not required_skills and not preferred_skills:
        return NEUTRAL_SCORE

    def skill_matches(skill: str) -> bool:
        return skill.lower().strip() in candidate_set

    # Required skills score (primary — weight 0.7 of total skill score)
    if required_skills:
        req_matched = sum(1 for s in required_skills if skill_matches(s))
        req_score = req_matched / len(required_skills)
    else:
        req_score = NEUTRAL_SCORE  # No required skills → neutral

    # Preferred skills score (secondary — weight 0.3 of total skill score)
    if preferred_skills:
        pref_matched = sum(1 for s in preferred_skills if skill_matches(s))
        pref_score = pref_matched / len(preferred_skills)
    else:
        pref_score = 0.0

    # Combine: if no preferred skills, score is purely required
    if preferred_skills:
        return float(0.7 * req_score + 0.3 * pref_score)
    return float(req_score)


# ── Experience Match Score ────────────────────────────────────────────────────

def compute_experience_match_score(
    candidate_years: float,
    required_experience_str: Optional[str],
) -> float:
    """
    Compare candidate's years of experience to job requirement.
    If no requirement specified → NEUTRAL_SCORE (not 1.0).
    Returns float 0.0–1.0.
    """
    if not required_experience_str:
        return NEUTRAL_SCORE  # No requirement → neutral (not perfect)

    if "fresher" in required_experience_str.lower() or "entry" in required_experience_str.lower():
        required_min = 0.0
    else:
        numbers = re.findall(r"\d+\.?\d*", required_experience_str)
        required_min = float(numbers[0]) if numbers else 0.0

    if required_min == 0.0:
        return 1.0
    if candidate_years >= required_min:
        return 1.0
    elif candidate_years >= required_min * 0.7:
        return 0.7
    elif candidate_years >= required_min * 0.5:
        return 0.4
    else:
        return 0.1


# ── Education Match Score ─────────────────────────────────────────────────────

def compute_education_match_score(
    candidate_degree: Optional[str],
    required_education: Optional[str],
) -> float:
    """
    Compare candidate's degree to job education requirement.
    If no requirement → NEUTRAL_SCORE (not 1.0).
    Returns float 0.0–1.0.
    """
    if not required_education:
        return NEUTRAL_SCORE  # No requirement → neutral
    if not candidate_degree:
        return 0.5  # Unknown — give partial credit

    degree_hierarchy = {
        "phd": 5, "ph.d": 5,
        "m.tech": 4, "mtech": 4, "m.e": 4, "m.sc": 4, "msc": 4, "master": 4,
        "b.tech": 3, "btech": 3, "b.e": 3, "b.sc": 3, "bsc": 3, "bachelor": 3,
        "diploma": 2,
        "any": 1,
    }

    def get_level(text: str) -> int:
        text_lower = text.lower()
        for key, level in degree_hierarchy.items():
            if key in text_lower:
                return level
        return 0

    candidate_level = get_level(candidate_degree)
    required_level = get_level(required_education)

    if required_level == 0:
        return 1.0
    if candidate_level >= required_level:
        return 1.0
    elif candidate_level == required_level - 1:
        return 0.7
    else:
        return 0.3


# ── Final Weighted Score ──────────────────────────────────────────────────────

def compute_match_score(
    candidate_text: str,
    job_text: str,
    candidate_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    candidate_years: float,
    required_experience_str: Optional[str],
    candidate_degree: Optional[str],
    required_education: Optional[str],
) -> dict:
    """
    Compute the full multi-stage match score.

    Weights:
        semantic_similarity : 0.50
        skill_match         : 0.30
        experience_match    : 0.10
        education_match     : 0.10

    Returns:
        {
            overall_score         : float (0–100),
            skill_match_score     : float (0–100),
            semantic_score        : float (0–100),
            experience_score      : float (0–100),
            education_score       : float (0–100),
            tfidf_score           : float (0–1),
            explanation           : dict
        }
    """
    # Stage 1: TF-IDF
    tfidf_raw = compute_tfidf_similarity(candidate_text, job_text)

    # Stage 2: Semantic similarity
    semantic_raw = compute_semantic_similarity(candidate_text, job_text)

    # Use max of TF-IDF and semantic for the semantic component
    # (TF-IDF can sometimes score higher for keyword-heavy resumes)
    combined_semantic = max(semantic_raw, tfidf_raw * 0.8)

    # Skill match
    skill_raw = compute_skill_match_score(candidate_skills, required_skills, preferred_skills)

    # Experience match
    exp_raw = compute_experience_match_score(candidate_years, required_experience_str)

    # Education match
    edu_raw = compute_education_match_score(candidate_degree, required_education)

    # Weighted final score (0–1) using configurable constants
    final_raw = (
        WEIGHT_SEMANTIC   * combined_semantic
        + WEIGHT_SKILL    * skill_raw
        + WEIGHT_EXPERIENCE * exp_raw
        + WEIGHT_EDUCATION  * edu_raw
    )

    # Convert to 0–100 scale
    def to_100(v: float) -> float:
        return round(float(np.clip(v * 100, 0, 100)), 2)

    overall = to_100(final_raw)
    skill_score = to_100(skill_raw)
    semantic_score = to_100(combined_semantic)
    exp_score = to_100(exp_raw)
    edu_score = to_100(edu_raw)

    # Build explanation (SHAP-style factors for UI display)
    explanation = _build_explanation(
        overall, skill_score, semantic_score, exp_score, edu_score,
        candidate_skills, required_skills
    )

    logger.info(
        "Match score computed: overall={} skill={} semantic={} exp={} edu={}",
        overall, skill_score, semantic_score, exp_score, edu_score
    )

    return {
        "overall_score": overall,
        "skill_match_score": skill_score,
        "semantic_similarity_score": semantic_score,
        "experience_match_score": exp_score,
        "education_match_score": edu_score,
        "tfidf_score": round(tfidf_raw, 4),
        "explanation": explanation,
    }


def _build_explanation(
    overall: float,
    skill_score: float,
    semantic_score: float,
    exp_score: float,
    edu_score: float,
    candidate_skills: list[str],
    required_skills: list[str],
) -> dict:
    """Build a human-readable explanation of the match score."""
    candidate_set = {s.lower() for s in candidate_skills}
    matched = [s for s in required_skills if s.lower() in candidate_set]
    missing = [s for s in required_skills if s.lower() not in candidate_set]

    factors = []

    if skill_score >= 70:
        factors.append({"factor": "Skill Match", "impact": "+", "value": skill_score})
    elif skill_score >= 40:
        factors.append({"factor": "Skill Match", "impact": "~", "value": skill_score})
    else:
        factors.append({"factor": "Skill Match", "impact": "-", "value": skill_score})

    if semantic_score >= 70:
        factors.append({"factor": "Profile Relevance", "impact": "+", "value": semantic_score})
    elif semantic_score >= 40:
        factors.append({"factor": "Profile Relevance", "impact": "~", "value": semantic_score})
    else:
        factors.append({"factor": "Profile Relevance", "impact": "-", "value": semantic_score})

    if exp_score >= 80:
        factors.append({"factor": "Experience", "impact": "+", "value": exp_score})
    elif exp_score >= 50:
        factors.append({"factor": "Experience", "impact": "~", "value": exp_score})
    else:
        factors.append({"factor": "Experience", "impact": "-", "value": exp_score})

    if edu_score >= 80:
        factors.append({"factor": "Education", "impact": "+", "value": edu_score})
    else:
        factors.append({"factor": "Education", "impact": "~", "value": edu_score})

    return {
        "factors": factors,
        "matched_skills": matched,
        "missing_skills": missing,
        "summary": _score_label(overall),
    }


def _score_label(score: float) -> str:
    if score >= 85:
        return "Excellent match"
    elif score >= 70:
        return "Strong match"
    elif score >= 55:
        return "Good match"
    elif score >= 40:
        return "Partial match"
    else:
        return "Low match"
