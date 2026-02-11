"""Work mode session APIs built on top of chat sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from octopusos.core.chat.service import ChatService, validate_message_role
from octopusos.core.chat.xss_sanitizer import sanitize_message_content, sanitize_metadata, sanitize_session_title
from octopusos.webui.api.validation import validate_content_length, validate_title_length

router = APIRouter(tags=["work"])


def _service() -> ChatService:
    return ChatService()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _message_to_api(message: Any) -> Dict[str, Any]:
    return {
        "id": message.message_id,
        "message_id": message.message_id,
        "session_id": message.session_id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat().replace("+00:00", "Z"),
        "timestamp": message.created_at.isoformat().replace("+00:00", "Z"),
        "metadata": message.metadata or {},
    }


def _normalize_history(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    history: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        history.append(
            {
                "id": str(item.get("id") or f"edit-{len(history) + 1}"),
                "created_at": str(item.get("created_at") or _iso_now()),
                "actor": str(item.get("actor") or "system"),
                "summary": str(item.get("summary") or "updated"),
                "operation": str(item.get("operation") or "replace"),
                "version": int(item.get("version") or 1),
            }
        )
    return history


def _normalize_artifact(raw: Any, fallback_index: int) -> Dict[str, Any]:
    item = raw if isinstance(raw, dict) else {}
    artifact_id = str(item.get("artifact_id") or f"artifact-md-{fallback_index + 1}")
    title = str(item.get("title") or "Untitled Artifact")
    artifact_type = str(item.get("type") or "markdown")
    content = str(item.get("content") or "")
    version = int(item.get("version") or 1)
    history = _normalize_history(item.get("history"))
    return {
        "artifact_id": artifact_id,
        "type": artifact_type,
        "title": title,
        "content": content,
        "version": max(1, version),
        "history": history,
    }


def _default_artifact() -> Dict[str, Any]:
    return {
        "artifact_id": "artifact-md-1",
        "type": "markdown",
        "title": "Work Draft",
        "content": "# Work Draft\n\nStart editing your markdown artifact here.",
        "version": 1,
        "history": [
            {
                "id": "edit-1",
                "created_at": _iso_now(),
                "actor": "system",
                "summary": "Session initialized",
                "operation": "create",
                "version": 1,
            }
        ],
    }


def _normalize_work_state(session_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    work_state = metadata.get("work_state")
    if not isinstance(work_state, dict):
        work_state = {}

    raw_artifacts = work_state.get("artifacts")
    artifacts: List[Dict[str, Any]]
    if isinstance(raw_artifacts, list) and raw_artifacts:
        artifacts = [_normalize_artifact(item, idx) for idx, item in enumerate(raw_artifacts)]
    else:
        artifacts = [_default_artifact()]

    active_artifact_id = str(work_state.get("active_artifact_id") or artifacts[0]["artifact_id"])
    if not any(item["artifact_id"] == active_artifact_id for item in artifacts):
        active_artifact_id = artifacts[0]["artifact_id"]

    ui_state_raw = work_state.get("ui_state")
    ui_state = ui_state_raw if isinstance(ui_state_raw, dict) else {}
    right_tab = str(ui_state.get("right_tab") or "preview")
    if right_tab not in {"preview", "outline", "edits", "assets"}:
        right_tab = "preview"

    return {
        "session_id": session_id,
        "work_mode": True,
        "artifacts": artifacts,
        "active_artifact_id": active_artifact_id,
        "ui_state": {
            "right_tab": right_tab,
            "left_width": int(ui_state.get("left_width") or 520),
            "selection": ui_state.get("selection") if isinstance(ui_state.get("selection"), dict) else None,
        },
    }


def _build_work_session_payload(chat_service: ChatService, session: Any, include_messages: bool = True) -> Dict[str, Any]:
    metadata = session.metadata if isinstance(session.metadata, dict) else {}
    normalized_state = _normalize_work_state(session.session_id, metadata)
    messages = chat_service.get_messages(session_id=session.session_id, limit=500, offset=0)
    messages = [item for item in messages if getattr(item, "role", None) != "tool"]
    payload: Dict[str, Any] = {
        "session_id": session.session_id,
        "title": session.title,
        "work_mode": True,
        "created_at": session.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": session.updated_at.isoformat().replace("+00:00", "Z"),
        "message_count": len(messages),
        "artifacts": normalized_state["artifacts"],
        "active_artifact_id": normalized_state["active_artifact_id"],
        "ui_state": normalized_state["ui_state"],
    }
    if include_messages:
        payload["messages"] = [_message_to_api(item) for item in messages]
    else:
        payload["last_message"] = messages[-1].content if messages else ""
    return payload


@router.get("/api/work/sessions")
async def list_work_sessions(
    recent: int = Query(default=20, ge=1, le=200),
    query: str = Query(default=""),
) -> JSONResponse:
    chat_service = _service()
    sessions = chat_service.list_sessions(limit=500, offset=0)
    normalized_query = query.strip().lower()
    matched: List[Dict[str, Any]] = []
    for session in sessions:
        metadata = session.metadata if isinstance(session.metadata, dict) else {}
        if not bool(metadata.get("work_mode")):
            continue
        if normalized_query and normalized_query not in str(session.title).lower():
            continue
        matched.append(_build_work_session_payload(chat_service, session, include_messages=False))
        if len(matched) >= recent:
            break
    return JSONResponse(status_code=200, content={"sessions": matched})


@router.post("/api/work/sessions")
async def create_work_session(request: Request) -> JSONResponse:
    if not request:
        payload = {}
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Invalid payload")

    title = str(payload.get("title") or f"Work Session {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    validate_title_length(title)
    safe_title = sanitize_session_title(title)

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    safe_metadata = sanitize_metadata(metadata)
    safe_metadata["work_mode"] = True

    chat_service = _service()
    session = chat_service.create_session(title=safe_title, metadata=safe_metadata)

    # Initialize normalized work state on creation.
    normalized_state = _normalize_work_state(session.session_id, safe_metadata)
    chat_service.update_session_metadata(
        session_id=session.session_id,
        metadata={
            "work_mode": True,
            "work_state": {
                "artifacts": normalized_state["artifacts"],
                "active_artifact_id": normalized_state["active_artifact_id"],
                "ui_state": normalized_state["ui_state"],
            },
        },
    )
    refreshed = chat_service.get_session(session.session_id)
    return JSONResponse(status_code=200, content=_build_work_session_payload(chat_service, refreshed, include_messages=True))


@router.get("/api/work/sessions/{session_id}")
async def get_work_session(session_id: str) -> JSONResponse:
    chat_service = _service()
    try:
        session = chat_service.get_session(session_id)
    except ValueError:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Session not found"})

    metadata = session.metadata if isinstance(session.metadata, dict) else {}
    if not bool(metadata.get("work_mode")):
        # Allow promoting an existing session into work mode.
        chat_service.update_session_metadata(session_id=session_id, metadata={"work_mode": True})
        session = chat_service.get_session(session_id)
    return JSONResponse(status_code=200, content=_build_work_session_payload(chat_service, session, include_messages=True))


@router.put("/api/work/sessions/{session_id}")
async def update_work_session(session_id: str, request: Request) -> JSONResponse:
    if not request:
        payload = {}
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Invalid payload")

    chat_service = _service()
    try:
        session = chat_service.get_session(session_id)
    except ValueError:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Session not found"})

    if "title" in payload:
        title = payload.get("title")
        if not isinstance(title, str):
            raise HTTPException(status_code=422, detail="title must be a string")
        validate_title_length(title)
        chat_service.update_session_title(session_id=session_id, title=sanitize_session_title(title))

    session = chat_service.get_session(session_id)
    metadata = session.metadata if isinstance(session.metadata, dict) else {}
    normalized_state = _normalize_work_state(session_id, metadata)

    incoming_artifacts = payload.get("artifacts")
    if isinstance(incoming_artifacts, list):
        normalized_state["artifacts"] = [_normalize_artifact(item, idx) for idx, item in enumerate(incoming_artifacts)]
        if not normalized_state["artifacts"]:
            normalized_state["artifacts"] = [_default_artifact()]

    incoming_active = payload.get("active_artifact_id")
    if isinstance(incoming_active, str) and incoming_active.strip():
        normalized_state["active_artifact_id"] = incoming_active.strip()
    if not any(item["artifact_id"] == normalized_state["active_artifact_id"] for item in normalized_state["artifacts"]):
        normalized_state["active_artifact_id"] = normalized_state["artifacts"][0]["artifact_id"]

    incoming_ui_state = payload.get("ui_state")
    if isinstance(incoming_ui_state, dict):
        normalized_state["ui_state"] = {
            **normalized_state["ui_state"],
            **incoming_ui_state,
        }
        right_tab = str(normalized_state["ui_state"].get("right_tab") or "preview")
        if right_tab not in {"preview", "outline", "edits", "assets"}:
            normalized_state["ui_state"]["right_tab"] = "preview"

    # Optional write path for messages: append non-duplicated items.
    incoming_messages = payload.get("messages")
    if isinstance(incoming_messages, list):
        existing = chat_service.get_messages(session_id=session_id, limit=5000, offset=0)
        existing_fingerprint = {
            f"{item.role}:{item.content.strip()}" for item in existing if isinstance(item.content, str)
        }
        for item in incoming_messages:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if not isinstance(role, str) or not isinstance(content, str):
                continue
            normalized_role = validate_message_role(role)
            validate_content_length(content)
            safe_content = sanitize_message_content(content)
            fingerprint = f"{normalized_role}:{safe_content.strip()}"
            if fingerprint in existing_fingerprint:
                continue
            chat_service.add_message(
                session_id=session_id,
                role=normalized_role,
                content=safe_content,
                metadata=sanitize_metadata(item.get("metadata") if isinstance(item.get("metadata"), dict) else {}),
            )
            existing_fingerprint.add(fingerprint)

    chat_service.update_session_metadata(
        session_id=session_id,
        metadata={
            "work_mode": True,
            "work_state": {
                "artifacts": normalized_state["artifacts"],
                "active_artifact_id": normalized_state["active_artifact_id"],
                "ui_state": normalized_state["ui_state"],
            },
        },
    )
    updated = chat_service.get_session(session_id)
    return JSONResponse(status_code=200, content=_build_work_session_payload(chat_service, updated, include_messages=True))


__all__ = ["router"]
