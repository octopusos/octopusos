from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


ScopeType = Literal["global", "project", "session", "resource"]
CardSeverity = Literal["info", "warn", "high", "critical"]
CardStatus = Literal["open", "snoozed", "closed"]
CardResolutionStatus = Literal["open", "acknowledged", "resolved", "dismissed", "deferred"]

InboxDeliveryType = Literal["inbox_only", "notify", "confirm"]
InboxStatus = Literal["unread", "read", "archived"]


@dataclass(frozen=True)
class StateCard:
    card_id: str
    scope_type: ScopeType
    scope_id: str
    card_type: str
    severity: CardSeverity
    status: CardStatus
    title: str
    summary: str
    first_seen_ms: int
    last_seen_ms: int
    last_event_id: Optional[str]
    merge_key: str
    cooldown_until_ms: Optional[int]
    metadata_json: str
    # Phase 4: closure semantics (keep status for storage/dedup rules, but use resolution_status for UX).
    resolution_status: CardResolutionStatus = "open"
    resolution_reason: Optional[str] = None
    resolved_at_ms: Optional[int] = None
    resolved_by: Optional[str] = None  # user|system
    resolution_note: Optional[str] = None
    linked_task_id: Optional[str] = None


@dataclass(frozen=True)
class InboxItem:
    inbox_item_id: str
    card_id: str
    scope_type: ScopeType
    scope_id: str
    delivery_type: InboxDeliveryType
    status: InboxStatus
    created_at_ms: int
    updated_at_ms: int
