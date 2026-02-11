"""Shared state and audit helpers for compat routers."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from octopusos.store import get_db_path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_connect() -> sqlite3.Connection:
    env_path = os.getenv("OCTOPUSOS_DB_PATH")
    db_path = Path(env_path) if env_path else get_db_path()
    if not db_path.exists():
        raise HTTPException(status_code=500, detail="Database not initialized")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS compat_entities (
            namespace TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            data_json TEXT NOT NULL,
            status TEXT,
            deleted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (namespace, entity_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS compat_state (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS compat_audit_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            actor TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            payload_json TEXT,
            result_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def audit_event(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    endpoint: str,
    actor: str,
    payload: Any,
    result: Any,
) -> None:
    ensure_schema(conn)
    payload_text = _json_dump(payload)
    payload_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
    conn.execute(
        """
        INSERT INTO compat_audit_events (
            event_type, endpoint, actor, payload_hash, payload_json, result_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            endpoint,
            actor,
            payload_hash,
            payload_text,
            _json_dump(result),
            now_iso(),
        ),
    )


def upsert_entity(
    conn: sqlite3.Connection,
    *,
    namespace: str,
    entity_id: str,
    data: Dict[str, Any],
    status: Optional[str] = None,
    deleted: int = 0,
) -> Dict[str, Any]:
    ensure_schema(conn)
    existing = conn.execute(
        "SELECT created_at FROM compat_entities WHERE namespace = ? AND entity_id = ?",
        (namespace, entity_id),
    ).fetchone()
    created_at = existing["created_at"] if existing else now_iso()
    updated_at = now_iso()
    conn.execute(
        """
        INSERT INTO compat_entities (
            namespace, entity_id, data_json, status, deleted, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(namespace, entity_id) DO UPDATE SET
            data_json = excluded.data_json,
            status = excluded.status,
            deleted = excluded.deleted,
            updated_at = excluded.updated_at
        """,
        (namespace, entity_id, _json_dump(data), status, int(deleted), created_at, updated_at),
    )
    conn.commit()
    return get_entity(conn, namespace=namespace, entity_id=entity_id) or {}


def get_entity(conn: sqlite3.Connection, *, namespace: str, entity_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema(conn)
    row = conn.execute(
        """
        SELECT entity_id, data_json, status, deleted, created_at, updated_at
        FROM compat_entities
        WHERE namespace = ? AND entity_id = ?
        """,
        (namespace, entity_id),
    ).fetchone()
    if not row:
        return None
    data = json.loads(row["data_json"])
    data["_entity_id"] = row["entity_id"]
    data["_status"] = row["status"]
    data["_deleted"] = bool(row["deleted"])
    data["_created_at"] = row["created_at"]
    data["_updated_at"] = row["updated_at"]
    return data


def list_entities(conn: sqlite3.Connection, *, namespace: str, include_deleted: bool = False) -> List[Dict[str, Any]]:
    ensure_schema(conn)
    sql = """
        SELECT entity_id, data_json, status, deleted, created_at, updated_at
        FROM compat_entities
        WHERE namespace = ?
    """
    params: list[Any] = [namespace]
    if not include_deleted:
        sql += " AND deleted = 0"
    sql += " ORDER BY updated_at DESC"
    rows = conn.execute(sql, params).fetchall()
    items: List[Dict[str, Any]] = []
    for row in rows:
        data = json.loads(row["data_json"])
        data["_entity_id"] = row["entity_id"]
        data["_status"] = row["status"]
        data["_deleted"] = bool(row["deleted"])
        data["_created_at"] = row["created_at"]
        data["_updated_at"] = row["updated_at"]
        items.append(data)
    return items


def soft_delete_entity(conn: sqlite3.Connection, *, namespace: str, entity_id: str) -> None:
    ensure_schema(conn)
    conn.execute(
        """
        UPDATE compat_entities
        SET deleted = 1, updated_at = ?
        WHERE namespace = ? AND entity_id = ?
        """,
        (now_iso(), namespace, entity_id),
    )
    conn.commit()


def set_state(conn: sqlite3.Connection, *, key: str, value: Any) -> None:
    ensure_schema(conn)
    conn.execute(
        """
        INSERT INTO compat_state (key, value_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
        """,
        (key, _json_dump(value), now_iso()),
    )
    conn.commit()


def get_state(conn: sqlite3.Connection, *, key: str, default: Any) -> Any:
    ensure_schema(conn)
    row = conn.execute("SELECT value_json FROM compat_state WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value_json"])
    except Exception:
        return default
