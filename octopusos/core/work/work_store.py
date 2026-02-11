from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.core.work.models import WorkItem, WorkStatus, WorkType
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid


def _row_to_work(row) -> WorkItem:
    return WorkItem(
        work_id=str(row[0]),
        type=str(row[1]),  # type: ignore[arg-type]
        title=str(row[2]),
        status=str(row[3]),  # type: ignore[arg-type]
        priority=int(row[4]),
        scope_type=str(row[5]),
        scope_id=str(row[6]),
        source_card_id=str(row[7]) if row[7] is not None else None,
        created_at_ms=int(row[8]),
        updated_at_ms=int(row[9]),
        started_at_ms=int(row[10]) if row[10] is not None else None,
        finished_at_ms=int(row[11]) if row[11] is not None else None,
        summary=str(row[12] or ""),
        detail_json=str(row[13] or "{}"),
        evidence_ref_json=str(row[14] or "[]"),
    )


@dataclass(frozen=True)
class ListResult:
    items: list[WorkItem]


class WorkStore:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def create(
        self,
        *,
        type: WorkType,
        title: str,
        scope_type: str,
        scope_id: str,
        source_card_id: Optional[str] = None,
        priority: int = 3,
        summary: str = "",
        detail: dict | None = None,
    ) -> WorkItem:
        wid = ulid()
        ts = now_ms()
        detail_json = json.dumps(detail or {}, ensure_ascii=False)

        def _op(conn: sqlite3.Connection) -> WorkItem:
            conn.execute(
                """
                INSERT INTO work_list_items (
                  work_id, type, title, status, priority,
                  scope_type, scope_id, source_card_id,
                  created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                  summary, detail_json, evidence_ref_json
                )
                VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, '[]')
                """,
                (
                    wid,
                    str(type),
                    str(title),
                    int(max(1, min(5, int(priority)))),
                    str(scope_type),
                    str(scope_id),
                    str(source_card_id) if source_card_id else None,
                    int(ts),
                    int(ts),
                    str(summary or ""),
                    detail_json,
                ),
            )
            row = conn.execute(
                """
                SELECT work_id, type, title, status, priority, scope_type, scope_id, source_card_id,
                       created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                       summary, detail_json, evidence_ref_json
                FROM work_list_items
                WHERE work_id = ?
                """,
                (wid,),
            ).fetchone()
            return _row_to_work(row)

        return self._writer.submit(_op, timeout=10.0)

    def find_latest_for_card(self, *, source_card_id: str, type: WorkType) -> Optional[WorkItem]:
        def _op(conn: sqlite3.Connection) -> Optional[WorkItem]:
            row = conn.execute(
                """
                SELECT work_id, type, title, status, priority, scope_type, scope_id, source_card_id,
                       created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                       summary, detail_json, evidence_ref_json
                FROM work_list_items
                WHERE source_card_id = ? AND type = ?
                ORDER BY updated_at_ms DESC
                LIMIT 1
                """,
                (str(source_card_id), str(type)),
            ).fetchone()
            return _row_to_work(row) if row else None

        return self._writer.submit(_op, timeout=10.0)

    def list(
        self,
        *,
        statuses: list[str] | None = None,
        limit: int = 50,
    ) -> ListResult:
        statuses = statuses or ["queued", "running", "failed", "succeeded"]
        safe = [s for s in statuses if isinstance(s, str) and s]
        safe = safe[:10] if safe else ["queued", "running"]
        lim = int(max(1, min(limit, 500)))

        def _op(conn: sqlite3.Connection) -> ListResult:
            rows = conn.execute(
                f"""
                SELECT work_id, type, title, status, priority, scope_type, scope_id, source_card_id,
                       created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                       summary, detail_json, evidence_ref_json
                FROM work_list_items
                WHERE status IN ({",".join(["?"] * len(safe))})
                ORDER BY updated_at_ms DESC
                LIMIT ?
                """,
                tuple(safe + [lim]),
            ).fetchall()
            return ListResult(items=[_row_to_work(r) for r in rows or []])

        return self._writer.submit(_op, timeout=10.0)

    def get(self, *, work_id: str) -> Optional[WorkItem]:
        def _op(conn: sqlite3.Connection) -> Optional[WorkItem]:
            row = conn.execute(
                """
                SELECT work_id, type, title, status, priority, scope_type, scope_id, source_card_id,
                       created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
                       summary, detail_json, evidence_ref_json
                FROM work_list_items
                WHERE work_id = ?
                """,
                (str(work_id),),
            ).fetchone()
            return _row_to_work(row) if row else None

        return self._writer.submit(_op, timeout=10.0)

    def update_status(
        self,
        *,
        work_id: str,
        status: WorkStatus,
        summary: Optional[str] = None,
        evidence_refs: Optional[list[dict]] = None,
    ) -> None:
        ts = now_ms()
        evidence_json = json.dumps(evidence_refs or [], ensure_ascii=False) if evidence_refs is not None else None

        def _op(conn: sqlite3.Connection) -> None:
            row = conn.execute(
                "SELECT status, started_at_ms, finished_at_ms, evidence_ref_json FROM work_list_items WHERE work_id = ?",
                (str(work_id),),
            ).fetchone()
            if not row:
                return
            prev_status = str(row[0] or "")
            started_at = int(row[1]) if row[1] is not None else None
            finished_at = int(row[2]) if row[2] is not None else None
            next_started = started_at
            next_finished = finished_at
            if status == "running" and started_at is None:
                next_started = int(ts)
            if status in {"succeeded", "failed", "cancelled"} and finished_at is None:
                next_finished = int(ts)

            next_evidence = evidence_json if evidence_json is not None else str(row[3] or "[]")
            conn.execute(
                """
                UPDATE work_list_items
                SET status = ?,
                    updated_at_ms = ?,
                    started_at_ms = ?,
                    finished_at_ms = ?,
                    summary = COALESCE(?, summary),
                    evidence_ref_json = ?
                WHERE work_id = ?
                """,
                (
                    str(status),
                    int(ts),
                    next_started,
                    next_finished,
                    summary,
                    next_evidence,
                    str(work_id),
                ),
            )

        self._writer.submit(_op, timeout=10.0)
