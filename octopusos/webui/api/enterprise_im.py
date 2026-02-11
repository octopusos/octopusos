"""Enterprise IM API (M1): Feishu/Lark bridge endpoints + audit view.

Goals:
- Bridge-only connect/disconnect/status endpoints for enterprise IM platforms
- Official webhook endpoint for event callbacks
- Audit view (metadata only; no plaintext content)

This router intentionally does NOT contain prompt logic or tool calls.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from octopusos.communicationos.audit import AuditStore
from octopusos.communicationos.runtime import get_communication_runtime
from octopusos.core.capabilities.admin_token import validate_admin_token
from octopusos.webui.api.compat_state import audit_event, db_connect, ensure_schema

router = APIRouter(prefix="/api/enterprise-im", tags=["enterprise-im"])


def _require_admin_token(token: Optional[str]) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="Admin token required")
    if not validate_admin_token(token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return "admin"


@router.post("/{platform}/connect")
def connect_platform(
    platform: str,
    payload: Dict[str, Any] = Body(default={}),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    actor = _require_admin_token(admin_token)
    platform = str(platform or "").strip().lower()
    if platform != "feishu":
        raise HTTPException(status_code=404, detail="unsupported platform")

    config = payload.get("config")
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="config must be an object")

    rt = get_communication_runtime()
    try:
        rt.configure_channel("feishu", config, performed_by="webui")
        rt.enable_channel("feishu", True, performed_by="webui")
        rt.ensure_adapter_started("feishu")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    conn = db_connect()
    try:
        ensure_schema(conn)
        audit_event(
            conn,
            event_type="enterprise_im_connect",
            endpoint=f"/api/enterprise-im/{platform}/connect",
            actor=actor,
            payload={"platform": platform, "config_keys": sorted(list(config.keys()))},
            result={"ok": True},
        )
        conn.commit()
    finally:
        conn.close()

    return {"ok": True, "platform": platform, "channel_id": "feishu", "source": "real"}


@router.get("/{platform}/status")
def platform_status(platform: str) -> Dict[str, Any]:
    platform = str(platform or "").strip().lower()
    if platform != "feishu":
        raise HTTPException(status_code=404, detail="unsupported platform")
    rt = get_communication_runtime()
    cfg = rt.config_store.get_config("feishu") or {}
    enabled = bool(rt.config_store.is_enabled("feishu"))
    status = rt.get_adapter_status("feishu") if enabled else {"channel_id": "feishu", "state": "disabled"}
    return {
        "ok": True,
        "platform": platform,
        "channel_id": "feishu",
        "configured": bool(cfg),
        "enabled": enabled,
        "status": status,
        "source": "real",
    }


@router.post("/{platform}/disconnect")
def disconnect_platform(
    platform: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    actor = _require_admin_token(admin_token)
    platform = str(platform or "").strip().lower()
    if platform != "feishu":
        raise HTTPException(status_code=404, detail="unsupported platform")

    rt = get_communication_runtime()
    rt.enable_channel("feishu", False, performed_by="webui")

    conn = db_connect()
    try:
        ensure_schema(conn)
        audit_event(
            conn,
            event_type="enterprise_im_disconnect",
            endpoint=f"/api/enterprise-im/{platform}/disconnect",
            actor=actor,
            payload={"platform": platform, "channel_id": "feishu"},
            result={"ok": True},
        )
        conn.commit()
    finally:
        conn.close()

    return {"ok": True, "platform": platform, "channel_id": "feishu", "enabled": False, "source": "real"}


@router.post("/{platform}/webhook")
async def platform_webhook(platform: str, request: Request) -> JSONResponse:
    platform = str(platform or "").strip().lower()
    if platform != "feishu":
        raise HTTPException(status_code=404, detail="unsupported platform")

    rt = get_communication_runtime()
    # Ensure adapter exists (but don't force enable in case user disabled; webhook still must answer challenge).
    try:
        rt.ensure_adapter_started("feishu")
    except Exception:
        # If config missing, still accept to avoid retry storm; Feishu will fail verification anyway.
        return JSONResponse(status_code=200, content={"ok": True})

    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    adapter = rt._adapters.get("feishu").adapter  # type: ignore[attr-defined]
    try:
        code, resp = adapter.handle_webhook(headers=headers, body_bytes=body)
        return JSONResponse(status_code=code, content=resp)
    except PermissionError as e:
        return JSONResponse(status_code=403, content={"ok": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=200, content={"ok": True, "error": f"ignored:{e}"})


@router.get("/events")
def list_enterprise_events(
    platform: str = Query(default="feishu"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> Dict[str, Any]:
    platform = str(platform or "").strip().lower()
    if platform != "feishu":
        raise HTTPException(status_code=404, detail="unsupported platform")

    store = AuditStore()
    # Read raw rows from the communicationos audit DB.
    with sqlite3.connect(store.db_path) as conn:  # type: ignore[attr-defined]
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT id, message_id, direction, channel_id, user_key, conversation_key, session_id,
                   timestamp_ms, processing_status, metadata, created_at_ms
            FROM message_audit
            WHERE channel_id = ?
            ORDER BY timestamp_ms DESC
            LIMIT ?
            """,
            ("feishu", int(limit)),
        )
        rows = [dict(r) for r in cur.fetchall()]

    return {"ok": True, "platform": platform, "items": rows, "total": len(rows), "source": "real"}
