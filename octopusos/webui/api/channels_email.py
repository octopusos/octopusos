"""Email Channel API (Channel-first; MCP-backed).

This router exists to keep user-facing semantics consistent:
- Email is a Channel: /channels/email
- MCP is the underlying capability layer (providers + instances + secrets)

Implementation note:
We deliberately *reuse* the existing MCP Email handlers to avoid forking logic.
The legacy MCP endpoints remain for compatibility (tests, external callers).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from octopusos.webui.api import mcp_email as _mcp
from octopusos.webui.api import mcp_email_oauth as _oauth


router = APIRouter(prefix="/api/channels/email", tags=["channels-email"])


# -------------------------
# Instances
# -------------------------


@router.get("/instances")
def list_instances() -> Dict[str, Any]:
    return _mcp.list_email_instances()


@router.post("/instances")
def create_instance(payload: _mcp.CreateInstanceRequest) -> Dict[str, Any]:
    return _mcp.create_email_instance(payload)


@router.post("/instances/{instance_id}/test")
def test_instance(instance_id: str) -> Dict[str, Any]:
    return _mcp.test_email_instance(instance_id)


# -------------------------
# Rules (instance-scoped)
# -------------------------


@router.post("/instances/{instance_id}/rules/allow_sender")
def allow_sender(instance_id: str, payload: _mcp.SenderRuleRequest) -> Dict[str, Any]:
    return _mcp.allow_sender(instance_id, payload)


@router.post("/instances/{instance_id}/rules/block_sender")
def block_sender(instance_id: str, payload: _mcp.SenderRuleRequest) -> Dict[str, Any]:
    return _mcp.block_sender(instance_id, payload)


@router.post("/instances/{instance_id}/rules/unblock_sender")
def unblock_sender(instance_id: str, payload: _mcp.SenderRuleRequest) -> Dict[str, Any]:
    return _mcp.unblock_sender(instance_id, payload)


@router.post("/instances/{instance_id}/rules/block_domain")
def block_domain(instance_id: str, payload: _mcp.DomainRuleRequest) -> Dict[str, Any]:
    return _mcp.block_domain(instance_id, payload)


@router.post("/instances/{instance_id}/rules/unblock_domain")
def unblock_domain(instance_id: str, payload: _mcp.DomainRuleRequest) -> Dict[str, Any]:
    return _mcp.unblock_domain(instance_id, payload)


# -------------------------
# Unread + actions
# -------------------------


@router.get("/{instance_id}/unread")
def list_unread(
    instance_id: str,
    since: Optional[str] = Query(default="today", description="today | all"),
    limit: int = Query(default=50, ge=1, le=200),
    tz: Optional[str] = Query(default=None, description="Timezone for 'today' calculation"),
) -> Dict[str, Any]:
    return _mcp.list_unread(instance_id=instance_id, since=since, limit=limit, tz=tz)


@router.post("/{instance_id}/snooze")
def snooze_message(instance_id: str, payload: _mcp.SnoozeRequest) -> Dict[str, Any]:
    return _mcp.snooze_message(instance_id, payload)


@router.post("/{instance_id}/mark-read")
def mark_read(instance_id: str, payload: _mcp.MarkReadRequest) -> Dict[str, Any]:
    return _mcp.mark_read(instance_id, payload)


@router.get("/{instance_id}/message/{message_id}")
def get_message(instance_id: str, message_id: str) -> Dict[str, Any]:
    return _mcp.get_message(instance_id, message_id)


@router.post("/{instance_id}/draft-reply")
def draft_reply(instance_id: str, payload: _mcp.DraftReplyRequest) -> Dict[str, Any]:
    return _mcp.draft_reply(instance_id, payload)


@router.post("/{instance_id}/send")
def send_draft(instance_id: str, payload: _mcp.SendDraftRequest) -> Dict[str, Any]:
    return _mcp.send_draft(instance_id, payload)


# -------------------------
# OAuth (optional, instance-scoped)
# -------------------------


@router.get("/{instance_id}/oauth/start")
def oauth_start(instance_id: str) -> Dict[str, Any]:
    return _oauth.oauth_start(instance_id)


@router.get("/{instance_id}/oauth/status")
def oauth_status(instance_id: str) -> Dict[str, Any]:
    return _oauth.oauth_status(instance_id)


@router.post("/{instance_id}/oauth/disconnect")
def oauth_disconnect(instance_id: str) -> Dict[str, Any]:
    return _oauth.oauth_disconnect(instance_id)


@router.get("/oauth/callback")
def oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> Dict[str, Any]:
    # Keep callback compatible with either /api/mcp/email/oauth/callback or /api/channels/email/oauth/callback.
    return _oauth.oauth_callback(code=code, state=state, error=error, error_description=error_description)

