"""
Roadmap Generator Service.

Primary path:   LLM generates a structured week-by-week learning roadmap.
Fallback path:  Rule-based generator (used when LLM_API_KEY not set or call fails).

Output format per week:
    {
        "week": 1,
        "topic": "...",
        "objectives": ["...", "..."],
        "time_estimate": "8-10 hours",
        "practice_task": "...",
        "project_task": "...",
        "resources": ["...", "..."],
        "is_completed": false
    }

IMPORTANT:
- Do NOT claim job placement outcomes from the roadmap.
- Roadmap is a personalized learning suggestion, not a guarantee.
"""
from __future__ import annotations

from typing import Optional

from app.services.llm_client import call_llm, extract_json_from_response
from app.utils.logger import logger


# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are an expert technical career coach and curriculum designer.
You create structured, practical, week-by-week learning roadmaps for software engineers and AI/ML professionals.

Your roadmaps must:
- Be realistic and achievable (8-12 hours per week)
- Focus on practical skills, not just theory
- Include hands-on practice tasks and mini-project tasks
- Recommend specific, real learning resources (courses, docs, tutorials)
- Be tailored to the target role and the specific missing skills

IMPORTANT:
- Do NOT promise job placement or guaranteed outcomes.
- Each skill should build on previous weeks logically.
- Output ONLY valid JSON. No prose, no markdown, no explanation outside JSON."""


def _build_user_prompt(
    target_role: str,
    missing_skills: list[str],
    weeks: int,
) -> str:
    skills_str = ", ".join(missing_skills)
    return f"""Create a {weeks}-week personalized learning roadmap for a candidate aiming for the role: "{target_role}"

They need to learn these skills: {skills_str}

Return a JSON array of exactly {weeks} week objects. Each object must have these exact keys:
- "week": integer (1 to {weeks})
- "topic": string (what is being learned this week)
- "objectives": array of 2-4 strings (specific learning goals)
- "time_estimate": string (e.g., "8-10 hours")
- "practice_task": string (a concrete hands-on exercise)
- "project_task": string (a small project or deliverable)
- "resources": array of 2-3 strings (specific resource names or URLs)
- "is_completed": false

Distribute the skills logically across weeks. Start with foundational topics and build up.
Return ONLY the JSON array, nothing else."""


# ── Rule-based fallback ───────────────────────────────────────────────────────
# Pre-built learning templates for common skills.
# Used when LLM is unavailable.

_SKILL_TEMPLATES: dict[str, dict] = {
    "PyTorch": {
        "topic": "PyTorch Fundamentals",
        "objectives": ["Understand tensors and autograd", "Build a simple neural network", "Train and evaluate a model"],
        "time_estimate": "10-12 hours",
        "practice_task": "Implement linear regression using PyTorch tensors",
        "project_task": "Train an image classifier on CIFAR-10 dataset",
        "resources": ["PyTorch Official Tutorials (pytorch.org)", "Deep Learning with PyTorch (book)", "fast.ai Practical Deep Learning"],
    },
    "TensorFlow": {
        "topic": "TensorFlow and Keras",
        "objectives": ["Build models with Keras Sequential API", "Understand training loops", "Save and load models"],
        "time_estimate": "10-12 hours",
        "practice_task": "Build a regression model on the Boston Housing dataset",
        "project_task": "Create an image classification pipeline with data augmentation",
        "resources": ["TensorFlow Official Tutorials (tensorflow.org)", "Hands-On ML with Scikit-Learn and TensorFlow (book)", "Google ML Crash Course"],
    },
    "Docker": {
        "topic": "Docker Containerization",
        "objectives": ["Understand containers vs VMs", "Write Dockerfiles", "Build and run Docker images"],
        "time_estimate": "8-10 hours",
        "practice_task": "Containerize a FastAPI application with a Dockerfile",
        "project_task": "Create a multi-service app with docker-compose (API + database)",
        "resources": ["Docker Official Docs (docs.docker.com)", "Docker Deep Dive (book by Nigel Poulton)", "Play with Docker (labs.play-with-docker.com)"],
    },
    "AWS": {
        "topic": "AWS Cloud Fundamentals",
        "objectives": ["Understand core AWS services (EC2, S3, Lambda)", "Deploy a web application to AWS", "Manage IAM users and roles"],
        "time_estimate": "10-12 hours",
        "practice_task": "Host a static website on S3 with CloudFront",
        "project_task": "Deploy a FastAPI app on EC2 with RDS database",
        "resources": ["AWS Free Tier (aws.amazon.com)", "AWS Certified Cloud Practitioner Study Guide", "A Cloud Guru AWS courses"],
    },
    "RAG": {
        "topic": "Retrieval-Augmented Generation (RAG)",
        "objectives": ["Understand RAG architecture", "Build a document ingestion pipeline", "Connect retrieval to LLM generation"],
        "time_estimate": "10-12 hours",
        "practice_task": "Build a Q&A system over a set of PDF documents using FAISS",
        "project_task": "Create a RAG-powered chatbot that answers questions from a knowledge base",
        "resources": ["LangChain Docs (python.langchain.com)", "LlamaIndex Docs (docs.llamaindex.ai)", "RAG from scratch (YouTube - LangChain channel)"],
    },
    "LangChain": {
        "topic": "LangChain for LLM Applications",
        "objectives": ["Understand chains, agents, and memory", "Build a conversational chain", "Integrate with vector stores"],
        "time_estimate": "8-10 hours",
        "practice_task": "Build a document Q&A chain with LangChain and OpenAI",
        "project_task": "Create an agent that can search the web and answer questions",
        "resources": ["LangChain Python Docs", "LangChain Cookbook (GitHub)", "LangChain YouTube tutorials"],
    },
    "Kubernetes": {
        "topic": "Kubernetes Orchestration",
        "objectives": ["Understand pods, deployments, services", "Deploy an app to a local cluster", "Configure scaling and rolling updates"],
        "time_estimate": "12-15 hours",
        "practice_task": "Deploy a containerized app using kubectl on Minikube",
        "project_task": "Set up a multi-replica deployment with load balancing and health checks",
        "resources": ["Kubernetes Official Docs (kubernetes.io)", "Kubernetes Up and Running (book)", "KodeKloud Kubernetes Course"],
    },
    "PostgreSQL": {
        "topic": "PostgreSQL Database",
        "objectives": ["Write complex SQL queries", "Design normalized schemas", "Use indexes and query optimization"],
        "time_estimate": "8-10 hours",
        "practice_task": "Design and query a schema for an e-commerce system",
        "project_task": "Optimize slow queries using EXPLAIN ANALYZE and indexes",
        "resources": ["PostgreSQL Official Docs", "Mode SQL Tutorial (mode.com/sql-tutorial)", "pgExercises (pgexercises.com)"],
    },
    "React": {
        "topic": "React Frontend Development",
        "objectives": ["Understand components, state, and props", "Use React hooks effectively", "Fetch data from REST APIs"],
        "time_estimate": "10-12 hours",
        "practice_task": "Build a todo app with CRUD operations using React hooks",
        "project_task": "Create a dashboard UI that fetches and displays live API data",
        "resources": ["React Official Docs (react.dev)", "Scrimba React Course", "Full Stack Open (fullstackopen.com)"],
    },
    "FastAPI": {
        "topic": "FastAPI Backend Development",
        "objectives": ["Build REST APIs with FastAPI", "Use Pydantic for validation", "Add JWT authentication"],
        "time_estimate": "8-10 hours",
        "practice_task": "Build a CRUD API for a todo application with SQLAlchemy",
        "project_task": "Add JWT auth, pagination, and error handling to a REST API",
        "resources": ["FastAPI Official Docs (fastapi.tiangolo.com)", "Full Stack FastAPI (GitHub template)", "TestDriven.io FastAPI tutorial"],
    },
    "Machine Learning": {
        "topic": "Machine Learning Fundamentals",
        "objectives": ["Understand supervised vs unsupervised learning", "Train and evaluate sklearn models", "Handle overfitting with cross-validation"],
        "time_estimate": "10-12 hours",
        "practice_task": "Train a classification model on the Titanic dataset",
        "project_task": "Build an end-to-end ML pipeline: EDA → feature engineering → model → evaluation",
        "resources": ["Hands-On ML with Scikit-Learn (book)", "scikit-learn User Guide (scikit-learn.org)", "Kaggle Learn ML Courses"],
    },
    "Scikit-learn": {
        "topic": "Scikit-learn ML Library",
        "objectives": ["Use Pipeline API for preprocessing + model", "Perform hyperparameter tuning with GridSearchCV", "Evaluate with cross_val_score"],
        "time_estimate": "8-10 hours",
        "practice_task": "Build a classification pipeline with StandardScaler + SVM",
        "project_task": "Tune an XGBoost classifier using RandomizedSearchCV on a Kaggle dataset",
        "resources": ["scikit-learn User Guide", "scikit-learn Examples Gallery", "Kaggle ML datasets"],
    },
    "NLP": {
        "topic": "Natural Language Processing",
        "objectives": ["Understand tokenization, embeddings, and transformers", "Use spaCy for NER and text classification", "Fine-tune a BERT model"],
        "time_estimate": "10-12 hours",
        "practice_task": "Build a text classifier using TF-IDF + Logistic Regression",
        "project_task": "Create a named entity recognition pipeline using spaCy",
        "resources": ["Hugging Face NLP Course (huggingface.co/course)", "spaCy Docs (spacy.io)", "Natural Language Processing with Python (NLTK book)"],
    },
    "default": {
        "topic": "{skill} Fundamentals",
        "objectives": ["Understand core concepts of {skill}", "Build a practical project using {skill}", "Integrate {skill} with existing tech stack"],
        "time_estimate": "8-10 hours",
        "practice_task": "Complete an introductory hands-on tutorial for {skill}",
        "project_task": "Build a small project that uses {skill} in a real scenario",
        "resources": ["Official {skill} documentation", "{skill} tutorial on YouTube", "Relevant Udemy or Coursera course for {skill}"],
    },
}


def _get_template(skill: str) -> dict:
    """Return a learning template for a skill, falling back to default."""
    # Direct match
    if skill in _SKILL_TEMPLATES:
        return _SKILL_TEMPLATES[skill]
    # Case-insensitive match
    for key, template in _SKILL_TEMPLATES.items():
        if key.lower() == skill.lower():
            return template
    # Default template with skill name substituted
    default = _SKILL_TEMPLATES["default"]
    return {k: (v.replace("{skill}", skill) if isinstance(v, str)
                else [i.replace("{skill}", skill) for i in v])
            for k, v in default.items()}


def _generate_fallback_roadmap(
    target_role: str,
    missing_skills: list[str],
) -> list[dict]:
    """
    Rule-based roadmap generator.
    Used when LLM is unavailable.
    Groups skills into weeks (1-2 skills per week).
    """
    roadmap = []
    week = 1

    # Group skills: 1 skill per week for complex skills, batch simple ones
    for i, skill in enumerate(missing_skills):
        template = _get_template(skill)
        roadmap.append({
            "week": week,
            "topic": template["topic"],
            "objectives": template["objectives"],
            "time_estimate": template["time_estimate"],
            "practice_task": template["practice_task"],
            "project_task": template["project_task"],
            "resources": template["resources"],
            "is_completed": False,
        })
        week += 1

    # Add a final integration week if there are multiple skills
    if len(missing_skills) > 2:
        skills_summary = ", ".join(missing_skills[:3])
        roadmap.append({
            "week": week,
            "topic": f"Integration Project — {target_role}",
            "objectives": [
                f"Combine {skills_summary} in a real project",
                "Document your work and push to GitHub",
                "Prepare to explain your project in an interview",
            ],
            "time_estimate": "12-15 hours",
            "practice_task": "Build a portfolio project integrating all learned skills",
            "project_task": f"Complete an end-to-end {target_role} project and write a README",
            "resources": [
                "GitHub (github.com) for version control",
                "dev.to or Medium for writing a project blog post",
                "LinkedIn to share your project",
            ],
            "is_completed": False,
        })

    return roadmap


def _validate_roadmap(data: list, expected_weeks: int) -> list[dict]:
    """
    Validate and clean LLM-generated roadmap data.
    Ensures all required fields are present with correct types.
    """
    validated = []
    for i, item in enumerate(data[:expected_weeks]):
        validated.append({
            "week":           int(item.get("week", i + 1)),
            "topic":          str(item.get("topic", f"Week {i+1}")),
            "objectives":     list(item.get("objectives", [])),
            "time_estimate":  str(item.get("time_estimate", "8-10 hours")),
            "practice_task":  str(item.get("practice_task", "")),
            "project_task":   str(item.get("project_task", "")),
            "resources":      list(item.get("resources", [])),
            "is_completed":   bool(item.get("is_completed", False)),
        })
    return validated


def generate_roadmap(
    target_role: str,
    missing_skills: list[str],
) -> dict:
    """
    Generate a personalized learning roadmap.

    Args:
        target_role:    The job role the candidate is targeting.
        missing_skills: Skills the candidate lacks (from skill gap analysis).

    Returns:
        {
            roadmap_data:  list of week dicts,
            total_weeks:   int,
            source:        "llm" | "fallback",
        }

    Disclaimer: This roadmap is a learning suggestion only.
    It does NOT guarantee job placement or any specific outcome.
    """
    if not missing_skills:
        logger.warning("generate_roadmap called with empty missing_skills")
        return {"roadmap_data": [], "total_weeks": 0, "source": "empty"}

    # Cap at 12 weeks to keep roadmap manageable
    capped_skills = missing_skills[:10]
    weeks = len(capped_skills) + (1 if len(capped_skills) > 2 else 0)
    weeks = min(weeks, 12)

    logger.info(
        "Generating roadmap: role='{}' skills={} weeks={}",
        target_role, capped_skills, weeks
    )

    # ── Try LLM first ─────────────────────────────────────────────────────────
    llm_response = call_llm(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(target_role, capped_skills, weeks),
        max_tokens=3000,
        temperature=0.4,
        expect_json=True,
    )

    if llm_response:
        parsed = extract_json_from_response(llm_response)
        if isinstance(parsed, list) and len(parsed) > 0:
            roadmap_data = _validate_roadmap(parsed, weeks)
            logger.info("Roadmap generated via LLM: {} weeks", len(roadmap_data))
            return {
                "roadmap_data": roadmap_data,
                "total_weeks":  len(roadmap_data),
                "source":       "llm",
            }
        else:
            logger.warning("LLM returned unparseable roadmap, using fallback.")

    # ── Fallback: rule-based generation ───────────────────────────────────────
    roadmap_data = _generate_fallback_roadmap(target_role, capped_skills)
    logger.info("Roadmap generated via fallback: {} weeks", len(roadmap_data))
    return {
        "roadmap_data": roadmap_data,
        "total_weeks":  len(roadmap_data),
        "source":       "fallback",
    }
