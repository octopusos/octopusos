"""
Logs API - Structured log querying

GET /api/logs - Query logs with filters
"""

from fastapi import APIRouter, Query
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime, timezone

# Import LogEntry from shared models
from agentos.core.logging.models import LogEntry

router = APIRouter()

# Forward declaration for type checking
if TYPE_CHECKING:
    from agentos.core.logging.store import LogStore


# Global log store instance (injected at startup)
_log_store: Optional["LogStore"] = None


def set_log_store(store: "LogStore") -> None:
    """
    Set the global log store instance.

    This should be called during application startup to inject
    the LogStore dependency.

    Args:
        store: The LogStore instance to use
    """
    global _log_store
    _log_store = store


@router.get("")
async def query_logs(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    since: Optional[str] = Query(None, description="Logs since timestamp (ISO 8601)"),
    logger: Optional[str] = Query(None, description="Filter by logger name"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
) -> List[LogEntry]:
    """
    Query logs with filters

    Args:
        task_id: Filter by task ID
        session_id: Filter by session ID
        level: Filter by log level
        since: Filter logs since timestamp
        logger: Filter by logger name
        limit: Maximum results

    Returns:
        List of log entries
    """
    # Use LogStore if available, otherwise return empty list
    if _log_store is None:
        return []

    # Query from LogStore (handles all filtering)
    logs = _log_store.query(
        task_id=task_id,
        session_id=session_id,
        level=level,
        since=since,
        logger_name=logger,
        limit=limit,
    )

    return logs


def add_log(log: LogEntry):
    """
    Add log entry (internal helper for backward compatibility).

    This function is kept for backward compatibility but now uses
    LogStore if available.

    Args:
        log: The log entry to add
    """
    if _log_store is not None:
        _log_store.add(log)
