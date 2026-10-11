"""
Job Description Analyzer Service.

Uses spaCy PhraseMatcher + regex rules to extract:
- Required skills
- Preferred skills
- Experience years
- Tools & technologies
- Responsibilities
- Education requirements

This is purely rule-based NLP — no LLM call needed for this step.
LLM is used later in Phase 9 (RAG) for deeper analysis.
"""
import re
from typing import Optional

import spacy
from spacy.matcher import PhraseMatcher

from app.utils.logger import logger

# ── Configurable weights (used by matching engine) ───────────────────────────
WEIGHT_SEMANTIC   = 0.40
WEIGHT_SKILL      = 0.35
WEIGHT_EXPERIENCE = 0.15
WEIGHT_EDUCATION  = 0.10

# ── Lazy-loaded spaCy model ───────────────────────────────────────────────────
_nlp: Optional[spacy.Language] = None


def _get_nlp() -> spacy.Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    return _nlp


# ── Master skill vocabulary ───────────────────────────────────────────────────
ALL_KNOWN_SKILLS = [
    # Programming
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C", "Go",
    "Rust", "R", "SQL", "Bash", "Scala", "Kotlin", "Swift",
    # ML / AI
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "Scikit-learn", "TensorFlow", "PyTorch", "XGBoost", "LightGBM",
    "Keras", "SHAP", "Pandas", "NumPy", "Matplotlib", "Seaborn",
    # GenAI
    "LLM", "RAG", "LangChain", "LlamaIndex", "Transformers",
    "Embeddings", "Prompt Engineering", "FAISS", "ChromaDB", "OpenAI API",
    # Backend frameworks
    "FastAPI", "Flask", "Django", "Spring Boot", "Node.js", "Express.js",
    # Frontend frameworks
    "React", "Vue.js", "Angular", "Next.js", "HTML", "CSS", "Tailwind CSS",
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Elasticsearch",
    # Cloud
    "AWS", "Azure", "GCP", "Heroku",
    # DevOps / tools (only classified as "tool" — not stripped from required/preferred)
    "Git", "GitHub", "REST API", "GraphQL", "Postman", "Linux", "Jupyter",
    "Docker", "Kubernetes", "CI/CD", "Jenkins",
]

# Canonical alias map — always normalize before storing/comparing
SKILL_ALIASES: dict[str, str] = {
    # Python
    "python3": "Python",
    "python 3": "Python",
    # Scikit-learn
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "scikit-learn": "Scikit-learn",
    "sci-kit learn": "Scikit-learn",
    # TensorFlow
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "tensorflow 2": "TensorFlow",
    # PyTorch
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    # Node / JS
    "nodejs": "Node.js",
    "node js": "Node.js",
    "node": "Node.js",
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    "vuejs": "Vue.js",
    "vue js": "Vue.js",
    "angularjs": "Angular",
    "angular js": "Angular",
    "nextjs": "Next.js",
    "next js": "Next.js",
    "expressjs": "Express.js",
    "express": "Express.js",
    # FastAPI
    "fast api": "FastAPI",
    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    # Cloud
    "amazon web services": "AWS",
    "amazon aws": "AWS",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "microsoft azure": "Azure",
    # GenAI
    "llms": "LLM",
    "large language model": "LLM",
    "large language models": "LLM",
    "retrieval augmented generation": "RAG",
    "langchain": "LangChain",
    "openai": "OpenAI API",
    "chatgpt": "OpenAI API",
    "gpt": "OpenAI API",
    "huggingface": "Transformers",
    "hugging face": "Transformers",
    "vector database": "Embeddings",
    "vector databases": "Embeddings",
    "vector store": "Embeddings",
    # Tools
    "git hub": "GitHub",
    "rest": "REST API",
    "restful": "REST API",
    "restful api": "REST API",
    "jupyter notebook": "Jupyter",
    "vscode": "Git",
    "linux/unix": "Linux",
    "unix": "Linux",
    # ML
    "machine-learning": "Machine Learning",
    "deep-learning": "Deep Learning",
    "natural language processing": "NLP",
    # Misc
    "html5": "HTML",
    "css3": "CSS",
    "tailwind": "Tailwind CSS",
    "c/c++": "C++",
    "golang": "Go",
    "sklearn": "Scikit-learn",
    "xgb": "XGBoost",
}

# Preferred signal patterns — skills near these words become "preferred"
PREFERRED_SIGNALS = [
    r"\bpreferred\b",
    r"\bnice[\s-]to[\s-]have\b",
    r"\bbonus\b",
    r"\bdesirable\b",
    r"\badvantage\b",
    r"\boptional\b",
    r"\bideally\b",
    r"\bexposure\b",           # "Exposure to X preferred"
    r"\bfamiliarity\b",        # "Familiarity with X"
    r"\bplus\b",
]

# Required signal patterns — skills near these words become "required"
REQUIRED_SIGNALS = [
    r"\brequired\b",
    r"\bmust[\s-]have\b",
    r"\bmandatory\b",
    r"\bessential\b",
    r"\bnecessary\b",
    r"\bminimum\b",
    r"\bneeded\b",
    r"\bexpected\b",
    r"\bproficient\b",
    r"\bexperience\s+with\b",  # "Experience with X required"
    r"\bstrong\b",             # "Strong Python skills"
]

# Experience patterns
EXPERIENCE_PATTERNS = [
    r"(\d+)\+?\s*(?:to\s*\d+)?\s*years?\s*(?:of)?\s*(?:work)?\s*experience",
    r"(\d+)\s*-\s*(\d+)\s*years?",
    r"minimum\s+(\d+)\s*years?",
    r"at\s+least\s+(\d+)\s*years?",
    r"fresher|entry[\s-]level|0[\s-]1\s*years?",
]

# Education patterns
EDUCATION_PATTERNS = [
    r"b\.?\s*tech|bachelor[\s\']*s?\s*(?:degree)?(?:\s+in\s+\w+)?",
    r"m\.?\s*tech|master[\s\']*s?\s*(?:degree)?(?:\s+in\s+\w+)?",
    r"b\.?\s*e\.?|b\.?\s*sc\.?|m\.?\s*sc\.?",
    r"phd|ph\.?\s*d\.?",
    r"diploma",
    r"any\s+graduate|any\s+degree",
]

# Responsibility section triggers
RESPONSIBILITY_TRIGGERS = [
    "responsibilities", "what you will do", "your role", "key responsibilities",
    "job responsibilities", "duties", "what we expect", "you will",
    "role and responsibilities", "your responsibilities",
]


def normalize_skill_name(raw: str) -> str:
    """
    Normalize a raw skill name to its canonical form.
    e.g. 'sklearn' → 'Scikit-learn', 'tensorflow' → 'TensorFlow'
    """
    lower = raw.lower().strip()
    return SKILL_ALIASES.get(lower, raw.strip())


def _build_skill_matcher(nlp: spacy.Language) -> tuple[PhraseMatcher, dict]:
    """
    Build a spaCy PhraseMatcher from the canonical skill list + aliases.
    Returns (matcher, skill_lookup) where skill_lookup maps lowercase → canonical name.
    """
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    skill_lookup: dict[str, str] = {}

    # Add canonical names
    for skill in ALL_KNOWN_SKILLS:
        key = skill.lower()
        skill_lookup[key] = skill
        try:
            matcher.add(f"SKILL_{key}", [nlp.make_doc(key)])
        except Exception:
            pass

    # Add alias patterns mapping to canonical names
    for alias_lower, canonical in SKILL_ALIASES.items():
        canonical_lower = canonical.lower()
        # Register canonical in lookup if not already there
        if canonical_lower not in skill_lookup:
            skill_lookup[canonical_lower] = canonical
        try:
            matcher.add(f"SKILL_{canonical_lower}", [nlp.make_doc(alias_lower)])
        except Exception:
            pass

    return matcher, skill_lookup


def _extract_matched_skills(text: str, nlp, matcher, skill_lookup) -> list[str]:
    """
    Run the PhraseMatcher on lowercased text.
    Returns sorted list of canonical skill names found.
    """
    doc = nlp(text.lower())
    matches = matcher(doc)
    found: set[str] = set()

    for match_id, start, end in matches:
        key = nlp.vocab.strings[match_id]
        # key format: "SKILL_<canonical_lower>"
        canonical_lower = key.replace("SKILL_", "")
        if canonical_lower in skill_lookup:
            found.add(skill_lookup[canonical_lower])

    return sorted(found)


def _classify_skills(
    text: str,
    all_skills: list[str],
) -> tuple[list[str], list[str]]:
    """
    Classify each found skill as required or preferred using sentence-level context.

    Strategy:
    1. Split JD into sentences (newlines / periods)
    2. For each sentence, check for required/preferred signal words
    3. Any skill in a "preferred" sentence → preferred
    4. Any skill in a "required" sentence → required
    5. Tie-break: skill appears in BOTH → required wins
    6. Skill in neither signal sentence → default required

    This replaces the old ±150 char window which misclassified most skills as preferred
    when the word "preferred" appeared once at the end of the JD.
    """
    required: set[str] = set()
    preferred: set[str] = set()
    text_lower = text.lower()

    # Split into sentences for context analysis
    sentences = re.split(r'[.\n]+', text_lower)

    # Map each skill to sentences it appears in
    for skill in all_skills:
        skill_lower = skill.lower()
        in_required_sentence = False
        in_preferred_sentence = False

        for sentence in sentences:
            if skill_lower not in sentence:
                continue

            # Check if this sentence has required signals
            for pat in REQUIRED_SIGNALS:
                if re.search(pat, sentence):
                    in_required_sentence = True
                    break

            # Check if this sentence has preferred signals
            for pat in PREFERRED_SIGNALS:
                if re.search(pat, sentence):
                    in_preferred_sentence = True
                    break

        # Classification logic:
        # - Required signal wins over preferred signal (required > preferred)
        # - If only preferred → preferred
        # - If both or only required → required
        # - If neither → required (default)
        if in_preferred_sentence and not in_required_sentence:
            preferred.add(skill)
        else:
            required.add(skill)

    return sorted(required), sorted(preferred)


def _extract_experience(text: str) -> Optional[str]:
    """Extract experience requirement string from JD text."""
    text_lower = text.lower()
    for pattern in EXPERIENCE_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(0).strip()
    return None


def _extract_education(text: str) -> Optional[str]:
    """Extract education requirement from JD text."""
    text_lower = text.lower()
    for pattern in EDUCATION_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def _extract_responsibilities(text: str) -> list[str]:
    """Extract responsibility bullet points from JD text."""
    lines = text.split("\n")
    responsibilities = []
    in_responsibilities = False

    for line in lines:
        stripped = line.strip()
        line_lower = stripped.lower()

        if any(trigger in line_lower for trigger in RESPONSIBILITY_TRIGGERS):
            in_responsibilities = True
            continue

        if in_responsibilities and stripped and len(stripped) < 50:
            words = stripped.split()
            if len(words) <= 5 and stripped.endswith(":"):
                in_responsibilities = False
                continue

        if in_responsibilities and stripped:
            cleaned = re.sub(r"^[\•\-\*\–\—\d\.\)]+\s*", "", stripped).strip()
            if cleaned and len(cleaned) > 10:
                responsibilities.append(cleaned)

    return responsibilities[:10]


def analyze_job_description(description: str) -> dict:
    """
    Analyze a job description and extract structured requirements.

    Flow:
    1. Run PhraseMatcher to find all mentioned skills
    2. Classify each skill as required or preferred using sentence-level context
    3. Tools remain in required/preferred lists (NOT stripped out)
       — they are also copied to ai_extracted_tools for reference
    4. Technologies = all skills (required + preferred combined, for reference)
    5. Return structured dict

    FIX vs old version:
    - Old version stripped ALL matched skills into 'technologies', leaving required_skills=[]
    - New version: required_skills and preferred_skills are the PRIMARY output
      tools/technologies are ADDITIONAL reference fields, never replacing required/preferred

    Returns:
        {
            required_skills    : list[str],  ← primary — used for skill matching
            preferred_skills   : list[str],  ← secondary — bonus in matching
            experience_years   : str | None,
            tools              : list[str],  ← reference only (subset of required/preferred)
            technologies       : list[str],  ← reference only (all skills combined)
            responsibilities   : list[str],
            education          : str | None,
        }
    """
    nlp = _get_nlp()
    matcher, skill_lookup = _build_skill_matcher(nlp)

    # Step 1: Find all skills in the JD
    all_skills = _extract_matched_skills(description, nlp, matcher, skill_lookup)

    # Step 2: Classify required vs preferred using sentence-level context
    required_skills, preferred_skills = _classify_skills(description, all_skills)

    # Step 3: tools is a reference subset (skills that are devops/tooling type)
    TOOL_SET = {
        "Git", "GitHub", "Postman", "Linux", "Jupyter",
        "Docker", "Kubernetes", "Jenkins", "CI/CD",
    }
    tools = [s for s in (required_skills + preferred_skills) if s in TOOL_SET]

    # Step 4: technologies = all skills combined (reference field)
    technologies = sorted(set(required_skills + preferred_skills))

    result = {
        "required_skills": required_skills,     # PRIMARY — do NOT strip
        "preferred_skills": preferred_skills,   # SECONDARY
        "experience_years": _extract_experience(description),
        "tools": tools,                         # REFERENCE only
        "technologies": technologies,           # REFERENCE only
        "responsibilities": _extract_responsibilities(description),
        "education": _extract_education(description),
    }

    logger.info(
        "JD analyzed: required={} preferred={} tools={} experience={}",
        required_skills,
        preferred_skills,
        tools,
        result["experience_years"],
    )

    return result
