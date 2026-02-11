"""SQLite-backed store for call sessions, events, transcripts, and voice contacts."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class IdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused with a different request payload."""


class CallStore:
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
                CREATE TABLE IF NOT EXISTS call_sessions (
                  id TEXT PRIMARY KEY,
                  runtime TEXT NOT NULL,
                  provider_id TEXT,
                  model_id TEXT,
                  voice_profile_id TEXT,
                  status TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  connected_at TEXT,
                  ended_at TEXT,
                  error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS call_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  call_session_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  payload_json TEXT,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(call_session_id) REFERENCES call_sessions(id)
                );

                CREATE TABLE IF NOT EXISTS call_transcripts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  call_session_id TEXT NOT NULL,
                  speaker TEXT NOT NULL,
                  text TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(call_session_id) REFERENCES call_sessions(id)
                );

                CREATE TABLE IF NOT EXISTS voice_contacts (
                  id TEXT PRIMARY KEY,
                  display_name TEXT NOT NULL,
                  runtime TEXT NOT NULL,
                  provider_id TEXT,
                  model_id TEXT,
                  voice_profile_id TEXT,
                  prefs_json TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS call_idempotency (
                  idempotency_key TEXT PRIMARY KEY,
                  request_hash TEXT NOT NULL,
                  call_session_id TEXT NOT NULL,
                  created_at INTEGER NOT NULL,
                  expires_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_call_idempotency_expires_at
                  ON call_idempotency(expires_at);

                CREATE TABLE IF NOT EXISTS call_task_links (
                  call_session_id TEXT PRIMARY KEY,
                  task_id TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(call_session_id) REFERENCES call_sessions(id)
                );
                """
            )
            self._conn.commit()

    def create_call_session(
        self,
        runtime: str,
        provider_id: Optional[str],
        model_id: Optional[str],
        voice_profile_id: Optional[str],
        *,
        idempotency_key: Optional[str] = None,
        request_hash: Optional[str] = None,
        ttl_seconds: int = 600,
    ) -> tuple[Dict[str, Any], bool]:
        if idempotency_key and not request_hash:
            raise ValueError("request_hash is required when idempotency_key is set")

        call_session_id = _new_id("call")
        created_at = _now_iso()
        now_ts = int(time.time())
        created = True

        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                if idempotency_key:
                    existing = self._conn.execute(
                        """
                        SELECT request_hash, call_session_id, expires_at
                        FROM call_idempotency
                        WHERE idempotency_key = ?
                        """,
                        (idempotency_key,),
                    ).fetchone()

                    if existing is not None:
                        if existing["expires_at"] < now_ts:
                            self._conn.execute(
                                "DELETE FROM call_idempotency WHERE idempotency_key = ?",
                                (idempotency_key,),
                            )
                        elif existing["request_hash"] != request_hash:
                            self._conn.rollback()
                            raise IdempotencyConflictError("idempotency_key_reuse_with_different_payload")
                        else:
                            session_row = self._conn.execute(
                                "SELECT * FROM call_sessions WHERE id = ?",
                                (existing["call_session_id"],),
                            ).fetchone()
                            if session_row is not None:
                                self._conn.commit()
                                created = False
                                return self._row_to_dict(session_row), created  # type: ignore[return-value]
                            self._conn.execute(
                                "DELETE FROM call_idempotency WHERE idempotency_key = ?",
                                (idempotency_key,),
                            )

                self._conn.execute(
                    """
                    INSERT INTO call_sessions (
                      id, runtime, provider_id, model_id, voice_profile_id, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (call_session_id, runtime, provider_id, model_id, voice_profile_id, "created", created_at),
                )

                self._insert_call_event_no_commit(
                    call_session_id=call_session_id,
                    event_type="created",
                    payload={
                        "runtime": runtime,
                        "provider_id": provider_id,
                        "model_id": model_id,
                        "voice_profile_id": voice_profile_id,
                    },
                    created_at=created_at,
                )

                if idempotency_key:
                    expires_at = now_ts + max(ttl_seconds, 1)
                    self._conn.execute(
                        """
                        INSERT INTO call_idempotency (
                          idempotency_key, request_hash, call_session_id, created_at, expires_at
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (idempotency_key, request_hash, call_session_id, now_ts, expires_at),
                    )

                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

        return self.get_call_session(call_session_id), created  # type: ignore[return-value]

    def get_call_session(self, call_session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM call_sessions WHERE id = ?",
                (call_session_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def update_call_status(
        self,
        call_session_id: str,
        status: str,
        *,
        error_message: Optional[str] = None,
    ) -> None:
        now = _now_iso()
        set_parts = ["status = ?", "error_message = ?"]
        args: List[Any] = [status, error_message]

        if status == "connected":
            set_parts.append("connected_at = ?")
            args.append(now)
        if status == "ended":
            set_parts.append("ended_at = ?")
            args.append(now)
        args.append(call_session_id)

        with self._lock:
            self._conn.execute(
                f"UPDATE call_sessions SET {', '.join(set_parts)} WHERE id = ?",
                tuple(args),
            )
            self._conn.commit()

    def add_call_event(self, call_session_id: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload_json = json.dumps(payload or {}, ensure_ascii=True)
        created_at = _now_iso()
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO call_events (call_session_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (call_session_id, event_type, payload_json, created_at),
            )
            event_id = cursor.lastrowid
            self._conn.commit()

        return {
            "id": event_id,
            "call_session_id": call_session_id,
            "event_type": event_type,
            "payload": payload or {},
            "created_at": created_at,
        }

    def _insert_call_event_no_commit(
        self,
        *,
        call_session_id: str,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> None:
        payload_json = json.dumps(payload or {}, ensure_ascii=True)
        self._conn.execute(
            """
            INSERT INTO call_events (call_session_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (call_session_id, event_type, payload_json, created_at or _now_iso()),
        )

    def list_call_events(self, call_session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, call_session_id, event_type, payload_json, created_at
                FROM call_events
                WHERE call_session_id = ?
                ORDER BY id ASC
                """,
                (call_session_id,),
            ).fetchall()

        events: List[Dict[str, Any]] = []
        for row in rows:
            events.append(
                {
                    "id": row["id"],
                    "call_session_id": row["call_session_id"],
                    "event_type": row["event_type"],
                    "payload": json.loads(row["payload_json"] or "{}"),
                    "created_at": row["created_at"],
                }
            )
        return events

    def add_transcript(self, call_session_id: str, speaker: str, text: str) -> Dict[str, Any]:
        created_at = _now_iso()
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO call_transcripts (call_session_id, speaker, text, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (call_session_id, speaker, text, created_at),
            )
            transcript_id = cursor.lastrowid
            self._conn.commit()

        return {
            "id": transcript_id,
            "call_session_id": call_session_id,
            "speaker": speaker,
            "text": text,
            "created_at": created_at,
        }

    def list_transcripts(self, call_session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, call_session_id, speaker, text, created_at
                FROM call_transcripts
                WHERE call_session_id = ?
                ORDER BY id ASC
                """,
                (call_session_id,),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "call_session_id": row["call_session_id"],
                "speaker": row["speaker"],
                "text": row["text"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_voice_contacts(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, display_name, runtime, provider_id, model_id, voice_profile_id,
                       prefs_json, created_at, updated_at
                FROM voice_contacts
                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [self._voice_contact_row_to_dict(row) for row in rows]

    def create_voice_contact(
        self,
        display_name: str,
        runtime: str,
        provider_id: Optional[str],
        model_id: Optional[str],
        voice_profile_id: Optional[str],
        prefs_json: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        contact_id = _new_id("vc")
        now = _now_iso()
        prefs_raw = json.dumps(prefs_json or {}, ensure_ascii=True)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO voice_contacts (
                  id, display_name, runtime, provider_id, model_id, voice_profile_id,
                  prefs_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contact_id,
                    display_name,
                    runtime,
                    provider_id,
                    model_id,
                    voice_profile_id,
                    prefs_raw,
                    now,
                    now,
                ),
            )
            self._conn.commit()

        return self.get_voice_contact(contact_id)  # type: ignore[return-value]

    def get_voice_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, display_name, runtime, provider_id, model_id, voice_profile_id,
                       prefs_json, created_at, updated_at
                FROM voice_contacts
                WHERE id = ?
                """,
                (contact_id,),
            ).fetchone()
        return self._voice_contact_row_to_dict(row)

    def update_voice_contact(
        self,
        contact_id: str,
        display_name: str,
        runtime: str,
        provider_id: Optional[str],
        model_id: Optional[str],
        voice_profile_id: Optional[str],
        prefs_json: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        now = _now_iso()
        prefs_raw = json.dumps(prefs_json or {}, ensure_ascii=True)
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE voice_contacts
                SET display_name = ?, runtime = ?, provider_id = ?, model_id = ?,
                    voice_profile_id = ?, prefs_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    display_name,
                    runtime,
                    provider_id,
                    model_id,
                    voice_profile_id,
                    prefs_raw,
                    now,
                    contact_id,
                ),
            )
            self._conn.commit()

        if cursor.rowcount == 0:
            return None
        return self.get_voice_contact(contact_id)

    def delete_voice_contact(self, contact_id: str) -> bool:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM voice_contacts WHERE id = ?", (contact_id,))
            self._conn.commit()
        return cursor.rowcount > 0

    def set_call_task_link(self, call_session_id: str, task_id: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO call_task_links (call_session_id, task_id, created_at)
                VALUES (?, ?, ?)
                """,
                (call_session_id, task_id, _now_iso()),
            )
            self._conn.commit()

    def get_call_task_link(self, call_session_id: str) -> Optional[Dict[str, str]]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT call_session_id, task_id, created_at
                FROM call_task_links
                WHERE call_session_id = ?
                """,
                (call_session_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "call_session_id": row["call_session_id"],
            "task_id": row["task_id"],
            "created_at": row["created_at"],
        }

    def cleanup_old_sessions(self, days: int = 30, max_rows: Optional[int] = None) -> Dict[str, int]:
        removed_by_age = 0
        removed_by_capacity = 0

        with self._lock:
            cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=max(days, 0))).isoformat().replace("+00:00", "Z")
            age_rows = self._conn.execute(
                """
                SELECT id FROM call_sessions
                WHERE status NOT IN ('created', 'connected')
                  AND created_at < ?
                ORDER BY created_at ASC
                """,
                (cutoff_iso,),
            ).fetchall()
            age_ids = [row["id"] for row in age_rows]
            removed_by_age = self._delete_sessions_by_ids(age_ids)

            if max_rows is not None and max_rows > 0:
                total_rows = self._conn.execute("SELECT COUNT(*) AS count FROM call_sessions").fetchone()["count"]
                overflow = max(total_rows - max_rows, 0)
                if overflow > 0:
                    capacity_rows = self._conn.execute(
                        """
                        SELECT id FROM call_sessions
                        WHERE status NOT IN ('created', 'connected')
                        ORDER BY created_at ASC
                        LIMIT ?
                        """,
                        (overflow,),
                    ).fetchall()
                    capacity_ids = [row["id"] for row in capacity_rows]
                    removed_by_capacity = self._delete_sessions_by_ids(capacity_ids)

            self._conn.execute(
                "DELETE FROM call_idempotency WHERE expires_at < ?",
                (int(time.time()),),
            )
            self._conn.commit()

        return {
            "removed_by_age": removed_by_age,
            "removed_by_capacity": removed_by_capacity,
            "removed_total": removed_by_age + removed_by_capacity,
        }

    def run_configured_cleanup(self) -> Dict[str, int]:
        days_raw = os.getenv("OCTOPUSOS_CALLS_CLEANUP_DAYS", "30").strip()
        max_rows_raw = os.getenv("OCTOPUSOS_CALLS_MAX_SESSIONS", "2000").strip()

        try:
            days = int(days_raw)
        except ValueError:
            days = 30
        if days < 0:
            days = 0

        try:
            max_rows = int(max_rows_raw)
        except ValueError:
            max_rows = 2000
        if max_rows <= 0:
            max_rows = None

        return self.cleanup_old_sessions(days=days, max_rows=max_rows)

    def _delete_sessions_by_ids(self, session_ids: List[str]) -> int:
        if not session_ids:
            return 0
        placeholders = ",".join(["?"] * len(session_ids))
        self._conn.execute(
            f"DELETE FROM call_events WHERE call_session_id IN ({placeholders})",
            tuple(session_ids),
        )
        self._conn.execute(
            f"DELETE FROM call_transcripts WHERE call_session_id IN ({placeholders})",
            tuple(session_ids),
        )
        self._conn.execute(
            f"DELETE FROM call_idempotency WHERE call_session_id IN ({placeholders})",
            tuple(session_ids),
        )
        self._conn.execute(
            f"DELETE FROM call_task_links WHERE call_session_id IN ({placeholders})",
            tuple(session_ids),
        )
        cursor = self._conn.execute(
            f"DELETE FROM call_sessions WHERE id IN ({placeholders})",
            tuple(session_ids),
        )
        self._conn.commit()
        return cursor.rowcount

    @staticmethod
    def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        return {
            "id": row["id"],
            "runtime": row["runtime"],
            "provider_id": row["provider_id"],
            "model_id": row["model_id"],
            "voice_profile_id": row["voice_profile_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "connected_at": row["connected_at"],
            "ended_at": row["ended_at"],
            "error_message": row["error_message"],
        }

    @staticmethod
    def _voice_contact_row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        return {
            "id": row["id"],
            "display_name": row["display_name"],
            "runtime": row["runtime"],
            "provider_id": row["provider_id"],
            "model_id": row["model_id"],
            "voice_profile_id": row["voice_profile_id"],
            "prefs_json": json.loads(row["prefs_json"] or "{}"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


_STORE: Optional[CallStore] = None


def get_call_store() -> CallStore:
    global _STORE
    if _STORE is not None:
        return _STORE

    configured = os.getenv("OCTOPUSOS_CALLS_DB", "store/webui_calls.sqlite")
    db_path = Path(configured)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _STORE = CallStore(str(db_path))
    _STORE.run_configured_cleanup()
    return _STORE
