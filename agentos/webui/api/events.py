"""
Events API - Event stream querying

GET /api/events - Query events with filters

Architecture:
- Subscribes to EventBus to capture all events
- Stores events in memory for HTTP API queries
- Provides REST interface as alternative to WebSocket
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from agentos.core.events.bus import get_event_bus
from agentos.core.events.types import Event as CoreEvent

logger = logging.getLogger(__name__)

router = APIRouter()


class Event(BaseModel):
    """Event model for API responses"""
    id: str
    type: str
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: str
    data: Dict[str, Any] = {}


# In-memory event store (connected to EventBus)
_events: List[Event] = []
_max_stored_events = 1000
_subscribed = False
_event_bus = None


def _ensure_subscribed():
    """Ensure subscribed to EventBus (lazy initialization)"""
    global _subscribed, _event_bus
    if _subscribed:
        return

    try:
        _event_bus = get_event_bus()
        _event_bus.subscribe(_on_event)
        _subscribed = True
        logger.info(f"Events API subscribed to EventBus (subscriber_count: {_event_bus.subscriber_count()})")

        # Emit test event to verify the flow
        try:
            test_event = CoreEvent.system_health(status="ok", message="Events API initialized")
            _event_bus.emit(test_event)
            logger.info("Test event emitted successfully")
        except Exception as test_error:
            logger.warning(f"Failed to emit test event: {test_error}")

    except Exception as e:
        logger.error(f"Failed to subscribe to EventBus: {e}", exc_info=True)


def _on_event(event: CoreEvent):
    """EventBus callback - store events for HTTP API"""
    try:
        # Extract task_id from entity if it's a task
        task_id = None
        if event.entity and event.entity.kind == "task":
            task_id = event.entity.id

        # Extract session_id from payload
        session_id = None
        if event.payload:
            session_id = event.payload.get("session_id")

        # Generate unique event ID
        event_id = f"{event.type.value}_{event.ts.replace(':', '-').replace('.', '-')}"

        # Convert CoreEvent to API Event model
        api_event = Event(
            id=event_id,
            type=event.type.value,
            task_id=task_id,
            session_id=session_id,
            timestamp=event.ts,
            data=event.payload or {}
        )

        # Add to store
        _events.append(api_event)

        # Keep only last N events
        if len(_events) > _max_stored_events:
            _events.pop(0)

        logger.debug(f"Event stored: {api_event.type} (total: {len(_events)})")
    except Exception as e:
        logger.error(f"Failed to store event: {e}", exc_info=True)


@router.get("/debug")
async def debug_events():
    """Debug endpoint to check EventBus subscription status"""
    _ensure_subscribed()  # Ensure subscribed
    bus = get_event_bus()
    return {
        "subscriber_count": bus.subscriber_count(),
        "sync_subscribers": len(bus._subscribers),
        "async_subscribers": len(bus._async_subscribers),
        "sync_subscriber_names": [sub.__name__ for sub in bus._subscribers],
        "async_subscriber_names": [sub.__name__ for sub in bus._async_subscribers],
        "events_stored": len(_events),
        "subscribed_flag": _subscribed,
    }


@router.post("/debug/emit")
async def emit_test_event():
    """Emit a test event to verify the flow"""
    from agentos.core.events.types import Event as CoreEvent

    event = CoreEvent.task_progress(
        task_id="test_debug_event",
        progress=75,
        message="Debug test event from API"
    )

    bus = get_event_bus()
    bus.emit(event)

    return {
        "message": "Test event emitted",
        "event_type": event.type.value,
        "subscriber_count": bus.subscriber_count(),
        "events_stored_after": len(_events)
    }


@router.get("")
async def query_events(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    since: Optional[str] = Query(None, description="Events since timestamp (ISO 8601)"),
    type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
) -> List[Event]:
    """
    Query events with filters

    Args:
        task_id: Filter by task ID
        session_id: Filter by session ID
        since: Filter events since timestamp
        type: Filter by event type
        limit: Maximum results

    Returns:
        List of events
    """
    # Ensure subscribed to EventBus
    _ensure_subscribed()

    events = _events.copy()

    # Apply filters
    if task_id:
        events = [e for e in events if e.task_id == task_id]
    if session_id:
        events = [e for e in events if e.session_id == session_id]
    if type:
        events = [e for e in events if e.type == type]
    if since:
        events = [e for e in events if e.timestamp >= since]

    # Sort by timestamp (newest first) and limit
    events = sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    return events


# Deprecated: Events are now automatically captured from EventBus
# def add_event(event: Event): ...
