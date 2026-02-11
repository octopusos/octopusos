from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from octopusos.core.attention.models import CardSeverity, StateCard


@dataclass(frozen=True)
class CardSpec:
    """Authoritative mapping for a card_type.

    This is intentionally small and conservative. It is meant to keep
    signal shaping, cooldowns, and chat injection content aligned.
    """

    card_type: str
    default_severity: CardSeverity
    cooldown_ms: int
    merge_key_for_scope_id: Callable[[str], str]
    injection_message_for_card: Callable[[StateCard], str]


def _merge_key_context_integrity_blocked(session_id: str) -> str:
    return f"context_integrity_blocked:{session_id}"


def _merge_key_chat_writer_anomaly(session_id: str) -> str:
    return f"chat_writer_anomaly:{session_id}"


def _inject_context_integrity_blocked(card: StateCard) -> str:
    # Short, actionable, and traceable. Keep it stable for user expectations.
    return (
        "Context check blocked\n"
        "I paused the next step because the attached context/evidence looks incomplete, "
        "so the result may be unreliable.\n"
        "Next: open Inbox to review and fix. "
        f"(card: {card.card_id})"
    )


def _inject_chat_writer_anomaly(card: StateCard) -> str:
    return (
        "Write anomaly detected\n"
        "I detected a write error while saving messages. Your session is safe, "
        "but I’m routing updates to Inbox until this is resolved.\n"
        "Next: open Inbox for details and recovery steps. "
        f"(card: {card.card_id})"
    )


def _merge_key_email_unread_digest(scope_id: str) -> str:
    return f"email_unread_digest:{scope_id}"


def _inject_email_unread_digest(card: StateCard) -> str:
    return (
        "Email unread digest\n"
        f"{card.summary}\n"
        "Next: open Inbox to review and act. "
        f"(card: {card.card_id})"
    )


_CATALOG: dict[str, CardSpec] = {
    "context_integrity_blocked": CardSpec(
        card_type="context_integrity_blocked",
        default_severity="high",
        cooldown_ms=10 * 60_000,
        merge_key_for_scope_id=_merge_key_context_integrity_blocked,
        injection_message_for_card=_inject_context_integrity_blocked,
    ),
    "chat_writer_anomaly": CardSpec(
        card_type="chat_writer_anomaly",
        default_severity="high",
        cooldown_ms=30 * 60_000,
        merge_key_for_scope_id=_merge_key_chat_writer_anomaly,
        injection_message_for_card=_inject_chat_writer_anomaly,
    ),
    "email_unread_digest": CardSpec(
        card_type="email_unread_digest",
        default_severity="warn",
        cooldown_ms=6 * 60_000,
        merge_key_for_scope_id=_merge_key_email_unread_digest,
        injection_message_for_card=_inject_email_unread_digest,
    ),
}


def get_card_spec(card_type: str) -> Optional[CardSpec]:
    return _CATALOG.get(str(card_type or "").strip())


def cooldown_until_ms_for_card_type(*, card_type: str, now_ms: int) -> int | None:
    spec = get_card_spec(card_type)
    if not spec:
        return None
    if spec.cooldown_ms <= 0:
        return None
    return int(now_ms + int(spec.cooldown_ms))
