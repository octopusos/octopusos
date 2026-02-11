from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from octopusos.core.work.work_store import WorkStore


router = APIRouter(tags=["work-items"])


class ListQuery(BaseModel):
    status: str = Field(default="queued,running,succeeded,failed")
    limit: int = Field(default=50, ge=1, le=500)


@router.get("/api/work/items")
def list_work_items(status: str = "queued,running,succeeded,failed", limit: int = 50):
    store = WorkStore()
    statuses = [s.strip() for s in str(status or "").split(",") if s.strip()]
    result = store.list(statuses=statuses, limit=limit)
    return JSONResponse(status_code=200, content={"ok": True, "items": [i.__dict__ for i in result.items]})


@router.get("/api/work/items/{work_id}")
def get_work_item(work_id: str):
    store = WorkStore()
    item = store.get(work_id=work_id)
    if not item:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Not found"})
    return JSONResponse(status_code=200, content={"ok": True, "item": item.__dict__})


@router.post("/api/work/items/{work_id}/cancel")
def cancel_work_item(work_id: str):
    store = WorkStore()
    # Work items are informational; cancellation is modeled by status only.
    store.update_status(work_id=work_id, status="cancelled", summary="Cancelled by user")
    return JSONResponse(status_code=200, content={"ok": True})

