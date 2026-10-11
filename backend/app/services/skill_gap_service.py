"""
Skill Gap Analysis Service.

Compares candidate skills against job required/preferred skills.
Returns:
  - matched_skills   : candidate has these
  - missing_skills   : candidate lacks these (required)
  - partial_skills   : candidate has similar but not exact match
  - preferred_gap    : candidate lacks these (preferred only)
"""
from typing import Optional
from app.utils.logger import logger

# Skill similarity groups — skills in the same group are "partial matches"
# e.g. candidate knows TensorFlow, job requires PyTorch → partial match
SKILL_GROUPS: list[set[str]] = [
    # Deep Learning frameworks
    {"TensorFlow", "PyTorch", "Keras"},
    # ML libraries
    {"Scikit-learn", "XGBoost", "LightGBM"},
    # Relational databases
    {"PostgreSQL", "MySQL", "SQLite"},
    # Cloud providers
    {"AWS", "Azure", "GCP"},
    # Frontend frameworks
    {"React", "Vue.js", "Angular"},
    # Backend frameworks
    {"FastAPI", "Flask", "Django"},
    # GenAI
    {"LangChain", "LlamaIndex"},
    {"FAISS", "ChromaDB"},
    # Programming languages
    {"Python", "R"},
    {"JavaScript", "TypeScript"},
    {"Java", "Kotlin"},
]


def _find_partial_match(skill: str, candidate_set: set[str]) -> Optional[str]:
    """
    Check if a candidate has a related skill in the same group.
    Returns the candidate's alternative skill name if found, else None.
    """
    skill_lower = skill.lower()
    for group in SKILL_GROUPS:
        group_lower = {s.lower() for s in group}
        if skill_lower in group_lower:
            # Check if candidate has any other skill in this group
            for candidate_skill in candidate_set:
                if candidate_skill.lower() in group_lower and candidate_skill.lower() != skill_lower:
                    return candidate_skill
    return None


def analyze_skill_gap(
    candidate_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str] = None,
) -> dict:
    """
    Perform skill gap analysis.

    Args:
        candidate_skills:  Skills the candidate has
        required_skills:   Skills the job requires (must-have)
        preferred_skills:  Skills the job prefers (nice-to-have)

    Returns:
        {
            matched_skills   : [...],   # candidate has, job requires
            missing_skills   : [...],   # candidate lacks, job requires
            partial_skills   : [...],   # candidate has similar skill
            preferred_gap    : [...],   # candidate lacks preferred skills
            match_percentage : float,   # % of required skills matched
            total_required   : int,
            total_matched    : int,
        }
    """
    preferred_skills = preferred_skills or []
    candidate_set = {s.lower().strip() for s in candidate_skills}
    candidate_original = {s.lower().strip(): s for s in candidate_skills}

    matched = []
    missing = []
    partial = []

    for skill in required_skills:
        skill_lower = skill.lower().strip()

        if skill_lower in candidate_set:
            matched.append(skill)
        else:
            # Check for partial match in same skill group
            alternative = _find_partial_match(skill, candidate_set)
            if alternative:
                partial.append({
                    "required": skill,
                    "candidate_has": candidate_original.get(alternative.lower(), alternative),
                    "note": f"You know {alternative} which is related to {skill}",
                })
            else:
                missing.append(skill)

    # Preferred skill gap
    preferred_gap = [
        s for s in preferred_skills
        if s.lower().strip() not in candidate_set
    ]

    total_required = len(required_skills)
    total_matched = len(matched) + len(partial)  # partial counts as half
    effective_matched = len(matched) + (len(partial) * 0.5)

    match_pct = round(
        (effective_matched / total_required * 100) if total_required > 0 else 100.0,
        2
    )

    logger.info(
        "Skill gap: matched={} missing={} partial={} match_pct={}%",
        len(matched), len(missing), len(partial), match_pct
    )

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "partial_skills": partial,
        "preferred_gap": preferred_gap,
        "match_percentage": match_pct,
        "total_required": total_required,
        "total_matched": len(matched),
    }
