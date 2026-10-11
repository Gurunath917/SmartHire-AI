"""
Pydantic schemas for resume endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ResumeResponse(BaseModel):
    """Returned after upload or on GET."""
    id: int
    user_id: int
    original_filename: str
    file_size_bytes: Optional[int]
    mime_type: str
    is_parsed: bool
    is_active: bool
    parsed_data: Optional[dict]
    extracted_sections: Optional[dict]
    parse_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeListResponse(BaseModel):
    """Minimal resume info for listing."""
    id: int
    original_filename: str
    file_size_bytes: Optional[int]
    is_parsed: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
