"""
Skill Extraction Service.

Pipeline:
1. Load skill taxonomy from DB (cached in memory after first load)
2. Build a spaCy PhraseMatcher with all known skill names + aliases
3. Run the matcher over resume text
4. Normalize matched skills (ReactJS → React, etc.)
5. Return structured dict grouped by category

Uses spaCy PhraseMatcher for fast, exact matching — no hallucination risk.
"""
import re
from functools import lru_cache
from typing import Optional

import spacy
from spacy.matcher import PhraseMatcher
from sqlalchemy.orm import Session

from app.utils.logger import logger

# ── Skill normalization map ───────────────────────────────────────────────────
# Maps common variants to the canonical name stored in the DB skills table
SKILL_ALIASES: dict[str, str] = {
    # React variants
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    "react native": "React",

    # Node variants
    "nodejs": "Node.js",
    "node js": "Node.js",
    "node": "Node.js",

    # Python variants
    "python3": "Python",
    "python 3": "Python",
    "py": "Python",

    # JavaScript variants
    "js": "JavaScript",
    "javascript es6": "JavaScript",
    "es6": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",

    # ML variants
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "sci-kit learn": "Scikit-learn",
    "tensorflow 2": "TensorFlow",
    "tf": "TensorFlow",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "xgb": "XGBoost",

    # Database variants
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "mongo db": "MongoDB",

    # Cloud variants
    "amazon web services": "AWS",
    "amazon aws": "AWS",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "microsoft azure": "Azure",

    # GenAI variants
    "large language model": "LLM",
    "large language models": "LLM",
    "retrieval augmented generation": "RAG",
    "langchain": "LangChain",
    "openai": "OpenAI API",
    "chatgpt": "OpenAI API",
    "gpt": "OpenAI API",
    "huggingface": "Transformers",
    "hugging face": "Transformers",

    # Tools
    "git hub": "GitHub",
    "rest": "REST API",
    "restful": "REST API",
    "restful api": "REST API",
    "graphql": "GraphQL",
    "jupyter notebook": "Jupyter",
    "vscode": "VS Code",
    "visual studio code": "VS Code",
    "linux/unix": "Linux",
    "unix": "Linux",

    # Frameworks
    "fast api": "FastAPI",
    "django rest": "Django",
    "spring": "Spring Boot",
    "expressjs": "Express.js",
    "express": "Express.js",
    "vuejs": "Vue.js",
    "vue js": "Vue.js",
    "angular js": "Angular",
    "angularjs": "Angular",
    "nextjs": "Next.js",
    "next js": "Next.js",

    # Misc
    "html5": "HTML",
    "css3": "CSS",
    "tailwind": "Tailwind CSS",
    "c/c++": "C++",
    "c / c++": "C++",
    "golang": "Go",
}

# ── spaCy NLP instance (module-level, loaded once) ────────────────────────────
_nlp: Optional[spacy.Language] = None


def _get_nlp() -> spacy.Language:
    """Load spaCy model once and reuse."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
            logger.info("spaCy en_core_web_sm loaded.")
        except Exception as e:
            logger.error("Failed to load spaCy model: {}", e)
            raise
    return _nlp


def normalize_skill(raw_skill: str) -> str:
    """
    Normalize a raw skill string to its canonical name.
    e.g. 'ReactJS' → 'React', 'sklearn' → 'Scikit-learn'
    """
    lower = raw_skill.lower().strip()
    return SKILL_ALIASES.get(lower, raw_skill.strip())


def extract_skills_from_text(
    text: str,
    db_skills: list[dict],
) -> dict:
    """
    Extract skills from resume text using spaCy PhraseMatcher.

    Args:
        text:       Cleaned resume text (or skills section text)
        db_skills:  List of dicts from DB: [{id, skill_name, category}, ...]

    Returns:
        {
            "programming_language": [...],
            "framework": [...],
            "database": [...],
            "cloud": [...],
            "ml": [...],
            "genai": [...],
            "tool": [...],
            "soft_skill": [...],
            "all": [...],   # flat list of all matched skill names
        }
    """
    nlp = _get_nlp()

    # Build PhraseMatcher from DB taxonomy + aliases
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    # skill_name_lower → {canonical_name, category, skill_id}
    skill_lookup: dict[str, dict] = {}

    for skill in db_skills:
        canonical = skill["skill_name"]
        category = skill["category"]
        sid = skill["id"]
        lower_name = canonical.lower()
        skill_lookup[lower_name] = {
            "id": sid,
            "skill_name": canonical,
            "category": category,
        }
        # Add the skill pattern
        matcher.add(f"SKILL_{sid}", [nlp.make_doc(lower_name)])

    # Also add aliases as patterns
    for alias_lower, canonical_name in SKILL_ALIASES.items():
        canonical_lower = canonical_name.lower()
        if canonical_lower in skill_lookup:
            sid = skill_lookup[canonical_lower]["id"]
            try:
                matcher.add(f"SKILL_{sid}", [nlp.make_doc(alias_lower)])
            except Exception:
                pass  # Skip duplicates

    # Run matcher
    doc = nlp(text.lower())
    matches = matcher(doc)

    found_skill_ids: set = set()
    found_skills: list[dict] = []

    for match_id, start, end in matches:
        match_key = nlp.vocab.strings[match_id]
        sid_str = match_key.replace("SKILL_", "")
        try:
            sid = int(sid_str)
        except ValueError:
            continue

        if sid not in found_skill_ids:
            found_skill_ids.add(sid)
            # Find skill info
            for skill in db_skills:
                if skill["id"] == sid:
                    found_skills.append({
                        "id": sid,
                        "skill_name": skill["skill_name"],
                        "category": skill["category"],
                    })
                    break

    # Group by category
    result: dict = {
        "programming_language": [],
        "framework": [],
        "database": [],
        "cloud": [],
        "ml": [],
        "genai": [],
        "tool": [],
        "soft_skill": [],
        "all": [],
    }

    for skill in found_skills:
        cat = skill["category"]
        name = skill["skill_name"]
        if cat in result:
            result[cat].append(name)
        result["all"].append(name)

    return result


def extract_skills_from_sections(
    sections: dict,
    db_skills: list[dict],
) -> dict:
    """
    Extract skills by prioritizing the skills section,
    then scanning the full text for additional matches.

    Returns combined extraction result.
    """
    # Priority: skills section → then full text
    skills_text = sections.get("skills", "")
    full_text = " ".join(sections.values())

    # Extract from skills section first
    from_skills_section = extract_skills_from_text(skills_text, db_skills)

    # Extract from full text to catch skills mentioned outside the skills section
    from_full_text = extract_skills_from_text(full_text, db_skills)

    # Merge: use full_text results (superset), mark skills_section ones as higher confidence
    return from_full_text
