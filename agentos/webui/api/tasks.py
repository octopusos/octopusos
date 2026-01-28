"""
Tasks API - Task querying and routing

GET /api/tasks - List tasks (with filters)
GET /api/tasks/{id} - Get task details
GET /api/tasks/{id}/route - Get task routing plan
POST /api/tasks/{id}/route - Override task routing
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json

from agentos.core.task import TaskManager, Task
from agentos.core.task.routing_service import TaskRoutingService
from agentos.router.models import RoutePlan

router = APIRouter()


class TaskSummary(BaseModel):
    """Task summary for list view"""
    task_id: str
    title: str
    status: str
    session_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = {}


@router.get("")
async def list_tasks(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
) -> List[TaskSummary]:
    """
    List tasks with optional filters

    Args:
        session_id: Filter by session ID
        status: Filter by status
        limit: Maximum number of results

    Returns:
        List of task summaries
    """
    try:
        manager = TaskManager()
        tasks = manager.list_tasks(limit=limit)

        # Apply filters
        if session_id:
            tasks = [t for t in tasks if t.session_id == session_id]
        if status:
            tasks = [t for t in tasks if t.status == status]

        # Convert to summaries
        summaries = [
            TaskSummary(
                task_id=t.task_id,
                title=t.title,
                status=t.status,
                session_id=t.session_id,
                created_at=t.created_at,
                updated_at=t.updated_at,
                metadata=t.metadata,
            )
            for t in tasks
        ]

        return summaries

    except Exception as e:
        # Return empty list on error
        return []


@router.get("/{task_id}")
async def get_task(task_id: str) -> Task:
    """
    Get task details by ID

    Args:
        task_id: Task ID

    Returns:
        Task details
    """
    manager = TaskManager()
    task = manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


# Routing endpoints (PR-2: Chat→Task Router Integration)


class RoutePlanResponse(BaseModel):
    """Route plan response"""
    task_id: str
    selected: str
    fallback: List[str]
    scores: Dict[str, float]
    reasons: List[str]
    router_version: str
    timestamp: str
    requirements: Optional[Dict[str, Any]] = None


class RouteOverrideRequest(BaseModel):
    """Route override request"""
    instance_id: str


@router.get("/{task_id}/route")
async def get_task_route(task_id: str) -> RoutePlanResponse:
    """
    Get routing plan for a task

    Args:
        task_id: Task ID

    Returns:
        RoutePlanResponse with routing details
    """
    manager = TaskManager()
    task = manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.route_plan_json:
        raise HTTPException(status_code=404, detail="Task has no routing information")

    try:
        plan_dict = json.loads(task.route_plan_json)
        plan = RoutePlan.from_dict(plan_dict)

        return RoutePlanResponse(
            task_id=plan.task_id,
            selected=plan.selected,
            fallback=plan.fallback,
            scores=plan.scores,
            reasons=plan.reasons,
            router_version=plan.router_version,
            timestamp=plan.timestamp or "",
            requirements=plan.requirements.to_dict() if plan.requirements else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse routing information: {str(e)}"
        )


@router.post("/{task_id}/route")
async def override_task_route(
    task_id: str,
    request: RouteOverrideRequest,
) -> RoutePlanResponse:
    """
    Override task routing (manual instance selection)

    Args:
        task_id: Task ID
        request: RouteOverrideRequest with new instance_id

    Returns:
        Updated RoutePlanResponse
    """
    try:
        routing_service = TaskRoutingService()
        new_plan = routing_service.override_route(task_id, request.instance_id)

        return RoutePlanResponse(
            task_id=new_plan.task_id,
            selected=new_plan.selected,
            fallback=new_plan.fallback,
            scores=new_plan.scores,
            reasons=new_plan.reasons,
            router_version=new_plan.router_version,
            timestamp=new_plan.timestamp or "",
            requirements=new_plan.requirements.to_dict() if new_plan.requirements else None,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to override route: {str(e)}"
        )
