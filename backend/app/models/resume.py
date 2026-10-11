"""
Resume model — stores uploaded PDF metadata and extracted content.
The actual file is stored on disk; only the path is saved here.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    # ── File metadata ─────────────────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)  # UUID-based safe name
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")

    # ── Extracted content ─────────────────────────────────────────────────
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    extracted_sections: Mapped[Optional[dict]] = mapped_column(JSON)
    # Structured parsed data (contact, education, experience, etc.)
    parsed_data: Mapped[Optional[dict]] = mapped_column(JSON)
    is_parsed: Mapped[bool] = mapped_column(Boolean, default=False)
    parse_error: Mapped[Optional[str]] = mapped_column(Text)

    # ── Status ────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # most recent resume

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="resumes")

    def __repr__(self) -> str:
        return f"<Resume id={self.id} user_id={self.user_id} file={self.original_filename}>"
