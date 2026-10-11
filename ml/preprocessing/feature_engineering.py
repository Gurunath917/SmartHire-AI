"""
Feature Engineering for ML Candidate Ranking.

Converts raw candidate-job match data into a clean feature vector
for the ML ranking model.

FEATURE_COLUMNS must stay in sync with:
  - ml/datasets/generate_demo_dataset.py
  - ml/training/train_ranker.py
  - backend/app/ml/ranking_service.py  (inference)

Do NOT change column order or names without updating all three.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

# ── Feature column order (must match training) ────────────────────────────────
FEATURE_COLUMNS = [
    "skill_match_score",            # 0–100
    "semantic_similarity_score",    # 0–100
    "tfidf_score",                  # 0–1 (kept as-is, model handles scale)
    "experience_match_score",       # 0–100
    "education_match_score",        # 0–100
    "years_of_experience",          # float
    "num_skills",                   # int
    "num_required_skills_matched",  # int
    "num_projects",                 # int
    "has_certification",            # 0/1
    "has_internship",               # 0/1
    "cgpa",                         # 0–10 (0 if not available)
]

TARGET_COLUMN = "shortlisted"

# ── Default/fallback values for missing data ─────────────────────────────────
FEATURE_DEFAULTS = {
    "skill_match_score":            50.0,
    "semantic_similarity_score":    50.0,
    "tfidf_score":                  0.1,
    "experience_match_score":       50.0,
    "education_match_score":        50.0,
    "years_of_experience":          0.0,
    "num_skills":                   0,
    "num_required_skills_matched":  0,
    "num_projects":                 0,
    "has_certification":            0,
    "has_internship":               0,
    "cgpa":                         0.0,
}


def build_feature_vector(
    skill_match_score: float,
    semantic_similarity_score: float,
    tfidf_score: float,
    experience_match_score: float,
    education_match_score: float,
    years_of_experience: float,
    num_skills: int,
    num_required_skills_matched: int,
    num_projects: int = 0,
    has_certification: int = 0,
    has_internship: int = 0,
    cgpa: float = 0.0,
) -> np.ndarray:
    """
    Build a 1D numpy feature vector in the canonical column order.
    Used at inference time in ranking_service.py.

    All inputs are validated and clipped to their expected ranges.
    Returns shape (1, len(FEATURE_COLUMNS)) for direct model.predict() use.
    """
    row = {
        "skill_match_score":            float(np.clip(skill_match_score, 0, 100)),
        "semantic_similarity_score":    float(np.clip(semantic_similarity_score, 0, 100)),
        "tfidf_score":                  float(np.clip(tfidf_score, 0, 1)),
        "experience_match_score":       float(np.clip(experience_match_score, 0, 100)),
        "education_match_score":        float(np.clip(education_match_score, 0, 100)),
        "years_of_experience":          float(max(0, years_of_experience)),
        "num_skills":                   int(max(0, num_skills)),
        "num_required_skills_matched":  int(max(0, num_required_skills_matched)),
        "num_projects":                 int(max(0, num_projects)),
        "has_certification":            int(bool(has_certification)),
        "has_internship":               int(bool(has_internship)),
        "cgpa":                         float(np.clip(cgpa, 0, 10)),
    }
    return np.array([[row[col] for col in FEATURE_COLUMNS]], dtype=np.float32)


def load_dataset(csv_path: str) -> pd.DataFrame:
    """Load and validate the training CSV."""
    df = pd.read_csv(csv_path)

    # Check all required columns are present
    required = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")

    # Fill any NaN values with defaults
    for col, default in FEATURE_DEFAULTS.items():
        if col in df.columns:
            df[col] = df[col].fillna(default)

    # Clip numeric ranges
    df["skill_match_score"]           = df["skill_match_score"].clip(0, 100)
    df["semantic_similarity_score"]   = df["semantic_similarity_score"].clip(0, 100)
    df["tfidf_score"]                 = df["tfidf_score"].clip(0, 1)
    df["experience_match_score"]      = df["experience_match_score"].clip(0, 100)
    df["education_match_score"]       = df["education_match_score"].clip(0, 100)
    df["years_of_experience"]         = df["years_of_experience"].clip(0)
    df["cgpa"]                        = df["cgpa"].clip(0, 10)
    df["has_certification"]           = df["has_certification"].astype(int)
    df["has_internship"]              = df["has_internship"].astype(int)

    return df


def get_X_y(df: pd.DataFrame):
    """Split dataframe into feature matrix X and target vector y."""
    X = df[FEATURE_COLUMNS].values.astype(np.float32)
    y = df[TARGET_COLUMN].values.astype(int)
    return X, y


def feature_names() -> list[str]:
    """Return canonical feature column names (used by SHAP for labels)."""
    return FEATURE_COLUMNS.copy()
