"""
Execution Snapshot API - Task execution aggregation endpoint

This module provides a unified execution snapshot aggregation endpoint that combines
data from multiple sources (task_manager, task_audit, artifact_service) to give
a complete view of task execution state.

Created for Agent-API-Contract (Wave1-A2)

Key Features:
1. Aggregated task execution snapshot (plan, steps, logs, artifacts, diffs)
2. Selective field inclusion via query parameters
3. Performance-optimized queries (avoid N+1)
4. Standard API response contract
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query, Depends

from agentos.core.task.manager import TaskManager
from agentos.core.task.audit_service import TaskAuditService
from agentos.core.task.artifact_service import TaskArtifactService
from agentos.store import get_db
from agentos.webui.api.contracts import (
    success,
    not_found_error,
    validation_error,
    ReasonCode,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/execution", tags=["execution"])


# ============================================
# Response Models
# ============================================

class ExecutionPlanStep(BaseModel):
    """Single execution step in plan"""
    step_id: str = Field(..., description="Step identifier")
    description: str = Field(..., description="Step description")
    status: str = Field(..., description="Step status (pending, running, completed, failed)")
    started_at: Optional[str] = Field(None, description="Step start timestamp")
    completed_at: Optional[str] = Field(None, description="Step completion timestamp")


class ExecutionPlan(BaseModel):
    """Task execution plan"""
    plan_id: Optional[str] = Field(None, description="Plan identifier")
    title: str = Field(..., description="Plan title")
    created_at: str = Field(..., description="Plan creation timestamp")
    steps: List[ExecutionPlanStep] = Field(default_factory=list, description="Execution steps")


class ExecutionLog(BaseModel):
    """Task execution log entry"""
    log_id: int = Field(..., description="Log entry ID")
    level: str = Field(..., description="Log level (info, warn, error)")
    event_type: str = Field(..., description="Event type")
    message: Optional[str] = Field(None, description="Log message")
    timestamp: str = Field(..., description="Log timestamp")
    repo_id: Optional[str] = Field(None, description="Repository ID (if repo-scoped)")


class ExecutionArtifact(BaseModel):
    """Task execution artifact"""
    artifact_id: int = Field(..., description="Artifact ID")
    repo_id: str = Field(..., description="Repository ID")
    ref_type: str = Field(..., description="Reference type (commit, branch, pr, etc.)")
    ref_value: str = Field(..., description="Reference value (commit hash, branch name, etc.)")
    summary: str = Field(..., description="Artifact summary")
    created_at: str = Field(..., description="Artifact creation timestamp")


class ExecutionDiff(BaseModel):
    """Task execution file diff summary"""
    file_path: str = Field(..., description="File path")
    lines_added: int = Field(0, description="Number of lines added")
    lines_deleted: int = Field(0, description="Number of lines deleted")
    status: str = Field(..., description="File status (added, modified, deleted)")


class ExecutionSnapshot(BaseModel):
    """Complete task execution snapshot

    Aggregates data from multiple sources to provide a unified view of task execution.
    """

    # Task basic info
    task_id: str = Field(..., description="Task ID")
    title: str = Field(..., description="Task title")
    status: str = Field(..., description="Task status")
    created_at: str = Field(..., description="Task creation timestamp")
    updated_at: str = Field(..., description="Task last update timestamp")

    # Execution plan (optional, controlled by ?include=plan)
    plan: Optional[ExecutionPlan] = Field(None, description="Execution plan")

    # Execution steps (optional, controlled by ?include=steps)
    steps: Optional[List[ExecutionPlanStep]] = Field(None, description="Execution steps")

    # Execution logs (optional, controlled by ?include=logs)
    logs: Optional[List[ExecutionLog]] = Field(None, description="Execution logs")

    # Artifacts (optional, controlled by ?include=artifacts)
    artifacts: Optional[List[ExecutionArtifact]] = Field(None, description="Execution artifacts")

    # Diffs (optional, controlled by ?include=diffs)
    diffs: Optional[List[ExecutionDiff]] = Field(None, description="File change summary")

    class Config:
        schema_extra = {
            "example": {
                "task_id": "01HQ7XYZ...",
                "title": "Implement feature X",
                "status": "running",
                "created_at": "2025-01-29T10:00:00Z",
                "updated_at": "2025-01-29T10:15:00Z",
                "plan": {
                    "plan_id": "plan-1",
                    "title": "Feature implementation plan",
                    "created_at": "2025-01-29T10:00:00Z",
                    "steps": [
                        {
                            "step_id": "step-1",
                            "description": "Design API",
                            "status": "completed",
                            "started_at": "2025-01-29T10:00:00Z",
                            "completed_at": "2025-01-29T10:05:00Z",
                        }
                    ],
                },
                "logs": [
                    {
                        "log_id": 1,
                        "level": "info",
                        "event_type": "task_started",
                        "message": "Task execution started",
                        "timestamp": "2025-01-29T10:00:00Z",
                        "repo_id": None,
                    }
                ],
                "artifacts": [
                    {
                        "artifact_id": 1,
                        "repo_id": "repo-1",
                        "ref_type": "commit",
                        "ref_value": "abc123...",
                        "summary": "Initial implementation",
                        "created_at": "2025-01-29T10:15:00Z",
                    }
                ],
                "diffs": [
                    {
                        "file_path": "src/api.py",
                        "lines_added": 50,
                        "lines_deleted": 10,
                        "status": "modified",
                    }
                ],
            }
        }


# ============================================
# API Endpoints
# ============================================

@router.get("/{task_id}/snapshot")
async def get_execution_snapshot(
    task_id: str,
    include: Optional[str] = Query(
        "plan,steps,logs,artifacts,diffs",
        description="Comma-separated list of fields to include (plan, steps, logs, artifacts, diffs)"
    ),
    log_limit: int = Query(100, ge=1, le=1000, description="Maximum number of log entries to return"),
    artifact_limit: int = Query(50, ge=1, le=500, description="Maximum number of artifacts to return"),
) -> Dict[str, Any]:
    """
    Get execution snapshot for a task

    Returns a unified view of task execution state, aggregating data from:
    - Task manager (basic info, status)
    - Task audits (logs, operations)
    - Artifact service (commits, PRs, branches)
    - Route plan (execution plan, steps)

    Args:
        task_id: Task ID
        include: Comma-separated list of fields to include (default: all)
        log_limit: Maximum number of log entries (default: 100, max: 1000)
        artifact_limit: Maximum number of artifacts (default: 50, max: 500)

    Returns:
        Standard API response with ExecutionSnapshot data

    Raises:
        HTTPException: 404 if task not found, 400 if invalid parameters

    Example:
        # Get full snapshot
        GET /api/execution/01HQ7XYZ.../snapshot

        # Get only plan and logs
        GET /api/execution/01HQ7XYZ.../snapshot?include=plan,logs

        # Get with limits
        GET /api/execution/01HQ7XYZ.../snapshot?log_limit=50&artifact_limit=20
    """
    try:
        # Validate task_id format
        if not task_id or len(task_id) < 10:
            raise validation_error(
                "Invalid task_id format",
                hint="task_id must be a valid ULID (at least 10 characters)",
            )

        # Parse include parameter
        include_fields = set(f.strip().lower() for f in include.split(",")) if include else set()

        # Initialize services
        task_manager = TaskManager()
        audit_service = TaskAuditService()
        artifact_service = TaskArtifactService()

        # Get task basic info
        task = task_manager.get_task(task_id)
        if not task:
            raise not_found_error("Task", task_id)

        # Build snapshot
        snapshot_data: Dict[str, Any] = {
            "task_id": task.task_id,
            "title": task.title,
            "status": task.status,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

        # Add optional fields based on include parameter
        if "plan" in include_fields or "steps" in include_fields:
            plan_data = _get_execution_plan(task)
            if "plan" in include_fields:
                snapshot_data["plan"] = plan_data
            if "steps" in include_fields:
                snapshot_data["steps"] = plan_data.get("steps", []) if plan_data else []

        if "logs" in include_fields:
            snapshot_data["logs"] = _get_execution_logs(task_id, audit_service, limit=log_limit)

        if "artifacts" in include_fields:
            snapshot_data["artifacts"] = _get_execution_artifacts(
                task_id, artifact_service, limit=artifact_limit
            )

        if "diffs" in include_fields:
            snapshot_data["diffs"] = _get_execution_diffs(task_id, audit_service)

        return success(snapshot_data)

    except Exception as e:
        if isinstance(e, Exception) and hasattr(e, 'status_code'):
            # Re-raise HTTPException
            raise
        logger.exception(f"Failed to get execution snapshot for task {task_id}")
        raise validation_error(
            f"Failed to get execution snapshot: {str(e)}",
            hint="Check server logs for details",
        )


# ============================================
# Helper Functions
# ============================================

def _get_execution_plan(task) -> Optional[Dict[str, Any]]:
    """Extract execution plan from task metadata or route plan

    Args:
        task: Task object

    Returns:
        Execution plan dictionary or None
    """
    try:
        # Try to get plan from route_plan_json (router integration)
        if task.route_plan_json:
            route_plan = json.loads(task.route_plan_json)
            return {
                "plan_id": route_plan.get("plan_id"),
                "title": route_plan.get("title", task.title),
                "created_at": task.created_at,
                "steps": route_plan.get("steps", []),
            }

        # Try to get plan from metadata
        if task.metadata and "execution_plan" in task.metadata:
            plan = task.metadata["execution_plan"]
            return {
                "plan_id": plan.get("plan_id"),
                "title": plan.get("title", task.title),
                "created_at": task.created_at,
                "steps": plan.get("steps", []),
            }

        # No plan available
        return None

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to parse execution plan for task {task.task_id}: {e}")
        return None


def _get_execution_logs(
    task_id: str,
    audit_service: TaskAuditService,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get execution logs from task audits

    Args:
        task_id: Task ID
        audit_service: Audit service instance
        limit: Maximum number of logs

    Returns:
        List of log entries
    """
    try:
        # Query audits from database
        conn = audit_service.db
        cursor = conn.execute(
            """
            SELECT audit_id, task_id, repo_id, level, event_type, payload, created_at
            FROM task_audits
            WHERE task_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (task_id, limit),
        )

        logs = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Parse payload for message
            payload = {}
            if row_dict.get("payload"):
                try:
                    payload = json.loads(row_dict["payload"])
                except (json.JSONDecodeError, TypeError):
                    pass

            logs.append({
                "log_id": row_dict["audit_id"],
                "level": row_dict["level"],
                "event_type": row_dict["event_type"],
                "message": payload.get("message") or payload.get("error_message"),
                "timestamp": row_dict["created_at"],
                "repo_id": row_dict.get("repo_id"),
            })

        return logs

    except Exception as e:
        logger.warning(f"Failed to get execution logs for task {task_id}: {e}")
        return []


def _get_execution_artifacts(
    task_id: str,
    artifact_service: TaskArtifactService,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get execution artifacts

    Args:
        task_id: Task ID
        artifact_service: Artifact service instance
        limit: Maximum number of artifacts

    Returns:
        List of artifact entries
    """
    try:
        # Query artifacts using artifact service
        artifacts = artifact_service.get_task_artifacts(task_id)

        # Limit results
        artifacts = artifacts[:limit]

        # Convert to response format
        return [
            {
                "artifact_id": art.artifact_id,
                "repo_id": art.repo_id,
                "ref_type": art.ref_type.value if hasattr(art.ref_type, 'value') else art.ref_type,
                "ref_value": art.ref_value,
                "summary": art.summary,
                "created_at": art.created_at,
            }
            for art in artifacts
        ]

    except Exception as e:
        logger.warning(f"Failed to get execution artifacts for task {task_id}: {e}")
        return []


def _get_execution_diffs(
    task_id: str,
    audit_service: TaskAuditService
) -> List[Dict[str, Any]]:
    """Get execution file diffs from audit logs

    Args:
        task_id: Task ID
        audit_service: Audit service instance

    Returns:
        List of file diff summaries
    """
    try:
        # Query audits with git change information
        conn = audit_service.db
        cursor = conn.execute(
            """
            SELECT payload
            FROM task_audits
            WHERE task_id = ?
            AND event_type IN ('repo_write', 'repo_commit')
            ORDER BY created_at DESC
            """,
            (task_id,),
        )

        # Aggregate file changes
        file_changes: Dict[str, Dict[str, Any]] = {}

        for row in cursor.fetchall():
            row_dict = dict(row)
            if not row_dict.get("payload"):
                continue

            try:
                payload = json.loads(row_dict["payload"])
                files_changed = payload.get("files_changed", [])
                lines_added = payload.get("lines_added", 0)
                lines_deleted = payload.get("lines_deleted", 0)

                # Update file change summary
                for file_path in files_changed:
                    if file_path not in file_changes:
                        file_changes[file_path] = {
                            "file_path": file_path,
                            "lines_added": 0,
                            "lines_deleted": 0,
                            "status": "modified",
                        }
                    # Aggregate changes (rough estimate)
                    file_changes[file_path]["lines_added"] += lines_added // max(len(files_changed), 1)
                    file_changes[file_path]["lines_deleted"] += lines_deleted // max(len(files_changed), 1)

            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.debug(f"Failed to parse audit payload: {e}")
                continue

        return list(file_changes.values())

    except Exception as e:
        logger.warning(f"Failed to get execution diffs for task {task_id}: {e}")
        return []
