from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EmailHeader:
    message_id: str
    from_email: str
    from_name: str | None
    subject: str
    date_ms: int
    snippet: str
    importance: str  # important|normal|filtered


@dataclass(frozen=True)
class EmailMessage:
    message_id: str
    from_email: str
    from_name: str | None
    to: list[str]
    cc: list[str]
    subject: str
    date_ms: int
    body_text: str
    body_md: str


@dataclass(frozen=True)
class EmailDraft:
    draft_id: str
    instance_id: str
    message_id: str
    subject: str
    body_md: str
    confirm_token: str
    expires_at_ms: int


@dataclass(frozen=True)
class SendResult:
    ok: bool
    provider_message_id: Optional[str] = None
    error: Optional[str] = None

