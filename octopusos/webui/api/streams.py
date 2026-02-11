"""Stream replay APIs for coding/demo runs."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from octopusos.webui.websocket.stream_bus import latest_run, list_events
from octopusos.webui.websocket import coding as ws_coding

router = APIRouter(tags=["streams"])


@router.get("/api/streams/{session_id}/latest-run")
async def get_latest_stream_run(session_id: str) -> JSONResponse:
    active = ws_coding.get_active_run(session_id)
    latest = latest_run(session_id)
    demo_state = ws_coding.get_demo_state(session_id)
    return JSONResponse(
        status_code=200,
        content={
            "session_id": session_id,
            "active_run": active,
            "latest_run": latest,
            "demo_state": demo_state,
        },
    )


@router.get("/api/streams/{session_id}/{run_id}")
async def get_stream_events(
    session_id: str,
    run_id: str,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=2000, ge=1, le=5000),
) -> JSONResponse:
    events = list_events(session_id=session_id, run_id=run_id, after_seq=after_seq, limit=limit)
    last_seq = events[-1]["seq"] if events else after_seq
    return JSONResponse(
        status_code=200,
        content={
            "session_id": session_id,
            "run_id": run_id,
            "after_seq": after_seq,
            "last_seq": last_seq,
            "events": events,
        },
    )
