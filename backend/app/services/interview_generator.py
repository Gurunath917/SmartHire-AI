"""
AI Interview Question Generator.

Generates role-specific interview questions using:
- Primary:  LLM (structured prompt → JSON array)
- Fallback: Rule-based question bank (works without API key)

Question types:
  TECHNICAL   — core ML/CS knowledge
  CODING      — algorithm/implementation problems
  BEHAVIORAL  — STAR-format soft skills
  PROJECT     — candidate's own project discussion
"""
from __future__ import annotations

from app.services.llm_client import call_llm, extract_json_from_response
from app.utils.logger import logger

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are an expert technical interviewer at a top technology company.
Generate realistic, role-specific interview questions.

Rules:
- Questions must be specific to the role and difficulty level
- Mix question types: TECHNICAL, CODING, BEHAVIORAL, PROJECT
- TECHNICAL: test conceptual knowledge
- CODING: ask to implement or explain code
- BEHAVIORAL: use STAR-format prompts
- PROJECT: ask them to explain a past project
- Output ONLY valid JSON. No prose outside JSON."""


def _build_question_prompt(
    target_role: str,
    experience_level: str,
    difficulty: str,
    total_questions: int,
) -> str:
    return f"""Generate {total_questions} interview questions for:
Role: {target_role}
Experience Level: {experience_level}
Difficulty: {difficulty}

Return a JSON array of exactly {total_questions} question objects.
Each object must have these exact keys:
- "question_number": integer (1 to {total_questions})
- "question_text": string (the actual question)
- "question_type": one of "TECHNICAL", "CODING", "BEHAVIORAL", "PROJECT"
- "difficulty": one of "EASY", "MEDIUM", "HARD"
- "expected_topics": array of 2-4 strings (key concepts the answer should cover)

Distribution: ~50% TECHNICAL, ~20% CODING, ~20% BEHAVIORAL, ~10% PROJECT
Return ONLY the JSON array, nothing else."""


# ── Rule-based fallback question bank ────────────────────────────────────────
_QUESTION_BANK: dict[str, list[dict]] = {
    "technical": [
        {
            "question_text": "Explain the bias-variance tradeoff in machine learning.",
            "question_type": "TECHNICAL",
            "expected_topics": ["bias", "variance", "underfitting", "overfitting", "model complexity"],
        },
        {
            "question_text": "What is the difference between supervised, unsupervised, and reinforcement learning?",
            "question_type": "TECHNICAL",
            "expected_topics": ["labeled data", "clustering", "reward signal", "examples"],
        },
        {
            "question_text": "How does gradient descent work? Explain the role of learning rate.",
            "question_type": "TECHNICAL",
            "expected_topics": ["loss function", "partial derivatives", "step size", "convergence"],
        },
        {
            "question_text": "What is overfitting and how do you prevent it?",
            "question_type": "TECHNICAL",
            "expected_topics": ["regularization", "dropout", "early stopping", "cross-validation", "more data"],
        },
        {
            "question_text": "Explain the transformer architecture and its key components.",
            "question_type": "TECHNICAL",
            "expected_topics": ["self-attention", "multi-head attention", "positional encoding", "feed-forward layers"],
        },
        {
            "question_text": "What is precision and recall? When would you prioritize one over the other?",
            "question_type": "TECHNICAL",
            "expected_topics": ["true positives", "false positives", "false negatives", "F1 score", "use cases"],
        },
        {
            "question_text": "How does Random Forest differ from a single Decision Tree?",
            "question_type": "TECHNICAL",
            "expected_topics": ["ensemble", "bagging", "feature randomness", "variance reduction"],
        },
        {
            "question_text": "Explain what RAG (Retrieval-Augmented Generation) is and when you would use it.",
            "question_type": "TECHNICAL",
            "expected_topics": ["retrieval", "vector database", "LLM grounding", "hallucination reduction"],
        },
        {
            "question_text": "What is cross-validation and why is it important?",
            "question_type": "TECHNICAL",
            "expected_topics": ["k-fold", "model selection", "data leakage prevention", "generalization"],
        },
        {
            "question_text": "What is the difference between L1 and L2 regularization?",
            "question_type": "TECHNICAL",
            "expected_topics": ["Lasso", "Ridge", "sparsity", "feature selection", "weight penalties"],
        },
    ],
    "coding": [
        {
            "question_text": "Write a Python function to compute the cosine similarity between two vectors.",
            "question_type": "CODING",
            "expected_topics": ["dot product", "magnitude", "numpy", "normalization"],
        },
        {
            "question_text": "Implement a simple linear regression from scratch using gradient descent in Python.",
            "question_type": "CODING",
            "expected_topics": ["hypothesis function", "MSE loss", "gradient update", "iterations"],
        },
        {
            "question_text": "Given a list of numbers, write Python code to normalize them to [0, 1] range.",
            "question_type": "CODING",
            "expected_topics": ["min-max normalization", "edge cases", "vectorization"],
        },
        {
            "question_text": "Write a function to split a dataset into training and test sets without using sklearn.",
            "question_type": "CODING",
            "expected_topics": ["random shuffle", "ratio", "reproducibility with seed"],
        },
    ],
    "behavioral": [
        {
            "question_text": "Tell me about a challenging ML project you worked on. What was the hardest part?",
            "question_type": "BEHAVIORAL",
            "expected_topics": ["specific project", "technical challenge", "how resolved", "outcome"],
        },
        {
            "question_text": "Describe a situation where your model performed poorly in production. How did you debug it?",
            "question_type": "BEHAVIORAL",
            "expected_topics": ["data drift", "debugging approach", "monitoring", "fix and outcome"],
        },
        {
            "question_text": "How do you stay updated with the latest developments in AI/ML?",
            "question_type": "BEHAVIORAL",
            "expected_topics": ["papers", "blogs", "courses", "communities", "practice"],
        },
        {
            "question_text": "Tell me about a time you had to explain a complex ML concept to a non-technical stakeholder.",
            "question_type": "BEHAVIORAL",
            "expected_topics": ["simplification", "analogies", "outcome", "communication skill"],
        },
    ],
    "project": [
        {
            "question_text": "Walk me through your most significant ML project. What problem did it solve?",
            "question_type": "PROJECT",
            "expected_topics": ["problem statement", "data", "model choice", "evaluation", "deployment"],
        },
        {
            "question_text": "What would you do differently if you rebuilt your most recent project from scratch?",
            "question_type": "PROJECT",
            "expected_topics": ["lessons learned", "technical improvements", "architecture decisions"],
        },
    ],
}


def _get_fallback_questions(
    total_questions: int,
    difficulty: str,
) -> list[dict]:
    """Build a question list from the rule-based question bank."""
    import random

    # Target distribution
    n_technical  = max(1, int(total_questions * 0.50))
    n_coding     = max(1, int(total_questions * 0.20))
    n_behavioral = max(1, int(total_questions * 0.20))
    n_project    = max(0, total_questions - n_technical - n_coding - n_behavioral)

    selected = []
    selected += random.sample(_QUESTION_BANK["technical"],  min(n_technical,  len(_QUESTION_BANK["technical"])))
    selected += random.sample(_QUESTION_BANK["coding"],     min(n_coding,     len(_QUESTION_BANK["coding"])))
    selected += random.sample(_QUESTION_BANK["behavioral"], min(n_behavioral, len(_QUESTION_BANK["behavioral"])))
    selected += random.sample(_QUESTION_BANK["project"],    min(n_project,    len(_QUESTION_BANK["project"])))

    # Trim or pad to exact count
    selected = selected[:total_questions]

    questions = []
    for i, q in enumerate(selected, 1):
        questions.append({
            "question_number": i,
            "question_text":   q["question_text"],
            "question_type":   q["question_type"],
            "difficulty":      difficulty,
            "expected_topics": q.get("expected_topics", []),
        })
    return questions


def generate_questions(
    target_role: str,
    experience_level: str,
    difficulty: str,
    total_questions: int,
) -> list[dict]:
    """
    Generate interview questions.

    Returns list of dicts with keys:
      question_number, question_text, question_type, difficulty, expected_topics
    """
    logger.info(
        "Generating {} questions: role='{}' level={} difficulty={}",
        total_questions, target_role, experience_level, difficulty
    )

    # Try LLM first
    llm_response = call_llm(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_build_question_prompt(
            target_role, experience_level, difficulty, total_questions
        ),
        max_tokens=3000,
        temperature=0.6,
        expect_json=True,
    )

    if llm_response:
        parsed = extract_json_from_response(llm_response)
        if isinstance(parsed, list) and len(parsed) > 0:
            # Validate and normalize
            questions = []
            for i, item in enumerate(parsed[:total_questions], 1):
                questions.append({
                    "question_number": i,
                    "question_text":   str(item.get("question_text", "")),
                    "question_type":   str(item.get("question_type", "TECHNICAL")).upper(),
                    "difficulty":      str(item.get("difficulty", difficulty)).upper(),
                    "expected_topics": list(item.get("expected_topics", [])),
                })
            logger.info("Questions generated via LLM: {}", len(questions))
            return questions
        else:
            logger.warning("LLM returned invalid questions format, using fallback.")

    # Fallback
    questions = _get_fallback_questions(total_questions, difficulty)
    logger.info("Questions generated via fallback: {}", len(questions))
    return questions
