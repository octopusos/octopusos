from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid


@dataclass(frozen=True)
class EmailInstance:
    instance_id: str
    name: str
    provider_type: str
    config_json: str
    secret_ref: str
    created_at_ms: int
    updated_at_ms: int
    last_test_ok: bool
    last_test_at_ms: int | None
    last_test_error: str | None


def _row_to_instance(row) -> EmailInstance:
    return EmailInstance(
        instance_id=str(row[0]),
        name=str(row[1]),
        provider_type=str(row[2]),
        config_json=str(row[3] or "{}"),
        secret_ref=str(row[4] or ""),
        created_at_ms=int(row[5]),
        updated_at_ms=int(row[6]),
        last_test_ok=bool(int(row[7] or 0)),
        last_test_at_ms=int(row[8]) if row[8] is not None else None,
        last_test_error=str(row[9]) if row[9] is not None else None,
    )


class EmailInstanceStore:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def list(self) -> list[EmailInstance]:
        def _op(conn: sqlite3.Connection) -> list[EmailInstance]:
            rows = conn.execute(
                """
                SELECT instance_id, name, provider_type, config_json, secret_ref,
                       created_at_ms, updated_at_ms, last_test_ok, last_test_at_ms, last_test_error
                FROM email_instances
                ORDER BY updated_at_ms DESC
                LIMIT 200
                """
            ).fetchall()
            return [_row_to_instance(r) for r in rows or []]

        return self._writer.submit(_op, timeout=10.0) or []

    def get(self, *, instance_id: str) -> Optional[EmailInstance]:
        def _op(conn: sqlite3.Connection) -> Optional[EmailInstance]:
            row = conn.execute(
                """
                SELECT instance_id, name, provider_type, config_json, secret_ref,
                       created_at_ms, updated_at_ms, last_test_ok, last_test_at_ms, last_test_error
                FROM email_instances
                WHERE instance_id = ?
                """,
                (str(instance_id),),
            ).fetchone()
            return _row_to_instance(row) if row else None

        return self._writer.submit(_op, timeout=10.0)

    def create(
        self,
        *,
        name: str,
        provider_type: str,
        config_obj: dict,
        secret_ref: str,
    ) -> str:
        iid = ulid()
        ts = now_ms()
        cfg = json.dumps(config_obj or {}, ensure_ascii=False)

        def _op(conn: sqlite3.Connection) -> str:
            conn.execute(
                """
                INSERT INTO email_instances (
                  instance_id, name, provider_type, config_json, secret_ref,
                  created_at_ms, updated_at_ms, last_test_ok, last_test_at_ms, last_test_error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL)
                """,
                (iid, str(name), str(provider_type), cfg, str(secret_ref or ""), int(ts), int(ts)),
            )
            return iid

        return self._writer.submit(_op, timeout=10.0)

    def update_test_result(self, *, instance_id: str, ok: bool, error: str | None) -> None:
        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE email_instances
                SET last_test_ok = ?,
                    last_test_at_ms = ?,
                    last_test_error = ?,
                    updated_at_ms = ?
                WHERE instance_id = ?
                """,
                (1 if ok else 0, int(ts), error, int(ts), str(instance_id)),
            )

        self._writer.submit(_op, timeout=10.0)

    def update_config(self, *, instance_id: str, patch: dict) -> None:
        """Merge patch into config_json without overwriting unrelated keys.

        Rules:
        - dict values are merged shallowly
        - list values are treated as sets (deduped, lowercased for sender-like keys)
        - other scalar values overwrite
        """

        def _normalize_list(key: str, items: list) -> list[str]:
            out: list[str] = []
            for x in items:
                s = str(x).strip()
                if not s:
                    continue
                if key in {"allow_senders", "block_senders", "block_domains"}:
                    s = s.lower()
                out.append(s)
            # Dedup while preserving order.
            seen: set[str] = set()
            deduped: list[str] = []
            for s in out:
                if s in seen:
                    continue
                seen.add(s)
                deduped.append(s)
            return deduped

        def _merge(base: dict, delta: dict) -> dict:
            merged = dict(base or {})
            for k, v in (delta or {}).items():
                if isinstance(v, dict) and isinstance(merged.get(k), dict):
                    merged[k] = {**merged.get(k, {}), **v}  # shallow merge
                elif isinstance(v, list) and isinstance(merged.get(k), list):
                    merged[k] = _normalize_list(str(k), list(merged.get(k, [])) + list(v))
                elif isinstance(v, list):
                    merged[k] = _normalize_list(str(k), list(v))
                else:
                    merged[k] = v
            return merged

        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            row = conn.execute(
                "SELECT config_json FROM email_instances WHERE instance_id = ?",
                (str(instance_id),),
            ).fetchone()
            if not row:
                return
            raw = str(row[0] or "{}")
            try:
                base = json.loads(raw)
                if not isinstance(base, dict):
                    base = {}
            except Exception:
                base = {}
            next_cfg = _merge(base, patch or {})
            next_json = json.dumps(next_cfg, ensure_ascii=False)
            conn.execute(
                """
                UPDATE email_instances
                SET config_json = ?, updated_at_ms = ?
                WHERE instance_id = ?
                """,
                (next_json, int(ts), str(instance_id)),
            )

        self._writer.submit(_op, timeout=10.0)

    def update_secret_ref(self, *, instance_id: str, secret_ref: str) -> None:
        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE email_instances
                SET secret_ref = ?, updated_at_ms = ?
                WHERE instance_id = ?
                """,
                (str(secret_ref or ""), int(ts), str(instance_id)),
            )

        self._writer.submit(_op, timeout=10.0)

    def append_list_key(self, *, instance_id: str, key: str, values: list[str]) -> None:
        """Append values to a list key in config_json (dedup + normalize)."""

        def _normalize_list(items: list) -> list[str]:
            out: list[str] = []
            for x in items:
                s = str(x).strip()
                if not s:
                    continue
                if key in {"allow_senders", "block_senders", "block_domains"}:
                    s = s.lower()
                out.append(s)
            seen: set[str] = set()
            deduped: list[str] = []
            for s in out:
                if s in seen:
                    continue
                seen.add(s)
                deduped.append(s)
            return deduped

        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            row = conn.execute(
                "SELECT config_json FROM email_instances WHERE instance_id = ?",
                (str(instance_id),),
            ).fetchone()
            if not row:
                return
            raw = str(row[0] or "{}")
            try:
                base = json.loads(raw)
                if not isinstance(base, dict):
                    base = {}
            except Exception:
                base = {}

            existing = base.get(key, [])
            merged = []
            if isinstance(existing, list):
                merged = list(existing) + list(values or [])
            else:
                merged = list(values or [])
            base[key] = _normalize_list(merged)
            next_json = json.dumps(base, ensure_ascii=False)
            conn.execute(
                "UPDATE email_instances SET config_json=?, updated_at_ms=? WHERE instance_id=?",
                (next_json, int(ts), str(instance_id)),
            )

        self._writer.submit(_op, timeout=10.0)

    def set_list_key(self, *, instance_id: str, key: str, values: list[str]) -> None:
        """Replace a list key in config_json with values (dedup + normalize)."""

        def _normalize_list(items: list) -> list[str]:
            out: list[str] = []
            for x in items:
                s = str(x).strip()
                if not s:
                    continue
                if key in {"allow_senders", "block_senders", "block_domains"}:
                    s = s.lower()
                out.append(s)
            seen: set[str] = set()
            deduped: list[str] = []
            for s in out:
                if s in seen:
                    continue
                seen.add(s)
                deduped.append(s)
            return deduped

        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            row = conn.execute(
                "SELECT config_json FROM email_instances WHERE instance_id = ?",
                (str(instance_id),),
            ).fetchone()
            if not row:
                return
            raw = str(row[0] or "{}")
            try:
                base = json.loads(raw)
                if not isinstance(base, dict):
                    base = {}
            except Exception:
                base = {}

            base[key] = _normalize_list(list(values or []))
            next_json = json.dumps(base, ensure_ascii=False)
            conn.execute(
                "UPDATE email_instances SET config_json=?, updated_at_ms=? WHERE instance_id=?",
                (next_json, int(ts), str(instance_id)),
            )

        self._writer.submit(_op, timeout=10.0)
