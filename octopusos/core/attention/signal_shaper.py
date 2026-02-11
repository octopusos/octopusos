from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from octopusos.core.attention.models import CardSeverity, ScopeType
from octopusos.core.attention.card_catalog import get_card_spec
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid


@dataclass(frozen=True)
class ShapedCard:
    scope_type: ScopeType
    scope_id: str
    card_type: str
    severity: CardSeverity
    title: str
    summary: str
    merge_key: str
    event_id: str
    event_created_at_ms: int
    metadata_json: str


def _severity_rank(sev: CardSeverity) -> int:
    order = {"info": 0, "warn": 1, "high": 2, "critical": 3}
    return order.get(sev, 0)


def _normalize_severity(value: Any) -> CardSeverity:
    raw = str(value or "").strip().lower()
    if raw in {"info", "warn", "high", "critical"}:
        return raw  # type: ignore[return-value]
    return "warn"


def _default_card_for_event(event_type: str, apply_status: str) -> tuple[str, CardSeverity] | None:
    if str(apply_status or "").strip().lower() == "failed":
        return "chat_writer_anomaly", "high"
    if str(event_type or "") == "context_integrity_blocked":
        return "context_integrity_blocked", "high"
    if str(event_type or "") == "CONTEXT_INTEGRITY_DEGRADED":
        return "context_integrity_blocked", "warn"
    if str(event_type or "") in {"audit_findings", "gate_findings"}:
        return "audit_or_gate_findings", "warn"
    return None


def shape_ledger_event(*, event: Any) -> Optional[ShapedCard]:
    """Translate a ledger event into a shaped card candidate.

    To keep Phase 2 safe, we only shape events that opt-in via payload.card_type
    or match a small allowlist of system events.
    """
    payload: dict[str, Any] = {}
    try:
        raw = getattr(event, "payload_json", None)
        if raw:
            payload = json.loads(raw)
    except Exception:
        payload = {}

    event_type = str(getattr(event, "event_type", "") or "")
    apply_status = str(getattr(event, "apply_status", "") or "")

    card_type = str(payload.get("card_type") or "").strip()
    severity = _normalize_severity(payload.get("severity"))
    if not card_type:
        fallback = _default_card_for_event(event_type, apply_status)
        if not fallback:
            return None
        card_type, severity = fallback
    else:
        # If the payload omitted severity, allow the catalog to define defaults.
        if not str(payload.get("severity") or "").strip():
            spec = get_card_spec(card_type)
            if spec:
                severity = spec.default_severity

    scope_type = str(payload.get("scope_type") or "").strip().lower() or "session"
    scope_id = str(payload.get("scope_id") or "").strip()
    if scope_type not in {"global", "project", "session", "resource"}:
        scope_type = "session"
    if not scope_id:
        scope_id = str(getattr(event, "session_id", "") or "")
    if not scope_id:
        # No stable scope; drop.
        return None

    title = str(payload.get("title") or "").strip() or card_type.replace("_", " ").title()
    summary = str(payload.get("summary") or "").strip()
    if not summary:
        summary = f"Event: {event_type or card_type}"

    merge_key = str(payload.get("merge_key") or "").strip()
    if not merge_key:
        spec = get_card_spec(card_type)
        if spec and scope_type == "session":
            merge_key = spec.merge_key_for_scope_id(scope_id)
        else:
            merge_key = f"{scope_type}:{scope_id}:{card_type}"

    created_ms = int(getattr(event, "created_at_ms", 0) or 0)
    if created_ms <= 0:
        created_ms = now_ms()

    meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if not isinstance(meta, dict):
        meta = {}
    # Persist a small trace for debugging.
    meta.setdefault("source_event_type", event_type)
    meta.setdefault("source_apply_status", apply_status)
    meta.setdefault("source_event_id", str(getattr(event, "event_id", "") or ""))

    return ShapedCard(
        scope_type=scope_type,  # type: ignore[arg-type]
        scope_id=scope_id,
        card_type=card_type,
        severity=severity,
        title=title,
        summary=summary,
        merge_key=merge_key,
        event_id=str(getattr(event, "event_id", "") or ulid()),
        event_created_at_ms=created_ms,
        metadata_json=json.dumps(meta, ensure_ascii=False),
    )


def merge_severity(existing: CardSeverity, incoming: CardSeverity) -> CardSeverity:
    return incoming if _severity_rank(incoming) > _severity_rank(existing) else existing
