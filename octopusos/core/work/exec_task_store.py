from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.core.work.models import ExecTask, TaskRisk, TaskStatus
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid


def _row_to_task(row) -> ExecTask:
    return ExecTask(
        task_id=str(row[0]),
        work_id=str(row[1]) if row[1] is not None else None,
        card_id=str(row[2]) if row[2] is not None else None,
        task_type=str(row[3]),
        status=str(row[4]),  # type: ignore[arg-type]
        risk_level=str(row[5]),  # type: ignore[arg-type]
        requires_confirmation=bool(int(row[6] or 0)),
        created_at_ms=int(row[7]),
        updated_at_ms=int(row[8]),
        started_at_ms=int(row[9]) if row[9] is not None else None,
        finished_at_ms=int(row[10]) if row[10] is not None else None,
        input_json=str(row[11] or "{}"),
        output_json=str(row[12] or "{}"),
        error_json=str(row[13]) if row[13] is not None else None,
        evidence_paths_json=str(row[14] or "[]"),
        idempotency_key=str(row[15]),
    )


@dataclass(frozen=True)
class ListResult:
    items: list[ExecTask]


class ExecTaskStore:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def enqueue(
        self,
        *,
        task_type: str,
        idempotency_key: str,
        work_id: Optional[str] = None,
        card_id: Optional[str] = None,
        risk_level: TaskRisk = "low",
        requires_confirmation: bool = False,
        input_obj: dict | None = None,
    ) -> str:
        tid = ulid()
        ts = now_ms()
        input_json = json.dumps(input_obj or {}, ensure_ascii=False)

        def _op(conn: sqlite3.Connection) -> str:
            try:
                conn.execute(
                    """
                    INSERT INTO exec_tasks (
                      task_id, work_id, card_id, task_type, status, risk_level, requires_confirmation,
                      created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                      input_json, output_json, error_json, evidence_paths_json, idempotency_key
                    )
                    VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?, NULL, NULL, ?, '{}', NULL, '[]', ?)
                    """,
                    (
                        tid,
                        str(work_id) if work_id else None,
                        str(card_id) if card_id else None,
                        str(task_type),
                        str(risk_level),
                        1 if requires_confirmation else 0,
                        int(ts),
                        int(ts),
                        input_json,
                        str(idempotency_key),
                    ),
                )
                return tid
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT task_id FROM exec_tasks WHERE idempotency_key = ? LIMIT 1",
                    (str(idempotency_key),),
                ).fetchone()
                return str(row[0]) if row else tid

        return self._writer.submit(_op, timeout=10.0)

    def list(self, *, statuses: list[str] | None = None, limit: int = 50) -> ListResult:
        statuses = statuses or ["queued", "running", "failed", "succeeded"]
        safe = [s for s in statuses if isinstance(s, str) and s]
        safe = safe[:10] if safe else ["queued", "running"]
        lim = int(max(1, min(limit, 500)))

        def _op(conn: sqlite3.Connection) -> ListResult:
            rows = conn.execute(
                f"""
                SELECT task_id, work_id, card_id, task_type, status, risk_level, requires_confirmation,
                       created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                       input_json, output_json, error_json, evidence_paths_json, idempotency_key
                FROM exec_tasks
                WHERE status IN ({",".join(["?"] * len(safe))})
                ORDER BY updated_at_ms DESC
                LIMIT ?
                """,
                tuple(safe + [lim]),
            ).fetchall()
            return ListResult(items=[_row_to_task(r) for r in rows or []])

        return self._writer.submit(_op, timeout=10.0)

    def get(self, *, task_id: str) -> Optional[ExecTask]:
        def _op(conn: sqlite3.Connection) -> Optional[ExecTask]:
            row = conn.execute(
                """
                SELECT task_id, work_id, card_id, task_type, status, risk_level, requires_confirmation,
                       created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                       input_json, output_json, error_json, evidence_paths_json, idempotency_key
                FROM exec_tasks
                WHERE task_id = ?
                """,
                (str(task_id),),
            ).fetchone()
            return _row_to_task(row) if row else None

        return self._writer.submit(_op, timeout=10.0)

    def cancel(self, *, task_id: str) -> None:
        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE exec_tasks
                SET status='cancelled', updated_at_ms=?, finished_at_ms=COALESCE(finished_at_ms, ?)
                WHERE task_id=? AND status IN ('queued','running')
                """,
                (int(ts), int(ts), str(task_id)),
            )

        self._writer.submit(_op, timeout=10.0)

    def retry(self, *, task_id: str) -> None:
        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE exec_tasks
                SET status='queued', updated_at_ms=?, started_at_ms=NULL, finished_at_ms=NULL, error_json=NULL
                WHERE task_id=? AND status IN ('failed','cancelled')
                """,
                (int(ts), str(task_id)),
            )

        self._writer.submit(_op, timeout=10.0)

    def claim_queued(self, *, limit: int, safe_only: bool) -> list[ExecTask]:
        ts = now_ms()
        lim = int(max(1, min(limit, 50)))

        def _op(conn: sqlite3.Connection) -> list[ExecTask]:
            where = "status = 'queued'"
            params: list[object] = []
            if safe_only:
                where += " AND risk_level = 'low' AND requires_confirmation = 0"
            rows = conn.execute(
                f"""
                SELECT task_id, work_id, card_id, task_type, status, risk_level, requires_confirmation,
                       created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                       input_json, output_json, error_json, evidence_paths_json, idempotency_key
                FROM exec_tasks
                WHERE {where}
                ORDER BY created_at_ms ASC
                LIMIT ?
                """,
                tuple(params + [lim]),
            ).fetchall()
            task_ids = [str(r[0]) for r in rows or []]
            if not task_ids:
                return []
            conn.executemany(
                """
                UPDATE exec_tasks
                SET status='running', updated_at_ms=?, started_at_ms=COALESCE(started_at_ms, ?)
                WHERE task_id=? AND status='queued'
                """,
                [(int(ts), int(ts), tid) for tid in task_ids],
            )
            # Re-read claimed tasks.
            claimed = conn.execute(
                f"""
                SELECT task_id, work_id, card_id, task_type, status, risk_level, requires_confirmation,
                       created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                       input_json, output_json, error_json, evidence_paths_json, idempotency_key
                FROM exec_tasks
                WHERE task_id IN ({",".join(["?"] * len(task_ids))})
                """,
                tuple(task_ids),
            ).fetchall()
            return [_row_to_task(r) for r in claimed or []]

        return self._writer.submit(_op, timeout=10.0) or []

    def finish(
        self,
        *,
        task_id: str,
        status: TaskStatus,
        output_json: str,
        evidence_paths: list[str],
        error_json: Optional[str] = None,
    ) -> None:
        ts = now_ms()
        evidence_json = json.dumps(evidence_paths or [], ensure_ascii=False)

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE exec_tasks
                SET status=?, updated_at_ms=?, finished_at_ms=COALESCE(finished_at_ms, ?),
                    output_json=?, evidence_paths_json=?, error_json=?
                WHERE task_id=?
                """,
                (
                    str(status),
                    int(ts),
                    int(ts),
                    str(output_json or "{}"),
                    evidence_json,
                    error_json,
                    str(task_id),
                ),
            )

        self._writer.submit(_op, timeout=10.0)

