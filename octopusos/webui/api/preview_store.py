"""Preview session persistence and filesystem rendering."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from octopusos.store import get_db

_PREVIEW_ROOT = Path("tmp/live_previews")
_SCHEMA_READY = False
_TABLE = "coding_preview_sessions"



def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()



def _ensure_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_TABLE} (
            preview_id TEXT PRIMARY KEY,
            session_id TEXT,
            run_id TEXT,
            preset TEXT NOT NULL,
            status TEXT NOT NULL,
            html TEXT,
            meta_json TEXT,
            version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    columns = {
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({_TABLE})").fetchall()
    }
    if "session_id" not in columns:
        cursor.execute(f"ALTER TABLE {_TABLE} ADD COLUMN session_id TEXT")
    if "run_id" not in columns:
        cursor.execute(f"ALTER TABLE {_TABLE} ADD COLUMN run_id TEXT")
    if "meta_json" not in columns:
        cursor.execute(f"ALTER TABLE {_TABLE} ADD COLUMN meta_json TEXT")
    if "version" not in columns:
        cursor.execute(f"ALTER TABLE {_TABLE} ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
    if "created_at" not in columns:
        cursor.execute(f"ALTER TABLE {_TABLE} ADD COLUMN created_at TEXT")
    if "updated_at" not in columns:
        cursor.execute(f"ALTER TABLE {_TABLE} ADD COLUMN updated_at TEXT")

    cursor.execute(
        f"""
        UPDATE {_TABLE}
        SET version = COALESCE(version, 1),
            created_at = COALESCE(created_at, updated_at, ?),
            updated_at = COALESCE(updated_at, created_at, ?)
        """,
        (_iso_now(), _iso_now()),
    )
    cursor.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_coding_preview_sessions_session_run
        ON {_TABLE}(session_id, run_id)
        """
    )
    conn.commit()
    _SCHEMA_READY = True



def _preview_dir(preview_id: str) -> Path:
    return _PREVIEW_ROOT / preview_id



def _preview_file(preview_id: str) -> Path:
    return _preview_dir(preview_id) / "index.html"



def _write_preview_file(preview_id: str, html: str) -> None:
    path = _preview_file(preview_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html or "", encoding="utf-8")



def create_preview_session(
    *,
    preset: str,
    html: str,
    session_id: Optional[str] = None,
    run_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    _ensure_schema()
    preview_id = f"preview_{uuid.uuid4().hex}"
    now = _iso_now()
    status = "ready"
    version = 1
    _write_preview_file(preview_id, html)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        INSERT INTO {_TABLE}
        (preview_id, session_id, run_id, preset, status, html, meta_json, version, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            preview_id,
            session_id,
            run_id,
            preset,
            status,
            html,
            json.dumps(meta or {}, ensure_ascii=False),
            version,
            now,
            now,
        ),
    )
    conn.commit()
    return {
        "preview_id": preview_id,
        "session_id": session_id,
        "run_id": run_id,
        "preset": preset,
        "status": status,
        "version": version,
        "url": f"/api/preview/{preview_id}/content?v={version}",
    }



def get_preview_session(preview_id: str) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        f"""
        SELECT preview_id, session_id, run_id, preset, status, html, meta_json, version, created_at, updated_at
        FROM {_TABLE}
        WHERE preview_id = ?
        """,
        (preview_id,),
    ).fetchone()
    if not row:
        return None
    try:
        meta = json.loads(row[6]) if row[6] else {}
    except Exception:
        meta = {}
    return {
        "preview_id": row[0],
        "session_id": row[1],
        "run_id": row[2],
        "preset": row[3],
        "status": row[4],
        "html": row[5] or "",
        "meta": meta if isinstance(meta, dict) else {},
        "version": int(row[7] or 1),
        "created_at": row[8],
        "updated_at": row[9],
        "url": f"/api/preview/{row[0]}/content?v={int(row[7] or 1)}",
    }



def update_preview_session(
    preview_id: str,
    *,
    html: Optional[str] = None,
    status: Optional[str] = None,
    bump_version: bool = True,
) -> Optional[Dict[str, Any]]:
    session = get_preview_session(preview_id)
    if not session:
        return None

    next_html = session["html"] if html is None else str(html)
    next_status = session["status"] if status is None else str(status)
    next_version = int(session["version"] + 1 if bump_version else session["version"])
    now = _iso_now()

    _write_preview_file(preview_id, next_html)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        UPDATE {_TABLE}
        SET status = ?, html = ?, version = ?, updated_at = ?
        WHERE preview_id = ?
        """,
        (next_status, next_html, next_version, now, preview_id),
    )
    conn.commit()
    return get_preview_session(preview_id)



def delete_preview_session(preview_id: str) -> bool:
    _ensure_schema()
    conn = get_db()
    cursor = conn.cursor()
    deleted = cursor.execute(f"DELETE FROM {_TABLE} WHERE preview_id = ?", (preview_id,)).rowcount
    conn.commit()

    path = _preview_dir(preview_id)
    if path.exists():
        for child in path.glob("**/*"):
            if child.is_file():
                child.unlink(missing_ok=True)
        for child in sorted(path.glob("**/*"), reverse=True):
            if child.is_dir():
                child.rmdir()
        if path.exists():
            path.rmdir()

    return bool(deleted)



def read_preview_html(preview_id: str) -> Optional[str]:
    path = _preview_file(preview_id)
    if path.exists():
        return path.read_text(encoding="utf-8")
    session = get_preview_session(preview_id)
    if not session:
        return None
    return str(session.get("html") or "")
