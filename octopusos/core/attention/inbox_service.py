from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from octopusos.core.attention.models import InboxItem, InboxStatus, InboxDeliveryType, ScopeType, StateCard
from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid


@dataclass(frozen=True)
class InboxListResult:
    items: list[InboxItem]
    unread_count: int


class InboxService:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def enqueue_from_card(
        self,
        *,
        card: StateCard,
        delivery_type: InboxDeliveryType = "inbox_only",
    ) -> Optional[str]:
        item_id = ulid()
        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> Optional[str]:
            try:
                conn.execute(
                    """
                    INSERT INTO inbox_items (
                      inbox_item_id, card_id, scope_type, scope_id,
                      delivery_type, status, created_at_ms, updated_at_ms
                    )
                    VALUES (?, ?, ?, ?, ?, 'unread', ?, ?)
                    """,
                    (
                        item_id,
                        card.card_id,
                        card.scope_type,
                        card.scope_id,
                        delivery_type,
                        int(ts),
                        int(ts),
                    ),
                )
                return item_id
            except sqlite3.IntegrityError:
                # Dedup by UNIQUE(card_id, delivery_type). Touch updated_at_ms to show freshness.
                conn.execute(
                    """
                    UPDATE inbox_items
                    SET updated_at_ms = ?
                    WHERE card_id = ? AND delivery_type = ?
                    """,
                    (int(ts), card.card_id, delivery_type),
                )
                row = conn.execute(
                    "SELECT inbox_item_id FROM inbox_items WHERE card_id = ? AND delivery_type = ? LIMIT 1",
                    (card.card_id, delivery_type),
                ).fetchone()
                return str(row[0]) if row else None

        return self._writer.submit(_op, timeout=10.0)

    def list_items(
        self,
        *,
        status: InboxStatus = "unread",
        limit: int = 50,
        scope_type: ScopeType | None = None,
        scope_id: str | None = None,
    ) -> InboxListResult:
        def _op(conn: sqlite3.Connection) -> InboxListResult:
            where = "WHERE status = ?"
            params: list[object] = [status]
            if scope_type:
                where += " AND scope_type = ?"
                params.append(scope_type)
            if scope_id:
                where += " AND scope_id = ?"
                params.append(scope_id)

            params_rows = params + [int(max(1, min(limit, 500)))]
            rows = conn.execute(
                f"""
                SELECT inbox_item_id, card_id, scope_type, scope_id, delivery_type, status, created_at_ms, updated_at_ms
                FROM inbox_items
                {where}
                ORDER BY updated_at_ms DESC
                LIMIT ?
                """,
                tuple(params_rows),
            ).fetchall()

            unread_row = conn.execute(
                "SELECT COUNT(*) FROM inbox_items WHERE status = 'unread'",
            ).fetchone()
            unread_count = int(unread_row[0] if unread_row else 0)

            items = [
                InboxItem(
                    inbox_item_id=str(r[0]),
                    card_id=str(r[1]),
                    scope_type=str(r[2]),  # type: ignore[arg-type]
                    scope_id=str(r[3]),
                    delivery_type=str(r[4]),  # type: ignore[arg-type]
                    status=str(r[5]),  # type: ignore[arg-type]
                    created_at_ms=int(r[6]),
                    updated_at_ms=int(r[7]),
                )
                for r in rows or []
            ]
            return InboxListResult(items=items, unread_count=unread_count)

        return self._writer.submit(_op, timeout=10.0)

    def mark_read(self, *, inbox_item_id: str) -> None:
        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE inbox_items
                SET status = 'read', updated_at_ms = ?
                WHERE inbox_item_id = ?
                """,
                (int(ts), str(inbox_item_id)),
            )

        self._writer.submit(_op, timeout=10.0)

    def archive_for_card(self, *, card_id: str) -> None:
        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE inbox_items
                SET status = 'archived', updated_at_ms = ?
                WHERE card_id = ?
                """,
                (int(ts), str(card_id)),
            )

        self._writer.submit(_op, timeout=10.0)

    def unread_count(self) -> int:
        def _op(conn: sqlite3.Connection) -> int:
            row = conn.execute(
                "SELECT COUNT(*) FROM inbox_items WHERE status = 'unread'",
            ).fetchone()
            return int(row[0] if row else 0)

        return int(self._writer.submit(_op, timeout=10.0) or 0)

    def has_delivery(self, *, card_id: str, delivery_type: InboxDeliveryType = "inbox_only") -> bool:
        def _op(conn: sqlite3.Connection) -> bool:
            row = conn.execute(
                """
                SELECT 1
                FROM inbox_items
                WHERE card_id = ? AND delivery_type = ?
                LIMIT 1
                """,
                (str(card_id), str(delivery_type)),
            ).fetchone()
            return bool(row)

        return bool(self._writer.submit(_op, timeout=10.0))
