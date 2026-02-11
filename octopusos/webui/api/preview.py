"""Preview API for live coding demos."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from octopusos.webui.api.preview_store import (
    create_preview_session,
    delete_preview_session,
    get_preview_session,
    read_preview_html,
    update_preview_session,
)
from octopusos.webui.websocket import coding as ws_coding

router = APIRouter(tags=["preview"])


@router.post("/api/preview")
async def create_preview(request: Request) -> JSONResponse:
    if not request:
        payload = {}
    else:
        try:
            payload = await request.json()
        except Exception:
            # Empty/invalid JSON must not surface as 500.
            payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Invalid payload")

    preset = str(payload.get("preset") or "html-basic")
    html = str(payload.get("html") or "")
    session_id = str(payload.get("session_id") or "").strip() or None
    run_id = str(payload.get("run_id") or "").strip() or None

    created = create_preview_session(
        preset=preset,
        html=html,
        session_id=session_id,
        run_id=run_id,
        meta={"files": payload.get("files")},
    )

    if session_id and run_id:
        await ws_coding.emit_external_event(
            session_id=session_id,
            run_id=run_id,
            event_type="preview.ready",
            payload={
                "preview_id": created["preview_id"],
                "url": created["url"],
                "status": created["status"],
            },
        )

    return JSONResponse(status_code=200, content=created)


@router.get("/api/preview/{preview_id}")
async def get_preview(preview_id: str) -> JSONResponse:
    session = get_preview_session(preview_id)
    if not session:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Preview not found"})
    return JSONResponse(
        status_code=200,
        content={
            "preview_id": session["preview_id"],
            "session_id": session.get("session_id"),
            "run_id": session.get("run_id"),
            "status": session["status"],
            "preset": session["preset"],
            "url": session["url"],
            "version": session["version"],
            "updated_at": session["updated_at"],
        },
    )


@router.get("/api/preview/{preview_id}/content")
async def get_preview_content(preview_id: str) -> HTMLResponse:
    html = read_preview_html(preview_id)
    if html is None:
        return HTMLResponse(status_code=404, content="Preview not found")
    return HTMLResponse(status_code=200, content=html)


@router.post("/api/preview/{preview_id}/reload")
async def reload_preview(preview_id: str, request: Request) -> JSONResponse:
    if not request:
        payload = {}
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}

    html: Optional[str] = payload.get("html") if isinstance(payload.get("html"), str) else None
    updated = update_preview_session(preview_id, html=html, bump_version=True)
    if not updated:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Preview not found"})

    session_id = str(payload.get("session_id") or updated.get("session_id") or "").strip() or None
    run_id = str(payload.get("run_id") or updated.get("run_id") or "").strip() or None
    if session_id and run_id:
        await ws_coding.emit_external_event(
            session_id=session_id,
            run_id=run_id,
            event_type="preview.reload",
            payload={
                "preview_id": preview_id,
                "url": updated["url"],
                "status": updated["status"],
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "preview_id": preview_id,
            "url": updated["url"],
            "status": updated["status"],
            "version": updated["version"],
        },
    )


@router.delete("/api/preview/{preview_id}")
async def remove_preview(preview_id: str) -> JSONResponse:
    ok = delete_preview_session(preview_id)
    if not ok:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Preview not found"})
    return JSONResponse(status_code=200, content={"ok": True, "preview_id": preview_id})
