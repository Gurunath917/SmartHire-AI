"""
Pydantic schemas for the RAG Career Assistant endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Body for POST /api/assistant/chat"""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[int] = None   # continue existing session

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "What skills do I need to become an AI/ML Engineer?",
                "session_id": None,
            }
        }
    }


class SourceCitation(BaseModel):
    """A single source citation from the RAG retrieval."""
    title: str
    score: float


class ChatMessageResponse(BaseModel):
    """A single chat message returned to the client."""
    id: int
    session_id: int
    msg_role: str          # USER or ASSISTANT
    content: str
    sources: Optional[list[SourceCitation]] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    """Full response from the assistant endpoint."""
    session_id: int
    user_message: str
    assistant_answer: str
    sources: list[SourceCitation] = []
    used_llm: bool


class ChatSessionResponse(BaseModel):
    """A chat session summary."""
    id: int
    title: Optional[str]
    is_active: bool
    message_count: int
    created_at: datetime
    updated_at: datetime
