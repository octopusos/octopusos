"""
Task Events API - Endpoints for Runner UI visualization

GET /api/tasks/{task_id}/events - Get task events (paginated, ordered by seq)
GET /api/tasks/{task_id}/events/latest - Get latest N events
GET /api/tasks/{task_id}/events/snapshot - Get initial snapshot for page load
GET /api/tasks/{task_id}/graph - Get span tree for pipeline graph rendering
GET /api/tasks/{task_id}/checkpoints - Get checkpoint events with evidence
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from agentos.core.task.event_service import TaskEventService, TaskEvent

router = APIRouter()


class EventResponse(BaseModel):
    """Event response model"""

    event_id: int
    task_id: str
    event_type: str
    phase: Optional[str] = None
    actor: str
    span_id: str
    parent_span_id: Optional[str] = None
    seq: int
    payload: Dict[str, Any] = {}
    created_at: str

    @classmethod
    def from_event(cls, event: TaskEvent) -> "EventResponse":
        """Create from TaskEvent"""
        return cls(
            event_id=event.event_id,
            task_id=event.task_id,
            event_type=event.event_type,
            phase=event.phase,
            actor=event.actor,
            span_id=event.span_id,
            parent_span_id=event.parent_span_id,
            seq=event.seq,
            payload=event.payload,
            created_at=event.created_at or "",
        )


class EventListResponse(BaseModel):
    """Paginated event list response"""

    events: List[EventResponse]
    total: int
    has_more: bool
    next_seq: Optional[int] = None


class SnapshotResponse(BaseModel):
    """Snapshot response for initial page load"""

    task_id: str
    events: List[EventResponse]
    total_events: int
    latest_seq: Optional[int] = None
    current_phase: Optional[str] = None
    active_spans: List[str] = []


class SpanNode(BaseModel):
    """Span node for graph rendering"""

    span_id: str
    parent_span_id: Optional[str] = None
    event_type: str
    phase: Optional[str] = None
    seq: int
    payload: Dict[str, Any] = {}


class GraphResponse(BaseModel):
    """Graph response for pipeline visualization"""

    task_id: str
    spans: List[SpanNode]
    edges: List[Dict[str, str]]  # [{"from": span_id, "to": span_id}]


# ============================================
# Event Streaming Endpoints
# ============================================


@router.get("/tasks/{task_id}/events")
async def get_task_events(
    task_id: str,
    since_seq: Optional[int] = Query(None, description="Resume from seq (exclusive)"),
    limit: int = Query(100, ge=1, le=1000, description="Max events to return"),
) -> EventListResponse:
    """
    Get task events (ordered by seq, supports pagination)

    Args:
        task_id: Task ID
        since_seq: Optional - Return events with seq > since_seq (for resumption)
        limit: Maximum number of events (default: 100, max: 1000)

    Returns:
        EventListResponse with events and pagination info

    Example:
        GET /api/tasks/task_01xyz/events?since_seq=100&limit=50
    """
    try:
        service = TaskEventService()

        # Get events
        events = service.get_events(task_id, since_seq=since_seq, limit=limit)

        # Get total count
        total = service.get_event_count(task_id)

        # Determine if there are more events
        has_more = len(events) == limit
        next_seq = events[-1].seq if events and has_more else None

        return EventListResponse(
            events=[EventResponse.from_event(e) for e in events],
            total=total,
            has_more=has_more,
            next_seq=next_seq,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get events: {str(e)}"
        )


@router.get("/tasks/{task_id}/events/latest")
async def get_latest_events(
    task_id: str,
    limit: int = Query(50, ge=1, le=500, description="Number of latest events"),
) -> EventListResponse:
    """
    Get latest N events for a task (ordered by seq DESC)

    Args:
        task_id: Task ID
        limit: Number of latest events (default: 50, max: 500)

    Returns:
        EventListResponse with latest events (reversed order)

    Example:
        GET /api/tasks/task_01xyz/events/latest?limit=20
    """
    try:
        service = TaskEventService()

        # Get latest events (DESC order)
        events = service.get_latest_events(task_id, limit=limit)

        # Get total count
        total = service.get_event_count(task_id)

        return EventListResponse(
            events=[EventResponse.from_event(e) for e in events],
            total=total,
            has_more=total > limit,
            next_seq=None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get latest events: {str(e)}"
        )


@router.get("/tasks/{task_id}/events/snapshot")
async def get_task_snapshot(
    task_id: str,
    limit: int = Query(100, ge=1, le=500, description="Number of events in snapshot"),
) -> SnapshotResponse:
    """
    Get task snapshot for initial page load

    Returns:
        - Latest N events
        - Total event count
        - Latest seq number
        - Current phase (derived from latest event)
        - Active spans (spans without exit events)

    Args:
        task_id: Task ID
        limit: Number of events in snapshot (default: 100, max: 500)

    Returns:
        SnapshotResponse with task state summary

    Example:
        GET /api/tasks/task_01xyz/events/snapshot?limit=50
    """
    try:
        service = TaskEventService()

        # Get latest events
        events = service.get_latest_events(task_id, limit=limit)

        # Get total count
        total = service.get_event_count(task_id)

        # Extract state from events
        latest_seq = events[0].seq if events else None
        current_phase = events[0].phase if events else None

        # Find active spans (spans with start but no exit)
        active_spans = []
        span_status = {}  # Track span lifecycle

        for event in reversed(events):  # Process in chronological order
            span_id = event.span_id
            if event.event_type in ["runner_spawn", "phase_enter", "work_item_start"]:
                span_status[span_id] = "active"
            elif event.event_type in ["runner_exit", "phase_exit", "work_item_complete", "work_item_failed"]:
                span_status[span_id] = "closed"

        active_spans = [span_id for span_id, status in span_status.items() if status == "active"]

        return SnapshotResponse(
            task_id=task_id,
            events=[EventResponse.from_event(e) for e in events],
            total_events=total,
            latest_seq=latest_seq,
            current_phase=current_phase,
            active_spans=active_spans,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get snapshot: {str(e)}"
        )


# ============================================
# Graph & Visualization Endpoints
# ============================================


@router.get("/tasks/{task_id}/graph")
async def get_task_graph(task_id: str) -> GraphResponse:
    """
    Get span tree for pipeline graph rendering

    Returns all events with span relationships intact.
    Client can build a graph from span_id and parent_span_id.

    Args:
        task_id: Task ID

    Returns:
        GraphResponse with span nodes and edges

    Example:
        GET /api/tasks/task_01xyz/graph
    """
    try:
        service = TaskEventService()

        # Get all events (ordered by seq)
        events = service.get_span_tree(task_id)

        # Build span nodes
        span_nodes = {}
        for event in events:
            if event.span_id not in span_nodes:
                span_nodes[event.span_id] = SpanNode(
                    span_id=event.span_id,
                    parent_span_id=event.parent_span_id,
                    event_type=event.event_type,
                    phase=event.phase,
                    seq=event.seq,
                    payload=event.payload,
                )

        # Build edges from parent relationships
        edges = []
        for span_id, node in span_nodes.items():
            if node.parent_span_id:
                edges.append({"from": node.parent_span_id, "to": span_id})

        return GraphResponse(
            task_id=task_id,
            spans=list(span_nodes.values()),
            edges=edges,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get graph: {str(e)}"
        )


# ============================================
# Checkpoint & Evidence Endpoints
# ============================================


@router.get("/tasks/{task_id}/checkpoints")
async def get_task_checkpoints(task_id: str) -> List[EventResponse]:
    """
    Get all checkpoint events with evidence references

    Args:
        task_id: Task ID

    Returns:
        List of checkpoint-related events with evidence_refs in payload

    Example:
        GET /api/tasks/task_01xyz/checkpoints

    Response payload includes:
        - checkpoint_id: Checkpoint identifier
        - checkpoint_type: Type of checkpoint
        - evidence_refs: Dictionary of evidence references
            - artifacts: List of artifact IDs
            - commit_hash: Git commit hash
            - work_items: List of work item IDs
    """
    try:
        service = TaskEventService()

        # Get checkpoint events
        events = service.get_checkpoint_events(task_id)

        return [EventResponse.from_event(e) for e in events]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get checkpoints: {str(e)}"
        )


# ============================================
# Phase-based Endpoints
# ============================================


@router.get("/tasks/{task_id}/events/phase/{phase}")
async def get_events_by_phase(
    task_id: str,
    phase: str,
    limit: int = Query(100, ge=1, le=1000, description="Max events"),
) -> EventListResponse:
    """
    Get events for a specific phase

    Args:
        task_id: Task ID
        phase: Phase name (planning, executing, verifying, recovery)
        limit: Maximum number of events (default: 100)

    Returns:
        EventListResponse with phase-filtered events

    Example:
        GET /api/tasks/task_01xyz/events/phase/executing?limit=50
    """
    try:
        service = TaskEventService()

        # Get events for phase
        events = service.get_events_by_phase(task_id, phase, limit=limit)

        # Get total count (all events)
        total = service.get_event_count(task_id)

        return EventListResponse(
            events=[EventResponse.from_event(e) for e in events],
            total=total,
            has_more=False,  # Phase filtering doesn't support pagination
            next_seq=None,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get phase events: {str(e)}"
        )


# ============================================
# Health Check
# ============================================


@router.get("/events/health")
async def events_health_check() -> Dict[str, str]:
    """
    Health check for events API

    Returns:
        Status message
    """
    return {"status": "ok", "service": "task_events_api", "version": "v0.32"}
