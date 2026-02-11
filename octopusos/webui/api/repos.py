"""Repos API router (v2)."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from octopusos.store import get_db_path

router = APIRouter(prefix="/api/repos", tags=["repos"])


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


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return bool(row)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r["name"]) for r in rows}


def _repo_table(conn: sqlite3.Connection) -> Optional[str]:
    if _table_exists(conn, "project_repos"):
        return "project_repos"
    if _table_exists(conn, "repos"):
        return "repos"
    return None


def _repo_id_col(cols: set[str]) -> str:
    if "repo_id" in cols:
        return "repo_id"
    if "id" in cols:
        return "id"
    raise HTTPException(status_code=500, detail="repo id column missing")


def _as_repo(row: sqlite3.Row) -> Dict[str, Any]:
    repo_id = row["repo_id"] if "repo_id" in row.keys() else row["id"]
    path = (
        row["workspace_relpath"]
        if "workspace_relpath" in row.keys()
        else row["local_path"]
        if "local_path" in row.keys()
        else row["path"]
        if "path" in row.keys()
        else "."
    )
    url = row["remote_url"] if "remote_url" in row.keys() else row["url"] if "url" in row.keys() else None
    return {
        "id": repo_id,
        "repo_id": repo_id,
        "project_id": row["project_id"] if "project_id" in row.keys() else "",
        "name": row["name"] if "name" in row.keys() else "",
        "path": path,
        "url": url,
        "created_at": row["created_at"] if "created_at" in row.keys() else _now_iso(),
        "updated_at": row["updated_at"] if "updated_at" in row.keys() else None,
    }


@router.get("")
def list_repos(
    project_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=500),
    offset: Optional[int] = Query(default=None, ge=0),
) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        table = _repo_table(conn)
        if table is None:
            return {"repos": [], "total": 0, "page": page, "limit": limit}

        where = []
        params: list[Any] = []
        if project_id:
            where.append("project_id = ?")
            params.append(project_id)
        where_sql = f" WHERE {' AND '.join(where)}" if where else ""

        use_offset = offset if offset is not None else (page - 1) * limit
        total = conn.execute(f"SELECT COUNT(*) FROM {table}{where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM {table}{where_sql} ORDER BY rowid DESC LIMIT ? OFFSET ?",
            params + [limit, use_offset],
        ).fetchall()
        return {
            "repos": [_as_repo(r) for r in rows],
            "total": total,
            "page": page,
            "limit": limit,
        }
    finally:
        conn.close()


@router.get("/{repo_id}")
def get_repo(repo_id: str) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        table = _repo_table(conn)
        if table is None:
            raise HTTPException(status_code=404, detail="Repo not found")
        cols = _table_columns(conn, table)
        id_col = _repo_id_col(cols)
        row = conn.execute(f"SELECT * FROM {table} WHERE {id_col} = ?", (repo_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Repo not found")
        return {"repo": _as_repo(row)}
    finally:
        conn.close()


@router.post("", status_code=201)
def create_repo(payload: Dict[str, Any]) -> Dict[str, Any]:
    project_id = payload.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    conn = _db_connect()
    try:
        table = _repo_table(conn)
        if table is None:
            raise HTTPException(status_code=500, detail="repos table missing")
        cols = _table_columns(conn, table)
        id_col = _repo_id_col(cols)

        repo_id = f"repo_{uuid4().hex[:12]}"
        now = _now_iso()
        path = payload.get("path") or payload.get("workspace_relpath") or "."
        data: Dict[str, Any] = {
            id_col: repo_id,
            "repo_id": repo_id,
            "project_id": project_id,
            "name": payload.get("name") or f"repo-{repo_id[-4:]}",
            "workspace_relpath": path,
            "local_path": path,
            "path": path,
            "remote_url": payload.get("url") or payload.get("remote_url"),
            "url": payload.get("url"),
            "default_branch": payload.get("default_branch") or "main",
            "role": payload.get("role") or "code",
            "is_writable": 1,
            "auth_profile": payload.get("auth_profile"),
            "created_at": now,
            "updated_at": now,
            "metadata": json.dumps(payload.get("metadata", {})),
            "vcs_type": payload.get("vcs_type") or "git",
        }
        insert_data = {k: v for k, v in data.items() if k in cols}
        keys = list(insert_data.keys())
        conn.execute(
            f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
            [insert_data[k] for k in keys],
        )
        conn.commit()
        row = conn.execute(f"SELECT * FROM {table} WHERE {id_col} = ?", (repo_id,)).fetchone()
        return {"repo": _as_repo(row)}
    finally:
        conn.close()


@router.patch("/{repo_id}")
def update_repo(repo_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        table = _repo_table(conn)
        if table is None:
            raise HTTPException(status_code=404, detail="Repo not found")
        cols = _table_columns(conn, table)
        id_col = _repo_id_col(cols)

        row = conn.execute(f"SELECT * FROM {table} WHERE {id_col} = ?", (repo_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Repo not found")

        updates = []
        params: list[Any] = []
        field_map = {
            "name": "name",
            "url": "remote_url" if "remote_url" in cols else "url",
            "remote_url": "remote_url" if "remote_url" in cols else "url",
            "path": "workspace_relpath" if "workspace_relpath" in cols else "local_path" if "local_path" in cols else "path",
            "default_branch": "default_branch",
        }
        for payload_key, column in field_map.items():
            if payload_key in payload and column in cols:
                updates.append(f"{column} = ?")
                params.append(payload[payload_key])

        if "metadata" in payload and "metadata" in cols:
            updates.append("metadata = ?")
            params.append(json.dumps(payload.get("metadata", {})))

        if "updated_at" in cols:
            updates.append("updated_at = ?")
            params.append(_now_iso())

        if updates:
            params.append(repo_id)
            conn.execute(
                f"UPDATE {table} SET {', '.join(updates)} WHERE {id_col} = ?",
                params,
            )
            conn.commit()

        updated = conn.execute(f"SELECT * FROM {table} WHERE {id_col} = ?", (repo_id,)).fetchone()
        return {"repo": _as_repo(updated)}
    finally:
        conn.close()


@router.delete("/{repo_id}")
def delete_repo(repo_id: str) -> Dict[str, bool]:
    conn = _db_connect()
    try:
        table = _repo_table(conn)
        if table is None:
            raise HTTPException(status_code=404, detail="Repo not found")
        cols = _table_columns(conn, table)
        id_col = _repo_id_col(cols)
        row = conn.execute(f"SELECT 1 FROM {table} WHERE {id_col} = ?", (repo_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Repo not found")
        conn.execute(f"DELETE FROM {table} WHERE {id_col} = ?", (repo_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()

