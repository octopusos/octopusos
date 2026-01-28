"""
Governance API - Decision Replay and Audit

Core endpoints for answering "Why was this task allowed/paused/blocked?"

GET /api/governance/tasks/{task_id}/summary - Task governance overview
GET /api/governance/tasks/{task_id}/decision-trace - Complete decision trace
GET /api/governance/decisions/{decision_id} - Single decision details
GET /api/governance/stats/blocked-reasons - Blocked tasks TopN
GET /api/governance/stats/decision-types - Decision type distribution
GET /api/governance/stats/decision-lag - Decision lag percentiles
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from agentos.core.supervisor.trace.replay import TraceAssembler, format_trace_item
from agentos.core.supervisor.trace.storage import TraceStorage
from agentos.core.supervisor.trace.stats import StatsCalculator
from agentos.store import get_db


router = APIRouter(prefix="/api/governance", tags=["governance"])


# Response Models
class AdminValidateResponse(BaseModel):
    """Admin validation response"""
    valid: bool
    message: str = "Admin access validated"


class TaskGovernanceSummaryResponse(BaseModel):
    """Task governance summary response"""
    task_id: str
    status: str
    last_decision_type: Optional[str] = None
    last_decision_ts: Optional[str] = None
    blocked_reason_code: Optional[str] = None
    inbox_backlog: int
    decision_count: int


class DecisionTraceResponse(BaseModel):
    """Decision trace response with pagination"""
    task_id: str
    trace_items: List[Dict[str, Any]]
    next_cursor: Optional[str] = None
    count: int


class DecisionDetailResponse(BaseModel):
    """Single decision detail response"""
    decision_id: str
    decision_snapshot: Dict[str, Any]


class BlockedReasonsStatsResponse(BaseModel):
    """Blocked reasons statistics response"""
    window: str
    top_n: int
    blocked_tasks: List[Dict[str, Any]]


class DecisionTypesStatsResponse(BaseModel):
    """Decision types statistics response"""
    window: str
    decision_types: Dict[str, int]
    total: int


class DecisionLagSample(BaseModel):
    """Single decision lag sample"""
    decision_id: str
    lag_ms: int
    source: str  # "columns" or "payload"


class DecisionLagStatsResponse(BaseModel):
    """Decision lag statistics response"""
    window: str
    percentile: int
    p50: Optional[float] = None
    p95: Optional[float] = None
    count: int
    samples: List[DecisionLagSample] = []
    query_method: str  # "columns" or "payload_fallback"
    redundant_column_coverage: float  # 0.0-1.0


def _parse_window(window: str) -> int:
    """
    Parse window string to hours

    Args:
        window: Window string (24h, 7d, 30d)

    Returns:
        Hours as integer

    Raises:
        ValueError: If window format is invalid
    """
    if window == "24h":
        return 24
    elif window == "7d":
        return 7 * 24
    elif window == "30d":
        return 30 * 24
    else:
        raise ValueError(f"Invalid window format: {window}")


@router.get("/admin/validate", response_model=AdminValidateResponse)
async def validate_admin() -> AdminValidateResponse:
    """
    Validate admin access

    Currently returns valid=True in local mode.
    In cloud deployments, this would check for admin tokens/permissions.

    Returns:
        AdminValidateResponse with valid field
    """
    # For local mode, always valid
    # In future cloud deployments, implement proper auth check
    return AdminValidateResponse(valid=True, message="Local mode - admin access granted")


@router.get("/tasks/{task_id}/summary", response_model=TaskGovernanceSummaryResponse)
async def get_task_governance_summary(task_id: str) -> TaskGovernanceSummaryResponse:
    """
    Get task governance summary

    Returns:
    - Task basic info (status, created_at)
    - Supervisor statistics (decision count, last decision, blocked reason)
    - Inbox backlog (if any)
    - Last N key audit events

    Args:
        task_id: Task ID

    Returns:
        Task governance summary

    Raises:
        HTTPException: 404 if task not found

    Example:
        ```bash
        curl http://localhost:8080/api/governance/tasks/task-123/summary
        ```
    """
    try:
        conn = get_db()
        storage = TraceStorage(conn)
        assembler = TraceAssembler(storage)

        summary = assembler.get_summary(task_id)

        if summary is None:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        return TaskGovernanceSummaryResponse(
            task_id=summary.task_id,
            status=summary.status,
            last_decision_type=summary.last_decision_type,
            last_decision_ts=summary.last_decision_ts,
            blocked_reason_code=summary.blocked_reason_code,
            inbox_backlog=summary.inbox_backlog,
            decision_count=summary.decision_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()


@router.get("/tasks/{task_id}/decision-trace", response_model=DecisionTraceResponse)
async def get_task_decision_trace(
    task_id: str,
    limit: int = Query(200, ge=1, le=500, description="Maximum number of trace items to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor (timestamp_id)")
) -> DecisionTraceResponse:
    """
    Get task decision trace (core endpoint)

    Returns time-ordered trace items:
    - event (from task_events / inbox)
    - supervisor_audit (with decision_snapshot)
    - resulting_state_change (task state changes)
    - gate_state_change (pause/enforcer records, if any)

    Args:
        task_id: Task ID
        limit: Maximum number of trace items (1-500, default 200)
        cursor: Pagination cursor for next page

    Returns:
        Decision trace with pagination support

    Raises:
        HTTPException: 400 if parameters invalid, 404 if task not found

    Example:
        ```bash
        # Get first page
        curl http://localhost:8080/api/governance/tasks/task-123/decision-trace?limit=50

        # Get next page
        curl http://localhost:8080/api/governance/tasks/task-123/decision-trace?limit=50&cursor=2024-01-01T00:00:00Z_123
        ```
    """
    try:
        # Validate limit
        if limit < 1 or limit > 500:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 500")

        conn = get_db()
        storage = TraceStorage(conn)
        assembler = TraceAssembler(storage)

        # Check if task exists
        task_info = storage.get_task_info(task_id)
        if task_info is None:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        # Get decision trace
        trace_items, next_cursor = assembler.get_decision_trace(
            task_id=task_id,
            limit=limit,
            cursor=cursor
        )

        # Format trace items for JSON response
        formatted_items = [format_trace_item(item) for item in trace_items]

        return DecisionTraceResponse(
            task_id=task_id,
            trace_items=formatted_items,
            next_cursor=next_cursor,
            count=len(formatted_items)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()


@router.get("/decisions/{decision_id}", response_model=DecisionDetailResponse)
async def get_decision(decision_id: str) -> DecisionDetailResponse:
    """
    Get single decision details

    Directly fetches decision_snapshot from audit.payload (no need to join many tables)

    Args:
        decision_id: Decision ID

    Returns:
        Complete decision snapshot

    Raises:
        HTTPException: 404 if decision not found

    Example:
        ```bash
        curl http://localhost:8080/api/governance/decisions/dec-123
        ```
    """
    try:
        conn = get_db()
        storage = TraceStorage(conn)
        assembler = TraceAssembler(storage)

        decision_snapshot = assembler.get_decision(decision_id)

        if decision_snapshot is None:
            raise HTTPException(
                status_code=404,
                detail=f"Decision not found: {decision_id}"
            )

        return DecisionDetailResponse(
            decision_id=decision_id,
            decision_snapshot=decision_snapshot
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()


@router.get("/stats/blocked-reasons", response_model=BlockedReasonsStatsResponse)
async def stats_blocked_reasons(
    window: str = Query("7d", pattern="^(24h|7d|30d)$", description="Time window (24h, 7d, 30d)"),
    top_n: int = Query(20, ge=1, le=100, description="Number of top results")
) -> BlockedReasonsStatsResponse:
    """
    Statistics: Blocked/Paused TopN (for Dashboard)

    Returns top N tasks by block count, useful for identifying problematic patterns

    Args:
        window: Time window (24h, 7d, 30d)
        top_n: Number of top results (1-100, default 20)

    Returns:
        Top N blocked tasks with reason codes

    Example:
        ```bash
        curl http://localhost:8080/api/governance/stats/blocked-reasons?window=7d&top_n=10
        ```
    """
    try:
        # Validate parameters
        if top_n < 1 or top_n > 100:
            raise HTTPException(status_code=400, detail="top_n must be between 1 and 100")

        conn = get_db()
        calculator = StatsCalculator(conn)

        blocked_tasks = calculator.get_blocked_tasks_topn(limit=top_n)

        return BlockedReasonsStatsResponse(
            window=window,
            top_n=top_n,
            blocked_tasks=blocked_tasks
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()


@router.get("/stats/decision-types", response_model=DecisionTypesStatsResponse)
async def stats_decision_types(
    window: str = Query("24h", pattern="^(24h|7d|30d)$", description="Time window (24h, 7d, 30d)")
) -> DecisionTypesStatsResponse:
    """
    Statistics: Decision type distribution

    Returns count of each decision type (ALLOW, PAUSE, BLOCK, RETRY) within time window

    Args:
        window: Time window (24h, 7d, 30d)

    Returns:
        Decision type distribution statistics

    Example:
        ```bash
        curl http://localhost:8080/api/governance/stats/decision-types?window=24h
        ```
    """
    try:
        hours = _parse_window(window)

        conn = get_db()
        calculator = StatsCalculator(conn)

        decision_types = calculator.get_decision_type_stats(hours=hours)
        total = sum(decision_types.values())

        return DecisionTypesStatsResponse(
            window=window,
            decision_types=decision_types,
            total=total
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()


@router.get("/stats/decision-lag", response_model=DecisionLagStatsResponse)
async def stats_decision_lag(
    window: str = Query("24h", pattern="^(24h|7d|30d)$", description="Time window (24h, 7d, 30d)"),
    pctl: int = Query(95, ge=50, le=99, description="Percentile to calculate (50-99)")
) -> DecisionLagStatsResponse:
    """
    Statistics: Decision lag percentiles

    Calculates decision processing lag (time from event to decision) percentiles

    v21+ Enhancement: Returns data source information (redundant columns vs payload)

    Args:
        window: Time window (24h, 7d, 30d)
        pctl: Percentile to calculate (50-99, default 95)

    Returns:
        Decision lag statistics with:
        - p50, p95: Percentile values (seconds)
        - count: Total samples
        - samples: High-lag samples with data source tags
        - query_method: "columns" (v21+ fast) or "payload_fallback" (v20 compat)
        - redundant_column_coverage: Percentage using v21 columns (0.0-1.0)

    Example:
        ```bash
        curl http://localhost:8080/api/governance/stats/decision-lag?window=24h&pctl=95
        ```
    """
    try:
        # Validate percentile
        if pctl < 50 or pctl > 99:
            raise HTTPException(status_code=400, detail="pctl must be between 50 and 99")

        hours = _parse_window(window)

        conn = get_db()
        calculator = StatsCalculator(conn)

        lag_stats = calculator.get_decision_lag_percentiles(hours=hours)

        # Convert samples to response model
        samples = [
            DecisionLagSample(
                decision_id=s["decision_id"],
                lag_ms=s["lag_ms"],
                source=s["source"]
            )
            for s in lag_stats.get("samples", [])
        ]

        return DecisionLagStatsResponse(
            window=window,
            percentile=pctl,
            p50=lag_stats.get("p50"),
            p95=lag_stats.get("p95"),
            count=lag_stats.get("count", 0),
            samples=samples,
            query_method=lag_stats.get("query_method", "payload_fallback"),
            redundant_column_coverage=lag_stats.get("redundant_column_coverage", 0.0)
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()
