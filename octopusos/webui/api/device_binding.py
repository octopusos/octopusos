"""Device binding API (M3).

Hard constraints:
- Fail-closed: unbound devices cannot access mobile chat API.
- Audit is isolated from CommunicationOS message_audit (stored in device_binding DB).
- No plaintext credentials in DB or logs.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from octopusos.device_store import DeviceStore
from octopusos.core.capabilities.admin_token import validate_admin_token

router = APIRouter()


def _require_admin_token(token: Optional[str]) -> str:
    safe = (token or "").strip()
    if not safe:
        raise HTTPException(status_code=401, detail="Admin token required")
    if not validate_admin_token(safe):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return "admin"


def _store() -> DeviceStore:
    return DeviceStore()


@router.post("/api/devices/pairing-code/create")
async def create_pairing_code(
    request: Request,
    ttl_sec: int = 60,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> JSONResponse:
    _require_admin_token(admin_token)
    ttl = max(10, min(600, int(ttl_sec or 60)))
    payload = _store().create_pairing_code(ttl_sec=ttl)
    return JSONResponse(status_code=200, content={"ok": True, **{k: payload[k] for k in ["pairing_code", "expires_at_ms", "ttl_sec"]}})


@router.post("/api/devices/pair")
async def pair_device(request: Request) -> JSONResponse:
    if not request:
        payload = {}
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Invalid payload")

    pairing_code = str(payload.get("pairing_code") or "").strip()
    device_fingerprint = str(payload.get("device_fingerprint") or "").strip()
    device_name = str(payload.get("device_name") or "").strip() or "mobile"
    client_pubkey = payload.get("client_pubkey")
    if client_pubkey is not None:
        client_pubkey = str(client_pubkey)

    if not pairing_code or not device_fingerprint:
        raise HTTPException(status_code=422, detail="pairing_code and device_fingerprint are required")

    res = _store().create_device_request_from_pairing_code(
        pairing_code=pairing_code,
        device_fingerprint=device_fingerprint,
        device_name=device_name,
        client_pubkey=client_pubkey,
    )
    if not res:
        # fail-closed: invalid/expired/used pairing code
        raise HTTPException(status_code=403, detail="Invalid pairing code")

    req = res["request"]
    return JSONResponse(status_code=200, content={"ok": True, "request": req, "poll_secret": res["poll_secret"]})


@router.get("/api/devices/pair/{request_id}/status")
async def pair_status(request_id: str, poll_secret: Optional[str] = None) -> JSONResponse:
    safe_poll = str(poll_secret or "").strip()
    store = _store()
    row = store.get_request(request_id)
    if not row:
        return JSONResponse(status_code=404, content={"ok": False, "error": "not_found"})
    if not store.validate_poll_secret(request_id=request_id, poll_secret=safe_poll):
        raise HTTPException(status_code=403, detail="Invalid poll secret")

    status = row.status
    token = None
    if status == "approved":
        token = store.fetch_credential_once(request_id=request_id)
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "request_id": row.id,
            "status": status,
            "credential": {"token": token} if token else None,
        },
    )


@router.get("/api/devices/pending")
async def list_pending(
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    limit: int = 200,
) -> JSONResponse:
    _require_admin_token(admin_token)
    items = [r.to_dict() for r in _store().list_requests(status="pending", limit=max(1, min(500, int(limit or 200))))]
    return JSONResponse(status_code=200, content={"ok": True, "items": items})


@router.get("/api/devices/approved")
async def list_approved(
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    limit: int = 200,
) -> JSONResponse:
    _require_admin_token(admin_token)
    items = [r.to_dict() for r in _store().list_requests(status="approved", limit=max(1, min(500, int(limit or 200))))]
    return JSONResponse(status_code=200, content={"ok": True, "items": items})


@router.post("/api/devices/{request_id}/approve")
async def approve_device(
    request_id: str,
    request: Request,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> JSONResponse:
    _require_admin_token(admin_token)
    if not request:
        payload = {}
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    ttl_sec = int(payload.get("ttl_sec") or 86400)
    store = _store()
    res = store.approve(request_id=request_id, ttl_sec=max(60, min(86400 * 30, ttl_sec)))
    if not res:
        return JSONResponse(status_code=404, content={"ok": False, "error": "not_found"})
    # NOTE: do not return the token here; mobile fetches it once via poll_secret gated endpoint.
    return JSONResponse(status_code=200, content={"ok": True, "request_id": request_id, "expires_at_ms": res["expires_at_ms"]})


@router.post("/api/devices/{request_id}/reject")
async def reject_device(
    request_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> JSONResponse:
    _require_admin_token(admin_token)
    ok = _store().reject(request_id=request_id)
    return JSONResponse(status_code=200 if ok else 404, content={"ok": ok})


@router.post("/api/devices/{request_id}/revoke")
async def revoke_device(
    request_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> JSONResponse:
    _require_admin_token(admin_token)
    ok = _store().revoke(request_id=request_id)
    return JSONResponse(status_code=200 if ok else 404, content={"ok": ok})


__all__ = ["router"]
