"""SQLite-backed configuration registry for WebUI config endpoints."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from octopusos.core.storage.paths import component_db_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _type_to_label(value_type: str) -> str:
    mapping = {
        "string": "String",
        "int": "Integer",
        "float": "Integer",
        "bool": "Boolean",
        "json": "JSON",
        "secret_ref": "String",
    }
    return mapping.get((value_type or "").lower(), "String")


def _render_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def _encode_key(key: str, project_id: Optional[str]) -> str:
    if project_id:
        return f"{project_id}::{key}"
    return key


def _decode_key(stored_key: str) -> tuple[str, Optional[str]]:
    if "::" in stored_key:
        project, logical = stored_key.split("::", 1)
        if project and logical:
            return logical, project
    return stored_key, None


class ConfigStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_config (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key TEXT NOT NULL UNIQUE,
                  value_json TEXT NOT NULL,
                  value_type TEXT NOT NULL,
                  module TEXT NOT NULL,
                  scope TEXT NOT NULL DEFAULT 'global',
                  project_id TEXT,
                  is_secret INTEGER NOT NULL DEFAULT 0,
                  is_hot_reload INTEGER NOT NULL DEFAULT 1,
                  schema_version INTEGER NOT NULL DEFAULT 1,
                  source TEXT NOT NULL DEFAULT 'db',
                  version INTEGER NOT NULL DEFAULT 1,
                  updated_at TEXT NOT NULL,
                  updated_by TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_app_config_module ON app_config(module);
                CREATE INDEX IF NOT EXISTS idx_app_config_scope ON app_config(scope);
                CREATE INDEX IF NOT EXISTS idx_app_config_key ON app_config(key);

                CREATE TABLE IF NOT EXISTS app_config_audit (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  config_key TEXT NOT NULL,
                  module TEXT NOT NULL,
                  project_id TEXT,
                  actor TEXT NOT NULL,
                  op TEXT NOT NULL,
                  old_hash TEXT,
                  new_hash TEXT NOT NULL,
                  old_preview TEXT,
                  new_preview TEXT,
                  schema_version INTEGER NOT NULL,
                  source TEXT NOT NULL,
                  decision_id TEXT,
                  reason TEXT,
                  risk_level TEXT,
                  created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_app_config_audit_key ON app_config_audit(config_key);
                CREATE INDEX IF NOT EXISTS idx_app_config_audit_created_at ON app_config_audit(created_at);

                CREATE TABLE IF NOT EXISTS app_config_snapshot (
                  snapshot_id TEXT PRIMARY KEY,
                  scope TEXT NOT NULL,
                  project_id TEXT,
                  actor TEXT NOT NULL,
                  source TEXT NOT NULL DEFAULT 'db',
                  note TEXT,
                  payload_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS app_config_timeline (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_type TEXT NOT NULL,
                  actor TEXT NOT NULL,
                  module TEXT,
                  config_key TEXT,
                  project_id TEXT,
                  decision_id TEXT,
                  risk_level TEXT,
                  reason TEXT,
                  payload_json TEXT,
                  created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_app_config_timeline_created_at ON app_config_timeline(created_at);
                """
            )
            self._ensure_columns()
            self._ensure_indexes()
            self._conn.commit()

    def _ensure_columns(self) -> None:
        self._ensure_column("app_config", "project_id", "TEXT")
        self._ensure_column("app_config_audit", "project_id", "TEXT")
        self._ensure_column("app_config_audit", "decision_id", "TEXT")
        self._ensure_column("app_config_audit", "reason", "TEXT")
        self._ensure_column("app_config_audit", "risk_level", "TEXT")
        self._ensure_column("app_config_snapshot", "note", "TEXT")

    def _ensure_indexes(self) -> None:
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_config_project_id ON app_config(project_id)"
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_app_config_project_key ON app_config(COALESCE(project_id, ''), key)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_config_audit_project_id ON app_config_audit(project_id)"
        )

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        rows = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row["name"]) for row in rows}
        if column in existing:
            return
        self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def list_entries(
        self,
        *,
        search: Optional[str],
        scope: Optional[str],
        project_id: Optional[str],
        type_filter: Optional[str],
        page: int,
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        clauses = ["1=1"]
        params: List[Any] = []

        if search:
            clauses.append("(key LIKE ? OR value_json LIKE ?)")
            needle = f"%{search}%"
            params.extend([needle, needle])
        if scope:
            clauses.append("scope = ?")
            params.append(scope)
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        else:
            clauses.append("(project_id IS NULL OR project_id = '')")
        if type_filter:
            clauses.append("LOWER(value_type) = ?")
            params.append(type_filter.lower())

        where_sql = " AND ".join(clauses)
        offset = (page - 1) * limit

        with self._lock:
            total_row = self._conn.execute(
                f"SELECT COUNT(*) AS count FROM app_config WHERE {where_sql}",
                tuple(params),
            ).fetchone()
            rows = self._conn.execute(
                f"""
                SELECT *
                FROM app_config
                WHERE {where_sql}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                tuple(params + [limit, offset]),
            ).fetchall()

        total = int(total_row["count"]) if total_row else 0
        return [self._row_to_entry(row) for row in rows], total

    def get_entry(self, key: str, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            if project_id:
                db_key = _encode_key(key, project_id)
                row = self._conn.execute(
                    """
                    SELECT * FROM app_config
                    WHERE key = ? AND project_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (db_key, project_id),
                ).fetchone()
            else:
                row = self._conn.execute(
                    """
                    SELECT * FROM app_config
                    WHERE key = ? AND (project_id IS NULL OR project_id = '')
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (_encode_key(key, None),),
                ).fetchone()
        return self._row_to_entry(row)

    def get_entry_by_id(self, entry_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT * FROM app_config
                WHERE id = ?
                LIMIT 1
                """,
                (entry_id,),
            ).fetchone()
        return self._row_to_entry(row)

    def upsert_entry(
        self,
        *,
        key: str,
        value: Any,
        value_type: str,
        module: str,
        scope: str,
        project_id: Optional[str],
        description: str,
        source: str,
        schema_version: int,
        is_secret: bool,
        is_hot_reload: bool,
        actor: str,
        audit_op: str = "set",
        decision_id: Optional[str] = None,
        reason: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        del description  # reserved for future schema, keep API-compatible input.
        now = _now_iso()
        payload_json = json.dumps(value, ensure_ascii=False, sort_keys=True)
        new_hash = _sha256_text(payload_json)
        op = audit_op or "set"
        db_key = _encode_key(key, project_id)

        with self._lock:
            existing = self._conn.execute(
                """
                SELECT * FROM app_config
                WHERE key = ? AND COALESCE(project_id, '') = COALESCE(?, '')
                LIMIT 1
                """,
                (db_key, project_id),
            ).fetchone()

            if existing is None:
                version = 1
                self._conn.execute(
                    """
                    INSERT INTO app_config (
                      key, value_json, value_type, module, scope,
                      project_id, is_secret, is_hot_reload, schema_version, source,
                      version, updated_at, updated_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        db_key,
                        payload_json,
                        value_type,
                        module,
                        scope,
                        project_id,
                        int(is_secret),
                        int(is_hot_reload),
                        schema_version,
                        source,
                        version,
                        now,
                        actor,
                    ),
                )
                old_hash = None
                old_preview = None
                op = audit_op or "set"
            else:
                version = int(existing["version"]) + 1
                old_raw = existing["value_json"] or ""
                old_hash = _sha256_text(old_raw)
                old_preview = old_raw[:300]
                self._conn.execute(
                    """
                    UPDATE app_config
                    SET value_json = ?, value_type = ?, module = ?, scope = ?,
                        project_id = ?, is_secret = ?, is_hot_reload = ?, schema_version = ?,
                        source = ?, version = ?, updated_at = ?, updated_by = ?
                    WHERE key = ? AND COALESCE(project_id, '') = COALESCE(?, '')
                    """,
                    (
                        payload_json,
                        value_type,
                        module,
                        scope,
                        project_id,
                        int(is_secret),
                        int(is_hot_reload),
                        schema_version,
                        source,
                        version,
                        now,
                        actor,
                        db_key,
                        project_id,
                    ),
                )
                if old_raw != payload_json:
                    op = audit_op or "set"

            self._conn.execute(
                """
                INSERT INTO app_config_audit (
                  config_key, module, project_id, actor, op, old_hash, new_hash,
                  old_preview, new_preview, schema_version, source, decision_id, reason, risk_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    db_key,
                    module,
                    project_id,
                    actor,
                    op,
                    old_hash,
                    new_hash,
                    old_preview,
                    payload_json[:300],
                    schema_version,
                    source,
                    decision_id,
                    reason,
                    risk_level,
                    now,
                ),
            )
            self._append_timeline_no_commit(
                event_type=f"config.{op}",
                actor=actor,
                module=module,
                config_key=db_key,
                project_id=project_id,
                decision_id=decision_id,
                risk_level=risk_level,
                reason=reason,
                payload={"scope": scope, "source": source, "schema_version": schema_version},
                created_at=now,
            )
            self._conn.commit()

        entry = self.get_entry(key, project_id=project_id)
        if entry is None:
            raise RuntimeError("Failed to load entry after upsert")
        return entry

    def list_modules(self) -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT module FROM app_config ORDER BY module ASC"
            ).fetchall()
        return [str(row["module"]) for row in rows if row["module"]]

    def delete_entry_by_id(
        self,
        *,
        entry_id: int,
        actor: str,
        decision_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        now = _now_iso()
        with self._lock:
            row = self._conn.execute(
                """
                SELECT * FROM app_config
                WHERE id = ?
                LIMIT 1
                """,
                (entry_id,),
            ).fetchone()
            if row is None:
                return None

            entry = self._row_to_entry(row)
            if entry is None:
                return None

            old_raw = row["value_json"] or ""
            old_hash = _sha256_text(old_raw)
            self._conn.execute(
                """
                DELETE FROM app_config
                WHERE id = ?
                """,
                (entry_id,),
            )
            self._conn.execute(
                """
                INSERT INTO app_config_audit (
                  config_key, module, project_id, actor, op, old_hash, new_hash,
                  old_preview, new_preview, schema_version, source, decision_id, reason, risk_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["key"],
                    row["module"],
                    row["project_id"],
                    actor,
                    "delete",
                    old_hash,
                    old_hash,
                    old_raw[:300],
                    "",
                    int(row["schema_version"]),
                    row["source"],
                    decision_id,
                    reason,
                    "high" if bool(row["is_secret"]) else "medium",
                    now,
                ),
            )
            self._append_timeline_no_commit(
                event_type="config.delete",
                actor=actor,
                module=row["module"],
                config_key=row["key"],
                project_id=row["project_id"],
                decision_id=decision_id,
                risk_level="high" if bool(row["is_secret"]) else "medium",
                reason=reason,
                payload={
                    "scope": row["scope"],
                    "source": row["source"],
                    "schema_version": int(row["schema_version"]),
                },
                created_at=now,
            )
            self._conn.commit()
            return entry

    def list_audit(self, key: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        candidates: List[str] = [key, _encode_key(key, None)]
        if project_id:
            candidates.append(_encode_key(key, project_id))
        placeholders = ", ".join("?" for _ in candidates)
        with self._lock:
            rows = self._conn.execute(
                f"""
                SELECT id, config_key, module, actor, op, old_hash, new_hash,
                       old_preview, new_preview, schema_version, source, project_id,
                       decision_id, reason, risk_level, created_at
                FROM app_config_audit
                WHERE config_key IN ({placeholders})
                ORDER BY id ASC
                """,
                tuple(candidates),
            ).fetchall()
        items: List[Dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            logical_key, _ = _decode_key(str(record["config_key"]))
            record["config_key"] = logical_key
            items.append(record)
        return items

    def get_audit_record(self, audit_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, config_key, module, actor, op, old_hash, new_hash,
                       old_preview, new_preview, schema_version, source, project_id,
                       decision_id, reason, risk_level, created_at
                FROM app_config_audit
                WHERE id = ?
                """,
                (audit_id,),
            ).fetchone()
        if row is None:
            return None
        record = dict(row)
        logical_key, _ = _decode_key(str(record["config_key"]))
        record["config_key"] = logical_key
        return record

    def create_snapshot(
        self,
        *,
        snapshot_id: str,
        scope: str,
        project_id: Optional[str],
        actor: str,
        source: str,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = _now_iso()
        entries, _ = self.list_entries(
            search=None,
            scope=scope if scope != "all" else None,
            project_id=project_id,
            type_filter=None,
            page=1,
            limit=10000,
        )
        snapshot_entries: List[Dict[str, Any]] = []
        for entry in entries:
            clone = dict(entry)
            if bool(clone.get("is_secret", False)):
                raw_ref = str(clone.get("value") or "")
                clone["secret_configured"] = bool(raw_ref)
                clone["value"] = ""
                clone["secret_ref_hash"] = _sha256_text(raw_ref) if raw_ref else ""
            snapshot_entries.append(clone)
        payload = {"entries": snapshot_entries}
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO app_config_snapshot (
                  snapshot_id, scope, project_id, actor, source, note, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (snapshot_id, scope, project_id, actor, source, note, payload_json, now),
            )
            self._append_timeline_no_commit(
                event_type="config.snapshot.created",
                actor=actor,
                module=None,
                config_key=None,
                project_id=project_id,
                decision_id=None,
                risk_level=None,
                reason=None,
                payload={"snapshot_id": snapshot_id, "scope": scope},
                created_at=now,
            )
            self._conn.commit()
        return {
            "snapshot_id": snapshot_id,
            "scope": scope,
            "project_id": project_id,
            "actor": actor,
            "source": source,
            "note": note,
            "created_at": now,
            "payload": payload,
        }

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT snapshot_id, scope, project_id, actor, source, payload_json, created_at
                , note
                FROM app_config_snapshot
                WHERE snapshot_id = ?
                """,
                (snapshot_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "snapshot_id": row["snapshot_id"],
            "scope": row["scope"],
            "project_id": row["project_id"],
            "actor": row["actor"],
            "source": row["source"],
            "note": row["note"],
            "payload": json.loads(row["payload_json"] or "{}"),
            "created_at": row["created_at"],
        }

    def list_timeline(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, event_type, actor, module, config_key, project_id,
                       decision_id, risk_level, reason, payload_json, created_at
                FROM app_config_timeline
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(limit, 1),),
            ).fetchall()
        items = []
        for row in rows:
            items.append(
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "actor": row["actor"],
                    "module": row["module"],
                    "config_key": row["config_key"],
                    "project_id": row["project_id"],
                    "decision_id": row["decision_id"],
                    "risk_level": row["risk_level"],
                    "reason": row["reason"],
                    "payload": json.loads(row["payload_json"] or "{}"),
                    "created_at": row["created_at"],
                }
            )
        return items

    def append_timeline(
        self,
        *,
        event_type: str,
        actor: str,
        module: Optional[str],
        config_key: Optional[str],
        project_id: Optional[str],
        decision_id: Optional[str],
        risk_level: Optional[str],
        reason: Optional[str],
        payload: Optional[Dict[str, Any]],
    ) -> None:
        with self._lock:
            self._append_timeline_no_commit(
                event_type=event_type,
                actor=actor,
                module=module,
                config_key=config_key,
                project_id=project_id,
                decision_id=decision_id,
                risk_level=risk_level,
                reason=reason,
                payload=payload,
                created_at=_now_iso(),
            )
            self._conn.commit()

    def _append_timeline_no_commit(
        self,
        *,
        event_type: str,
        actor: str,
        module: Optional[str],
        config_key: Optional[str],
        project_id: Optional[str],
        decision_id: Optional[str],
        risk_level: Optional[str],
        reason: Optional[str],
        payload: Optional[Dict[str, Any]],
        created_at: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO app_config_timeline (
              event_type, actor, module, config_key, project_id,
              decision_id, risk_level, reason, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                actor,
                module,
                config_key,
                project_id,
                decision_id,
                risk_level,
                reason,
                json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
                created_at,
            ),
        )

    @staticmethod
    def _row_to_entry(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        value_obj = json.loads(row["value_json"])
        value_type = row["value_type"]
        logical_key, embedded_project = _decode_key(str(row["key"]))
        return {
            "id": row["id"],
            "key": logical_key,
            "value": _render_value(value_obj),
            "type": _type_to_label(value_type),
            "scope": row["scope"],
            "project_id": row["project_id"] or embedded_project,
            "description": "",
            "lastModified": row["updated_at"],
            "module": row["module"],
            "value_type": value_type,
            "is_secret": bool(row["is_secret"]),
            "is_hot_reload": bool(row["is_hot_reload"]),
            "schema_version": int(row["schema_version"]),
            "source": row["source"],
            "version": int(row["version"]),
            "updated_by": row["updated_by"],
        }


_STORE: Optional[ConfigStore] = None


def get_config_store() -> ConfigStore:
    global _STORE
    if _STORE is not None:
        return _STORE

    configured = os.getenv("OCTOPUSOS_CONFIG_DB", "").strip()
    if configured:
        db_path = Path(configured)
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
    else:
        db_path = component_db_path("octopusos")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    _STORE = ConfigStore(str(db_path))
    return _STORE


def _reset_config_store_for_tests() -> None:
    global _STORE
    _STORE = None
