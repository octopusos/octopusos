"""Dispatch proposal state machine (v3.2 MVP)."""

from __future__ import annotations

VALID_STATUSES = {"pending", "approved", "rejected", "cancelled", "executed", "failed"}

ALLOWED_TRANSITIONS = {
    "pending": {"approved", "rejected", "cancelled"},
    "approved": {"executed", "failed"},
    "rejected": set(),
    "cancelled": set(),
    "executed": set(),
    "failed": set(),
}


def can_transition(current: str, target: str) -> bool:
    if current not in VALID_STATUSES or target not in VALID_STATUSES:
        return False
    return target in ALLOWED_TRANSITIONS.get(current, set())
