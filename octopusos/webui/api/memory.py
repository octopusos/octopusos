"""Memory proposal API endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from octopusos.core.memory.capabilities import PermissionDenied
from octopusos.core.memory.proposals import get_proposal_service
from octopusos.core.time import utc_now_ms


router = APIRouter(prefix="/api/memory", tags=["memory"])


DEFAULT_PROPOSER = "chat_agent"
DEFAULT_REVIEWER = "user:admin"
MS_PER_SECOND = 1000


class ProposeMemoryRequest(BaseModel):
    agent_id: Optional[str] = None
    memory_item: Dict[str, Any]
    reason: Optional[str] = None


class ApproveProposalRequest(BaseModel):
    reviewer_id: Optional[str] = None
    reason: Optional[str] = None


class RejectProposalRequest(BaseModel):
    reviewer_id: Optional[str] = None
    reason: str


def _to_iso_from_ms(timestamp_ms: Optional[int]) -> str:
    if not timestamp_ms:
        timestamp_ms = utc_now_ms()
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp_ms / MS_PER_SECOND, tz=timezone.utc).isoformat()


def _coerce_content(memory_item: Dict[str, Any]) -> Dict[str, Any]:
    content = memory_item.get("content")
    if isinstance(content, dict):
        return content
    return {
        "key": memory_item.get("key"),
        "value": memory_item.get("value"),
    }


def _proposal_to_response_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    memory_item = raw.get("memory_item") or {}
    content = _coerce_content(memory_item)
    metadata = dict(memory_item.get("metadata") or {})
    metadata.setdefault("proposed_by", raw.get("proposed_by"))

    return {
        "id": raw.get("proposal_id"),
        "proposal_type": memory_item.get("type", "memory_update"),
        "content": metadata,
        "status": raw.get("status", "pending"),
        "created_at": _to_iso_from_ms(raw.get("proposed_at_ms")),
        "updated_at": _to_iso_from_ms(raw.get("reviewed_at_ms") or raw.get("proposed_at_ms")),
        "memory_item": {
            **memory_item,
            "content": content,
        },
    }


@router.post("/propose")
def propose_memory(req: ProposeMemoryRequest) -> Dict[str, Any]:
    proposal_service = get_proposal_service()
    agent_id = req.agent_id or DEFAULT_PROPOSER
    try:
        proposal_id = proposal_service.propose_memory(
            agent_id=agent_id,
            memory_item=req.memory_item,
            reason=req.reason,
        )
        return {"proposal_id": proposal_id, "status": "pending"}
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to propose memory: {e}") from e


@router.get("/proposals")
def list_proposals(
    status: Optional[str] = Query(default=None),
    proposed_by: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
) -> Dict[str, Any]:
    proposal_service = get_proposal_service()
    offset = (page - 1) * limit
    try:
        rows = proposal_service.list_proposals(
            agent_id=DEFAULT_REVIEWER,
            status=status,
            proposed_by=proposed_by,
            limit=limit,
            offset=offset,
        )
        proposals = [_proposal_to_response_row(row) for row in rows]
        return {"proposals": proposals, "total": len(proposals)}
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list memory proposals: {e}") from e


@router.get("/proposals/stats")
def proposal_stats() -> Dict[str, Any]:
    proposal_service = get_proposal_service()
    try:
        return proposal_service.get_proposal_stats(DEFAULT_REVIEWER)
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read proposal stats: {e}") from e


@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str) -> Dict[str, Any]:
    proposal_service = get_proposal_service()
    try:
        proposal = proposal_service.get_proposal(DEFAULT_REVIEWER, proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return {"proposal": _proposal_to_response_row(proposal)}
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get proposal: {e}") from e


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: str, req: ApproveProposalRequest) -> Dict[str, Any]:
    proposal_service = get_proposal_service()
    reviewer_id = req.reviewer_id or DEFAULT_REVIEWER
    try:
        proposal_service.approve_proposal(
            reviewer_id=reviewer_id,
            proposal_id=proposal_id,
            reason=req.reason,
        )
        proposal = proposal_service.get_proposal(reviewer_id, proposal_id)
        return {"proposal": _proposal_to_response_row(proposal or {})}
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve proposal: {e}") from e


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: str, req: RejectProposalRequest) -> Dict[str, Any]:
    proposal_service = get_proposal_service()
    reviewer_id = req.reviewer_id or DEFAULT_REVIEWER
    reason = (req.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    try:
        proposal_service.reject_proposal(
            reviewer_id=reviewer_id,
            proposal_id=proposal_id,
            reason=reason,
        )
        proposal = proposal_service.get_proposal(reviewer_id, proposal_id)
        return {"proposal": _proposal_to_response_row(proposal or {})}
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reject proposal: {e}") from e
