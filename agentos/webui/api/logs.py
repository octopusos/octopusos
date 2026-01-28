"""
Logs API - Structured log querying

GET /api/logs - Query logs with filters
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

router = APIRouter()


class LogEntry(BaseModel):
    """Log entry model"""
    id: str
    level: str  # "debug" | "info" | "warn" | "error"
    timestamp: str
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    span_id: Optional[str] = None
    message: str
    metadata: Dict[str, Any] = {}


# In-memory log store (TODO: integrate with actual logging system)
_logs: List[LogEntry] = []


@router.get("")
async def query_logs(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    since: Optional[str] = Query(None, description="Logs since timestamp (ISO 8601)"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
) -> List[LogEntry]:
    """
    Query logs with filters

    Args:
        task_id: Filter by task ID
        session_id: Filter by session ID
        level: Filter by log level
        since: Filter logs since timestamp
        limit: Maximum results

    Returns:
        List of log entries
    """
    logs = _logs.copy()

    # Apply filters
    if task_id:
        logs = [l for l in logs if l.task_id == task_id]
    if session_id:
        logs = [l for l in logs if l.session_id == session_id]
    if level:
        logs = [l for l in logs if l.level == level]
    if since:
        logs = [l for l in logs if l.timestamp >= since]

    # Sort by timestamp (newest first) and limit
    logs = sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]

    return logs


def add_log(log: LogEntry):
    """Add log entry (internal helper)"""
    _logs.append(log)

    # Keep only last 5000 logs in memory
    if len(_logs) > 5000:
        _logs.pop(0)
