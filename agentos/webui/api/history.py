"""
History API - Command history querying

GET /api/history - Query command history with filters
GET /api/history/pinned - Get pinned commands
POST /api/history/{history_id}/pin - Pin a command
DELETE /api/history/{history_id}/pin - Unpin a command
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path

router = APIRouter()


class HistoryEntry(BaseModel):
    """History entry model"""
    id: str
    command_id: str
    args: Dict[str, Any]
    executed_at: str
    duration_ms: Optional[int]
    status: str  # "success" | "failure" | "running"
    result_summary: Optional[str]
    error: Optional[str]
    task_id: Optional[str]
    session_id: Optional[str]
    is_pinned: bool = False


@router.get("")
async def query_history(
    command_id: Optional[str] = Query(None, description="Filter by command ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
) -> List[HistoryEntry]:
    """
    Query command history with filters

    Args:
        command_id: Filter by command ID (e.g., "kb:search")
        status: Filter by status ("success", "failure")
        task_id: Filter by task ID
        session_id: Filter by session ID
        limit: Maximum results

    Returns:
        List of history entries
    """
    from agentos.core.command.history import CommandHistoryService

    try:
        service = CommandHistoryService()
        entries = service.list(
            command_id=command_id,
            status=status,
            task_id=task_id,
            limit=limit
        )

        # Get pinned entries to mark them
        pinned_entries = service.list_pinned()
        pinned_ids = {e.id for e in pinned_entries}

        # Convert to HistoryEntry models
        result = []
        for entry in entries:
            result.append(
                HistoryEntry(
                    id=entry.id,
                    command_id=entry.command_id,
                    args=entry.args,
                    executed_at=entry.executed_at,
                    duration_ms=entry.duration_ms,
                    status=entry.status,
                    result_summary=entry.result_summary,
                    error=entry.error,
                    task_id=entry.task_id,
                    session_id=entry.session_id,
                    is_pinned=entry.id in pinned_ids,
                )
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query history: {str(e)}")


@router.get("/pinned")
async def get_pinned() -> List[HistoryEntry]:
    """
    Get all pinned commands

    Returns:
        List of pinned history entries
    """
    from agentos.core.command.history import CommandHistoryService

    try:
        service = CommandHistoryService()
        entries = service.list_pinned()

        # Convert to HistoryEntry models
        result = []
        for entry in entries:
            result.append(
                HistoryEntry(
                    id=entry.id,
                    command_id=entry.command_id,
                    args=entry.args,
                    executed_at=entry.executed_at,
                    duration_ms=entry.duration_ms,
                    status=entry.status,
                    result_summary=entry.result_summary,
                    error=entry.error,
                    task_id=entry.task_id,
                    session_id=entry.session_id,
                    is_pinned=True,
                )
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pinned commands: {str(e)}")


class PinRequest(BaseModel):
    """Pin request model"""
    note: Optional[str] = None


@router.post("/{history_id}/pin")
async def pin_command(history_id: str, request: PinRequest) -> Dict[str, str]:
    """
    Pin a command

    Args:
        history_id: History entry ID
        request: Pin request with optional note

    Returns:
        Pin ID
    """
    from agentos.core.command.history import CommandHistoryService

    try:
        service = CommandHistoryService()

        # Check if entry exists
        entry = service.get(history_id)
        if not entry:
            raise HTTPException(status_code=404, detail=f"History entry not found: {history_id}")

        pin_id = service.pin(history_id, note=request.note)

        return {"pin_id": pin_id, "message": "Command pinned successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pin command: {str(e)}")


@router.delete("/{history_id}/pin")
async def unpin_command(history_id: str) -> Dict[str, str]:
    """
    Unpin a command

    Args:
        history_id: History entry ID

    Returns:
        Success message
    """
    from agentos.core.command.history import CommandHistoryService

    try:
        service = CommandHistoryService()

        # Check if entry exists
        entry = service.get(history_id)
        if not entry:
            raise HTTPException(status_code=404, detail=f"History entry not found: {history_id}")

        service.unpin(history_id)

        return {"message": "Command unpinned successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unpin command: {str(e)}")


@router.get("/{history_id}")
async def get_history_entry(history_id: str) -> HistoryEntry:
    """
    Get a specific history entry

    Args:
        history_id: History entry ID

    Returns:
        History entry
    """
    from agentos.core.command.history import CommandHistoryService

    try:
        service = CommandHistoryService()
        entry = service.get(history_id)

        if not entry:
            raise HTTPException(status_code=404, detail=f"History entry not found: {history_id}")

        # Check if pinned
        pinned_entries = service.list_pinned()
        is_pinned = entry.id in {e.id for e in pinned_entries}

        return HistoryEntry(
            id=entry.id,
            command_id=entry.command_id,
            args=entry.args,
            executed_at=entry.executed_at,
            duration_ms=entry.duration_ms,
            status=entry.status,
            result_summary=entry.result_summary,
            error=entry.error,
            task_id=entry.task_id,
            session_id=entry.session_id,
            is_pinned=is_pinned,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history entry: {str(e)}")
