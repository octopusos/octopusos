"""Mobile chat API (M3).

This API is intentionally minimal:
- It is fail-closed behind device credentials.
- It routes into the existing ChatEngine pipeline for real replies (not echo).
- It does not add/modify CommunicationOS message_audit semantics.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from octopusos.device_store import DeviceStore
from octopusos.webui.websocket import chat as ws_chat
from octopusos.store import get_db

router = APIRouter()


def _store() -> DeviceStore:
    return DeviceStore()


def _parse_device_token(authorization: Optional[str]) -> Optional[str]:
    raw = (authorization or "").strip()
    if not raw:
        return None
    parts = raw.split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts[0].strip(), parts[1].strip()
    if scheme.lower() != "device":
        return None
    return token or None


def _require_device_request_id(authorization: Optional[str]) -> str:
    token = _parse_device_token(authorization)
    if not token:
        raise HTTPException(status_code=403, detail="Missing device credential")
    store = _store()
    device_request_id = store.validate_credential(token)
    if not device_request_id:
        raise HTTPException(status_code=403, detail="Invalid device credential")
    return str(device_request_id)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _message_to_api(message: Any) -> Dict[str, Any]:
    created = getattr(message, "created_at", None)
    created_at = created.isoformat().replace("+00:00", "Z") if created else _iso_now()
    return {
        "id": getattr(message, "message_id", None),
        "message_id": getattr(message, "message_id", None),
        "session_id": getattr(message, "session_id", None),
        "role": getattr(message, "role", None),
        "content": getattr(message, "content", ""),
        "created_at": created_at,
        "timestamp": created_at,
        "metadata": getattr(message, "metadata", None) or {},
    }


def _normalize_runtime_config(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    runtime = payload.get("runtime")
    provider = payload.get("provider")
    model = payload.get("model")

    safe_runtime = str(runtime).strip().lower() if isinstance(runtime, str) else None
    if safe_runtime not in {None, "", "local", "cloud"}:
        safe_runtime = None

    safe_provider = str(provider).strip() if isinstance(provider, str) else None
    safe_model = str(model).strip() if isinstance(model, str) else None
    return safe_runtime or None, safe_provider or None, safe_model or None


def _update_message_metadata(message_id: str, updates: Dict[str, Any]) -> None:
    if not message_id:
        return
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("SELECT metadata FROM chat_messages WHERE message_id = ?", (str(message_id),)).fetchone()
    if not row:
        return
    current: Dict[str, Any] = {}
    raw = row[0]
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                current = parsed
        except Exception:
            current = {}
    merged = {**current, **(updates or {})}
    cursor.execute("UPDATE chat_messages SET metadata = ? WHERE message_id = ?", (json.dumps(merged, ensure_ascii=False), str(message_id)))
    conn.commit()


def _extract_mobile_payload(request_json: Any) -> Dict[str, Any]:
    payload = request_json if isinstance(request_json, dict) else {}
    return payload


async def _handle_mobile_history(
    *,
    authorization: Optional[str],
    session_id: Optional[str],
    limit: int,
    offset: int,
) -> JSONResponse:
    device_request_id = _require_device_request_id(authorization)
    store = _store()
    chat_service = ws_chat.get_chat_service()

    safe_client = str(session_id or "").strip() or None
    server_session_id: Optional[str] = None

    if safe_client:
        link = store.get_device_session_link(request_id=device_request_id, client_session_id=safe_client)
        if not link:
            return JSONResponse(status_code=404, content={"ok": False, "error": "not_found"})
        server_session_id = str(link.get("server_session_id") or "").strip() or None
    else:
        # Legacy fallback for clients that don't send session_id.
        def _create_session_id() -> str:
            session = chat_service.create_session(
                title="Mobile Chat",
                metadata={"source": "mobile", "device_request_id": device_request_id},
            )
            return str(session.session_id)

        server_session_id = store.get_or_create_device_session(request_id=device_request_id, create_session=_create_session_id)

    if not server_session_id:
        return JSONResponse(status_code=404, content={"ok": False, "error": "not_found"})

    messages = chat_service.get_messages(
        session_id=server_session_id,
        limit=max(1, min(500, int(limit or 200))),
        offset=max(0, int(offset or 0)),
    )
    messages = [m for m in messages if getattr(m, "role", None) != "tool"]
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "session_id": safe_client,
            "messages": [_message_to_api(m) for m in messages],
        },
    )


async def _handle_mobile_chat(*, authorization: Optional[str], request_json: Any) -> JSONResponse:
    device_request_id = _require_device_request_id(authorization)
    store = _store()

    payload = _extract_mobile_payload(request_json)

    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is required")
    idempotency_key = payload.get("idempotency_key")
    if idempotency_key is not None:
        idempotency_key = str(idempotency_key).strip() or None

    chat_service = ws_chat.get_chat_service()

    runtime, provider, model = _normalize_runtime_config(payload)

    client_session_id = str(payload.get("session_id") or "").strip() or None
    title = str(payload.get("title") or "").strip() or "Chat"

    session_id: str
    if client_session_id:
        def _create_session(safe_title: str) -> str:
            session = chat_service.create_session(
                title=safe_title,
                metadata={"source": "mobile", "device_request_id": device_request_id},
            )
            return str(session.session_id)

        session_id = store.get_or_create_device_session_link(
            request_id=device_request_id,
            client_session_id=client_session_id,
            title=title,
            create_session=_create_session,
        )
        store.set_active_client_session_id(request_id=device_request_id, client_session_id=client_session_id)
    else:
        # Legacy fallback for clients that don't send session_id.
        def _create_session_id() -> str:
            session = chat_service.create_session(
                title="Mobile Chat",
                metadata={"source": "mobile", "device_request_id": device_request_id},
            )
            return str(session.session_id)

        session_id = store.get_or_create_device_session(request_id=device_request_id, create_session=_create_session_id)

    # Session-scoped runtime selection; affects future messages but does not rewrite past messages.
    patch: Dict[str, Any] = {}
    if runtime:
        patch["model_route"] = runtime
    if provider:
        patch["provider"] = provider
    if model:
        patch["model"] = model
    if patch:
        try:
            chat_service.update_session_metadata(session_id=session_id, metadata=patch)
        except Exception:
            pass

    engine = ws_chat.get_chat_engine()
    result: Dict[str, Any] = engine.send_message(session_id=session_id, user_input=text, stream=False, idempotency_key=idempotency_key)
    content = str(result.get("content") or "")

    # Record the per-message routing config on the latest user message so history can show it.
    if patch:
        try:
            recent = chat_service.get_recent_messages(session_id, count=4)
            last_user = None
            for m in reversed(recent):
                if getattr(m, "role", None) == "user":
                    last_user = m
                    break
            if last_user is not None:
                _update_message_metadata(str(last_user.message_id), {"runtime": runtime, "provider": provider, "model": model})
        except Exception:
            pass

    return JSONResponse(status_code=200, content={"ok": True, "session_id": client_session_id, "server_session_id": session_id, "reply": content})


@router.get("/api/mobile/sessions")
async def mobile_list_sessions(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    limit: int = 200,
) -> JSONResponse:
    device_request_id = _require_device_request_id(authorization)
    store = _store()
    chat_service = ws_chat.get_chat_service()

    links = store.list_device_session_links(request_id=device_request_id, limit=limit)
    out: List[Dict[str, Any]] = []
    for link in links:
        server_session_id = link.get("server_session_id")
        if not server_session_id:
            continue
        try:
            session = chat_service.get_session(str(server_session_id))
            recent = chat_service.get_recent_messages(str(server_session_id), count=1)
            out.append(
                {
                    "session_id": link.get("client_session_id"),
                    "title": str(link.get("title") or session.title or "Chat"),
                    "updated_at": session.updated_at.isoformat().replace("+00:00", "Z"),
                    "created_at": session.created_at.isoformat().replace("+00:00", "Z"),
                    "last_message": recent[0].content if recent else "",
                    "message_count": chat_service.count_messages(str(server_session_id)),
                }
            )
        except Exception:
            continue

    active = store.get_active_client_session_id(request_id=device_request_id)
    return JSONResponse(status_code=200, content={"ok": True, "active_session_id": active, "sessions": out})


@router.post("/api/mobile/sessions")
async def mobile_create_session(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> JSONResponse:
    device_request_id = _require_device_request_id(authorization)
    if not request:
        payload = {}
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Invalid payload")

    client_session_id = str(payload.get("session_id") or "").strip()
    if not client_session_id:
        raise HTTPException(status_code=422, detail="session_id is required")
    title = str(payload.get("title") or "").strip() or "Chat"

    store = _store()
    chat_service = ws_chat.get_chat_service()

    def _create_session(safe_title: str) -> str:
        session = chat_service.create_session(
            title=safe_title,
            metadata={"source": "mobile", "device_request_id": device_request_id},
        )
        return str(session.session_id)

    server_session_id = store.get_or_create_device_session_link(
        request_id=device_request_id,
        client_session_id=client_session_id,
        title=title,
        create_session=_create_session,
    )
    store.set_active_client_session_id(request_id=device_request_id, client_session_id=client_session_id)
    return JSONResponse(status_code=200, content={"ok": True, "session_id": client_session_id, "server_session_id": server_session_id})


@router.get("/api/mobile/history")
async def mobile_history(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    session_id: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> JSONResponse:
    return await _handle_mobile_history(authorization=authorization, session_id=session_id, limit=limit, offset=offset)


@router.post("/api/mobile/chat")
async def mobile_chat(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> JSONResponse:
    if not request:
        request_json = {}
    else:
        try:
            request_json = await request.json()
        except Exception:
            request_json = {}
    if request_json is not None and not isinstance(request_json, dict):
        raise HTTPException(status_code=422, detail="Invalid payload")
    return await _handle_mobile_chat(authorization=authorization, request_json=request_json)


# Aliases (product-friendly paths).
@router.post("/chat/send")
async def chat_send_alias(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> JSONResponse:
    if not request:
        request_json = {}
    else:
        try:
            request_json = await request.json()
        except Exception:
            request_json = {}
    if request_json is not None and not isinstance(request_json, dict):
        raise HTTPException(status_code=422, detail="Invalid payload")
    return await _handle_mobile_chat(authorization=authorization, request_json=request_json)


@router.get("/chat/history")
async def chat_history_alias(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    session_id: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> JSONResponse:
    return await _handle_mobile_history(authorization=authorization, session_id=session_id, limit=limit, offset=offset)


__all__ = ["router"]
