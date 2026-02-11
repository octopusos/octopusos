from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from octopusos.core.work.exec_task_store import ExecTaskStore


router = APIRouter(tags=["exec-tasks"])


@router.get("/api/tasks/items")
def list_exec_tasks(status: str = "queued,running,succeeded,failed", limit: int = 50):
    store = ExecTaskStore()
    statuses = [s.strip() for s in str(status or "").split(",") if s.strip()]
    result = store.list(statuses=statuses, limit=limit)
    return JSONResponse(status_code=200, content={"ok": True, "items": [t.__dict__ for t in result.items]})


@router.get("/api/tasks/items/{task_id}")
def get_exec_task(task_id: str):
    store = ExecTaskStore()
    item = store.get(task_id=task_id)
    if not item:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Not found"})
    return JSONResponse(status_code=200, content={"ok": True, "item": item.__dict__})


@router.post("/api/tasks/items/{task_id}/cancel")
def cancel_exec_task(task_id: str):
    store = ExecTaskStore()
    store.cancel(task_id=task_id)
    return JSONResponse(status_code=200, content={"ok": True})


@router.post("/api/tasks/items/{task_id}/retry")
def retry_exec_task(task_id: str):
    store = ExecTaskStore()
    store.retry(task_id=task_id)
    return JSONResponse(status_code=200, content={"ok": True})

