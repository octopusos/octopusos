"""Shared stream event persistence for coding/demo runs."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from octopusos.store import get_db

_WRITE_LOCK = threading.Lock()
_SCHEMA_READY = False



def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()



def ensure_stream_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _WRITE_LOCK:
        if _SCHEMA_READY:
            return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stream_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                ts TEXT NOT NULL,
                type TEXT NOT NULL,
                task_id TEXT,
                role TEXT,
                demo_stage TEXT,
                plan_id TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        columns = {row[1] for row in cursor.execute("PRAGMA table_info(stream_events)").fetchall()}
        if "role" not in columns:
            cursor.execute("ALTER TABLE stream_events ADD COLUMN role TEXT")
        if "demo_stage" not in columns:
            cursor.execute("ALTER TABLE stream_events ADD COLUMN demo_stage TEXT")
        if "plan_id" not in columns:
            cursor.execute("ALTER TABLE stream_events ADD COLUMN plan_id TEXT")
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_stream_events_session_run_seq
            ON stream_events(session_id, run_id, seq)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_stream_events_session_run_id
            ON stream_events(session_id, run_id, id)
            """
        )
        conn.commit()
        _SCHEMA_READY = True



def next_seq(session_id: str, run_id: str) -> int:
    ensure_stream_schema()
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM stream_events WHERE session_id = ? AND run_id = ?",
        (session_id, run_id),
    ).fetchone()
    max_seq = int(row[0] if row else 0)
    return max_seq + 1



def append_event(
    *,
    session_id: str,
    run_id: str,
    event_type: str,
    payload: Dict[str, Any],
    task_id: Optional[str] = None,
    role: Optional[str] = None,
    demo_stage: Optional[str] = None,
    plan_id: Optional[str] = None,
    seq: Optional[int] = None,
    ts: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_stream_schema()
    event_ts = ts or _iso_now()
    with _WRITE_LOCK:
        event_seq = seq if seq is not None else next_seq(session_id, run_id)
        envelope = {
            "run_id": run_id,
            "task_id": task_id,
            "session_id": session_id,
            "seq": int(event_seq),
            "ts": event_ts,
            "type": event_type,
            "role": role,
            "demo_stage": demo_stage,
            "plan_id": plan_id,
            "payload": payload if isinstance(payload, dict) else {},
        }

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO stream_events (session_id, run_id, seq, ts, type, task_id, role, demo_stage, plan_id, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                run_id,
                int(event_seq),
                event_ts,
                event_type,
                task_id,
                role,
                demo_stage,
                plan_id,
                json.dumps(envelope["payload"], ensure_ascii=False),
            ),
        )
        conn.commit()
        return envelope



def list_events(*, session_id: str, run_id: str, after_seq: int = 0, limit: int = 2000) -> List[Dict[str, Any]]:
    ensure_stream_schema()
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute(
        """
        SELECT run_id, task_id, session_id, seq, ts, type, role, demo_stage, plan_id, payload_json
        FROM stream_events
        WHERE session_id = ? AND run_id = ? AND seq > ?
        ORDER BY seq ASC
        LIMIT ?
        """,
        (session_id, run_id, max(0, int(after_seq)), max(1, min(int(limit), 5000))),
    ).fetchall()

    events: List[Dict[str, Any]] = []
    for row in rows:
        payload_raw = row[9]
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except Exception:
            payload = {}
        events.append(
            {
                "run_id": row[0],
                "task_id": row[1],
                "session_id": row[2],
                "seq": int(row[3]),
                "ts": row[4],
                "type": row[5],
                "role": row[6],
                "demo_stage": row[7],
                "plan_id": row[8],
                "payload": payload if isinstance(payload, dict) else {},
            }
        )
    return events



def latest_run(session_id: str) -> Optional[Dict[str, Any]]:
    ensure_stream_schema()
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        """
        SELECT run_id, task_id, MAX(seq) AS last_seq, MAX(ts) AS last_ts
        FROM stream_events
        WHERE session_id = ?
        GROUP BY run_id
        ORDER BY last_ts DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "session_id": session_id,
        "run_id": row[0],
        "task_id": row[1],
        "last_seq": int(row[2] or 0),
        "last_ts": row[3],
    }
