"""Compatibility endpoints for external facts replay chain."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from octopusos.core.capabilities.external_facts.evidence_store import EvidenceStore
from octopusos.core.capabilities.external_facts.replay_store import ReplayStore

router = APIRouter(prefix="/api/compat/external-facts", tags=["compat"])

_evidence_store = EvidenceStore()
_replay_store = ReplayStore()


@router.get("/recent")
async def list_recent_evidence(limit: int = Query(default=20, ge=1, le=100)):
    items = _evidence_store.list(limit=limit)
    return {"ok": True, "data": [asdict(item) for item in items], "source": "compat"}


@router.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: str):
    item = _evidence_store.get(evidence_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {"ok": True, "data": asdict(item), "source": "compat"}


@router.get("/evidence/{evidence_id}/extractions")
async def list_extractions(evidence_id: str):
    records = _replay_store.list_extractions(evidence_id)
    return {"ok": True, "data": [asdict(r) for r in records], "source": "compat"}


@router.get("/evidence/{evidence_id}/verifications")
async def list_verifications(evidence_id: str):
    records = _replay_store.list_verifications(evidence_id)
    return {"ok": True, "data": [asdict(r) for r in records], "source": "compat"}
