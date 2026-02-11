"""External facts card schema API (versioned, auditable)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException, Query

from octopusos.core.capabilities.external_facts.schema_store import ExternalFactsSchemaStore

router = APIRouter(prefix="/api/compat/external-facts/schema", tags=["compat"])
_store = ExternalFactsSchemaStore()


def _require_admin_token(token: Optional[str]) -> str:
    expected = os.getenv("OCTOPUSOS_ADMIN_TOKEN", "").strip()
    incoming = (token or "").strip()
    if not expected:
        raise HTTPException(status_code=401, detail="Admin token not configured")
    if not incoming:
        raise HTTPException(status_code=401, detail="Admin token required")
    if incoming != expected:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return "admin"


@router.get("")
async def list_schemas():
    data = []
    for row in _store.list_effective():
        data.append({
            "kind": row.kind,
            "version": row.version,
            "source": row.source,
            "schema": row.schema,
        })
    return {"ok": True, "data": data}


@router.get("/export")
async def export_schemas():
    return {"ok": True, "data": _store.export_json()}


@router.get("/history")
async def schema_history(kind: Optional[str] = Query(default=None), limit: int = Query(default=100, ge=1, le=500)):
    return {"ok": True, "data": _store.history(kind=kind, limit=limit)}


@router.put("/apply")
async def apply_schemas(
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    schemas = payload.get("schemas")
    if not isinstance(schemas, dict):
        raise HTTPException(status_code=422, detail="schemas must be an object")
    note = str(payload.get("note") or "")
    result = _store.apply_bulk(schemas=schemas, actor=actor, note=note)
    return {"ok": True, "data": result}


@router.post("/rollback")
async def rollback_schema(
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    kind = str(payload.get("kind") or "").strip()
    target_version = int(payload.get("target_version") or 0)
    if not kind or target_version <= 0:
        raise HTTPException(status_code=422, detail="kind and target_version are required")
    result = _store.rollback(kind=kind, target_version=target_version, actor=actor)
    return {"ok": True, "data": result}
