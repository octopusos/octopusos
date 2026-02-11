"""SessionWriter (Phase 1).

Phase 1 contract:
- Only takeover user message writes when chat.writer.mode == ledger_primary.
- dual_write must never call writer apply.
- Ledger semantics:
  - append pending (strict)
  - apply projection to existing read model (chat_sessions/chat_messages)
  - mark applied
  - recovery scans pending and re-applies idempotently
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Optional

from octopusos.core.chat import event_ledger
from octopusos.core.chat.writer_mode import get_chat_writer_failpoint
from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.store.timestamp_utils import now_ms, from_epoch_ms
from octopusos.util.ulid import ulid

logger = logging.getLogger(__name__)


FAILPOINT_AFTER_LEDGER_APPEND = "after_ledger_append_before_projection"
FAILPOINT_AFTER_PROJECTION = "after_projection_before_apply_mark"


def _maybe_trigger_failpoint(name: str) -> None:
    if get_chat_writer_failpoint() != name:
        return
    # For crash-recovery gates we need true process termination, but unit-level
    # runs must not kill the test runner. Use env to switch behavior.
    if os.getenv("OCTOPUSOS_FAILPOINT_EXIT", "0").strip() in {"1", "true", "yes", "on"}:
        os._exit(1)  # noqa: S404 - intentional failpoint
    raise RuntimeError(f"FAILPOINT:{name}")


@dataclass(frozen=True)
class ApplyOutcome:
    message_id: str
    event_id: str
    ordering_key: int


class SessionWriter:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def apply_user_message_requested(
        self,
        *,
        session_id: str,
        content: str,
        idempotency_key: str,
        source: str,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        extra_payload: dict | None = None,
    ) -> ApplyOutcome:
        if not session_id:
            raise ValueError("session_id required")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content required")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("idempotency_key required")

        idempotency_key = idempotency_key.strip()
        extra_payload = extra_payload or {}

        # Step 1: append pending (durable boundary).
        def _append_pending(conn) -> ApplyOutcome:
            def _row_to_outcome(row) -> ApplyOutcome | None:
                if not row:
                    return None
                raw_payload = row[2] or "{}"
                try:
                    payload = json.loads(raw_payload)
                except Exception:
                    payload = {}
                message_id = str(payload.get("message_id") or "").strip()
                ordering_key = int(row[3] or 0)
                status = str(row[1] or "")
                if message_id and status in {"applied", "pending"}:
                    return ApplyOutcome(message_id=message_id, event_id=str(row[0]), ordering_key=ordering_key)
                return None

            existing = conn.execute(
                """
                SELECT event_id, apply_status, payload_json, ordering_key
                FROM session_event_ledger
                WHERE session_id = ? AND idempotency_key = ?
                LIMIT 1
                """,
                (session_id, idempotency_key),
            ).fetchone()
            outcome = _row_to_outcome(existing)
            if outcome:
                return outcome

            row = conn.execute(
                """
                SELECT COALESCE(MAX(ordering_key), 0)
                FROM session_event_ledger
                WHERE session_id = ? AND ordering_key IS NOT NULL
                """,
                (session_id,),
            ).fetchone()
            next_ordering = int(row[0] if row and row[0] is not None else 0) + 1

            event_id = ulid()
            message_id = ulid()
            created_ms = now_ms()
            payload = {
                "message_id": message_id,
                "role": "user",
                "content": content,
                "content_hash": None,
                "created_at_ms": int(created_ms),
                **(extra_payload or {}),
            }
            try:
                conn.execute(
                    """
                    INSERT INTO session_event_ledger (
                      event_id, session_id, ordering_key, event_type, source,
                      idempotency_key, causation_id, correlation_id,
                      payload_json, created_at_ms, apply_status, applied_at_ms, apply_error_json
                    )
                    VALUES (?, ?, ?, 'user_message_requested', ?, ?, ?, ?, ?, ?, 'pending', NULL, NULL)
                    """,
                    (
                        event_id,
                        session_id,
                        int(next_ordering),
                        source,
                        idempotency_key,
                        causation_id,
                        correlation_id,
                        json.dumps(payload, ensure_ascii=False),
                        int(created_ms),
                    ),
                )
            except sqlite3.IntegrityError:
                # Another concurrent caller inserted the idempotency key first.
                existing2 = conn.execute(
                    """
                    SELECT event_id, apply_status, payload_json, ordering_key
                    FROM session_event_ledger
                    WHERE session_id = ? AND idempotency_key = ?
                    LIMIT 1
                    """,
                    (session_id, idempotency_key),
                ).fetchone()
                outcome2 = _row_to_outcome(existing2)
                if outcome2:
                    return outcome2
                raise

            return ApplyOutcome(message_id=message_id, event_id=event_id, ordering_key=next_ordering)

        outcome = self._writer.submit(_append_pending, timeout=10.0)

        _maybe_trigger_failpoint(FAILPOINT_AFTER_LEDGER_APPEND)

        # Step 2: projection (durable boundary).
        def _apply_projection(conn) -> None:
            row = conn.execute(
                "SELECT payload_json FROM session_event_ledger WHERE event_id = ?",
                (outcome.event_id,),
            ).fetchone()
            raw_payload = row[0] if row else "{}"
            try:
                payload = json.loads(raw_payload or "{}")
            except Exception:
                payload = {}
            created_ms = int(payload.get("created_at_ms") or now_ms())
            created_at = from_epoch_ms(created_ms)
            msg_content = str(payload.get("content") or "")

            conn.execute(
                """
                INSERT OR IGNORE INTO chat_messages
                (message_id, session_id, role, content, metadata, created_at, created_at_ms)
                VALUES (?, ?, 'user', ?, ?, ?, ?)
                """,
                (
                    outcome.message_id,
                    session_id,
                    msg_content,
                    json.dumps({"idempotency_key": idempotency_key}, ensure_ascii=False),
                    created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    int(created_ms),
                ),
            )
            conn.execute(
                """
                UPDATE chat_sessions
                SET updated_at = ?,
                    updated_at_ms = CASE
                      WHEN updated_at_ms IS NULL OR ? > updated_at_ms THEN ?
                      ELSE updated_at_ms
                    END
                WHERE session_id = ?
                """,
                (
                    created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    int(created_ms),
                    int(created_ms),
                    session_id,
                ),
            )

        self._writer.submit(_apply_projection, timeout=10.0)

        _maybe_trigger_failpoint(FAILPOINT_AFTER_PROJECTION)

        # Step 3: mark applied (durable boundary).
        def _mark_applied(conn) -> None:
            conn.execute(
                """
                UPDATE session_event_ledger
                SET apply_status = 'applied',
                    applied_at_ms = ?,
                    apply_error_json = NULL
                WHERE event_id = ?
                """,
                (int(now_ms()), outcome.event_id),
            )

        self._writer.submit(_mark_applied, timeout=10.0)

        return outcome

    def apply_system_message_requested(
        self,
        *,
        session_id: str,
        content: str,
        idempotency_key: str,
        source: str,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        extra_payload: dict | None = None,
    ) -> ApplyOutcome:
        if not session_id:
            raise ValueError("session_id required")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content required")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("idempotency_key required")

        idempotency_key = idempotency_key.strip()
        extra_payload = extra_payload or {}

        def _append_pending(conn) -> ApplyOutcome:
            def _row_to_outcome(row) -> ApplyOutcome | None:
                if not row:
                    return None
                raw_payload = row[2] or "{}"
                try:
                    payload = json.loads(raw_payload)
                except Exception:
                    payload = {}
                message_id = str(payload.get("message_id") or "").strip()
                ordering_key = int(row[3] or 0)
                status = str(row[1] or "")
                if message_id and status in {"applied", "pending"}:
                    return ApplyOutcome(message_id=message_id, event_id=str(row[0]), ordering_key=ordering_key)
                return None

            existing = conn.execute(
                """
                SELECT event_id, apply_status, payload_json, ordering_key
                FROM session_event_ledger
                WHERE session_id = ? AND idempotency_key = ?
                LIMIT 1
                """,
                (session_id, idempotency_key),
            ).fetchone()
            outcome = _row_to_outcome(existing)
            if outcome:
                return outcome

            row = conn.execute(
                """
                SELECT COALESCE(MAX(ordering_key), 0)
                FROM session_event_ledger
                WHERE session_id = ? AND ordering_key IS NOT NULL
                """,
                (session_id,),
            ).fetchone()
            next_ordering = int(row[0] if row and row[0] is not None else 0) + 1

            event_id = ulid()
            message_id = ulid()
            created_ms = now_ms()
            payload = {
                "message_id": message_id,
                "role": "system",
                "content": content,
                "created_at_ms": int(created_ms),
                **(extra_payload or {}),
            }
            try:
                conn.execute(
                    """
                    INSERT INTO session_event_ledger (
                      event_id, session_id, ordering_key, event_type, source,
                      idempotency_key, causation_id, correlation_id,
                      payload_json, created_at_ms, apply_status, applied_at_ms, apply_error_json
                    )
                    VALUES (?, ?, ?, 'system_message_requested', ?, ?, ?, ?, ?, ?, 'pending', NULL, NULL)
                    """,
                    (
                        event_id,
                        session_id,
                        int(next_ordering),
                        source,
                        idempotency_key,
                        causation_id,
                        correlation_id,
                        json.dumps(payload, ensure_ascii=False),
                        int(created_ms),
                    ),
                )
            except sqlite3.IntegrityError:
                existing2 = conn.execute(
                    """
                    SELECT event_id, apply_status, payload_json, ordering_key
                    FROM session_event_ledger
                    WHERE session_id = ? AND idempotency_key = ?
                    LIMIT 1
                    """,
                    (session_id, idempotency_key),
                ).fetchone()
                outcome2 = _row_to_outcome(existing2)
                if outcome2:
                    return outcome2
                raise

            return ApplyOutcome(message_id=message_id, event_id=event_id, ordering_key=next_ordering)

        outcome = self._writer.submit(_append_pending, timeout=10.0)

        def _apply_projection(conn) -> None:
            row = conn.execute(
                "SELECT payload_json FROM session_event_ledger WHERE event_id = ?",
                (outcome.event_id,),
            ).fetchone()
            raw_payload = row[0] if row else "{}"
            try:
                payload = json.loads(raw_payload or "{}")
            except Exception:
                payload = {}
            created_ms = int(payload.get("created_at_ms") or now_ms())
            created_at = from_epoch_ms(created_ms)
            msg_content = str(payload.get("content") or "")

            conn.execute(
                """
                INSERT OR IGNORE INTO chat_messages
                (message_id, session_id, role, content, metadata, created_at, created_at_ms)
                VALUES (?, ?, 'system', ?, ?, ?, ?)
                """,
                (
                    outcome.message_id,
                    session_id,
                    msg_content,
                    json.dumps({"idempotency_key": idempotency_key, **(extra_payload or {})}, ensure_ascii=False),
                    created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    int(created_ms),
                ),
            )
            conn.execute(
                """
                UPDATE chat_sessions
                SET updated_at = ?,
                    updated_at_ms = CASE
                      WHEN updated_at_ms IS NULL OR ? > updated_at_ms THEN ?
                      ELSE updated_at_ms
                    END
                WHERE session_id = ?
                """,
                (
                    created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    int(created_ms),
                    int(created_ms),
                    session_id,
                ),
            )

        self._writer.submit(_apply_projection, timeout=10.0)

        def _mark_applied(conn) -> None:
            conn.execute(
                """
                UPDATE session_event_ledger
                SET apply_status = 'applied',
                    applied_at_ms = ?,
                    apply_error_json = NULL
                WHERE event_id = ?
                """,
                (int(now_ms()), outcome.event_id),
            )

        self._writer.submit(_mark_applied, timeout=10.0)
        return outcome

    def recover_pending_for_session(self, session_id: str, limit: int = 1000) -> int:
        if not session_id:
            return 0

        def _recover(conn) -> int:
            rows = conn.execute(
                """
                SELECT event_id, ordering_key, payload_json
                FROM session_event_ledger
                WHERE session_id = ? AND apply_status = 'pending'
                ORDER BY ordering_key ASC
                LIMIT ?
                """,
                (session_id, int(max(1, min(limit, 5000)))),
            ).fetchall()
            applied = 0
            for event_id, ordering_key, payload_json in rows:
                try:
                    payload = json.loads(payload_json or "{}")
                except Exception:
                    payload = {}
                message_id = str(payload.get("message_id") or "").strip()
                content = str(payload.get("content") or "")
                created_ms = int(payload.get("created_at_ms") or now_ms())
                created_at = from_epoch_ms(created_ms)

                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO chat_messages
                        (message_id, session_id, role, content, metadata, created_at, created_at_ms)
                        VALUES (?, ?, 'user', ?, ?, ?, ?)
                        """,
                        (
                            message_id or ulid(),
                            session_id,
                            content,
                            json.dumps({"recovered_from_event_id": str(event_id)}, ensure_ascii=False),
                            created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            int(created_ms),
                        ),
                    )
                    conn.execute(
                        """
                        UPDATE chat_sessions
                        SET updated_at = ?,
                            updated_at_ms = CASE
                              WHEN updated_at_ms IS NULL OR ? > updated_at_ms THEN ?
                              ELSE updated_at_ms
                            END
                        WHERE session_id = ?
                        """,
                        (
                            created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            int(created_ms),
                            int(created_ms),
                            session_id,
                        ),
                    )
                    conn.execute(
                        """
                        UPDATE session_event_ledger
                        SET apply_status = 'applied',
                            applied_at_ms = ?,
                            apply_error_json = NULL
                        WHERE event_id = ?
                        """,
                        (int(now_ms()), str(event_id)),
                    )
                    applied += 1
                except Exception as exc:
                    conn.execute(
                        """
                        UPDATE session_event_ledger
                        SET apply_status = 'failed',
                            apply_error_json = ?,
                            applied_at_ms = NULL
                        WHERE event_id = ?
                        """,
                        (json.dumps({"error": str(exc)}, ensure_ascii=False), str(event_id)),
                    )
                    break  # Stop to avoid continuing on uncertain ordering.
            return applied

        return int(self._writer.submit(_recover, timeout=30.0) or 0)
