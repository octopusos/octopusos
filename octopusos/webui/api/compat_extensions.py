"""P1 compatibility router for extensions endpoints expected by apps/webui."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Query

from octopusos.core.capabilities.admin_token import validate_admin_token
from octopusos.store import get_db_path
from octopusos.webui.api.compat_state import audit_event

router = APIRouter(prefix="/api/extensions", tags=["compat"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_connect() -> sqlite3.Connection:
    env_path = os.getenv("OCTOPUSOS_DB_PATH")
    db_path = Path(env_path) if env_path else get_db_path()
    if not db_path.exists():
        raise HTTPException(status_code=500, detail="Database not initialized")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS compat_extensions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'disabled',
            trust_tier TEXT NOT NULL DEFAULT 'local',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT COUNT(*) AS c FROM compat_extensions").fetchone()
    if row and int(row["c"]) > 0:
        return
    now = _now_iso()
    conn.executemany(
        """
        INSERT INTO compat_extensions (id, name, version, description, status, trust_tier, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("ext.core.observability", "Core Observability", "0.1.0", "System health and diagnostics extension", "enabled", "local", now, now),
            ("ext.core.marketplace", "Marketplace Connector", "0.1.0", "Basic marketplace compatibility extension", "disabled", "local", now, now),
        ],
    )
    conn.commit()


def _require_admin_token(token: Optional[str]) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="Admin token required")
    if not validate_admin_token(token):
        raise HTTPException(status_code=403, detail="Invalid admin token")


def _to_extension(row: sqlite3.Row) -> Dict[str, Any]:
    status = row["status"]
    enabled = status == "enabled"
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] or "",
        "version": row["version"],
        "status": status,
        "enabled": enabled,
        "trust_tier": row["trust_tier"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "source": "compat",
    }


@router.get("")
def list_extensions(
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=500),
) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        _ensure_table(conn)
        _seed_if_empty(conn)
        use_offset = (page - 1) * limit
        params: list[Any] = []
        where = ""
        if status in {"enabled", "disabled"}:
            where = " WHERE status = ?"
            params.append(status)
        total = conn.execute(f"SELECT COUNT(*) AS c FROM compat_extensions{where}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT * FROM compat_extensions{where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [limit, use_offset],
        ).fetchall()
        items = [_to_extension(r) for r in rows]
        # Keep both shapes for compatibility with various callers.
        return {
            "extensions": items,
            "items": items,
            "total": int(total),
            "page": page,
            "limit": limit,
            "source": "compat",
        }
    finally:
        conn.close()


def _set_extension_status(extension_id: str, status: str) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        _ensure_table(conn)
        _seed_if_empty(conn)
        row = conn.execute("SELECT * FROM compat_extensions WHERE id = ?", (extension_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Extension not found")
        now = _now_iso()
        conn.execute(
            "UPDATE compat_extensions SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, extension_id),
        )
        audit_event(
            conn,
            event_type=f"extension_{status}",
            endpoint=f"/api/extensions/{extension_id}/{status}",
            actor="admin",
            payload={"extension_id": extension_id, "status": status},
            result={"ok": True},
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM compat_extensions WHERE id = ?", (extension_id,)).fetchone()
        extension = _to_extension(updated)
        return {
            "id": extension_id,
            "enabled": status == "enabled",
            "extension": extension,
            "source": "compat",
        }
    finally:
        conn.close()


@router.post("/{extension_id}/enable")
def enable_extension(
    extension_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin_token(admin_token)
    return _set_extension_status(extension_id, "enabled")


@router.post("/{extension_id}/disable")
def disable_extension(
    extension_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin_token(admin_token)
    return _set_extension_status(extension_id, "disabled")


@router.delete("/{extension_id}")
def delete_extension(
    extension_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin_token(admin_token)
    conn = _db_connect()
    try:
        _ensure_table(conn)
        row = conn.execute("SELECT id FROM compat_extensions WHERE id = ?", (extension_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Extension not found")
        conn.execute("DELETE FROM compat_extensions WHERE id = ?", (extension_id,))
        audit_event(
            conn,
            event_type="extension_delete",
            endpoint=f"/api/extensions/{extension_id}",
            actor="admin",
            payload={"extension_id": extension_id},
            result={"ok": True},
        )
        conn.commit()
        return {"ok": True, "id": extension_id, "source": "compat"}
    finally:
        conn.close()
