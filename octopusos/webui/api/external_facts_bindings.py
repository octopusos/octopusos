"""External facts bindings APIs (capability/item -> connector endpoint)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException

from octopusos.core.capabilities.external_facts.fact_bindings_store import FactBindingsStore

router = APIRouter(prefix="/api/compat/external-facts/bindings", tags=["compat"])
_store = FactBindingsStore()


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
async def list_bindings():
    return {"ok": True, "data": _store.list()}


@router.post("")
async def upsert_binding(
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    try:
        item = _store.upsert(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True, "data": item}


@router.delete("/{capability_id}/{item_id}")
async def delete_binding(
    capability_id: str,
    item_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    ok = _store.delete(capability_id, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Binding not found")
    return {"ok": True, "data": {"capability_id": capability_id, "item_id": item_id}}
