"""
PDF Parser Service.

Responsibilities:
1. Extract raw text from a PDF file using PyMuPDF
2. Clean the extracted text (whitespace, encoding artifacts)
3. Detect resume sections (Contact, Summary, Education, Skills, etc.)

Uses pymupdf (not the deprecated fitz alias).
Falls back to pdfplumber if pymupdf extraction is poor.
"""
import re
from pathlib import Path
from typing import Optional

import pymupdf  # replaces deprecated 'import fitz'
import pdfplumber

from app.utils.logger import logger


# ── Section header patterns ───────────────────────────────────────────────────
# Each key maps to a list of regex patterns that match common section headings
SECTION_PATTERNS = {
    "contact": [
        r"^(contact|personal\s+info(rmation)?|about\s+me)\s*$",
    ],
    "summary": [
        r"^(summary|professional\s+summary|career\s+objective|objective|profile|about)\s*$",
    ],
    "education": [
        r"^(education|academic(s)?|educational\s+background|qualifications?)\s*$",
    ],
    "experience": [
        r"^(experience|work\s+experience|employment|professional\s+experience|work\s+history|career)\s*$",
    ],
    "skills": [
        r"^(skills?|technical\s+skills?|core\s+competencies|competencies|technologies|tech\s+stack)\s*$",
    ],
    "projects": [
        r"^(projects?|personal\s+projects?|academic\s+projects?|portfolio)\s*$",
    ],
    "certifications": [
        r"^(certifications?|certificates?|courses?|training|licenses?)\s*$",
    ],
    "achievements": [
        r"^(achievements?|awards?|honors?|accomplishments?|recognition)\s*$",
    ],
    "internships": [
        r"^(internships?|internship\s+experience|trainings?)\s*$",
    ],
    "languages": [
        r"^(languages?|language\s+proficiency)\s*$",
    ],
    "hobbies": [
        r"^(hobbies|interests?|extra.?curricular)\s*$",
    ],
}


def extract_text_pymupdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF (primary method)."""
    text_parts = []
    try:
        doc = pymupdf.open(file_path)
        for page in doc:
            text_parts.append(page.get_text("text"))
        doc.close()
    except Exception as e:
        logger.warning("PyMuPDF extraction failed for {}: {}", file_path, e)
        return ""
    return "\n".join(text_parts)


def extract_text_pdfplumber(file_path: str) -> str:
    """Extract text using pdfplumber (fallback method)."""
    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        logger.warning("pdfplumber extraction failed for {}: {}", file_path, e)
        return ""
    return "\n".join(text_parts)


def clean_text(raw_text: str) -> str:
    """
    Clean extracted PDF text.
    - Remove null bytes and control characters
    - Normalize whitespace
    - Remove excessive blank lines
    - Strip leading/trailing whitespace per line
    """
    if not raw_text:
        return ""

    # Remove null bytes and non-printable control chars (except newlines/tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw_text)

    # Normalize unicode dashes and quotes
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip each line
    lines = [line.strip() for line in text.split("\n")]

    # Remove runs of more than 2 consecutive blank lines
    cleaned_lines = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def detect_sections(text: str) -> dict:
    """
    Split resume text into named sections.

    Strategy:
    - Scan line by line
    - If a line matches a section header pattern, start a new section
    - Lines before any recognized section go into 'header' (contact info)
    - Return dict: {section_name: text_content}
    """
    lines = text.split("\n")
    sections: dict = {}
    current_section = "header"
    current_lines: list = []

    for line in lines:
        stripped = line.strip()
        matched_section = _match_section_header(stripped)

        if matched_section:
            # Save current section before switching
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    if current_section in sections:
                        sections[current_section] += "\n" + content
                    else:
                        sections[current_section] = content
            current_section = matched_section
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            if current_section in sections:
                sections[current_section] += "\n" + content
            else:
                sections[current_section] = content

    return sections


def _match_section_header(line: str) -> Optional[str]:
    """
    Check if a line is a section header.
    Returns the section key if matched, else None.
    Ignores very long lines (not a heading) and empty lines.
    """
    if not line or len(line) > 60:
        return None

    line_lower = line.lower().strip()
    # Remove trailing colons (e.g. "SKILLS:" → "SKILLS")
    line_lower = line_lower.rstrip(":")

    for section_key, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, line_lower, re.IGNORECASE):
                return section_key

    return None


def extract_contact_info(header_text: str) -> dict:
    """
    Extract basic contact information from the resume header/contact section.
    Returns: {name, email, phone, linkedin, github, location}
    """
    contact = {
        "name": None,
        "email": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "location": None,
    }

    lines = [l.strip() for l in header_text.split("\n") if l.strip()]

    # Email
    email_pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    for line in lines:
        match = re.search(email_pattern, line)
        if match:
            contact["email"] = match.group(0).lower()
            break

    # Phone — various formats
    phone_pattern = r"(\+?\d[\d\s\-().]{7,15}\d)"
    for line in lines:
        match = re.search(phone_pattern, line)
        if match:
            phone = re.sub(r"[\s\-()]", "", match.group(0))
            if len(phone) >= 7:
                contact["phone"] = match.group(0).strip()
                break

    # LinkedIn
    linkedin_pattern = r"linkedin\.com/in/[\w\-]+"
    for line in lines:
        match = re.search(linkedin_pattern, line, re.IGNORECASE)
        if match:
            contact["linkedin"] = "https://" + match.group(0)
            break

    # GitHub
    github_pattern = r"github\.com/[\w\-]+"
    for line in lines:
        match = re.search(github_pattern, line, re.IGNORECASE)
        if match:
            contact["github"] = "https://" + match.group(0)
            break

    # Name — typically the first non-empty line before email/phone
    for line in lines:
        if line and not re.search(email_pattern, line) and not re.search(phone_pattern, line):
            # Likely a name if it has 2-4 words and no special chars
            words = line.split()
            if 1 <= len(words) <= 5 and all(re.match(r"[A-Za-z.\-']+$", w) for w in words):
                contact["name"] = line
                break

    return contact


def parse_pdf(file_path: str) -> dict:
    """
    Main entry point for PDF parsing.

    Steps:
    1. Extract raw text (pymupdf → fallback pdfplumber)
    2. Clean the text
    3. Detect sections
    4. Extract contact info

    Returns:
        {
            raw_text: str,
            cleaned_text: str,
            sections: dict,
            contact: dict,
            page_count: int,
            extraction_method: str
        }
    """
    result = {
        "raw_text": "",
        "cleaned_text": "",
        "sections": {},
        "contact": {},
        "page_count": 0,
        "extraction_method": "none",
    }

    # Get page count
    try:
        doc = pymupdf.open(file_path)
        result["page_count"] = doc.page_count
        doc.close()
    except Exception:
        pass

    # Try pymupdf first
    raw_text = extract_text_pymupdf(file_path)
    method = "pymupdf"

    # Fallback to pdfplumber if text is too short (scanned/image PDF)
    if len(raw_text.strip()) < 100:
        logger.info("PyMuPDF got minimal text, trying pdfplumber for {}", file_path)
        raw_text = extract_text_pdfplumber(file_path)
        method = "pdfplumber"

    if not raw_text.strip():
        logger.warning("Could not extract text from PDF: {}", file_path)
        result["extraction_method"] = "failed"
        return result

    cleaned = clean_text(raw_text)
    sections = detect_sections(cleaned)

    # Build contact from header + contact section
    contact_text = sections.get("header", "") + "\n" + sections.get("contact", "")
    contact = extract_contact_info(contact_text)

    result.update({
        "raw_text": raw_text,
        "cleaned_text": cleaned,
        "sections": sections,
        "contact": contact,
        "extraction_method": method,
    })

    logger.info(
        "PDF parsed: method={} pages={} sections={} chars={}",
        method,
        result["page_count"],
        list(sections.keys()),
        len(cleaned),
    )

    return result
