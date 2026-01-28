"""Task Audit API - Endpoints for querying task audit trails

GET /api/tasks/{task_id}/audits - Get task audit records
GET /api/tasks/{task_id}/artifacts - Get task artifact references
GET /api/repos/{repo_id}/audits - Get repository audit trail
GET /api/repos/{repo_id}/artifacts - Get repository artifacts
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from agentos.core.task.audit_service import TaskAuditService, TaskAudit
from agentos.core.task.artifact_service import TaskArtifactService, TaskArtifactRef

router = APIRouter()


class AuditSummary(BaseModel):
    """Audit summary for API response"""

    audit_id: int
    task_id: str
    repo_id: Optional[str] = None
    level: str
    event_type: str
    operation: Optional[str] = None
    status: str
    files_changed: List[str] = []
    lines_added: int = 0
    lines_deleted: int = 0
    commit_hash: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str

    @classmethod
    def from_audit(cls, audit: TaskAudit) -> "AuditSummary":
        """Create from TaskAudit"""
        return cls(
            audit_id=audit.audit_id,
            task_id=audit.task_id,
            repo_id=audit.repo_id,
            level=audit.level,
            event_type=audit.event_type,
            operation=audit.operation,
            status=audit.status,
            files_changed=audit.files_changed,
            lines_added=audit.lines_added,
            lines_deleted=audit.lines_deleted,
            commit_hash=audit.commit_hash,
            error_message=audit.error_message,
            created_at=audit.created_at,
        )


class AuditDetail(AuditSummary):
    """Detailed audit record with Git summaries"""

    git_status_summary: Optional[str] = None
    git_diff_summary: Optional[str] = None
    payload: Dict[str, Any] = {}

    @classmethod
    def from_audit(cls, audit: TaskAudit) -> "AuditDetail":
        """Create from TaskAudit"""
        return cls(
            audit_id=audit.audit_id,
            task_id=audit.task_id,
            repo_id=audit.repo_id,
            level=audit.level,
            event_type=audit.event_type,
            operation=audit.operation,
            status=audit.status,
            files_changed=audit.files_changed,
            lines_added=audit.lines_added,
            lines_deleted=audit.lines_deleted,
            commit_hash=audit.commit_hash,
            error_message=audit.error_message,
            git_status_summary=audit.git_status_summary,
            git_diff_summary=audit.git_diff_summary,
            payload=audit.payload,
            created_at=audit.created_at,
        )


class ArtifactSummary(BaseModel):
    """Artifact summary for API response"""

    artifact_id: int
    task_id: str
    repo_id: str
    ref_type: str
    ref_value: str
    summary: str
    metadata: Dict[str, Any] = {}
    created_at: str

    @classmethod
    def from_artifact(cls, artifact: TaskArtifactRef) -> "ArtifactSummary":
        """Create from TaskArtifactRef"""
        return cls(
            artifact_id=artifact.artifact_id,
            task_id=artifact.task_id,
            repo_id=artifact.repo_id,
            ref_type=artifact.ref_type.value if hasattr(artifact.ref_type, "value") else artifact.ref_type,
            ref_value=artifact.ref_value,
            summary=artifact.summary,
            metadata=artifact.metadata,
            created_at=artifact.created_at,
        )


# ============================================
# Task Audit Endpoints
# ============================================


@router.get("/tasks/{task_id}/audits")
async def get_task_audits(
    task_id: str,
    repo_id: Optional[str] = Query(None, description="Filter by repository ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    detailed: bool = Query(False, description="Include Git summaries"),
) -> List[AuditSummary] | List[AuditDetail]:
    """
    Get audit records for a task

    Args:
        task_id: Task ID
        repo_id: Filter by repository ID (optional)
        event_type: Filter by event type (optional)
        limit: Maximum number of results
        detailed: Include Git change summaries (default: False)

    Returns:
        List of audit records (ordered by created_at DESC)
    """
    try:
        service = TaskAuditService()
        audits = service.get_task_audits(
            task_id=task_id,
            repo_id=repo_id,
            event_type=event_type,
            limit=limit,
        )

        # Convert to response model
        if detailed:
            return [AuditDetail.from_audit(audit) for audit in audits]
        else:
            return [AuditSummary.from_audit(audit) for audit in audits]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audits: {str(e)}")


@router.get("/repos/{repo_id}/audits")
async def get_repo_audits(
    repo_id: str,
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    detailed: bool = Query(False, description="Include Git summaries"),
) -> List[AuditSummary] | List[AuditDetail]:
    """
    Get audit trail for a repository (across all tasks)

    Args:
        repo_id: Repository ID
        limit: Maximum number of results
        detailed: Include Git change summaries (default: False)

    Returns:
        List of audit records (ordered by created_at DESC)
    """
    try:
        service = TaskAuditService()
        audits = service.get_repo_audits(repo_id=repo_id, limit=limit)

        # Convert to response model
        if detailed:
            return [AuditDetail.from_audit(audit) for audit in audits]
        else:
            return [AuditSummary.from_audit(audit) for audit in audits]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repo audits: {str(e)}")


# ============================================
# Task Artifact Endpoints
# ============================================


@router.get("/tasks/{task_id}/artifacts")
async def get_task_artifacts(
    task_id: str,
    repo_id: Optional[str] = Query(None, description="Filter by repository ID"),
    ref_type: Optional[str] = Query(None, description="Filter by reference type"),
) -> List[ArtifactSummary]:
    """
    Get artifact references for a task

    Args:
        task_id: Task ID
        repo_id: Filter by repository ID (optional)
        ref_type: Filter by reference type (commit, branch, pr, patch, file, tag)

    Returns:
        List of artifact references (ordered by created_at DESC)
    """
    try:
        service = TaskArtifactService()
        artifacts = service.get_task_artifacts(
            task_id=task_id,
            repo_id=repo_id,
            ref_type=ref_type,
        )

        return [ArtifactSummary.from_artifact(artifact) for artifact in artifacts]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get artifacts: {str(e)}")


@router.get("/repos/{repo_id}/artifacts")
async def get_repo_artifacts(
    repo_id: str,
    ref_type: Optional[str] = Query(None, description="Filter by reference type"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
) -> List[ArtifactSummary]:
    """
    Get artifact references for a repository (across all tasks)

    Args:
        repo_id: Repository ID
        ref_type: Filter by reference type (optional)
        limit: Maximum number of results

    Returns:
        List of artifact references (ordered by created_at DESC)
    """
    try:
        service = TaskArtifactService()
        artifacts = service.get_repo_artifacts(
            repo_id=repo_id,
            ref_type=ref_type,
            limit=limit,
        )

        return [ArtifactSummary.from_artifact(artifact) for artifact in artifacts]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repo artifacts: {str(e)}")
