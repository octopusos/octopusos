"""Growth loop metrics and replay verification endpoints."""

from __future__ import annotations

from typing import Dict, Any
import sqlite3

from fastapi import APIRouter, HTTPException, Query, Body

from octopusos.core.growth.metrics import GrowthMetricsService
from octopusos.core.growth.evidence import replay_verify_task
from octopusos.core.growth.actionable_kb import ActionableKBService


router = APIRouter(prefix="/api/growth", tags=["growth"])
_kb_service = ActionableKBService()


@router.get("/metrics")
def growth_metrics() -> Dict[str, Any]:
    service = GrowthMetricsService()
    return {"ok": True, "data": service.snapshot()}


@router.get("/replay-verify/{task_id}")
def growth_replay_verify(task_id: str) -> Dict[str, Any]:
    result = replay_verify_task(task_id)
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result)
    return {"ok": True, "data": result}


@router.get("/brain/failure-decisions")
def failure_decisions(limit: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    from octopusos.core.db import registry_db

    try:
        rows = registry_db.query_all(
            """
            SELECT decision_id, task_id, category, retryable, decision_type,
                   ignore_reason, improvement_candidate, evidence_refs_json, created_at
            FROM brain_failure_decisions
            ORDER BY decision_id DESC
            LIMIT ?
            """,
            (limit,),
        )
    except sqlite3.OperationalError:
        # Fresh DB may not have the growth tables yet; return empty rather than 500.
        rows = []
    out = []
    for r in rows:
        out.append(
            {
                "decision_id": r["decision_id"],
                "task_id": r["task_id"],
                "category": r["category"],
                "retryable": bool(r["retryable"]),
                "decision_type": r["decision_type"],
                "ignore_reason": r["ignore_reason"],
                "improvement_candidate": r["improvement_candidate"],
                "evidence_refs_json": r["evidence_refs_json"],
                "created_at": r["created_at"],
            }
        )
    return {"ok": True, "data": out}


@router.post("/action-kb/seed")
def seed_action_kb() -> Dict[str, Any]:
    return {"ok": True, "data": {"kb_ids": _kb_service.seed_default_entries()}}


@router.post("/action-kb/entries")
def upsert_action_kb_entry(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    try:
        kb_id = _kb_service.upsert_entry(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except sqlite3.OperationalError:
        # Fresh DB may not have growth KB tables yet; return a 4xx rather than 500.
        raise HTTPException(status_code=412, detail="action_kb_not_initialized")
    return {"ok": True, "data": {"kb_id": kb_id}}


@router.post("/tasks/{task_id}/require-kb/{kb_id}")
def require_kb(task_id: str, kb_id: str) -> Dict[str, Any]:
    _kb_service.require_kb_execution(task_id=task_id, kb_id=kb_id)
    return {"ok": True, "data": {"task_id": task_id, "kb_id": kb_id}}


@router.post("/tasks/{task_id}/kb-execution/{kb_id}")
def record_kb_execution(task_id: str, kb_id: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    verify_passed = bool(payload.get("verify_passed"))
    evidence_refs = payload.get("evidence_refs") if isinstance(payload.get("evidence_refs"), list) else []
    notes = str(payload.get("notes") or "")
    _kb_service.record_execution(
        task_id=task_id,
        kb_id=kb_id,
        verify_passed=verify_passed,
        evidence_refs=evidence_refs,
        notes=notes,
    )
    validation = _kb_service.validate_task_success(task_id)
    return {"ok": True, "data": {"task_id": task_id, "kb_id": kb_id, "validation": validation.to_dict()}}
