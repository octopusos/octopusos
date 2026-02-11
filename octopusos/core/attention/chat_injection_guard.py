from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from octopusos.core.attention.chat_injection_config import (
    injection_enabled,
    injection_mode,
    max_per_global_per_minute,
    max_per_session_per_minute,
    only_when_session_active,
    require_user_idle_ms,
    severity_threshold,
)
from octopusos.core.attention.models import StateCard
from octopusos.core.db import registry_db
from octopusos.store.timestamp_utils import now_ms
from octopusos.core.work.work_mode import get_work_mode_global


@dataclass(frozen=True)
class InjectionDecision:
    allowed: bool
    reason: str


def _severity_rank(value: str) -> int:
    order = {"info": 0, "warn": 1, "high": 2, "critical": 3}
    return order.get(str(value or "").strip().lower(), 0)


def decide_chat_injection(*, card: StateCard, session_id: str) -> InjectionDecision:
    """Decide whether a state card may be injected into the chat transcript.

    Gate-3 contract:
    - must be runtime-switchable and safe to disable immediately
    - must be explainable (reason string)
    - must be rate-limited (per-session and global)
    - must respect only_when_session_active
    - must respect require_user_idle_ms (best-effort server-side approximation)
    """
    work_mode = get_work_mode_global()
    if work_mode != "proactive":
        return InjectionDecision(False, f"work_mode:{work_mode}")
    if not injection_enabled():
        return InjectionDecision(False, "disabled")
    mode = injection_mode()
    if mode != "chat_allowed":
        return InjectionDecision(False, f"mode:{mode}")

    if card.scope_type != "session":
        return InjectionDecision(False, "scope:not_session")
    if not session_id or card.scope_id != session_id:
        return InjectionDecision(False, "scope:mismatch")

    if _severity_rank(card.severity) < _severity_rank(severity_threshold()):
        return InjectionDecision(False, "severity:below_threshold")

    conn = registry_db.get_db()
    cur = conn.cursor()
    now = now_ms()
    window_start = int(now - 60_000)

    if only_when_session_active():
        # We define "active" as the UI having recently touched presence for this session.
        # This is intentionally conservative.
        row = cur.execute(
            "SELECT last_seen_ms FROM session_presence WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        last_seen = int(row[0]) if row and row[0] is not None else 0
        if now - last_seen > 30_000:
            return InjectionDecision(False, "session:not_active")

    idle_ms = require_user_idle_ms()
    if idle_ms > 0:
        row = cur.execute(
            """
            SELECT COALESCE(MAX(created_at_ms), 0)
            FROM chat_messages
            WHERE session_id = ? AND role = 'user'
            """,
            (session_id,),
        ).fetchone()
        last_user = int(row[0] if row else 0)
        if last_user and now - last_user < idle_ms:
            return InjectionDecision(False, "user:not_idle")

    # Rate limits based on injection queue creations.
    max_sess = max_per_session_per_minute()
    if max_sess > 0:
        row = cur.execute(
            """
            SELECT COUNT(*)
            FROM chat_injection_queue
            WHERE session_id = ? AND created_at_ms > ? AND status IN ('queued', 'applied')
            """,
            (session_id, window_start),
        ).fetchone()
        if int(row[0] if row else 0) >= max_sess:
            return InjectionDecision(False, "rate_limit:session")

    max_global = max_per_global_per_minute()
    if max_global > 0:
        row = cur.execute(
            """
            SELECT COUNT(*)
            FROM chat_injection_queue
            WHERE created_at_ms > ? AND status IN ('queued', 'applied')
            """,
            (window_start,),
        ).fetchone()
        if int(row[0] if row else 0) >= max_global:
            return InjectionDecision(False, "rate_limit:global")

    return InjectionDecision(True, "allow")
