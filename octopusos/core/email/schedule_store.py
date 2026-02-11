from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter


class EmailDigestRunStore:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def already_ran(self, *, instance_id: str, run_key: str) -> bool:
        def _op(conn: sqlite3.Connection) -> bool:
            row = conn.execute(
                "SELECT 1 FROM email_digest_runs WHERE instance_id=? AND run_key=?",
                (str(instance_id), str(run_key)),
            ).fetchone()
            return bool(row)

        return bool(self._writer.submit(_op, timeout=10.0))

    def mark_ran(self, *, instance_id: str, run_key: str, last_run_ms: int) -> None:
        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT INTO email_digest_runs (instance_id, run_key, last_run_ms)
                VALUES (?, ?, ?)
                ON CONFLICT(instance_id, run_key) DO UPDATE SET last_run_ms = excluded.last_run_ms
                """,
                (str(instance_id), str(run_key), int(last_run_ms)),
            )

        self._writer.submit(_op, timeout=10.0)

