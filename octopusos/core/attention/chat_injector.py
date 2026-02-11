from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

from octopusos.core.attention.chat_injection_guard import decide_chat_injection
from octopusos.core.attention.card_catalog import get_card_spec
from octopusos.core.attention.inbox_service import InboxService
from octopusos.core.attention.models import StateCard
from octopusos.core.attention.state_card_store import StateCardStore
from octopusos.core.chat.event_ledger import append_observed_event
from octopusos.core.chat.session_writer import SessionWriter
from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid


@dataclass(frozen=True)
class DrainResult:
    applied: int
    failed: int
    cancelled: int


class ChatInjector:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())
        self._cards = StateCardStore()
        self._session_writer = SessionWriter()

    def enqueue_from_card(self, *, card: StateCard, session_id: str, reason: str) -> Optional[str]:
        injection_id = ulid()
        ts = now_ms()
        idem = f"inject:{card.card_id}"
        ledger_idem = f"enqueue:{card.card_id}"

        def _op(conn: sqlite3.Connection) -> Optional[str]:
            try:
                conn.execute(
                    """
                    INSERT INTO chat_injection_queue (
                      injection_id, card_id, session_id, idempotency_key,
                      status, message_id, created_at_ms, updated_at_ms, error_json
                    )
                    VALUES (?, ?, ?, ?, 'queued', NULL, ?, ?, NULL)
                    """,
                    (
                        injection_id,
                        card.card_id,
                        session_id,
                        idem,
                        int(ts),
                        int(ts),
                    ),
                )
                return injection_id
            except sqlite3.IntegrityError:
                # Already enqueued for this session/card; do not create duplicates.
                row = conn.execute(
                    """
                    SELECT injection_id
                    FROM chat_injection_queue
                    WHERE session_id = ? AND idempotency_key = ?
                    LIMIT 1
                    """,
                    (session_id, idem),
                ).fetchone()
                return str(row[0]) if row else None

        injection = self._writer.submit(_op, timeout=10.0)
        if injection:
            append_observed_event(
                session_id=session_id,
                event_type="chat_injection_enqueued",
                source="attention",
                payload={"card_id": card.card_id, "injection_id": injection, "reason": reason},
                idempotency_key=ledger_idem,
                causation_id=card.last_event_id,
                correlation_id=card.card_id,
                # Keep the observed audit event aligned with the card timeline to avoid
                # poller checkpoints jumping ahead of older ledger events (tests + clock skew).
                created_at_ms=card.last_seen_ms,
            )
        return injection

    def maybe_enqueue_from_card_id(self, *, card_id: str) -> Optional[str]:
        # Load card row directly for simplicity (Phase 3).
        conn = registry_db.get_db()
        row = conn.execute(
            """
            SELECT card_id, scope_type, scope_id, card_type, severity, status, title, summary,
                   first_seen_ms, last_seen_ms, last_event_id, merge_key, cooldown_until_ms, metadata_json
            FROM state_cards
            WHERE card_id = ?
            """,
            (card_id,),
        ).fetchone()
        if not row:
            return None
        card = StateCard(
            card_id=str(row[0]),
            scope_type=str(row[1]),  # type: ignore[arg-type]
            scope_id=str(row[2]),
            card_type=str(row[3]),
            severity=str(row[4]),  # type: ignore[arg-type]
            status=str(row[5]),  # type: ignore[arg-type]
            title=str(row[6]),
            summary=str(row[7]),
            first_seen_ms=int(row[8]),
            last_seen_ms=int(row[9]),
            last_event_id=str(row[10]) if row[10] is not None else None,
            merge_key=str(row[11]),
            cooldown_until_ms=int(row[12]) if row[12] is not None else None,
            metadata_json=str(row[13] or "{}"),
        )
        if card.status != "open":
            return None
        session_id = card.scope_id if card.scope_type == "session" else ""
        if not session_id:
            return None

        decision = decide_chat_injection(card=card, session_id=session_id)
        if not decision.allowed:
            append_observed_event(
                session_id=session_id,
                event_type="chat_injection_suppressed",
                source="attention",
                payload={"card_id": card.card_id, "reason": decision.reason},
                idempotency_key=f"suppress:{card.card_id}",
                causation_id=card.last_event_id,
                correlation_id=card.card_id,
                created_at_ms=card.last_seen_ms,
            )
            return None

        return self.enqueue_from_card(card=card, session_id=session_id, reason=decision.reason)

    def drain_queue(self, *, limit: int = 100) -> DrainResult:
        limit = int(max(1, min(limit, 5000)))
        applied = 0
        failed = 0
        cancelled = 0

        def _list(conn: sqlite3.Connection):
            return conn.execute(
                """
                SELECT injection_id, card_id, session_id, idempotency_key
                FROM chat_injection_queue
                WHERE status = 'queued'
                ORDER BY created_at_ms ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        rows = self._writer.submit(_list, timeout=10.0) or []
        for injection_id, card_id, session_id, idempotency_key in rows:
            card_row = registry_db.get_db().execute(
                "SELECT card_type, severity, title, summary FROM state_cards WHERE card_id = ?",
                (str(card_id),),
            ).fetchone()
            if not card_row:
                cancelled += 1
                self._writer.submit(
                    lambda conn: conn.execute(
                        "UPDATE chat_injection_queue SET status='cancelled', updated_at_ms=? WHERE injection_id=?",
                        (int(now_ms()), str(injection_id)),
                    ),
                    timeout=10.0,
                )
                continue

            card_type = str(card_row[0] or "")
            severity = str(card_row[1] or "warn")
            title = str(card_row[2] or "")
            summary = str(card_row[3] or "")
            # For cataloged high-severity cards, use stable user-facing templates.
            spec = get_card_spec(card_type)
            if spec:
                content = spec.injection_message_for_card(
                    StateCard(
                        card_id=str(card_id),
                        scope_type="session",
                        scope_id=str(session_id),
                        card_type=card_type,
                        severity=severity,  # type: ignore[arg-type]
                        status="open",
                        title=title,
                        summary=summary,
                        first_seen_ms=0,
                        last_seen_ms=0,
                        last_event_id=None,
                        merge_key="",
                        cooldown_until_ms=None,
                        metadata_json="{}",
                    )
                )
            else:
                content = f"[{severity}] {title}\n\n{summary}\n\n(card_id={card_id})"

            try:
                outcome = self._session_writer.apply_system_message_requested(
                    session_id=str(session_id),
                    content=content,
                    idempotency_key=str(idempotency_key),
                    source="attention",
                    extra_payload={"card_id": str(card_id)},
                )
                applied += 1
                self._writer.submit(
                    lambda conn: conn.execute(
                        """
                        UPDATE chat_injection_queue
                        SET status='applied', message_id=?, updated_at_ms=?, error_json=NULL
                        WHERE injection_id=?
                        """,
                        (outcome.message_id, int(now_ms()), str(injection_id)),
                    ),
                    timeout=10.0,
                )
            except Exception as exc:
                failed += 1
                self._writer.submit(
                    lambda conn: conn.execute(
                        """
                        UPDATE chat_injection_queue
                        SET status='failed', updated_at_ms=?, error_json=?
                        WHERE injection_id=?
                        """,
                        (int(now_ms()), json.dumps({"error": str(exc)}, ensure_ascii=False), str(injection_id)),
                    ),
                    timeout=10.0,
                )

        return DrainResult(applied=applied, failed=failed, cancelled=cancelled)
