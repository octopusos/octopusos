"""P0 compatibility router for models endpoints expected by apps/webui."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from octopusos.webui.api.compat_state import (
    audit_event,
    db_connect,
    ensure_schema,
    get_entity,
    list_entities,
    now_iso,
    soft_delete_entity,
    upsert_entity,
)
from octopusos.webui.api.providers import _provider_ids

router = APIRouter(prefix="/api/models", tags=["compat"])


def _build_models() -> List[Dict[str, Any]]:
    models: List[Dict[str, Any]] = []
    for provider in _provider_ids():
        seed_name = f"{provider}-default"
        models.append(
            {
                "id": seed_name,
                "name": seed_name,
                "size": None,
                "status": "installed",
                "provider_id": provider,
                "provider": provider,
                "modified": now_iso(),
                "digest": "",
                "family": "compat",
                "parameters": "",
            }
        )

    conn = db_connect()
    try:
        ensure_schema(conn)
        for item in list_entities(conn, namespace="models", include_deleted=False):
            model_id = item.get("id") or item.get("_entity_id")
            if not model_id:
                continue
            model = {
                "id": model_id,
                "name": item.get("name") or model_id,
                "size": item.get("size"),
                "status": item.get("status") or "installed",
                "provider_id": item.get("provider_id") or "ollama",
                "provider": item.get("provider_id") or "ollama",
                "modified": item.get("modified") or item.get("_updated_at") or now_iso(),
                "digest": item.get("digest") or "",
                "family": item.get("family") or "compat",
                "parameters": item.get("parameters") or "",
            }
            models = [m for m in models if m["id"] != model_id]
            models.append(model)
    finally:
        conn.close()
    return models


@router.get("/list")
def list_models(provider_id: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
    models = _build_models()
    if provider_id:
        models = [m for m in models if m["provider_id"] == provider_id]
    if status:
        models = [m for m in models if m["status"] == status]
    return {"models": models, "total": len(models), "source": "compat"}


@router.post("/pull")
async def pull_model(request: Request) -> Dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON payload")
    model_name = payload.get("model_name")
    if not model_name:
        raise HTTPException(status_code=400, detail="model_name is required")

    provider_id = payload.get("provider_id") or "ollama"
    task_id = f"pull_{uuid4().hex[:12]}"
    task = {
        "task_id": task_id,
        "model_name": str(model_name),
        "provider_id": str(provider_id),
        "created_at": datetime.now(timezone.utc).timestamp(),
        "status": "running",
    }

    conn = db_connect()
    try:
        ensure_schema(conn)
        upsert_entity(conn, namespace="model_pull_tasks", entity_id=task_id, data=task, status="running")
        upsert_entity(
            conn,
            namespace="models",
            entity_id=str(model_name),
            data={
                "id": str(model_name),
                "name": str(model_name),
                "status": "downloading",
                "provider_id": str(provider_id),
                "modified": now_iso(),
            },
            status="downloading",
        )
        audit_event(
            conn,
            event_type="model_pull_start",
            endpoint="/api/models/pull",
            actor="admin",
            payload=payload,
            result={"task_id": task_id, "model_name": model_name},
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "model": {
            "id": str(model_name),
            "name": str(model_name),
            "status": "downloading",
            "provider_id": str(provider_id),
        },
        "task_id": task_id,
        "source": "compat",
    }


@router.get("/pull/{task_id}/progress")
def pull_model_progress(task_id: str) -> Dict[str, Any]:
    conn = db_connect()
    try:
        ensure_schema(conn)
        task = get_entity(conn, namespace="model_pull_tasks", entity_id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Pull task not found")

        elapsed = max(0.0, datetime.now(timezone.utc).timestamp() - float(task.get("created_at", 0.0)))
        progress = min(100, int(elapsed * 35))
        status = "running"
        if progress >= 100:
            status = "completed"
            upsert_entity(
                conn,
                namespace="model_pull_tasks",
                entity_id=task_id,
                data={**task, "status": "completed"},
                status="completed",
            )
            upsert_entity(
                conn,
                namespace="models",
                entity_id=str(task["model_name"]),
                data={
                    "id": str(task["model_name"]),
                    "name": str(task["model_name"]),
                    "status": "installed",
                    "provider_id": str(task.get("provider_id") or "ollama"),
                    "modified": now_iso(),
                },
                status="installed",
            )
            conn.commit()
        return {
            "progress": progress,
            "status": status,
            "message": f"Pulling {task['model_name']}",
            "source": "compat",
        }
    finally:
        conn.close()


@router.delete("/{model_id}")
def delete_model(model_id: str) -> Dict[str, Any]:
    conn = db_connect()
    try:
        ensure_schema(conn)
        soft_delete_entity(conn, namespace="models", entity_id=model_id)
        audit_event(
            conn,
            event_type="model_delete",
            endpoint=f"/api/models/{model_id}",
            actor="admin",
            payload={"model_id": model_id},
            result={"ok": True},
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "model_id": model_id, "source": "compat"}
