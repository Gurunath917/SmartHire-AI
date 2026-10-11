"""
Resume Parser Orchestrator.

Combines:
  1. PDF text extraction (pdf_parser)
  2. Skill extraction (skill_extractor)
  3. Saves results to DB (resume + candidate_skills tables)

Called:
  - Automatically after resume upload
  - On-demand via POST /api/resumes/{id}/parse
"""
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.models.candidate_profile import CandidateProfile
from app.models.skill import Skill, CandidateSkill
from app.services.pdf_parser import parse_pdf
from app.services.skill_extractor import extract_skills_from_sections
from app.utils.logger import logger


def _load_skills_from_db(db: Session) -> list[dict]:
    """Load all skills from the taxonomy table."""
    skills = db.query(Skill).all()
    return [
        {"id": s.id, "skill_name": s.skill_name, "category": s.category}
        for s in skills
    ]


def _calculate_ats_score(sections: dict, skills_found: list) -> int:
    """
    Simple ATS-style score heuristic (0–100).
    This is an internal score for the platform — not a universal ATS standard.

    Factors:
    - Has contact info (name, email, phone)
    - Has education section
    - Has experience or internships section
    - Has skills section
    - Has projects section
    - Number of skills found
    - Resume length (not too short, not too long)
    """
    score = 0

    if sections.get("header") or sections.get("contact"):
        score += 15
    if sections.get("education"):
        score += 15
    if sections.get("experience") or sections.get("internships"):
        score += 20
    if sections.get("skills"):
        score += 15
    if sections.get("projects"):
        score += 10
    if sections.get("summary"):
        score += 5
    if sections.get("certifications"):
        score += 5

    # Skills count bonus (up to 15 points)
    skill_count = len(skills_found)
    if skill_count >= 10:
        score += 15
    elif skill_count >= 5:
        score += 10
    elif skill_count >= 2:
        score += 5

    return min(score, 100)


def parse_and_store_resume(resume_id: int, db: Session) -> dict:
    """
    Full pipeline: parse PDF → extract skills → store results.

    Args:
        resume_id: ID of the resume record in DB
        db: SQLAlchemy session

    Returns:
        {success, message, skills_found, sections, contact, ats_score}
    """
    # Load resume record
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        return {"success": False, "message": "Resume not found."}

    logger.info("Starting parse for resume_id={} file={}", resume_id, resume.original_filename)

    # Mark as processing
    resume.is_parsed = False
    resume.parse_error = None
    db.commit()

    try:
        # ── Step 1: Parse PDF ─────────────────────────────────────────────
        parse_result = parse_pdf(resume.file_path)

        if not parse_result["cleaned_text"]:
            resume.parse_error = "Could not extract text from PDF. File may be scanned/image-based."
            db.commit()
            return {
                "success": False,
                "message": resume.parse_error,
            }

        # ── Step 2: Load skill taxonomy ───────────────────────────────────
        db_skills = _load_skills_from_db(db)

        # ── Step 3: Extract skills ────────────────────────────────────────
        extracted = extract_skills_from_sections(
            parse_result["sections"],
            db_skills,
        )
        skills_found = extracted.get("all", [])

        # ── Step 4: Calculate ATS score ───────────────────────────────────
        ats_score = _calculate_ats_score(parse_result["sections"], skills_found)

        # ── Step 5: Store results in resume table ─────────────────────────
        resume.raw_text = parse_result["raw_text"]
        resume.extracted_sections = parse_result["sections"]
        resume.parsed_data = {
            "contact": parse_result["contact"],
            "skills": extracted,
            "page_count": parse_result["page_count"],
            "extraction_method": parse_result["extraction_method"],
        }
        resume.is_parsed = True
        resume.parse_error = None

        # ── Step 6: Store skills in candidate_skills table ────────────────
        profile = db.query(CandidateProfile).filter(
            CandidateProfile.user_id == resume.user_id
        ).first()

        if profile:
            # Update ATS score on profile — after parsing, not before
            profile.resume_ats_score = ats_score

            # Remove old AI-extracted skills (keep manually_added ones)
            db.query(CandidateSkill).filter(
                CandidateSkill.candidate_profile_id == profile.id,
                CandidateSkill.skill_source == "ai_extracted",
            ).delete()
            # Flush the DELETE before INSERT to avoid unique constraint violations on re-parse
            db.flush()

            # Insert newly found skills
            skill_name_to_id = {s["skill_name"]: s["id"] for s in db_skills}

            added_skill_ids = set()
            for category, skill_names in extracted.items():
                if category == "all":
                    continue
                for skill_name in skill_names:
                    skill_id = skill_name_to_id.get(skill_name)
                    if skill_id and skill_id not in added_skill_ids:
                        added_skill_ids.add(skill_id)
                        cs = CandidateSkill(
                            candidate_profile_id=profile.id,
                            skill_id=skill_id,
                            skill_source="ai_extracted",
                        )
                        db.add(cs)

        db.commit()

        logger.info(
            "Resume parsed: resume_id={} skills={} ats_score={}",
            resume_id, len(skills_found), ats_score
        )

        return {
            "success": True,
            "message": f"Resume parsed successfully. Found {len(skills_found)} skills.",
            "skills_found": skills_found,
            "sections": list(parse_result["sections"].keys()),
            "contact": parse_result["contact"],
            "ats_score": ats_score,
        }

    except Exception as e:
        logger.error("Resume parse failed for resume_id={}: {}", resume_id, e)
        resume.parse_error = str(e)
        resume.is_parsed = False
        db.commit()
        return {
            "success": False,
            "message": f"Parse failed: {str(e)}",
        }
