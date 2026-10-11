"""
Resume file storage service.

Responsibilities:
- Validate file extension (.pdf only)
- Validate MIME type (application/pdf only)
- Enforce file size limit
- Generate a UUID-based safe filename (never trust original filename)
- Store file outside public assets
- Return stored path metadata

Never execute uploaded files.
Never store files in a publicly accessible web directory.
"""
import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.utils.errors import bad_request, unprocessable
from app.utils.logger import logger

# Allowed file type constants
ALLOWED_EXTENSION = ".pdf"
ALLOWED_MIME_TYPE = "application/pdf"
MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # convert MB → bytes


def _get_upload_dir() -> Path:
    """Return the upload directory, creating it if it doesn't exist."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def validate_and_store_resume(file: UploadFile, user_id: int) -> dict:
    """
    Validate a resume file upload and store it safely.

    Checks:
      1. Extension must be .pdf
      2. MIME type must be application/pdf (checked from file bytes, not header)
      3. File size must be within MAX_UPLOAD_SIZE_MB

    Storage:
      - Filename: {user_id}_{uuid4}.pdf  (safe, no user-controlled characters)
      - Location: settings.UPLOAD_DIR

    Returns:
        dict with: original_filename, stored_filename, file_path, file_size_bytes, mime_type

    Raises:
        HTTPException 400/422 on any validation failure.
    """
    # ── 1. Validate extension ─────────────────────────────────────────────────
    original_filename = file.filename or "resume.pdf"
    ext = Path(original_filename).suffix.lower()
    if ext != ALLOWED_EXTENSION:
        raise bad_request(
            f"Only PDF files are accepted. Received file with extension '{ext}'."
        )

    # ── 2. Read file contents ─────────────────────────────────────────────────
    contents = file.file.read()
    file_size = len(contents)

    # ── 3. Validate file size ─────────────────────────────────────────────────
    if file_size == 0:
        raise bad_request("Uploaded file is empty.")
    if file_size > MAX_SIZE_BYTES:
        raise bad_request(
            f"File too large. Maximum allowed size is {settings.MAX_UPLOAD_SIZE_MB} MB. "
            f"Your file is {file_size / (1024 * 1024):.1f} MB."
        )

    # ── 4. Validate MIME type from actual bytes (not trusting Content-Type) ───
    # Check the PDF magic bytes header (%PDF) as a reliable fallback
    # python-magic is optional — we always check the raw header bytes
    is_pdf_header = contents[:4] == b"%PDF"

    try:
        import magic as libmagic
        detected_mime = libmagic.from_buffer(contents[:2048], mime=True)
    except Exception:
        # python-magic not available or failed — rely on header check
        detected_mime = ALLOWED_MIME_TYPE if is_pdf_header else "unknown"

    if not is_pdf_header or detected_mime != ALLOWED_MIME_TYPE:
        raise unprocessable(
            "File content does not appear to be a valid PDF. "
            "Please upload a proper PDF file."
        )

    # ── 5. Generate safe filename ─────────────────────────────────────────────
    safe_uuid = uuid.uuid4().hex
    stored_filename = f"{user_id}_{safe_uuid}.pdf"

    # ── 6. Store file ─────────────────────────────────────────────────────────
    upload_dir = _get_upload_dir()
    file_path = upload_dir / stored_filename

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
        logger.info(
            "Resume stored: user_id={} file={} size={}KB",
            user_id, stored_filename, round(file_size / 1024, 1)
        )
    except OSError as e:
        logger.error("Failed to write resume file: {}", e)
        raise unprocessable("Failed to store the uploaded file. Please try again.")

    return {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_path": str(file_path),
        "file_size_bytes": file_size,
        "mime_type": ALLOWED_MIME_TYPE,
    }


def delete_resume_file(file_path: str) -> None:
    """Delete a stored resume file from disk. Fails silently if not found."""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.info("Resume file deleted: {}", file_path)
    except OSError as e:
        logger.warning("Could not delete resume file {}: {}", file_path, e)
