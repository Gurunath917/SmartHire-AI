"""
ML Candidate Ranking — Training Pipeline.

Trains XGBoost and Random Forest classifiers on the demo dataset.
Selects the best model by ROC-AUC on the validation set.
Saves the best model + scaler to ml/saved_models/.

IMPORTANT:
- This uses SYNTHETIC demo data only.
- Reported metrics are on demo data — NOT real hiring data.
- Do NOT claim these metrics represent real-world hiring accuracy.

Run:
    python ml/training/train_ranker.py
"""
import os
import sys
import json
from pathlib import Path

# Allow running from project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
    classification_report,
)
from xgboost import XGBClassifier

# ── Paths ─────────────────────────────────────────────────────────────────────
DATASET_PATH    = PROJECT_ROOT / "ml" / "datasets" / "candidate_ranking_demo.csv"
SAVED_MODELS_DIR = PROJECT_ROOT / "ml" / "saved_models"
MODEL_PATH      = SAVED_MODELS_DIR / "ranker_model.joblib"
METADATA_PATH   = SAVED_MODELS_DIR / "ranker_metadata.json"

# Import feature engineering
ML_DIR = PROJECT_ROOT / "ml"
sys.path.insert(0, str(ML_DIR))
from preprocessing.feature_engineering import load_dataset, get_X_y, feature_names

SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ── Model definitions ─────────────────────────────────────────────────────────
def get_models() -> dict:
    """Return candidate models to evaluate."""
    return {
        "xgboost": XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features="sqrt",
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=150,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            min_samples_split=10,
            random_state=42,
        ),
    }


# ── Evaluation ────────────────────────────────────────────────────────────────
def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    """Compute and return all evaluation metrics."""
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    return {
        "accuracy":  round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall":    round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1":        round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc":   round(float(roc_auc_score(y_test, y_prob)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }


def cross_validate_model(model, X: np.ndarray, y: np.ndarray, cv: int = 5) -> dict:
    """Run stratified k-fold cross-validation."""
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    auc_scores = cross_val_score(model, X, y, cv=skf, scoring="roc_auc", n_jobs=-1)
    f1_scores  = cross_val_score(model, X, y, cv=skf, scoring="f1", n_jobs=-1)
    return {
        "cv_roc_auc_mean": round(float(auc_scores.mean()), 4),
        "cv_roc_auc_std":  round(float(auc_scores.std()), 4),
        "cv_f1_mean":      round(float(f1_scores.mean()), 4),
        "cv_f1_std":       round(float(f1_scores.std()), 4),
    }


# ── Main training flow ────────────────────────────────────────────────────────
def train():
    print("=" * 60)
    print("SmartHire AI — ML Candidate Ranking Training")
    print("NOTE: Using SYNTHETIC demo data. Metrics are not real.")
    print("=" * 60)

    # 1. Load data
    print(f"\nLoading dataset: {DATASET_PATH}")
    df = load_dataset(str(DATASET_PATH))
    X, y = get_X_y(df)
    print(f"  Samples: {len(X)}, Features: {X.shape[1]}, "
          f"Class balance: {y.mean()*100:.1f}% shortlisted")

    # 2. Train/validation/test split (60/20/20)
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.25, stratify=y_temp, random_state=42
    )
    print(f"  Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # 3. Scale features (for RF/GB; XGBoost is tree-based but scale doesn't hurt)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s   = scaler.transform(X_val)
    X_test_s  = scaler.transform(X_test)

    # 4. Train and evaluate all models
    models = get_models()
    results = {}
    best_model_name = None
    best_auc = -1.0
    best_model_obj = None

    for name, model in models.items():
        print(f"\nTraining: {name}")
        model.fit(X_train_s, y_train)

        val_metrics = evaluate_model(model, X_val_s, y_val)
        print(f"  Val  — AUC: {val_metrics['roc_auc']:.4f}  F1: {val_metrics['f1']:.4f}")

        cv_metrics = cross_validate_model(model, X_train_s, y_train, cv=5)
        print(f"  CV   — AUC: {cv_metrics['cv_roc_auc_mean']:.4f} ±{cv_metrics['cv_roc_auc_std']:.4f}")

        results[name] = {**val_metrics, **cv_metrics}

        if val_metrics["roc_auc"] > best_auc:
            best_auc = val_metrics["roc_auc"]
            best_model_name = name
            best_model_obj = model

    # 5. Final evaluation of best model on held-out test set
    print(f"\nBest model: {best_model_name} (val AUC={best_auc:.4f})")
    test_metrics = evaluate_model(best_model_obj, X_test_s, y_test)
    print(f"Test set metrics:")
    print(f"  Accuracy : {test_metrics['accuracy']}")
    print(f"  Precision: {test_metrics['precision']}")
    print(f"  Recall   : {test_metrics['recall']}")
    print(f"  F1       : {test_metrics['f1']}")
    print(f"  ROC-AUC  : {test_metrics['roc_auc']}")
    print(f"  Confusion matrix: {test_metrics['confusion_matrix']}")
    print()
    print(classification_report(
        y_test,
        best_model_obj.predict(X_test_s),
        target_names=["Not Shortlisted", "Shortlisted"]
    ))

    # 6. Feature importance
    feat_names = feature_names()
    if hasattr(best_model_obj, "feature_importances_"):
        importances = best_model_obj.feature_importances_
        importance_dict = dict(zip(feat_names, [round(float(v), 4) for v in importances]))
        ranked = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
        print("Feature importances:")
        for feat, imp in ranked:
            bar = "#" * int(imp * 40)
            print(f"  {feat:<35} {imp:.4f} {bar}")
    else:
        importance_dict = {}

    # 7. Save model + scaler as a bundle
    bundle = {
        "model": best_model_obj,
        "scaler": scaler,
        "feature_names": feat_names,
        "model_name": best_model_name,
    }
    joblib.dump(bundle, MODEL_PATH)
    print(f"\nModel saved: {MODEL_PATH}")

    # 8. Save metadata (for audit / display in UI)
    metadata = {
        "model_name":        best_model_name,
        "feature_names":     feat_names,
        "dataset":           "SYNTHETIC demo data — NOT real hiring data",
        "n_samples":         len(X),
        "n_features":        X.shape[1],
        "train_size":        len(X_train),
        "val_size":          len(X_val),
        "test_size":         len(X_test),
        "test_metrics":      test_metrics,
        "all_model_results": results,
        "feature_importances": importance_dict,
        "warning": (
            "These metrics are from synthetic data only. "
            "Do not claim them as real-world hiring accuracy."
        ),
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved: {METADATA_PATH}")
    print("\nTraining complete.")
    return bundle


if __name__ == "__main__":
    train()
