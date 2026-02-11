"""Session event ledger (Phase 1).

Dual-write contract (Phase 1):
- legacy/dual_write: ledger is best-effort "observed" append; failures must not break chat.
- ledger_primary: writer will use strict pending/applied semantics (added in P1-T1.5+).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from octopusos.core.db import registry_db
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    session_id: str
    ordering_key: Optional[int]
    event_type: str
    source: str
    idempotency_key: Optional[str]
    causation_id: Optional[str]
    correlation_id: Optional[str]
    payload_json: str
    created_at_ms: int
    apply_status: str
    applied_at_ms: Optional[int]
    apply_error_json: Optional[str]


def append_observed_event(
    *,
    session_id: str,
    event_type: str,
    source: str,
    payload: dict,
    idempotency_key: str | None = None,
    causation_id: str | None = None,
    correlation_id: str | None = None,
    created_at_ms: int | None = None,
) -> None:
    event_id = ulid()
    created = int(created_at_ms) if created_at_ms is not None else now_ms()
    try:
        conn = registry_db.get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO session_event_ledger (
              event_id, session_id, ordering_key, event_type, source,
              idempotency_key, causation_id, correlation_id,
              payload_json, created_at_ms, apply_status, applied_at_ms, apply_error_json
            )
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, 'observed', NULL, NULL)
            """,
            (
                event_id,
                session_id,
                event_type,
                source,
                (idempotency_key or None),
                (causation_id or None),
                (correlation_id or None),
                json.dumps(payload or {}, ensure_ascii=False),
                int(created),
            ),
        )
        conn.commit()
    except Exception as exc:
        # Phase 1 best-effort: do not break chat if ledger fails.
        logger.warning(
            "Ledger append_observed_event failed (session=%s type=%s source=%s): %s",
            session_id,
            event_type,
            source,
            exc,
        )


def append_pending_event(
    *,
    event_id: str,
    session_id: str,
    ordering_key: int,
    event_type: str,
    source: str,
    payload: dict,
    idempotency_key: str | None,
    causation_id: str | None,
    correlation_id: str | None,
) -> None:
    created = now_ms()
    conn = registry_db.get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO session_event_ledger (
          event_id, session_id, ordering_key, event_type, source,
          idempotency_key, causation_id, correlation_id,
          payload_json, created_at_ms, apply_status, applied_at_ms, apply_error_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, NULL)
        """,
        (
            event_id,
            session_id,
            int(ordering_key),
            event_type,
            source,
            (idempotency_key or None),
            (causation_id or None),
            (correlation_id or None),
            json.dumps(payload or {}, ensure_ascii=False),
            int(created),
        ),
    )
    conn.commit()


def mark_applied(*, event_id: str, applied_at_ms: int) -> None:
    conn = registry_db.get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE session_event_ledger
        SET apply_status = 'applied',
            applied_at_ms = ?,
            apply_error_json = NULL
        WHERE event_id = ?
        """,
        (int(applied_at_ms), event_id),
    )
    conn.commit()


def mark_failed(*, event_id: str, error: dict) -> None:
    conn = registry_db.get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE session_event_ledger
        SET apply_status = 'failed',
            apply_error_json = ?,
            applied_at_ms = NULL
        WHERE event_id = ?
        """,
        (json.dumps(error or {}, ensure_ascii=False), event_id),
    )
    conn.commit()


def get_event_by_idempotency_key(*, session_id: str, idempotency_key: str) -> LedgerEvent | None:
    if not idempotency_key:
        return None
    conn = registry_db.get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        """
        SELECT
          event_id, session_id, ordering_key, event_type, source,
          idempotency_key, causation_id, correlation_id,
          payload_json, created_at_ms, apply_status, applied_at_ms, apply_error_json
        FROM session_event_ledger
        WHERE session_id = ? AND idempotency_key = ?
        LIMIT 1
        """,
        (session_id, idempotency_key),
    ).fetchone()
    if not row:
        return None
    row_dict = {k: row[k] for k in row.keys()} if hasattr(row, "keys") else dict(row)
    return LedgerEvent(
        event_id=str(row_dict["event_id"]),
        session_id=str(row_dict["session_id"]),
        ordering_key=(int(row_dict["ordering_key"]) if row_dict.get("ordering_key") is not None else None),
        event_type=str(row_dict["event_type"]),
        source=str(row_dict["source"]),
        idempotency_key=(str(row_dict["idempotency_key"]) if row_dict.get("idempotency_key") else None),
        causation_id=(str(row_dict["causation_id"]) if row_dict.get("causation_id") else None),
        correlation_id=(str(row_dict["correlation_id"]) if row_dict.get("correlation_id") else None),
        payload_json=str(row_dict["payload_json"] or "{}"),
        created_at_ms=int(row_dict["created_at_ms"]),
        apply_status=str(row_dict["apply_status"]),
        applied_at_ms=(int(row_dict["applied_at_ms"]) if row_dict.get("applied_at_ms") is not None else None),
        apply_error_json=(str(row_dict["apply_error_json"]) if row_dict.get("apply_error_json") else None),
    )


def list_pending(*, session_id: str, limit: int = 1000) -> list[LedgerEvent]:
    conn = registry_db.get_db()
    cursor = conn.cursor()
    rows = cursor.execute(
        """
        SELECT
          event_id, session_id, ordering_key, event_type, source,
          idempotency_key, causation_id, correlation_id,
          payload_json, created_at_ms, apply_status, applied_at_ms, apply_error_json
        FROM session_event_ledger
        WHERE session_id = ? AND apply_status = 'pending'
        ORDER BY ordering_key ASC
        LIMIT ?
        """,
        (session_id, int(max(1, min(limit, 5000)))),
    ).fetchall()
    events: list[LedgerEvent] = []
    for row in rows:
        row_dict = {k: row[k] for k in row.keys()} if hasattr(row, "keys") else dict(row)
        events.append(
            LedgerEvent(
                event_id=str(row_dict["event_id"]),
                session_id=str(row_dict["session_id"]),
                ordering_key=(int(row_dict["ordering_key"]) if row_dict.get("ordering_key") is not None else None),
                event_type=str(row_dict["event_type"]),
                source=str(row_dict["source"]),
                idempotency_key=(str(row_dict["idempotency_key"]) if row_dict.get("idempotency_key") else None),
                causation_id=(str(row_dict["causation_id"]) if row_dict.get("causation_id") else None),
                correlation_id=(str(row_dict["correlation_id"]) if row_dict.get("correlation_id") else None),
                payload_json=str(row_dict["payload_json"] or "{}"),
                created_at_ms=int(row_dict["created_at_ms"]),
                apply_status=str(row_dict["apply_status"]),
                applied_at_ms=(int(row_dict["applied_at_ms"]) if row_dict.get("applied_at_ms") is not None else None),
                apply_error_json=(str(row_dict["apply_error_json"]) if row_dict.get("apply_error_json") else None),
            )
        )
    return events


def list_events(
    *,
    session_id: str,
    limit: int = 200,
    after_created_at_ms: int | None = None,
) -> list[LedgerEvent]:
    conn = registry_db.get_db()
    cursor = conn.cursor()
    params: list[Any] = [session_id]
    sql = """
        SELECT
          event_id, session_id, ordering_key, event_type, source,
          idempotency_key, causation_id, correlation_id,
          payload_json, created_at_ms, apply_status, applied_at_ms, apply_error_json
        FROM session_event_ledger
        WHERE session_id = ?
    """
    if after_created_at_ms is not None:
        sql += " AND created_at_ms > ?"
        params.append(int(after_created_at_ms))
    sql += " ORDER BY created_at_ms ASC LIMIT ?"
    params.append(int(max(1, min(limit, 5000))))
    rows = cursor.execute(sql, params).fetchall()
    events: list[LedgerEvent] = []
    for row in rows:
        row_dict = {k: row[k] for k in row.keys()} if hasattr(row, "keys") else dict(row)
        events.append(
            LedgerEvent(
                event_id=str(row_dict["event_id"]),
                session_id=str(row_dict["session_id"]),
                ordering_key=(int(row_dict["ordering_key"]) if row_dict.get("ordering_key") is not None else None),
                event_type=str(row_dict["event_type"]),
                source=str(row_dict["source"]),
                idempotency_key=(str(row_dict["idempotency_key"]) if row_dict.get("idempotency_key") else None),
                causation_id=(str(row_dict["causation_id"]) if row_dict.get("causation_id") else None),
                correlation_id=(str(row_dict["correlation_id"]) if row_dict.get("correlation_id") else None),
                payload_json=str(row_dict["payload_json"] or "{}"),
                created_at_ms=int(row_dict["created_at_ms"]),
                apply_status=str(row_dict["apply_status"]),
                applied_at_ms=(int(row_dict["applied_at_ms"]) if row_dict.get("applied_at_ms") is not None else None),
                apply_error_json=(str(row_dict["apply_error_json"]) if row_dict.get("apply_error_json") else None),
            )
        )
    return events


def list_events_global(
    *,
    after_created_at_ms: int | None = None,
    after_event_id: str | None = None,
    limit: int = 200,
) -> list[LedgerEvent]:
    """List ledger events globally (ordered, cursorable).

    Cursor semantics:
    - If after_created_at_ms is provided, fetch events strictly after that timestamp.
    - If after_event_id is also provided, treat (created_at_ms, event_id) as a stable cursor.
    """
    conn = registry_db.get_db()
    cursor = conn.cursor()
    params: list[Any] = []
    sql = """
        SELECT
          event_id, session_id, ordering_key, event_type, source,
          idempotency_key, causation_id, correlation_id,
          payload_json, created_at_ms, apply_status, applied_at_ms, apply_error_json
        FROM session_event_ledger
        WHERE 1 = 1
    """
    if after_created_at_ms is not None:
        if after_event_id:
            sql += " AND (created_at_ms > ? OR (created_at_ms = ? AND event_id > ?))"
            params.extend([int(after_created_at_ms), int(after_created_at_ms), str(after_event_id)])
        else:
            sql += " AND created_at_ms > ?"
            params.append(int(after_created_at_ms))

    sql += " ORDER BY created_at_ms ASC, event_id ASC LIMIT ?"
    params.append(int(max(1, min(limit, 5000))))

    rows = cursor.execute(sql, params).fetchall()
    events: list[LedgerEvent] = []
    for row in rows:
        row_dict = {k: row[k] for k in row.keys()} if hasattr(row, "keys") else dict(row)
        events.append(
            LedgerEvent(
                event_id=str(row_dict["event_id"]),
                session_id=str(row_dict["session_id"]),
                ordering_key=(int(row_dict["ordering_key"]) if row_dict.get("ordering_key") is not None else None),
                event_type=str(row_dict["event_type"]),
                source=str(row_dict["source"]),
                idempotency_key=(str(row_dict["idempotency_key"]) if row_dict.get("idempotency_key") else None),
                causation_id=(str(row_dict["causation_id"]) if row_dict.get("causation_id") else None),
                correlation_id=(str(row_dict["correlation_id"]) if row_dict.get("correlation_id") else None),
                payload_json=str(row_dict["payload_json"] or "{}"),
                created_at_ms=int(row_dict["created_at_ms"]),
                apply_status=str(row_dict["apply_status"]),
                applied_at_ms=(int(row_dict["applied_at_ms"]) if row_dict.get("applied_at_ms") is not None else None),
                apply_error_json=(str(row_dict["apply_error_json"]) if row_dict.get("apply_error_json") else None),
            )
        )
    return events
