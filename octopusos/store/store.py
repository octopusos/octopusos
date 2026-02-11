"""Simple SQLite store wrapper used in tests and lightweight tooling."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence


class Store:
    """Lightweight SQLite wrapper."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

    def execute_sql(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        cursor = self._conn.cursor()
        cursor.execute(sql, params or [])
        self._conn.commit()

    def fetchone(self, sql: str, params: Optional[Sequence[Any]] = None):
        cursor = self._conn.cursor()
        cursor.execute(sql, params or [])
        return cursor.fetchone()

    def fetchall(self, sql: str, params: Optional[Sequence[Any]] = None):
        cursor = self._conn.cursor()
        cursor.execute(sql, params or [])
        return cursor.fetchall()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
