"""
Context API - Session-level context management

Endpoints:
- GET /api/context/status - Get context status for a session
- POST /api/context/attach - Attach memory/RAG to a session
- POST /api/context/refresh - Refresh context state

Sprint B Task #8 implementation
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel

from agentos.context import ContextManager, ContextState
from agentos.context.manager import MemoryConfig, RAGConfig
from agentos.webui.middleware import sanitize_response

router = APIRouter()


class MemoryConfigRequest(BaseModel):
    """Memory configuration request"""
    enabled: bool
    namespace: str


class RAGConfigRequest(BaseModel):
    """RAG configuration request"""
    enabled: bool
    index: Optional[str] = None


class AttachRequest(BaseModel):
    """Context attach request"""
    session_id: str
    memory: Optional[MemoryConfigRequest] = None
    rag: Optional[RAGConfigRequest] = None


class AttachResponse(BaseModel):
    """Context attach response"""
    ok: bool
    message: Optional[str] = None


class RefreshRequest(BaseModel):
    """Context refresh request"""
    session_id: str


class RefreshResponse(BaseModel):
    """Context refresh response"""
    ok: bool
    state: str


class ContextStatusResponse(BaseModel):
    """Context status response"""
    session_id: str
    state: str
    updated_at: str
    tokens: Dict[str, Any]
    rag: Dict[str, Any]
    memory: Dict[str, Any]


@router.get("/status")
async def get_context_status(
    session_id: str = Query(..., description="Session ID to check")
) -> ContextStatusResponse:
    """
    Get context status for a session

    Returns current state including:
    - Overall state (EMPTY/ATTACHED/BUILDING/STALE/ERROR)
    - Token statistics (prompt, completion, context window)
    - RAG status (enabled, index, last refresh)
    - Memory status (enabled, namespace, last write)

    Query params:
    - session_id: Session ID to check

    Note: This is read-only and fast - safe to poll frequently
    """
    manager = ContextManager()
    status = manager.get_status(session_id)

    response = ContextStatusResponse(
        session_id=status.session_id,
        state=status.state.value,
        updated_at=status.updated_at,
        tokens=status.tokens,
        rag=status.rag,
        memory=status.memory,
    )

    # Apply sanitization as safety net
    return sanitize_response(response.model_dump())


@router.post("/attach")
async def attach_context(request: AttachRequest) -> AttachResponse:
    """
    Attach memory and/or RAG to a session

    Creates or updates context binding for the session.
    Stores configuration persistently in ~/.agentos/runtime/session_context.json

    Body:
    - session_id: Session to attach to
    - memory: Memory configuration (enabled, namespace)
    - rag: RAG configuration (enabled, index)

    Either memory or RAG can be attached independently.

    Returns:
    - ok: true if successful
    - message: Optional message

    Note: Does not trigger refresh automatically - call /refresh after attach
    """
    manager = ContextManager()

    # Convert to internal types
    memory_config = None
    if request.memory:
        memory_config = MemoryConfig(
            enabled=request.memory.enabled,
            namespace=request.memory.namespace,
        )

    rag_config = None
    if request.rag:
        rag_config = RAGConfig(
            enabled=request.rag.enabled,
            index=request.rag.index,
        )

    try:
        manager.attach(
            session_id=request.session_id,
            memory=memory_config,
            rag=rag_config,
        )

        return AttachResponse(
            ok=True,
            message=f"Context attached to session '{request.session_id}'",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to attach context: {str(e)}",
        )


@router.post("/detach")
async def detach_context(session_id: str) -> AttachResponse:
    """
    Detach all context from a session

    Removes memory and RAG bindings.

    Query params:
    - session_id: Session to detach from

    Returns:
    - ok: true if successful
    """
    manager = ContextManager()

    try:
        manager.detach(session_id)

        return AttachResponse(
            ok=True,
            message=f"Context detached from session '{session_id}'",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detach context: {str(e)}",
        )


@router.post("/refresh")
async def refresh_context(request: RefreshRequest) -> RefreshResponse:
    """
    Refresh context state for a session

    Updates memory and RAG state, marks last_refresh timestamp.

    v0.3 Implementation:
    - Marks session as BUILDING
    - Verifies memory directory accessible
    - Updates last_refresh timestamp
    - Clears BUILDING flag

    Future versions will:
    - Rebuild RAG index
    - Sync memory embeddings
    - Recompute token statistics

    Body:
    - session_id: Session to refresh

    Returns:
    - ok: true if successful
    - state: New state after refresh
    """
    import asyncio
    manager = ContextManager()

    try:
        # Mark as building
        manager.start_refresh(request.session_id)

        # Simulate refresh work (v0.3 placeholder)
        # In v0.5+, this will do actual RAG rebuild, memory sync, etc.
        await asyncio.sleep(0.5)

        # For v0.3, we just verify basic accessibility
        ctx = manager.get_context(request.session_id)
        if ctx:
            # Check memory directory
            if ctx.memory_namespace:
                from pathlib import Path
                memory_dir = Path.home() / ".agentos" / "memory"
                memory_dir.mkdir(parents=True, exist_ok=True)

        # Complete refresh
        manager.complete_refresh(request.session_id)

        # Get new status
        status = manager.get_status(request.session_id)

        return RefreshResponse(
            ok=True,
            state=status.state.value,
        )

    except Exception as e:
        # Clear building flag on error
        ctx = manager.get_context(request.session_id)
        if ctx and ctx.refresh_in_progress:
            manager.complete_refresh(request.session_id)

        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh context: {str(e)}",
        )
