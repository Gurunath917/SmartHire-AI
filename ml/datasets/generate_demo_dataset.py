"""
Demo Dataset Generator for SmartHire AI — ML Candidate Ranking.

IMPORTANT: This generates SYNTHETIC data for development/demonstration only.
           It is clearly labelled as demo data and does NOT represent real hiring outcomes.
           Do NOT present these metrics as real hiring performance data.

Run:
    python ml/datasets/generate_demo_dataset.py

Outputs:
    ml/datasets/candidate_ranking_demo.csv
"""
import random
import csv
import os

random.seed(42)

# Output path
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "candidate_ranking_demo.csv")

# ── Feature definitions ───────────────────────────────────────────────────────
# These match exactly the features used by the ML pipeline in training/inference.
# DO NOT change column names here without also updating feature_engineering.py

COLUMNS = [
    "candidate_id",
    "job_id",
    # Matching scores (from Phase 6 — computed before ML ranking)
    "skill_match_score",          # 0–100: % of required skills candidate has
    "semantic_similarity_score",  # 0–100: embedding similarity
    "tfidf_score",                # 0–1:   TF-IDF cosine similarity
    "experience_match_score",     # 0–100: years experience vs requirement
    "education_match_score",      # 0–100: degree level match
    # Candidate profile features
    "years_of_experience",        # float: actual years
    "num_skills",                 # int: total skills in profile
    "num_required_skills_matched",# int: exact count of required skills matched
    "num_projects",               # int: projects on resume (proxy)
    "has_certification",          # 0/1
    "has_internship",             # 0/1
    "cgpa",                       # float 0–10, 0 if not available
    # Target variable
    "shortlisted",                # 0 = not shortlisted, 1 = shortlisted
]

# ── Synthetic data generation ─────────────────────────────────────────────────

def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def generate_candidate(candidate_id: int, job_id: int) -> dict:
    """
    Generate a single synthetic candidate-job pair.
    Shortlisting probability correlates with feature quality
    so the ML model has a learnable signal.
    """
    years_exp = round(random.uniform(0, 10), 1)
    num_skills = random.randint(3, 25)
    num_req_matched = random.randint(0, min(num_skills, 8))
    has_cert = random.choice([0, 0, 0, 1])   # 25% have certification
    has_intern = random.choice([0, 1])
    cgpa = round(random.uniform(5.0, 10.0), 2) if random.random() > 0.2 else 0.0
    num_projects = random.randint(0, 8)

    # Compute feature-correlated scores (with noise)
    skill_score = _clamp(
        (num_req_matched / 8) * 100 + random.gauss(0, 8), 0, 100
    )
    semantic_score = _clamp(
        skill_score * 0.7 + years_exp * 2 + random.gauss(0, 10), 0, 100
    )
    tfidf = _clamp(semantic_score / 100 * 0.8 + random.gauss(0, 0.05), 0, 1)
    exp_score = _clamp(
        min(years_exp / 3, 1) * 100 + random.gauss(0, 5), 0, 100
    )
    edu_score = _clamp(
        (cgpa / 10) * 80 + 20 + random.gauss(0, 5), 0, 100
    ) if cgpa > 0 else _clamp(50 + random.gauss(0, 10), 0, 100)

    # Shortlisting logic: weighted combination + threshold + noise
    shortlist_score = (
        0.35 * (skill_score / 100)
        + 0.25 * (semantic_score / 100)
        + 0.15 * (exp_score / 100)
        + 0.10 * (edu_score / 100)
        + 0.05 * (num_projects / 8)
        + 0.05 * has_cert
        + 0.05 * has_intern
        + random.gauss(0, 0.08)  # noise
    )
    shortlisted = 1 if shortlist_score > 0.55 else 0

    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "skill_match_score": round(skill_score, 2),
        "semantic_similarity_score": round(semantic_score, 2),
        "tfidf_score": round(tfidf, 4),
        "experience_match_score": round(exp_score, 2),
        "education_match_score": round(edu_score, 2),
        "years_of_experience": years_exp,
        "num_skills": num_skills,
        "num_required_skills_matched": num_req_matched,
        "num_projects": num_projects,
        "has_certification": has_cert,
        "has_internship": has_intern,
        "cgpa": cgpa,
        "shortlisted": shortlisted,
    }


def generate_dataset(n_samples: int = 2000) -> list[dict]:
    rows = []
    for i in range(n_samples):
        candidate_id = random.randint(1, 500)
        job_id = random.randint(1, 50)
        rows.append(generate_candidate(candidate_id, job_id))
    return rows


if __name__ == "__main__":
    print("Generating synthetic demo dataset...")
    rows = generate_dataset(n_samples=2000)

    shortlisted_count = sum(r["shortlisted"] for r in rows)
    print(f"  Total samples      : {len(rows)}")
    print(f"  Shortlisted (1)    : {shortlisted_count} ({shortlisted_count/len(rows)*100:.1f}%)")
    print(f"  Not shortlisted (0): {len(rows) - shortlisted_count}")

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Saved to: {OUTPUT_FILE}")
    print("DONE — NOTE: This is SYNTHETIC demo data only.")
