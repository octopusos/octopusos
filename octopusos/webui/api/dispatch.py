"""Dispatch Proposal API (v3.3)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException, Query

from octopusos.core.capabilities.admin_token import validate_admin_token
from octopusos.core.dispatch import (
    DispatchRepo,
    DispatchProposal,
    DispatchEngine,
    calculate_risk,
    can_transition,
)
from octopusos.core.time import utc_now_ms
from octopusos.store.timestamp_utils import from_epoch_ms

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])


STATUS_PENDING = "pending"


def _iso_from_ms(ms: int) -> str:
    dt = from_epoch_ms(ms)
    if dt is None:
        return ""
    return dt.isoformat().replace('+00:00', 'Z')


def _require_admin_token(token: Optional[str]) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="Admin token required")
    if not validate_admin_token(token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return "admin"


def _proposal_to_response(proposal: DispatchProposal) -> Dict[str, Any]:
    data = proposal.to_dict()
    data["requested_at"] = _iso_from_ms(proposal.requested_at)
    data["reviewed_at"] = _iso_from_ms(proposal.reviewed_at) if proposal.reviewed_at else None
    data["created_at"] = _iso_from_ms(proposal.created_at)
    data["updated_at"] = _iso_from_ms(proposal.updated_at)
    return data


def _job_to_response(job) -> Dict[str, Any]:
    data = job.to_dict()
    data["started_at"] = _iso_from_ms(job.started_at) if job.started_at else None
    data["ended_at"] = _iso_from_ms(job.ended_at) if job.ended_at else None
    data["created_at"] = _iso_from_ms(job.created_at)
    data["updated_at"] = _iso_from_ms(job.updated_at)
    return data


@router.post("/proposals")
def create_proposal(payload: Dict[str, Any] = Body(...)):
    repo = DispatchRepo()
    repo.ensure_tables()

    proposal_type = payload.get("proposal_type")
    if not proposal_type:
        raise HTTPException(status_code=400, detail="proposal_type is required")

    scope = payload.get("scope") or {"type": "global"}
    payload_data = payload.get("payload") or {}
    reason = payload.get("reason") or ""
    evidence_refs = payload.get("evidence_refs") or []

    risk_level = payload.get("risk_level")
    calculated_risk = calculate_risk(str(proposal_type), payload_data)
    if risk_level not in {"low", "medium", "high", "critical"}:
        risk_level = calculated_risk
    elif risk_level != calculated_risk:
        risk_level = calculated_risk

    now = utc_now_ms()
    proposal_id = f"dp_{now}_{proposal_type}"

    proposal = DispatchProposal(
        proposal_id=proposal_id,
        source=payload.get("source") or "frontdesk",
        proposal_type=str(proposal_type),
        status=STATUS_PENDING,
        risk_level=risk_level,
        scope=scope,
        payload=payload_data,
        reason=reason,
        evidence_refs=evidence_refs,
        requested_by=payload.get("requested_by") or "frontdesk",
        requested_at=now,
        reviewed_by=None,
        reviewed_at=None,
        review_comment=None,
        execution_ref=None,
        created_at=now,
        updated_at=now,
    )

    repo.create_proposal(proposal)
    repo.append_audit(
        proposal_id,
        "create",
        proposal.requested_by,
        {
            "status_before": None,
            "status_after": STATUS_PENDING,
            "evidence_refs": evidence_refs,
        },
    )

    return {"proposal_id": proposal_id, "status": STATUS_PENDING, "risk_level": risk_level}


@router.get("/proposals")
def list_proposals(status: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    repo = DispatchRepo()
    repo.ensure_tables()
    proposals = repo.list_proposals(status=status, limit=limit)
    return {"proposals": [_proposal_to_response(p) for p in proposals]}


@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str):
    repo = DispatchRepo()
    repo.ensure_tables()
    proposal = repo.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return {"proposal": _proposal_to_response(proposal)}


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(
    proposal_id: str,
    body: Dict[str, Any] = Body(default={}),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    repo = DispatchRepo()
    repo.ensure_tables()
    engine = DispatchEngine(repo)
    proposal = repo.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if not can_transition(proposal.status, "approved"):
        raise HTTPException(status_code=400, detail="Invalid status transition")

    comment = body.get("comment")
    auto_eligible, auto_reason = engine.auto_execute_eligible(proposal)
    auto_policy = "on_approve" if auto_eligible else "never"
    approved_then_auto = 1 if auto_eligible else 0

    repo.update_status(
        proposal_id,
        "approved",
        actor,
        comment,
        proposal.execution_ref,
        auto_execute_eligible=1 if auto_eligible else 0,
        auto_execute_policy=auto_policy,
        approved_then_auto_execute=approved_then_auto,
    )
    repo.append_audit(
        proposal_id,
        "approve",
        actor,
        {
            "status_before": proposal.status,
            "status_after": "approved",
            "comment": comment,
            "evidence_refs": proposal.evidence_refs,
            "auto_execute_eligible": auto_eligible,
            "auto_execute_reason": auto_reason,
        },
    )

    job_id = None
    auto_execute_scheduled = False
    job_status = None
    execution_state = None
    if auto_eligible:
        outcome = engine.execute_proposal(proposal, execution_mode="auto")
        if outcome.job:
            job_id = outcome.job.job_id
            job_status = outcome.job.status
            execution_state = outcome.state
            auto_execute_scheduled = outcome.state in {"succeeded", "failed", "already_in_progress", "already_succeeded"}
            if auto_execute_scheduled:
                repo.update_status(
                    proposal_id,
                    "approved",
                    actor,
                    comment,
                    proposal.execution_ref,
                    approved_then_auto_execute=1,
                )
            if outcome.state in {"succeeded", "failed"}:
                next_status = "executed" if outcome.state == "succeeded" else "failed"
                repo.update_status(
                    proposal_id,
                    next_status,
                    actor,
                    comment,
                    job_id,
                )
                repo.append_audit(
                    proposal_id,
                    "execute" if outcome.state == "succeeded" else "execute_failed",
                    actor,
                    {
                        "status_before": "approved",
                        "status_after": next_status,
                        "execution_ref": job_id,
                        "evidence_refs": proposal.evidence_refs,
                    },
                )

    return {
        "proposal_id": proposal_id,
        "status": "approved",
        "auto_execute_scheduled": auto_execute_scheduled,
        "job_id": job_id,
        "job_status": job_status,
        "execution_state": execution_state,
    }


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: str,
    body: Dict[str, Any] = Body(default={}),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    repo = DispatchRepo()
    repo.ensure_tables()
    proposal = repo.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if not can_transition(proposal.status, "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status transition")

    comment = body.get("comment")
    repo.update_status(proposal_id, "rejected", actor, comment, proposal.execution_ref)
    repo.append_audit(
        proposal_id,
        "reject",
        actor,
        {
            "status_before": proposal.status,
            "status_after": "rejected",
            "comment": comment,
            "evidence_refs": proposal.evidence_refs,
        },
    )

    return {"proposal_id": proposal_id, "status": "rejected"}


@router.post("/proposals/{proposal_id}/execute")
def execute_proposal(
    proposal_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    repo = DispatchRepo()
    repo.ensure_tables()
    engine = DispatchEngine(repo)
    proposal = repo.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status in {"pending", "rejected", "cancelled"}:
        raise HTTPException(status_code=400, detail="Invalid status transition")

    outcome = engine.execute_proposal(proposal, execution_mode="manual")
    if not outcome.job:
        raise HTTPException(status_code=400, detail="Execution not supported")

    if outcome.state == "succeeded":
        execution_ref = outcome.job.job_id
        repo.update_status(proposal_id, "executed", actor, proposal.review_comment, execution_ref)
        repo.append_audit(
            proposal_id,
            "execute",
            actor,
            {
                "status_before": proposal.status,
                "status_after": "executed",
                "execution_ref": execution_ref,
                "evidence_refs": proposal.evidence_refs,
            },
        )
    elif outcome.state == "failed":
        execution_ref = outcome.job.job_id
        repo.update_status(proposal_id, "failed", actor, proposal.review_comment, execution_ref)
        repo.append_audit(
            proposal_id,
            "execute_failed",
            actor,
            {
                "status_before": proposal.status,
                "status_after": "failed",
                "execution_ref": execution_ref,
                "evidence_refs": proposal.evidence_refs,
            },
        )

    return {
        "proposal_id": proposal_id,
        "status": outcome.job.status,
        "job_id": outcome.job.job_id,
        "execution_state": outcome.state,
    }


@router.get("/jobs")
def list_jobs(
    status: Optional[str] = Query(None),
    proposal_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    repo = DispatchRepo()
    repo.ensure_tables()
    jobs = repo.list_jobs(status=status, proposal_id=proposal_id, limit=limit)
    return {"jobs": [_job_to_response(j) for j in jobs]}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    repo = DispatchRepo()
    repo.ensure_tables()
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": _job_to_response(job)}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    repo = DispatchRepo()
    repo.ensure_tables()
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "queued":
        raise HTTPException(status_code=400, detail="Only queued jobs can be cancelled")

    repo.update_job_status(
        job_id,
        "cancelled",
        job.started_at,
        utc_now_ms(),
        job.attempt,
        job.last_error_code,
        job.last_error_message,
    )
    repo.append_audit(
        job.proposal_id,
        "dispatch_job_cancelled",
        actor,
        {
            "job_id": job.job_id,
            "status_before": job.status,
            "status_after": "cancelled",
        },
    )
    return {"job_id": job_id, "status": "cancelled"}


@router.post("/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    repo = DispatchRepo()
    repo.ensure_tables()
    engine = DispatchEngine(repo)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    proposal = repo.get_proposal(job.proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    outcome = engine.retry_job(job, proposal)
    if not outcome.job:
        raise HTTPException(status_code=400, detail="Retry not possible")
    repo.append_audit(
        proposal.proposal_id,
        "dispatch_job_retry",
        actor,
        {
            "job_id": job.job_id,
            "state": outcome.state,
        },
    )
    return {"job_id": job.job_id, "status": outcome.job.status, "execution_state": outcome.state}


@router.post("/jobs/{job_id}/rollback")
def rollback_job(
    job_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    repo = DispatchRepo()
    repo.ensure_tables()
    engine = DispatchEngine(repo)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    proposal = repo.get_proposal(job.proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    outcome = engine.rollback_job(job, proposal)
    if outcome.state not in {"rolled_back", "rollback_failed"}:
        raise HTTPException(status_code=400, detail="Rollback not possible")
    repo.append_audit(
        proposal.proposal_id,
        "dispatch_job_rollback",
        actor,
        {
            "job_id": job.job_id,
            "state": outcome.state,
        },
    )
    return {"job_id": job.job_id, "status": outcome.state}
