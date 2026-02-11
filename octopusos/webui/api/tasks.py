"""Tasks API router (v2)."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from octopusos.store import get_db_path

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class RoutePlanResponse(BaseModel):
    route: str


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


def _task_id_col(cols: set[str]) -> str:
    if "task_id" in cols:
        return "task_id"
    if "id" in cols:
        return "id"
    raise HTTPException(status_code=500, detail="task id column missing")


def _as_task(row: sqlite3.Row, id_col: str) -> Dict[str, Any]:
    return {
        "id": row[id_col],
        "task_id": row[id_col],
        "project_id": row["project_id"] if "project_id" in row.keys() else None,
        "session_id": row["session_id"] if "session_id" in row.keys() else None,
        "title": row["title"] if "title" in row.keys() else "",
        "description": row["description"] if "description" in row.keys() else None,
        "status": row["status"] if "status" in row.keys() and row["status"] else "created",
        "created_at": row["created_at"] if "created_at" in row.keys() else _now_iso(),
        "updated_at": row["updated_at"] if "updated_at" in row.keys() else None,
    }


@router.get("")
def list_tasks(
    project_id: Optional[str] = None,
    session_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=500),
    offset: Optional[int] = Query(default=None, ge=0),
) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        if not _table_exists(conn, "tasks"):
            return {"tasks": [], "total": 0, "page": page, "limit": limit}
        cols = _table_columns(conn, "tasks")
        id_col = _task_id_col(cols)

        where = []
        params: list[Any] = []
        if project_id and "project_id" in cols:
            where.append("project_id = ?")
            params.append(project_id)
        if session_id and "session_id" in cols:
            where.append("session_id = ?")
            params.append(session_id)
        if status and "status" in cols:
            where.append("status = ?")
            params.append(status)
        where_sql = f" WHERE {' AND '.join(where)}" if where else ""

        use_offset = offset if offset is not None else (page - 1) * limit
        total = conn.execute(f"SELECT COUNT(*) FROM tasks{where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM tasks{where_sql} ORDER BY rowid DESC LIMIT ? OFFSET ?",
            params + [limit, use_offset],
        ).fetchall()
        return {
            "tasks": [_as_task(r, id_col) for r in rows],
            "total": total,
            "page": page,
            "limit": limit,
        }
    finally:
        conn.close()


@router.get("/{task_id}")
def get_task(task_id: str) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        if not _table_exists(conn, "tasks"):
            raise HTTPException(status_code=404, detail="Task not found")
        cols = _table_columns(conn, "tasks")
        id_col = _task_id_col(cols)
        row = conn.execute(f"SELECT * FROM tasks WHERE {id_col} = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"task": _as_task(row, id_col)}
    finally:
        conn.close()


@router.post("", status_code=201)
def create_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        if not _table_exists(conn, "tasks"):
            raise HTTPException(status_code=500, detail="tasks table missing")
        cols = _table_columns(conn, "tasks")
        id_col = _task_id_col(cols)

        task_id = f"task_{uuid4().hex[:12]}"
        now = _now_iso()
        created_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        status = payload.get("status") or "created"
        data: Dict[str, Any] = {
            id_col: task_id,
            "title": payload.get("title") or "Untitled Task",
            "description": payload.get("description"),
            "status": status,
            "project_id": payload.get("project_id"),
            "session_id": payload.get("session_id"),
            "created_at": now,
            "updated_at": now,
            "created_by": "webui",
            "metadata": json.dumps(payload.get("metadata", {})),
            "created_at_ms": created_ms,
            "updated_at_ms": created_ms,
        }
        insert_data = {k: v for k, v in data.items() if k in cols}
        keys = list(insert_data.keys())
        conn.execute(
            f"INSERT INTO tasks ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
            [insert_data[k] for k in keys],
        )
        conn.commit()
        row = conn.execute(f"SELECT * FROM tasks WHERE {id_col} = ?", (task_id,)).fetchone()
        return {"task": _as_task(row, id_col)}
    finally:
        conn.close()


@router.post("/create_and_start", status_code=201)
def create_and_start_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    payload_with_running = dict(payload)
    payload_with_running["status"] = payload.get("status") or "running"
    return create_task(payload_with_running)


@router.delete("/{task_id}")
def delete_task(task_id: str) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        if not _table_exists(conn, "tasks"):
            raise HTTPException(status_code=404, detail="Task not found")
        cols = _table_columns(conn, "tasks")
        id_col = _task_id_col(cols)
        row = conn.execute(f"SELECT 1 FROM tasks WHERE {id_col} = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        conn.execute(f"DELETE FROM tasks WHERE {id_col} = ?", (task_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/{task_id}/route", response_model=RoutePlanResponse)
def get_task_route(task_id: str) -> Dict[str, str]:
    conn = _db_connect()
    try:
        if not _table_exists(conn, "tasks"):
            raise HTTPException(status_code=404, detail="Task not found")
        cols = _table_columns(conn, "tasks")
        id_col = _task_id_col(cols)
        row = conn.execute(f"SELECT * FROM tasks WHERE {id_col} = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        route = "default"
        if "route" in row.keys() and row["route"]:
            route = str(row["route"])
        elif "metadata" in row.keys() and row["metadata"]:
            try:
                route = str(json.loads(row["metadata"]).get("route") or route)
            except Exception:
                pass
        return {"route": route}
    finally:
        conn.close()


@router.post("/{task_id}/route")
def update_task_route(task_id: str, payload: Dict[str, Any]) -> Dict[str, bool]:
    route = payload.get("route")
    if not route:
        raise HTTPException(status_code=400, detail="route is required")

    conn = _db_connect()
    try:
        if not _table_exists(conn, "tasks"):
            raise HTTPException(status_code=404, detail="Task not found")
        cols = _table_columns(conn, "tasks")
        id_col = _task_id_col(cols)
        row = conn.execute(f"SELECT * FROM tasks WHERE {id_col} = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")

        now = _now_iso()
        if "route" in cols:
            conn.execute(
                f"UPDATE tasks SET route = ?, updated_at = ? WHERE {id_col} = ?",
                (route, now, task_id),
            )
        elif "metadata" in cols:
            metadata = {}
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except Exception:
                    metadata = {}
            metadata["route"] = route
            conn.execute(
                f"UPDATE tasks SET metadata = ?, updated_at = ? WHERE {id_col} = ?",
                (json.dumps(metadata), now, task_id),
            )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/batch")
def batch_create_tasks(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = payload.get("tasks")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="tasks must be a list")

    created = []
    for item in items:
        if not isinstance(item, dict):
            continue
        created.append(create_task(item)["task"])
    return {"tasks": created}
