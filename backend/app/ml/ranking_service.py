"""
ML Candidate Ranking Inference Service.

Loads the pre-trained XGBoost model at FastAPI startup (once, cached).
Provides:
  - rank_candidate()     : returns ML rank score 0–100 + SHAP explanation
  - get_model_metadata() : returns training metadata for UI display

The model is a decision-support tool only.
It does NOT make autonomous hiring decisions.
Scores are NOT guaranteed hiring probabilities.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import joblib
import numpy as np

from app.utils.logger import logger

# ── Paths ─────────────────────────────────────────────────────────────────────
_BACKEND_ROOT  = Path(__file__).resolve().parents[2]
_PROJECT_ROOT  = _BACKEND_ROOT.parent
_MODEL_PATH    = _PROJECT_ROOT / "ml" / "saved_models" / "ranker_model.joblib"
_METADATA_PATH = _PROJECT_ROOT / "ml" / "saved_models" / "ranker_metadata.json"

# ── Module-level cache ────────────────────────────────────────────────────────
_bundle: Optional[dict] = None
_metadata: Optional[dict] = None


def _load_model() -> dict:
    """Load model bundle once and cache it. Thread-safe for read-only use."""
    global _bundle
    if _bundle is None:
        if not _MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Trained model not found at {_MODEL_PATH}. "
                "Run ml/training/train_ranker.py first."
            )
        logger.info("Loading ML ranking model from: {}", _MODEL_PATH)
        _bundle = joblib.load(_MODEL_PATH)
        logger.info(
            "ML ranking model loaded: {} — features: {}",
            _bundle.get("model_name", "unknown"),
            _bundle.get("feature_names", []),
        )
    return _bundle


def _load_metadata() -> dict:
    """Load training metadata (used to display model info in UI)."""
    global _metadata
    if _metadata is None:
        if _METADATA_PATH.exists():
            with open(_METADATA_PATH) as f:
                _metadata = json.load(f)
        else:
            _metadata = {"warning": "Metadata not found."}
    return _metadata


def _build_feature_vector(features: dict, feature_names: list[str]) -> np.ndarray:
    """Build feature vector in correct column order with safe defaults."""
    defaults = {
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
    row = [float(features.get(col, defaults.get(col, 0.0))) for col in feature_names]
    return np.array([row], dtype=np.float32)


def _compute_shap_explanation(
    model,
    X_scaled: np.ndarray,
    feature_names: list[str],
) -> dict:
    """
    Compute SHAP values for a single prediction.
    Returns human-readable positive/negative factor lists.

    Falls back gracefully if SHAP fails (e.g. model type not supported).
    """
    try:
        import shap

        model_name = type(model).__name__.lower()

        if "xgb" in model_name:
            explainer = shap.TreeExplainer(model)
        elif "forest" in model_name or "boosting" in model_name:
            explainer = shap.TreeExplainer(model)
        else:
            explainer = shap.Explainer(model, X_scaled)

        shap_values = explainer.shap_values(X_scaled)

        # For binary classifiers, shap_values may be a list [neg, pos]
        if isinstance(shap_values, list):
            sv = shap_values[1][0]   # positive class, first (only) sample
        else:
            sv = shap_values[0]      # single output, first sample

        # Build factor list: (feature_name, shap_value, feature_value)
        factors = []
        for i, fname in enumerate(feature_names):
            factors.append({
                "feature":       fname,
                "shap_value":    round(float(sv[i]), 4),
                "feature_value": round(float(X_scaled[0][i]), 2),
            })

        # Sort by absolute SHAP value (most impactful first)
        factors.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        positive_factors = [f for f in factors if f["shap_value"] > 0][:5]
        negative_factors = [f for f in factors if f["shap_value"] < 0][:5]

        return {
            "positive_factors": positive_factors,
            "negative_factors": negative_factors,
            "all_factors":      factors,
        }

    except Exception as e:
        logger.warning("SHAP explanation failed (non-critical): {}", e)
        return {
            "positive_factors": [],
            "negative_factors": [],
            "all_factors":      [],
            "error":            "SHAP explanation unavailable",
        }


def rank_candidate(
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
    include_shap: bool = True,
) -> dict:
    """
    Run ML ranking inference for a single candidate-job pair.

    Returns:
        {
            ml_rank_score     : float (0–100) — ML-based ranking score
            shortlist_probability : float (0–1) — raw model probability
            explanation       : dict  — SHAP factor breakdown
            model_name        : str
            warning           : str   — disclaimer about synthetic model
        }

    IMPORTANT: ml_rank_score is a decision-support score from a model
    trained on SYNTHETIC data. It is NOT a guarantee of hiring suitability.
    """
    bundle = _load_model()
    model        = bundle["model"]
    scaler       = bundle["scaler"]
    feat_names   = bundle["feature_names"]
    model_name   = bundle.get("model_name", "unknown")

    features = {
        "skill_match_score":            skill_match_score,
        "semantic_similarity_score":    semantic_similarity_score,
        "tfidf_score":                  tfidf_score,
        "experience_match_score":       experience_match_score,
        "education_match_score":        education_match_score,
        "years_of_experience":          years_of_experience,
        "num_skills":                   num_skills,
        "num_required_skills_matched":  num_required_skills_matched,
        "num_projects":                 num_projects,
        "has_certification":            has_certification,
        "has_internship":               has_internship,
        "cgpa":                         cgpa,
    }

    # Build and scale feature vector
    X_raw    = _build_feature_vector(features, feat_names)
    X_scaled = scaler.transform(X_raw)

    # Predict probability of shortlisting
    prob = float(model.predict_proba(X_scaled)[0][1])

    # Convert to 0–100 score
    ml_rank_score = round(prob * 100, 2)

    # SHAP explanation
    explanation = _compute_shap_explanation(model, X_scaled, feat_names) if include_shap else {}

    logger.info(
        "ML rank: score={} prob={:.4f} model={}",
        ml_rank_score, prob, model_name
    )

    return {
        "ml_rank_score":         ml_rank_score,
        "shortlist_probability": round(prob, 4),
        "explanation":           explanation,
        "model_name":            model_name,
        "warning": (
            "This score is generated by a model trained on synthetic demo data. "
            "It is a decision-support tool only — NOT a hiring guarantee."
        ),
    }


def get_model_metadata() -> dict:
    """Return training metadata for display in the UI."""
    return _load_metadata()


def is_model_available() -> bool:
    """Check if the trained model file exists."""
    return _MODEL_PATH.exists()


def warmup_model() -> None:
    """
    Pre-load the model on server startup so the first request isn't slow.
    Call this from FastAPI lifespan.
    """
    if is_model_available():
        try:
            _load_model()
            logger.info("ML ranking model pre-loaded successfully.")
        except Exception as e:
            logger.warning("ML model warmup failed (non-critical): {}", e)
    else:
        logger.warning(
            "ML model not found at {}. "
            "Run ml/training/train_ranker.py to train it.",
            _MODEL_PATH,
        )
