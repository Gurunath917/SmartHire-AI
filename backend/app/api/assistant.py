"""
RAG Career Assistant API routes.

POST /api/assistant/chat          — send a message, get an AI answer
GET  /api/assistant/history       — list chat sessions
GET  /api/assistant/history/{id}  — get messages in a session
DELETE /api/assistant/history/{id} — delete a session
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.misc import ChatSession, ChatMessage, MessageRole
from app.schemas.assistant import (
    ChatRequest,
    ChatResponse,
    ChatMessageResponse,
    ChatSessionResponse,
    SourceCitation,
)
from app.schemas.auth import MessageResponse
from app.rag.rag_chain import answer
from app.utils.dependencies import get_current_user
from app.utils.errors import not_found, forbidden
from app.utils.logger import logger

router = APIRouter()


def _get_or_create_session(
    user: User,
    session_id: int | None,
    first_message: str,
    db: Session,
) -> ChatSession:
    """Get an existing session or create a new one."""
    if session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        ).first()
        if session:
            return session

    # Auto-title from first message (truncated)
    title = first_message[:50] + ("..." if len(first_message) > 50 else "")
    session = ChatSession(
        user_id=user.id,
        title=title,
        is_active=True,
    )
    db.add(session)
    db.flush()
    return session


# ── POST /api/assistant/chat ──────────────────────────────────────────────────
@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with the AI Career Assistant",
    description=(
        "Send a question about your career, skills, interview prep, or resume. "
        "The assistant retrieves relevant context from its knowledge base "
        "and generates a grounded answer with source citations. "
        "It will NOT invent sources or guarantee job outcomes."
    ),
)
def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Get or create session
    session = _get_or_create_session(
        current_user, body.session_id, body.message, db
    )

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        msg_role=MessageRole.USER,
        content=body.message,
        sources=[],
    )
    db.add(user_msg)

    logger.info(
        "Assistant chat: user={} session={} query='{}'",
        current_user.id, session.id, body.message[:60]
    )

    # Get RAG answer
    result = answer(query=body.message, top_k=4)

    # Save assistant message with source citations
    assistant_msg = ChatMessage(
        session_id=session.id,
        msg_role=MessageRole.ASSISTANT,
        content=result["answer"],
        sources=[{"title": s["title"], "score": s["score"]} for s in result["sources"]],
    )
    db.add(assistant_msg)
    db.commit()

    sources = [
        SourceCitation(title=s["title"], score=s["score"])
        for s in result["sources"]
    ]

    return ChatResponse(
        session_id=session.id,
        user_message=body.message,
        assistant_answer=result["answer"],
        sources=sources,
        used_llm=result["used_llm"],
    )


# ── GET /api/assistant/history ────────────────────────────────────────────────
@router.get(
    "/history",
    response_model=list[ChatSessionResponse],
    summary="List my chat sessions",
)
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for s in sessions:
        msg_count = db.query(ChatMessage).filter(
            ChatMessage.session_id == s.id
        ).count()
        result.append(ChatSessionResponse(
            id=s.id,
            title=s.title,
            is_active=s.is_active,
            message_count=msg_count,
            created_at=s.created_at,
            updated_at=s.updated_at,
        ))
    return result


# ── GET /api/assistant/history/{id} ──────────────────────────────────────────
@router.get(
    "/history/{session_id}",
    response_model=list[ChatMessageResponse],
    summary="Get messages in a session",
)
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id
    ).first()
    if not session:
        raise not_found("Chat session")
    if session.user_id != current_user.id:
        raise forbidden("You can only access your own chat sessions.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return messages


# ── DELETE /api/assistant/history/{id} ───────────────────────────────────────
@router.delete(
    "/history/{session_id}",
    response_model=MessageResponse,
    summary="Delete a chat session",
)
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id
    ).first()
    if not session:
        raise not_found("Chat session")
    if session.user_id != current_user.id:
        raise forbidden("You can only delete your own chat sessions.")

    db.delete(session)
    db.commit()

    logger.info("Chat session deleted: id={} user={}", session_id, current_user.id)
    return MessageResponse(message="Chat session deleted successfully.")
