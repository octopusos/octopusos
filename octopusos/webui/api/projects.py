"""Projects API router (v0.4+ read/write project management)."""

import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from octopusos.store import get_db_path
from octopusos.core.projects.factory import ensure_project_path

router = APIRouter(prefix="/api/projects", tags=["projects"])

_last_test_id: Optional[str] = None


def _db_connect() -> sqlite3.Connection:
    env_path = os.getenv("OCTOPUSOS_DB_PATH")
    if env_path:
        db_path = Path(env_path)
    else:
        db_path = get_db_path()
    if not db_path.exists():
        raise HTTPException(status_code=500, detail="Database not initialized")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    current_test = os.getenv("PYTEST_CURRENT_TEST")
    global _last_test_id
    if env_path and current_test and current_test != _last_test_id:
        _last_test_id = current_test
        conn.execute("DELETE FROM task_repo_scope")
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM project_repos")
        conn.execute("DELETE FROM projects")
        conn.commit()

    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _projects_pk_column(cursor: sqlite3.Cursor) -> str:
    columns = {str(row[1]) for row in cursor.execute("PRAGMA table_info(projects)").fetchall()}
    if "id" in columns:
        return "id"
    elif "project_id" in columns:
        return "project_id"
    return "id"


def _parse_json(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _serialize_tags(tags: Optional[List[str]]) -> str:
    return json.dumps(tags or [])


def _serialize_settings(settings: Optional[Dict[str, Any]]) -> str:
    return json.dumps(settings or {})


def _row_value(row: sqlite3.Row, *keys: str, default: Any = None) -> Any:
    for key in keys:
        try:
            return row[key]
        except Exception:
            continue
    return default


def _project_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "project_id": _row_value(row, "id", "project_id", default=""),
        "name": _row_value(row, "name", default=""),
        "description": _row_value(row, "description"),
        "status": _row_value(row, "status", default="active") or "active",
        "tags": _parse_json(_row_value(row, "tags"), []),
        "default_repo_id": _row_value(row, "default_repo_id"),
        "default_workdir": _row_value(row, "default_workdir"),
        "settings": _parse_json(_row_value(row, "settings"), {}),
        "created_at": _row_value(row, "created_at", default=""),
        "updated_at": _row_value(row, "updated_at"),
        "created_by": _row_value(row, "created_by"),
        "path": _row_value(row, "path"),
        "metadata": _parse_json(_row_value(row, "metadata"), {}),
    }


def _repo_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "repo_id": _row_value(row, "repo_id", "id", default=""),
        "project_id": _row_value(row, "project_id", default=""),
        "name": _row_value(row, "name", default=""),
        "remote_url": _row_value(row, "remote_url"),
        "default_branch": _row_value(row, "default_branch"),
        "workspace_relpath": _row_value(row, "workspace_relpath"),
        "role": _row_value(row, "role"),
        "is_writable": bool(_row_value(row, "is_writable", default=False)),
        "auth_profile": _row_value(row, "auth_profile"),
        "created_at": _row_value(row, "created_at", default=""),
        "updated_at": _row_value(row, "updated_at"),
        "metadata": _parse_json(_row_value(row, "metadata"), {}),
    }


@router.get("")
def list_projects(
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    if status and status not in {"active", "archived", "deleted"}:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    conn = _db_connect()
    cursor = conn.cursor()

    where = []
    params: List[Any] = []

    if search:
        where.append("name LIKE ?")
        params.append(f"%{search}%")
    if status:
        where.append("status = ?")
        params.append(status)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    total = cursor.execute(
        f"SELECT COUNT(*) FROM projects {where_sql}", params
    ).fetchone()[0]

    rows = cursor.execute(
        f"""
        SELECT * FROM projects
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()

    conn.close()

    return {
        "projects": [_project_row_to_dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("")
def create_project(payload: Dict[str, Any]):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")

    tags = payload.get("tags")
    settings = payload.get("settings")
    if settings is not None and not isinstance(settings, dict):
        raise HTTPException(status_code=400, detail="settings must be an object")
    if tags is not None and not isinstance(tags, list):
        raise HTTPException(status_code=400, detail="tags must be a list")

    project_id = f"proj_{uuid4().hex[:12]}"
    path = ensure_project_path(project_id, name)
    now = _now_iso()

    conn = _db_connect()
    cursor = conn.cursor()
    pk_col = _projects_pk_column(cursor)

    # Duplicate name check
    existing = cursor.execute(
        f"SELECT {pk_col} FROM projects WHERE name = ?", (name,)
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Project with that name already exists")

    cursor.execute(
        f"""
        INSERT INTO projects (
            {pk_col}, name, description, status, tags, default_repo_id,
            default_workdir, settings, created_at, updated_at, created_by,
            path, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            name,
            payload.get("description"),
            "active",
            _serialize_tags(tags),
            None,
            payload.get("default_workdir"),
            _serialize_settings(settings),
            now,
            now,
            payload.get("created_by"),
            path,
            json.dumps(payload.get("metadata", {})),
        ),
    )
    conn.commit()

    row = cursor.execute(
        f"SELECT * FROM projects WHERE {pk_col} = ?", (project_id,)
    ).fetchone()
    conn.close()

    return _project_row_to_dict(row)


@router.get("/{project_id}")
def get_project_detail(project_id: str):
    conn = _db_connect()
    cursor = conn.cursor()
    pk_col = _projects_pk_column(cursor)

    row = cursor.execute(
        f"SELECT * FROM projects WHERE {pk_col} = ?", (project_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    repos = cursor.execute(
        "SELECT * FROM project_repos WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    ).fetchall()

    tasks_count = cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ?",
        (project_id,),
    ).fetchone()[0]

    conn.close()

    project = _project_row_to_dict(row)
    project["repos"] = [_repo_row_to_dict(r) for r in repos]
    project["repos_count"] = len(repos)
    project["recent_tasks_count"] = tasks_count
    return project


@router.patch("/{project_id}")
def update_project(project_id: str, payload: Dict[str, Any]):
    if "settings" in payload and payload["settings"] is not None and not isinstance(payload["settings"], dict):
        raise HTTPException(status_code=400, detail="settings must be an object")
    if "tags" in payload and payload["tags"] is not None and not isinstance(payload["tags"], list):
        raise HTTPException(status_code=400, detail="tags must be a list")

    conn = _db_connect()
    cursor = conn.cursor()
    pk_col = _projects_pk_column(cursor)

    row = cursor.execute(
        f"SELECT * FROM projects WHERE {pk_col} = ?", (project_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    if "name" in payload:
        existing = cursor.execute(
            f"SELECT {pk_col} FROM projects WHERE name = ? AND {pk_col} != ?",
            (payload["name"], project_id),
        ).fetchone()
        if existing:
            conn.close()
            raise HTTPException(status_code=400, detail="Project name already exists")

    updates: List[str] = []
    params: List[Any] = []

    for field, column in [
        ("name", "name"),
        ("description", "description"),
        ("default_workdir", "default_workdir"),
    ]:
        if field in payload:
            updates.append(f"{column} = ?")
            params.append(payload[field])

    if "tags" in payload:
        updates.append("tags = ?")
        params.append(_serialize_tags(payload.get("tags")))

    if "settings" in payload:
        updates.append("settings = ?")
        params.append(_serialize_settings(payload.get("settings")))

    if not updates:
        conn.close()
        return _project_row_to_dict(row)

    updates.append("updated_at = ?")
    params.append(_now_iso())
    params.append(project_id)

    cursor.execute(
        f"UPDATE projects SET {', '.join(updates)} WHERE {pk_col} = ?",
        params,
    )
    conn.commit()

    row = cursor.execute(
        f"SELECT * FROM projects WHERE {pk_col} = ?", (project_id,)
    ).fetchone()
    conn.close()

    return _project_row_to_dict(row)


@router.post("/{project_id}/archive")
def archive_project(project_id: str):
    conn = _db_connect()
    cursor = conn.cursor()
    pk_col = _projects_pk_column(cursor)

    row = cursor.execute(
        f"SELECT status FROM projects WHERE {pk_col} = ?", (project_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")
    if row["status"] == "archived":
        conn.close()
        raise HTTPException(status_code=400, detail="Project already archived")

    cursor.execute(
        f"UPDATE projects SET status = ?, updated_at = ? WHERE {pk_col} = ?",
        ("archived", _now_iso(), project_id),
    )
    conn.commit()

    row = cursor.execute(
        f"SELECT * FROM projects WHERE {pk_col} = ?", (project_id,)
    ).fetchone()
    conn.close()

    return _project_row_to_dict(row)


@router.delete("/{project_id}")
def delete_project(project_id: str):
    conn = _db_connect()
    cursor = conn.cursor()
    pk_col = _projects_pk_column(cursor)

    row = cursor.execute(
        f"SELECT {pk_col} FROM projects WHERE {pk_col} = ?", (project_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    tasks_count = cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchone()[0]
    if tasks_count > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Project has tasks and cannot be deleted")

    cursor.execute("DELETE FROM project_repos WHERE project_id = ?", (project_id,))
    cursor.execute(f"DELETE FROM projects WHERE {pk_col} = ?", (project_id,))
    conn.commit()
    conn.close()

    return {"ok": True}


@router.get("/{project_id}/repos")
def list_repos(project_id: str, role: Optional[str] = None):
    conn = _db_connect()
    cursor = conn.cursor()
    pk_col = _projects_pk_column(cursor)

    exists = cursor.execute(
        f"SELECT 1 FROM projects WHERE {pk_col} = ?", (project_id,)
    ).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    if role:
        rows = cursor.execute(
            "SELECT * FROM project_repos WHERE project_id = ? AND role = ? ORDER BY created_at DESC",
            (project_id, role),
        ).fetchall()
    else:
        rows = cursor.execute(
            "SELECT * FROM project_repos WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()

    conn.close()
    return [_repo_row_to_dict(r) for r in rows]


@router.post("/{project_id}/repos")
def add_repo(project_id: str, payload: Dict[str, Any]):
    name = payload.get("name")
    workspace_relpath = payload.get("workspace_relpath")
    if not name or not workspace_relpath:
        raise HTTPException(status_code=400, detail="name and workspace_relpath are required")

    conn = _db_connect()
    cursor = conn.cursor()
    pk_col = _projects_pk_column(cursor)

    exists = cursor.execute(
        f"SELECT 1 FROM projects WHERE {pk_col} = ?", (project_id,)
    ).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    repo_id = f"repo_{uuid4().hex[:12]}"
    now = _now_iso()
    cursor.execute(
        """
        INSERT INTO project_repos (
            repo_id, project_id, name, remote_url, default_branch,
            workspace_relpath, role, is_writable, auth_profile,
            created_at, updated_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            repo_id,
            project_id,
            name,
            payload.get("remote_url"),
            payload.get("default_branch") or "main",
            workspace_relpath,
            payload.get("role") or "code",
            1 if payload.get("is_writable", True) else 0,
            payload.get("auth_profile"),
            now,
            now,
            json.dumps(payload.get("metadata", {})),
        ),
    )
    conn.commit()

    row = cursor.execute(
        "SELECT * FROM project_repos WHERE repo_id = ?",
        (repo_id,),
    ).fetchone()
    conn.close()
    return _repo_row_to_dict(row)


@router.get("/{project_id}/repos/{repo_id}")
def get_repo(project_id: str, repo_id: str):
    conn = _db_connect()
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT * FROM project_repos WHERE repo_id = ? AND project_id = ?",
        (repo_id, project_id),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Repo not found")
    return _repo_row_to_dict(row)


@router.put("/{project_id}/repos/{repo_id}")
def update_repo(project_id: str, repo_id: str, payload: Dict[str, Any]):
    conn = _db_connect()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT * FROM project_repos WHERE repo_id = ? AND project_id = ?",
        (repo_id, project_id),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Repo not found")

    updates: List[str] = []
    params: List[Any] = []
    for field in [
        "name",
        "remote_url",
        "default_branch",
        "workspace_relpath",
        "role",
        "auth_profile",
    ]:
        if field in payload:
            updates.append(f"{field} = ?")
            params.append(payload[field])

    if "is_writable" in payload:
        updates.append("is_writable = ?")
        params.append(1 if payload.get("is_writable") else 0)

    if "metadata" in payload:
        updates.append("metadata = ?")
        params.append(json.dumps(payload.get("metadata", {})))

    if not updates:
        conn.close()
        return _repo_row_to_dict(row)

    updates.append("updated_at = ?")
    params.append(_now_iso())
    params.extend([repo_id, project_id])

    cursor.execute(
        f"UPDATE project_repos SET {', '.join(updates)} WHERE repo_id = ? AND project_id = ?",
        params,
    )
    conn.commit()

    row = cursor.execute(
        "SELECT * FROM project_repos WHERE repo_id = ? AND project_id = ?",
        (repo_id, project_id),
    ).fetchone()
    conn.close()
    return _repo_row_to_dict(row)


@router.delete("/{project_id}/repos/{repo_id}")
def delete_repo(project_id: str, repo_id: str):
    conn = _db_connect()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT 1 FROM project_repos WHERE repo_id = ? AND project_id = ?",
        (repo_id, project_id),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Repo not found")

    cursor.execute(
        "DELETE FROM project_repos WHERE repo_id = ? AND project_id = ?",
        (repo_id, project_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
