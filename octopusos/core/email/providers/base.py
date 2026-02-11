from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from octopusos.core.email.models import EmailDraft, EmailHeader, EmailMessage, SendResult


class EmailProvider(ABC):
    @abstractmethod
    def list_unread(self, *, since_ms: Optional[int], limit: int) -> list[EmailHeader]:
        raise NotImplementedError

    @abstractmethod
    def get_message(self, *, message_id: str) -> EmailMessage:
        raise NotImplementedError

    @abstractmethod
    def create_draft_reply(self, *, message_id: str, user_text: str) -> tuple[str, str, str]:
        """Return (subject, body_md, reasoning_summary)."""
        raise NotImplementedError

    @abstractmethod
    def send(self, *, subject: str, body_text: str, to: list[str], cc: list[str] | None = None) -> SendResult:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> tuple[bool, str | None]:
        """Return (ok, error)."""
        raise NotImplementedError

    # Optional capabilities (default: unsupported)
    def supports_mark_read(self) -> bool:
        return False

    def mark_read(self, *, message_id: str) -> None:
        raise NotImplementedError("NOT_SUPPORTED")
