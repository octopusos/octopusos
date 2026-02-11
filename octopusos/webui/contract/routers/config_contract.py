"""Contract-only OpenAPI declarations for Config endpoints.

These routes are mounted only for contract snapshot export and are kept
aligned with runtime routes defined in octopusos.webui.app.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query

router = APIRouter(tags=["contract-config"])


@router.get("/api/config")
def config_get() -> dict[str, Any]:
    return {}


@router.get("/api/config/entries")
def config_entries_get(
    search: Optional[str] = Query(default=None),
    scope: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    type_filter: Optional[str] = Query(default=None, alias="type"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=500),
) -> dict[str, Any]:
    return {}


@router.get("/api/config/entries/{key:path}")
def config_entry_get(key: str, project_id: Optional[str] = Query(default=None)) -> dict[str, Any]:
    return {"key": key, "project_id": project_id}


@router.post("/api/config/entries")
def config_entry_create(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@router.put("/api/config/entries/{id}")
def config_entry_update(id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {"id": id, **payload}


@router.delete("/api/config/entries/{id}")
def config_entry_delete(
    id: int,
    decision_id: Optional[str] = Query(default=None),
    reason: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    return {"id": id, "decision_id": decision_id, "reason": reason}


@router.get("/api/config/modules")
def config_modules_get() -> dict[str, Any]:
    return {}


@router.get("/api/config/allowlist")
def config_allowlist_get() -> dict[str, Any]:
    return {}


@router.get("/api/config/secret-status")
def config_secret_status(
    key: str = Query(..., min_length=1),
    project_id: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    return {"key": key, "project_id": project_id}


@router.get("/api/config/resolve")
def config_resolve_get(
    key: str = Query(..., min_length=1),
    project_id: Optional[str] = Query(default=None),
    request_override: Optional[str] = Query(default=None),
    admin_token: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    return {
        "key": key,
        "project_id": project_id,
        "request_override": request_override,
        "admin_token": admin_token,
    }


@router.post("/api/config/rollback")
def config_rollback(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@router.post("/api/config/snapshot")
def config_snapshot_create(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@router.get("/api/config/snapshot/{snapshot_id}")
def config_snapshot_get(snapshot_id: str) -> dict[str, Any]:
    return {"snapshot_id": snapshot_id}


@router.get("/api/config/diff")
def config_diff_get(
    module: Optional[str] = Query(default=None),
    key: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    return {"module": module, "key": key, "project_id": project_id}


@router.post("/api/config/rollback_from_snapshot")
def config_rollback_from_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@router.get("/api/config/timeline")
def config_timeline_get(
    key: Optional[str] = Query(default=None),
    module_prefix: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    return {
        "key": key,
        "module_prefix": module_prefix,
        "project_id": project_id,
        "limit": limit,
    }
