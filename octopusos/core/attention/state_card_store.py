from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from octopusos.core.attention.models import CardSeverity, CardStatus, StateCard
from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid


@dataclass(frozen=True)
class UpsertResult:
    card: StateCard
    is_new: bool


class StateCardStore:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def upsert_open_card(
        self,
        *,
        scope_type: str,
        scope_id: str,
        card_type: str,
        severity: CardSeverity,
        title: str,
        summary: str,
        merge_key: str,
        event_id: str,
        event_created_at_ms: int,
        metadata_json: str,
        cooldown_until_ms: Optional[int],
    ) -> UpsertResult:
        def _op(conn: sqlite3.Connection) -> UpsertResult:
            row = conn.execute(
                """
                SELECT card_id, scope_type, scope_id, card_type, severity, status, title, summary,
                       first_seen_ms, last_seen_ms, last_event_id, merge_key, cooldown_until_ms, metadata_json,
                       resolution_status, resolution_reason, resolved_at_ms, resolved_by, resolution_note, linked_task_id
                FROM state_cards
                WHERE merge_key = ? AND status = 'open'
                LIMIT 1
                """,
                (merge_key,),
            ).fetchone()
            if row:
                card_id = str(row[0])
                existing_sev = str(row[4])
                # Keep the highest severity.
                merged_sev = severity if severity != existing_sev else existing_sev
                if merged_sev not in {"info", "warn", "high", "critical"}:
                    merged_sev = severity
                conn.execute(
                    """
                    UPDATE state_cards
                    SET severity = ?,
                        title = ?,
                        summary = ?,
                        last_seen_ms = ?,
                        last_event_id = ?,
                        cooldown_until_ms = ?,
                        metadata_json = ?
                    WHERE card_id = ?
                    """,
                    (
                        merged_sev,
                        title,
                        summary,
                        int(max(int(row[9]), int(event_created_at_ms))),
                        str(event_id),
                        cooldown_until_ms,
                        metadata_json,
                        card_id,
                    ),
                )
                updated = conn.execute(
                    """
                    SELECT card_id, scope_type, scope_id, card_type, severity, status, title, summary,
                           first_seen_ms, last_seen_ms, last_event_id, merge_key, cooldown_until_ms, metadata_json,
                           resolution_status, resolution_reason, resolved_at_ms, resolved_by, resolution_note, linked_task_id
                    FROM state_cards
                    WHERE card_id = ?
                    """,
                    (card_id,),
                ).fetchone()
                return UpsertResult(card=_row_to_card(updated), is_new=False)

            card_id = ulid()
            first_seen = int(event_created_at_ms or now_ms())
            conn.execute(
                """
                INSERT INTO state_cards (
                  card_id, scope_type, scope_id, card_type, severity, status,
                  title, summary,
                  first_seen_ms, last_seen_ms, last_event_id,
                  merge_key, cooldown_until_ms, metadata_json,
                  resolution_status, resolution_reason, resolved_at_ms, resolved_by, resolution_note, linked_task_id
                )
                VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, 'open', NULL, NULL, NULL, NULL, NULL)
                """,
                (
                    card_id,
                    scope_type,
                    scope_id,
                    card_type,
                    severity,
                    title,
                    summary,
                    first_seen,
                    first_seen,
                    str(event_id),
                    merge_key,
                    cooldown_until_ms,
                    metadata_json,
                ),
            )
            created = conn.execute(
                """
                SELECT card_id, scope_type, scope_id, card_type, severity, status, title, summary,
                       first_seen_ms, last_seen_ms, last_event_id, merge_key, cooldown_until_ms, metadata_json,
                       resolution_status, resolution_reason, resolved_at_ms, resolved_by, resolution_note, linked_task_id
                FROM state_cards
                WHERE card_id = ?
                """,
                (card_id,),
            ).fetchone()
            return UpsertResult(card=_row_to_card(created), is_new=True)

        try:
            return self._writer.submit(_op, timeout=10.0)
        except sqlite3.IntegrityError:
            # Concurrent insert against ux_state_cards_open_merge_key; re-run as update.
            return self._writer.submit(_op, timeout=10.0)

    def link_event(self, *, card_id: str, event_id: str, added_at_ms: Optional[int] = None) -> None:
        added = int(added_at_ms or now_ms())

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT OR IGNORE INTO state_card_events (card_id, event_id, added_at_ms)
                VALUES (?, ?, ?)
                """,
                (str(card_id), str(event_id), int(added)),
            )

        self._writer.submit(_op, timeout=10.0)

    def list_open_cards(self, *, scope_type: Optional[str] = None, scope_id: Optional[str] = None, limit: int = 50) -> list[StateCard]:
        def _op(conn: sqlite3.Connection) -> list[StateCard]:
            where = "WHERE status = 'open'"
            params: list[object] = []
            if scope_type:
                where += " AND scope_type = ?"
                params.append(scope_type)
            if scope_id:
                where += " AND scope_id = ?"
                params.append(scope_id)
            params.append(int(max(1, min(limit, 500))))
            rows = conn.execute(
                f"""
                SELECT card_id, scope_type, scope_id, card_type, severity, status, title, summary,
                       first_seen_ms, last_seen_ms, last_event_id, merge_key, cooldown_until_ms, metadata_json,
                       resolution_status, resolution_reason, resolved_at_ms, resolved_by, resolution_note, linked_task_id
                FROM state_cards
                {where}
                ORDER BY last_seen_ms DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            return [_row_to_card(r) for r in rows or []]

        return self._writer.submit(_op, timeout=10.0) or []

    def close_card(self, *, card_id: str) -> None:
        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                "UPDATE state_cards SET status = 'closed' WHERE card_id = ?",
                (str(card_id),),
            )

        self._writer.submit(_op, timeout=10.0)

    def update_resolution(
        self,
        *,
        card_id: str,
        resolution_status: str,
        resolved_by: str,
        resolved_at_ms: int,
        resolution_reason: str | None = None,
        resolution_note: str | None = None,
        linked_task_id: str | None = None,
        defer_until_ms: int | None = None,
    ) -> None:
        """Update Phase 4 closure fields. Keeps status=open unless resolved/dismissed."""
        # For "deferred" we keep status=open but extend cooldown_until_ms.
        status = None
        if resolution_status in {"resolved", "dismissed"}:
            status = "closed"

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE state_cards
                SET status = COALESCE(?, status),
                    resolution_status = ?,
                    resolution_reason = ?,
                    resolved_at_ms = ?,
                    resolved_by = ?,
                    resolution_note = ?,
                    linked_task_id = COALESCE(?, linked_task_id),
                    cooldown_until_ms = COALESCE(?, cooldown_until_ms),
                    last_seen_ms = CASE
                      WHEN last_seen_ms IS NULL OR ? > last_seen_ms THEN ?
                      ELSE last_seen_ms
                    END
                WHERE card_id = ?
                """,
                (
                    status,
                    str(resolution_status),
                    resolution_reason,
                    int(resolved_at_ms),
                    str(resolved_by),
                    resolution_note,
                    linked_task_id,
                    int(defer_until_ms) if defer_until_ms is not None else None,
                    int(resolved_at_ms),
                    int(resolved_at_ms),
                    str(card_id),
                ),
            )

        self._writer.submit(_op, timeout=10.0)


def _row_to_card(row) -> StateCard:
    return StateCard(
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
        resolution_status=str(row[14] or "open"),  # type: ignore[arg-type]
        resolution_reason=str(row[15]) if row[15] is not None else None,
        resolved_at_ms=int(row[16]) if row[16] is not None else None,
        resolved_by=str(row[17]) if row[17] is not None else None,
        resolution_note=str(row[18]) if row[18] is not None else None,
        linked_task_id=str(row[19]) if row[19] is not None else None,
    )
