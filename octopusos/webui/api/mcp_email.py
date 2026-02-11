"""MCP Email APIs (multi-instance IMAP/SMTP MVP).

This is intentionally small and transparent:
- Instances are stored in the registry DB (email_instances).
- Draft sending is confirmation-based (draft -> confirm -> send).
"""

from __future__ import annotations

import json
import datetime as dt
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from octopusos.core.email.adapter import EmailAdapter
from octopusos.core.email.draft_store import EmailDraftStore
from octopusos.core.email.digest import build_digest_md, since_start_of_day_ms
from octopusos.core.email.instance_store import EmailInstanceStore
from octopusos.core.email.snooze_store import EmailSnoozeStore
from octopusos.store.timestamp_utils import now_ms


def _inject_deprecation_headers(response: Response) -> None:
    # Compatibility layer: prefer /api/channels/email for Channel-first semantics.
    response.headers.setdefault("X-OctopusOS-Deprecated", "use /api/channels/email")
    response.headers.setdefault("X-OctopusOS-Deprecated-Since", "2026-02-10")
    response.headers.setdefault("Link", '</api/channels/email>; rel="successor-version"')


router = APIRouter(
    prefix="/api/mcp/email",
    tags=["mcp-email"],
    dependencies=[Depends(_inject_deprecation_headers)],
)

def _raise_adapter_error(exc: Exception) -> None:
    if not isinstance(exc, ValueError):
        raise HTTPException(status_code=500, detail="internal error")
    code = str(exc)
    if code in {"INSTANCE_NOT_FOUND", "DRAFT_NOT_FOUND", "MESSAGE_NOT_FOUND"}:
        raise HTTPException(status_code=404, detail=code.lower())
    if code in {"missing_credentials", "missing_token"}:
        raise HTTPException(status_code=412, detail=code)
    if code in {"PROVIDER_NOT_SUPPORTED", "NOT_SUPPORTED"}:
        raise HTTPException(status_code=422, detail=code)
    raise HTTPException(status_code=422, detail=code)


def _tz_name(value: str | None) -> str:
    v = (value or "").strip()
    return v or "Australia/Sydney"


def _since_ms_from_param(*, since: str | None, tz: str) -> int | None:
    raw = (since or "").strip().lower()
    if not raw:
        return None
    if raw == "today":
        return since_start_of_day_ms(tz_name=tz)
    if raw == "all":
        return None
    return None


class CreateInstanceRequest(BaseModel):
    name: str = Field(..., min_length=1)
    provider_type: str = Field(..., description="imap_smtp | mock | gmail_oauth | outlook_oauth")
    config: Dict[str, Any] = Field(default_factory=dict)
    secret_ref: str = Field(default="", description="secret://... reference (password/token). Stored as a reference only.")


class DraftReplyRequest(BaseModel):
    message_id: str = Field(..., min_length=1)
    user_text: str = Field(default="", description="User's reply intent (will be polished/structured).")


class SendDraftRequest(BaseModel):
    draft_id: str = Field(..., min_length=1)
    confirm_token: str = Field(..., min_length=1)
    user_confirmed: bool = Field(default=False)

class SenderRuleRequest(BaseModel):
    sender: str = Field(..., min_length=3)

class DomainRuleRequest(BaseModel):
    domain: str = Field(..., min_length=3)


class SnoozeRequest(BaseModel):
    message_id: str = Field(..., min_length=1)
    hours: int = Field(default=24, ge=1, le=72)


class MarkReadRequest(BaseModel):
    message_id: str = Field(..., min_length=1)


@router.get("/instances")
def list_email_instances() -> Dict[str, Any]:
    adapter = EmailAdapter()
    items = []
    for inst in adapter.list_instances():
        items.append(
            {
                "instance_id": inst.instance_id,
                "name": inst.name,
                "provider_type": inst.provider_type,
                "config_json": inst.config_json,
                "secret_ref": inst.secret_ref,
                "created_at_ms": inst.created_at_ms,
                "updated_at_ms": inst.updated_at_ms,
                "last_test_ok": inst.last_test_ok,
                "last_test_at_ms": inst.last_test_at_ms,
                "last_test_error": inst.last_test_error,
            }
        )
    return {"ok": True, "instances": items}


@router.post("/instances")
def create_email_instance(payload: CreateInstanceRequest) -> Dict[str, Any]:
    provider_type = (payload.provider_type or "").strip()
    if provider_type not in {"imap_smtp", "mock", "gmail_oauth", "outlook_oauth"}:
        raise HTTPException(status_code=400, detail="provider_type not supported")
    store = EmailInstanceStore()
    iid = store.create(
        name=payload.name,
        provider_type=provider_type,
        config_obj=payload.config or {},
        secret_ref=payload.secret_ref or "",
    )
    return {"ok": True, "instance_id": iid}


@router.post("/instances/{instance_id}/test")
def test_email_instance(instance_id: str) -> Dict[str, Any]:
    adapter = EmailAdapter()
    store = EmailInstanceStore()
    try:
        ok, err = adapter.test_instance(instance_id=instance_id)
    except Exception as exc:
        _raise_adapter_error(exc)
    store.update_test_result(instance_id=instance_id, ok=ok, error=err)
    return {"ok": True, "test_ok": ok, "error": err}

@router.post("/instances/{instance_id}/rules/allow_sender")
def allow_sender(instance_id: str, payload: SenderRuleRequest) -> Dict[str, Any]:
    sender = (payload.sender or "").strip().lower()
    if "@" not in sender:
        raise HTTPException(status_code=400, detail="invalid sender")
    EmailInstanceStore().append_list_key(instance_id=instance_id, key="allow_senders", values=[sender])
    return {"ok": True}


@router.post("/instances/{instance_id}/rules/block_sender")
def block_sender(instance_id: str, payload: SenderRuleRequest) -> Dict[str, Any]:
    sender = (payload.sender or "").strip().lower()
    if "@" not in sender:
        raise HTTPException(status_code=400, detail="invalid sender")
    EmailInstanceStore().append_list_key(instance_id=instance_id, key="block_senders", values=[sender])
    return {"ok": True}


@router.post("/instances/{instance_id}/rules/unblock_sender")
def unblock_sender(instance_id: str, payload: SenderRuleRequest) -> Dict[str, Any]:
    # Best-effort: remove from block_senders if present.
    sender = (payload.sender or "").strip().lower()
    if "@" not in sender:
        raise HTTPException(status_code=400, detail="invalid sender")
    inst = EmailInstanceStore().get(instance_id=instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="instance not found")
    try:
        cfg = json.loads(inst.config_json or "{}")
    except Exception:
        cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    current = cfg.get("block_senders", [])
    next_block: list[str] = []
    if isinstance(current, list):
        next_block = [str(x).strip().lower() for x in current if str(x).strip().lower() and str(x).strip().lower() != sender]
    EmailInstanceStore().set_list_key(instance_id=instance_id, key="block_senders", values=next_block)
    return {"ok": True}


def _normalize_domain(value: str) -> str:
    v = (value or "").strip().lower()
    if v.startswith("mailto:"):
        v = v[len("mailto:") :]
    if v.startswith("@"):
        v = v[1:]
    v = v.strip().strip(".")
    return v


def _is_valid_domain(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return False
    if " " in v or "/" in v or "\\" in v:
        return False
    if "." not in v:
        return False
    return True


def _current_block_domains(instance_id: str) -> list[str]:
    inst = EmailInstanceStore().get(instance_id=instance_id)
    if not inst:
        return []
    try:
        cfg = json.loads(inst.config_json or "{}")
    except Exception:
        cfg = {}
    if not isinstance(cfg, dict):
        return []
    raw = cfg.get("block_domains", [])
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        d = _normalize_domain(str(x))
        if d:
            out.append(d)
    # De-dupe while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for d in out:
        if d in seen:
            continue
        seen.add(d)
        deduped.append(d)
    return deduped


@router.post("/instances/{instance_id}/rules/block_domain")
def block_domain(instance_id: str, payload: DomainRuleRequest) -> Dict[str, Any]:
    domain = _normalize_domain(payload.domain or "")
    if not _is_valid_domain(domain):
        raise HTTPException(status_code=400, detail="invalid domain")
    EmailInstanceStore().append_list_key(instance_id=instance_id, key="block_domains", values=[domain])
    return {"ok": True, "block_domains": _current_block_domains(instance_id)}


@router.post("/instances/{instance_id}/rules/unblock_domain")
def unblock_domain(instance_id: str, payload: DomainRuleRequest) -> Dict[str, Any]:
    domain = _normalize_domain(payload.domain or "")
    if not _is_valid_domain(domain):
        raise HTTPException(status_code=400, detail="invalid domain")
    current = _current_block_domains(instance_id)
    next_domains = [d for d in current if d != domain]
    EmailInstanceStore().set_list_key(instance_id=instance_id, key="block_domains", values=next_domains)
    return {"ok": True, "block_domains": _current_block_domains(instance_id)}


@router.get("/{instance_id}/unread")
def list_unread(
    instance_id: str,
    since: Optional[str] = Query(default="today", description="today | all"),
    limit: int = Query(default=50, ge=1, le=200),
    tz: Optional[str] = Query(default=None, description="Timezone for 'today' calculation"),
) -> Dict[str, Any]:
    tz_name = _tz_name(tz)
    since_ms = _since_ms_from_param(since=since, tz=tz_name)
    adapter = EmailAdapter()
    try:
        headers = adapter.list_unread(instance_id=instance_id, since_ms=since_ms, limit=limit)
    except Exception as exc:
        _raise_adapter_error(exc)

    inst = EmailInstanceStore().get(instance_id=instance_id)
    instance_name = inst.name if inst else instance_id

    digest_md, important, normal, filtered = build_digest_md(instance_name=instance_name, headers=headers, tz_name=tz_name)
    return {
        "ok": True,
        "instance_id": instance_id,
        "instance_name": instance_name,
        "total_unread": len(headers),
        "important": [h.__dict__ for h in important],
        "normal": [h.__dict__ for h in normal],
        "filtered": [h.__dict__ for h in filtered],
        "digest_md": digest_md,
        "generated_at_ms": now_ms(),
        "timezone": tz_name,
    }

@router.post("/{instance_id}/snooze")
def snooze_message(instance_id: str, payload: SnoozeRequest) -> Dict[str, Any]:
    hours = int(payload.hours or 24)
    until = int(now_ms() + hours * 60 * 60 * 1000)
    EmailSnoozeStore().upsert(instance_id=instance_id, message_id=payload.message_id, until_ms=until)
    return {"ok": True, "until_ms": until}


@router.post("/{instance_id}/mark-read")
def mark_read(instance_id: str, payload: MarkReadRequest) -> Dict[str, Any]:
    adapter = EmailAdapter()
    try:
        adapter.mark_read(instance_id=instance_id, message_id=payload.message_id)
    except ValueError as exc:
        if str(exc) == "NOT_SUPPORTED":
            raise HTTPException(status_code=400, detail="not supported") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/{instance_id}/message/{message_id}")
def get_message(instance_id: str, message_id: str) -> Dict[str, Any]:
    adapter = EmailAdapter()
    try:
        msg = adapter.get_message(instance_id=instance_id, message_id=message_id)
    except Exception as exc:
        _raise_adapter_error(exc)
    return {"ok": True, "message": msg.__dict__}


@router.post("/{instance_id}/draft-reply")
def draft_reply(instance_id: str, payload: DraftReplyRequest) -> Dict[str, Any]:
    adapter = EmailAdapter()
    draft, reasoning = adapter.create_draft_reply(instance_id=instance_id, message_id=payload.message_id, user_text=payload.user_text)
    return {
        "ok": True,
        "draft": draft.__dict__,
        "polished_text": draft.body_md,
        "reasoning_summary": reasoning,
    }


@router.post("/{instance_id}/send")
def send_draft(instance_id: str, payload: SendDraftRequest) -> Dict[str, Any]:
    # Hard redline: sending must be confirmation-based.
    if not payload.user_confirmed:
        raise HTTPException(status_code=400, detail="user_confirmed required")

    # Instance scoping guard: avoid cross-instance confusion.
    row = EmailDraftStore().get(draft_id=payload.draft_id)
    if not row:
        raise HTTPException(status_code=404, detail="draft not found")
    if str(row.instance_id) != str(instance_id):
        raise HTTPException(status_code=400, detail="draft instance mismatch")

    adapter = EmailAdapter()
    result = adapter.send_draft(draft_id=payload.draft_id, confirm_token=payload.confirm_token)
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error or "send_failed")
    return {"ok": True, "provider_message_id": result.provider_message_id}
