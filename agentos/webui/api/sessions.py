"""
Sessions API - Chat session management

GET /api/sessions - List all sessions (paginated)
POST /api/sessions - Create new session
GET /api/sessions/{id} - Get session details
GET /api/sessions/{id}/messages - Get session messages (paginated)
POST /api/sessions/{id}/messages - Add message to session
DELETE /api/sessions/{id} - Delete session

Refactored in v0.3.2 (P1 Sprint):
- Replaced in-memory dict with SessionStore abstraction
- Added pagination support
- Added persistent storage (SQLite)
- Retained backward compatibility
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Import SessionStore (injected via app.py)
from agentos.webui.store import SessionStore, Session as SessionModel, Message as MessageModel

router = APIRouter()

# Global store instance (set by app.py)
_store: Optional[SessionStore] = None


def set_session_store(store: SessionStore):
    """Inject session store (called from app.py)"""
    global _store
    _store = store


def get_session_store() -> SessionStore:
    """Get current session store"""
    if _store is None:
        raise RuntimeError("SessionStore not initialized. Call set_session_store() in app.py")
    return _store


def _get_default_language() -> str:
    """Get default language from application settings

    Returns:
        Language code (e.g., "en", "zh"), defaults to "en"
    """
    try:
        from agentos.config import load_settings
        settings = load_settings()
        language = getattr(settings, "language", "en")
        return language
    except Exception:
        return "en"


# ============================================================================
# Pydantic Models (API Layer)
# ============================================================================
# These are kept for backward compatibility with existing frontend code

class SessionResponse(BaseModel):
    """Session API response (backward compatible)"""
    id: str
    title: str
    created_at: str
    updated_at: str
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

    @classmethod
    def from_model(cls, session: SessionModel) -> "SessionResponse":
        """Convert internal Session to API response"""
        return cls(
            id=session.session_id,
            title=session.metadata.get("title", f"Session {session.session_id[:8]}"),
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            tags=session.metadata.get("tags", []),
            metadata=session.metadata
        )


class CreateSessionRequest(BaseModel):
    """Create session request"""
    title: Optional[str] = None
    tags: List[str] = []
    user_id: Optional[str] = "default"
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Message API response (backward compatible)"""
    id: str
    session_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str
    metadata: Dict[str, Any] = {}

    @classmethod
    def from_model(cls, message: MessageModel) -> "MessageResponse":
        """Convert internal Message to API response"""
        return cls(
            id=message.message_id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            timestamp=message.created_at.isoformat(),
            metadata=message.metadata
        )


class AddMessageRequest(BaseModel):
    """Add message request"""
    role: str  # "user" | "assistant" | "system"
    content: str
    metadata: Dict[str, Any] = {}


# ============================================================================
# API Endpoints
# ============================================================================

def _ensure_main_session():
    """Ensure 'main' session exists (backward compatibility)"""
    store = get_session_store()
    main_session = store.get_session("main")

    if main_session is None:
        # Create main session with fixed ID
        # Note: This bypasses ULID generation for backward compat
        try:
            session = store.create_session(
                user_id="default",
                metadata={"title": "Main Session", "tags": ["default"]}
            )
            # Manually override ID to "main" (requires direct DB access)
            # For now, just create with random ID
            # TODO: Add explicit session_id parameter to create_session
        except Exception:
            pass  # Already exists


@router.get("")
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> List[SessionResponse]:
    """
    List all sessions (paginated)

    Query params:
    - limit: Max results (default 50, max 100)
    - offset: Skip N results (default 0)

    Returns sessions ordered by updated_at DESC
    """
    store = get_session_store()
    sessions = store.list_sessions(limit=limit, offset=offset)
    return [SessionResponse.from_model(s) for s in sessions]


@router.post("")
async def create_session(req: CreateSessionRequest) -> SessionResponse:
    """Create new session"""
    store = get_session_store()

    # Load language preference from config
    language = _get_default_language()

    # Start with default metadata
    metadata = {
        "title": req.title or "New Session",
        "tags": req.tags,
        "language": language  # Add language to session metadata
    }

    # Merge with any additional metadata from request
    if req.metadata:
        metadata.update(req.metadata)
        # Ensure title and tags from top-level fields take precedence
        if req.title:
            metadata["title"] = req.title
        metadata["tags"] = req.tags

    session = store.create_session(
        user_id=req.user_id or "default",
        metadata=metadata
    )

    return SessionResponse.from_model(session)


@router.get("/{session_id}")
async def get_session(session_id: str) -> SessionResponse:
    """Get session details"""
    store = get_session_store()
    session = store.get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return SessionResponse.from_model(session)


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> List[MessageResponse]:
    """
    Get session messages (paginated)

    Query params:
    - limit: Max results (default 100, max 500)
    - offset: Skip N results (default 0)

    Returns messages ordered by created_at ASC (chronological)
    """
    store = get_session_store()

    # Verify session exists
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    messages = store.get_messages(session_id, limit=limit, offset=offset)
    return [MessageResponse.from_model(m) for m in messages]


@router.post("/{session_id}/messages")
async def add_message(session_id: str, req: AddMessageRequest) -> MessageResponse:
    """
    Add message to session

    Body:
    - role: 'user' | 'assistant' | 'system'
    - content: Message text
    - metadata: Optional metadata (e.g., model, tokens)
    """
    store = get_session_store()

    try:
        message = store.add_message(
            session_id=session_id,
            role=req.role,
            content=req.content,
            metadata=req.metadata
        )
        return MessageResponse.from_model(message)
    except ValueError as e:
        # Invalid message (e.g., bad role, empty content)
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete session and all its messages"""
    store = get_session_store()

    success = store.delete_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return {"status": "deleted", "session_id": session_id}


@router.delete("")
async def delete_all_sessions():
    """Delete all sessions (clear all history)"""
    store = get_session_store()

    # Get all sessions
    sessions = store.list_sessions(limit=1000, offset=0)

    deleted_count = 0
    for session in sessions:
        success = store.delete_session(session.session_id)
        if success:
            deleted_count += 1

    return {
        "status": "deleted",
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} session(s)"
    }
