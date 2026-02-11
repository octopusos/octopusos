from __future__ import annotations

import sqlite3
from typing import Iterable

from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.store.timestamp_utils import now_ms


class EmailSnoozeStore:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def upsert(self, *, instance_id: str, message_id: str, until_ms: int) -> None:
        until = int(max(0, int(until_ms)))

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT INTO email_snoozes (instance_id, message_id, until_ms)
                VALUES (?, ?, ?)
                ON CONFLICT(instance_id, message_id) DO UPDATE SET until_ms = excluded.until_ms
                """,
                (str(instance_id), str(message_id), until),
            )

        self._writer.submit(_op, timeout=10.0)

    def snoozed_message_ids(self, *, instance_id: str, message_ids: Iterable[str], now_ms_value: int | None = None) -> set[str]:
        ids = [str(x) for x in message_ids if str(x).strip()]
        if not ids:
            return set()
        nowv = int(now_ms_value or now_ms())

        def _op(conn: sqlite3.Connection) -> set[str]:
            rows = conn.execute(
                f"""
                SELECT message_id
                FROM email_snoozes
                WHERE instance_id = ?
                  AND until_ms > ?
                  AND message_id IN ({",".join(["?"] * len(ids))})
                """,
                tuple([str(instance_id), int(nowv)] + ids),
            ).fetchall()
            return {str(r[0]) for r in (rows or []) if r and r[0] is not None}

        return set(self._writer.submit(_op, timeout=10.0) or set())

    def cleanup_expired(self, *, now_ms_value: int | None = None) -> int:
        nowv = int(now_ms_value or now_ms())

        def _op(conn: sqlite3.Connection) -> int:
            cur = conn.execute(
                "DELETE FROM email_snoozes WHERE until_ms <= ?",
                (int(nowv),),
            )
            return int(cur.rowcount or 0)

        return int(self._writer.submit(_op, timeout=10.0) or 0)

