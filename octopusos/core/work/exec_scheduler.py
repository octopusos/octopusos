from __future__ import annotations

import json
import time
from dataclasses import dataclass

from octopusos.core.attention.attention_mode import quiet_hours_enabled, quiet_hours_end, quiet_hours_start
from octopusos.core.work.exec_task_store import ExecTaskStore
from octopusos.core.work.work_store import WorkStore
from octopusos.core.work.models import ExecTask
from octopusos.core.work.work_mode import (
    auto_execute_enabled,
    auto_execute_fail_open,
    auto_execute_max_concurrent,
    auto_execute_quiet_hours_respect,
    auto_execute_safe_only,
)
from octopusos.store.timestamp_utils import now_ms


def _parse_hhmm(value: str) -> tuple[int, int] | None:
    raw = (value or "").strip()
    if len(raw) != 5 or raw[2] != ":":
        return None
    try:
        hh = int(raw[0:2])
        mm = int(raw[3:5])
    except Exception:
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return hh, mm


def _in_quiet_hours(now_struct: time.struct_time) -> bool:
    start = _parse_hhmm(quiet_hours_start())
    end = _parse_hhmm(quiet_hours_end())
    if not start or not end:
        return False
    start_min = start[0] * 60 + start[1]
    end_min = end[0] * 60 + end[1]
    now_min = now_struct.tm_hour * 60 + now_struct.tm_min
    if start_min == end_min:
        return False
    if start_min < end_min:
        return start_min <= now_min < end_min
    return now_min >= start_min or now_min < end_min


@dataclass(frozen=True)
class DrainSummary:
    claimed: int
    succeeded: int
    failed: int
    cancelled: int


class ExecScheduler:
    def __init__(self) -> None:
        self._tasks = ExecTaskStore()
        self._work = WorkStore()

    def drain_once(self) -> DrainSummary:
        # Gate by config (fail-closed by default).
        try:
            if not auto_execute_enabled():
                return DrainSummary(claimed=0, succeeded=0, failed=0, cancelled=0)
            if auto_execute_quiet_hours_respect() and quiet_hours_enabled():
                if _in_quiet_hours(time.localtime(now_ms() / 1000.0)):
                    return DrainSummary(claimed=0, succeeded=0, failed=0, cancelled=0)
        except Exception:
            if not auto_execute_fail_open():
                return DrainSummary(claimed=0, succeeded=0, failed=0, cancelled=0)

        max_c = auto_execute_max_concurrent()
        safe_only = auto_execute_safe_only()

        claimed = self._tasks.claim_queued(limit=max_c, safe_only=safe_only)
        if not claimed:
            return DrainSummary(claimed=0, succeeded=0, failed=0, cancelled=0)

        succ = 0
        fail = 0
        canc = 0
        for t in claimed:
            if t.work_id:
                self._work.update_status(work_id=t.work_id, status="running", summary="Task running")
        for t in claimed:
            outcome = self._run_task(t)
            if outcome == "cancelled":
                canc += 1
            elif outcome == "succeeded":
                succ += 1
            else:
                fail += 1
        return DrainSummary(claimed=len(claimed), succeeded=succ, failed=fail, cancelled=canc)

    def _run_task(self, task: ExecTask) -> str:
        # Re-check current status: it could have been cancelled by API.
        fresh = self._tasks.get(task_id=task.task_id)
        if not fresh or fresh.status == "cancelled":
            self._tasks.finish(task_id=task.task_id, status="cancelled", output_json="{}", evidence_paths=[], error_json=None)
            return "cancelled"

        try:
            input_obj = json.loads(fresh.input_json or "{}")
        except Exception:
            input_obj = {}

        if fresh.task_type == "context_repair_assist":
            from octopusos.core.work.task_runners.context_repair_assist import run as _run
            result = _run(task_id=fresh.task_id, input_obj=input_obj)
        elif fresh.task_type == "writer_recovery_assist":
            from octopusos.core.work.task_runners.writer_recovery_assist import run as _run
            result = _run(task_id=fresh.task_id, input_obj=input_obj)
        elif fresh.task_type == "email_unread_digest":
            from octopusos.core.work.task_runners.email_unread_digest import run as _run
            result = _run(task_id=fresh.task_id, input_obj=input_obj)
        else:
            self._tasks.finish(
                task_id=fresh.task_id,
                status="failed",
                output_json="{}",
                evidence_paths=[],
                error_json=json.dumps({"error": "unknown_task_type", "task_type": fresh.task_type}),
            )
            return "failed"

        if result.ok:
            self._tasks.finish(
                task_id=fresh.task_id,
                status="succeeded",
                output_json=result.output_json,
                evidence_paths=result.evidence_paths,
                error_json=None,
            )
            if fresh.work_id:
                self._work.update_status(
                    work_id=fresh.work_id,
                    status="succeeded",
                    summary="Task succeeded",
                    evidence_refs=[{"type": "path", "path": p} for p in (result.evidence_paths or [])],
                )
            return "succeeded"
        self._tasks.finish(
            task_id=fresh.task_id,
            status="failed",
            output_json=result.output_json,
            evidence_paths=result.evidence_paths,
            error_json=result.error_json,
        )
        if fresh.work_id:
            self._work.update_status(
                work_id=fresh.work_id,
                status="failed",
                summary="Task failed",
                evidence_refs=[{"type": "path", "path": p} for p in (result.evidence_paths or [])],
            )
        return "failed"
