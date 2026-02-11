from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from octopusos.core.email.models import EmailHeader, EmailMessage, SendResult
from octopusos.core.email.providers.base import EmailProvider


@dataclass(frozen=True)
class _MockMsg:
    message_id: str
    from_email: str
    from_name: str | None
    subject: str
    date_ms: int
    body_text: str
    unread: bool = True
    to: list[str] | None = None


def _load_messages(config_json: str) -> list[_MockMsg]:
    try:
        cfg = json.loads(config_json or "{}")
    except Exception:
        cfg = {}
    items = cfg.get("mock_messages", [])
    if not isinstance(items, list):
        return []
    out: list[_MockMsg] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(
            _MockMsg(
                message_id=str(it.get("message_id") or ""),
                from_email=str(it.get("from_email") or "sender@example.com"),
                from_name=(str(it.get("from_name")) if it.get("from_name") is not None else None),
                subject=str(it.get("subject") or ""),
                date_ms=int(it.get("date_ms") or 0),
                body_text=str(it.get("body_text") or ""),
                unread=bool(it.get("unread", True)),
                to=it.get("to") if isinstance(it.get("to"), list) else None,
            )
        )
    return [m for m in out if m.message_id]


class MockEmailProvider(EmailProvider):
    def __init__(self, *, config_json: str):
        self._config_json = config_json or "{}"
        self._sent: list[dict] = []

    def list_unread(self, *, since_ms: Optional[int], limit: int) -> list[EmailHeader]:
        items = [m for m in _load_messages(self._config_json) if m.unread]
        if since_ms is not None:
            items = [m for m in items if int(m.date_ms or 0) >= int(since_ms)]
        items.sort(key=lambda m: int(m.date_ms or 0), reverse=True)
        out: list[EmailHeader] = []
        for m in items[: max(1, min(int(limit), 200))]:
            out.append(
                EmailHeader(
                    message_id=m.message_id,
                    from_email=m.from_email,
                    from_name=m.from_name,
                    subject=m.subject,
                    date_ms=int(m.date_ms or 0),
                    snippet=(m.body_text[:160] if m.body_text else ""),
                    importance="normal",
                )
            )
        return out

    def get_message(self, *, message_id: str) -> EmailMessage:
        msgs = _load_messages(self._config_json)
        for m in msgs:
            if m.message_id == message_id:
                body = m.body_text or ""
                md = (
                    f"**From:** {m.from_name + ' ' if m.from_name else ''}<{m.from_email}>\n\n"
                    f"**Subject:** {m.subject}\n\n"
                    f"---\n\n{body}\n"
                )
                return EmailMessage(
                    message_id=m.message_id,
                    from_email=m.from_email,
                    from_name=m.from_name,
                    to=m.to or ["me@example.com"],
                    cc=[],
                    subject=m.subject,
                    date_ms=int(m.date_ms or 0),
                    body_text=body,
                    body_md=md,
                )
        raise ValueError("MESSAGE_NOT_FOUND")

    def create_draft_reply(self, *, message_id: str, user_text: str) -> tuple[str, str, str]:
        msg = self.get_message(message_id=message_id)
        subject = msg.subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        body_md = (
            f"Hi {msg.from_name or msg.from_email},\n\n"
            f"{(user_text or '').strip()}\n\n"
            f"---\n\n"
            f"> On {msg.date_ms}, {msg.from_email} wrote:\n"
            + "\n".join([f"> {line}" for line in (msg.body_text or "").splitlines()][:20])
            + "\n"
        )
        reasoning = "Rule-based formatting (no model)."
        return subject, body_md, reasoning

    def send(self, *, subject: str, body_text: str, to: list[str], cc: list[str] | None = None) -> SendResult:
        self._sent.append({"subject": subject, "body_text": body_text, "to": to, "cc": cc or []})
        return SendResult(ok=True, provider_message_id="mock-sent-1")

    def test_connection(self) -> tuple[bool, str | None]:
        return True, None

    # Mark-as-read is intentionally unsupported for mock (UI should hide it).
