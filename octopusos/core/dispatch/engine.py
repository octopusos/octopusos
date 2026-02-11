"""Dispatch execution engine for v3.3."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from octopusos.core.db import registry_db, SQLiteWriter
from octopusos.core.dispatch.config import load_dispatch_config
from octopusos.core.dispatch.repo import (
    DispatchExecutionJob,
    DispatchProposal,
    DispatchRepo,
    DispatchRollbackJob,
)
from octopusos.core.time import utc_now_iso, utc_now_ms


SUPPORTED_AUTO_TYPES = {"reassign_task", "reprioritize_task"}
SUPPORTED_EXEC_TYPES = {"reassign_task", "reprioritize_task", "pause_agent", "resume_agent"}


@dataclass
class ExecutionOutcome:
    job: Optional[DispatchExecutionJob]
    state: str
    reason_code: Optional[str] = None
    message: Optional[str] = None


class DispatchEngine:
    def __init__(self, repo: Optional[DispatchRepo] = None) -> None:
        self._repo = repo or DispatchRepo()
        self._repo.ensure_tables()
        self._writer = SQLiteWriter(registry_db._get_db_path())

    def compute_idempotency_key(self, proposal: DispatchProposal) -> str:
        action_signature = self._action_signature(proposal)
        raw = f"{proposal.proposal_id}:{proposal.updated_at}:{action_signature}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def compute_resource_key(self, proposal: DispatchProposal) -> str:
        payload = proposal.payload or {}
        if proposal.proposal_type in {"reassign_task", "reprioritize_task"}:
            task_id = payload.get("task_id")
            return f"task:{task_id}" if task_id else f"proposal:{proposal.proposal_id}"
        if proposal.proposal_type in {"pause_agent", "resume_agent"}:
            agent_id = payload.get("agent_id") or payload.get("agent")
            return f"agent:{agent_id}" if agent_id else f"proposal:{proposal.proposal_id}"
        return f"proposal:{proposal.proposal_id}"

    def auto_execute_eligible(self, proposal: DispatchProposal) -> Tuple[bool, str]:
        cfg = load_dispatch_config()
        if not cfg.auto_execute_enabled:
            return False, "auto_execute_disabled"
        if proposal.proposal_type not in SUPPORTED_AUTO_TYPES:
            return False, "unsupported_type"
        if not self._risk_allowed(proposal.risk_level, cfg.auto_execute_max_risk):
            return False, "risk_blocked"
        return True, "eligible"

    def execute_proposal(
        self,
        proposal: DispatchProposal,
        execution_mode: str,
    ) -> ExecutionOutcome:
        if proposal.proposal_type not in SUPPORTED_EXEC_TYPES:
            return ExecutionOutcome(
                job=None,
                state="unsupported",
                reason_code="UNSUPPORTED_TYPE",
                message="Proposal type not supported for execution",
            )

        if proposal.status in {"executed", "failed"}:
            existing_jobs = self._repo.list_jobs(proposal_id=proposal.proposal_id, limit=1)
            if existing_jobs:
                job = existing_jobs[0]
                state = "already_succeeded" if job.status == "succeeded" else "already_failed"
                return ExecutionOutcome(job=job, state=state)

        idempotency_key = self.compute_idempotency_key(proposal)
        existing = self._repo.get_job_by_idempotency(idempotency_key)
        if existing:
            if existing.status == "succeeded":
                return ExecutionOutcome(job=existing, state="already_succeeded")
            if existing.status in {"queued", "running"}:
                return ExecutionOutcome(job=existing, state="already_in_progress")

        resource_key = self.compute_resource_key(proposal)
        now = utc_now_ms()
        job = DispatchExecutionJob(
            job_id=f"dj_{uuid.uuid4().hex}",
            proposal_id=proposal.proposal_id,
            status="queued",
            idempotency_key=idempotency_key,
            resource_key=resource_key,
            execution_mode=execution_mode,
            started_at=None,
            ended_at=None,
            attempt=0,
            max_attempts=load_dispatch_config().max_attempts,
            last_error_code=None,
            last_error_message=None,
            evidence={"proposal_id": proposal.proposal_id, "before": None, "after": None},
            created_at=now,
            updated_at=now,
        )

        try:
            self._repo.create_job(job)
        except sqlite3.IntegrityError:
            active = self._repo.get_active_job_by_resource(resource_key)
            if active:
                return ExecutionOutcome(job=active, state="already_in_progress")
            existing = self._repo.get_job_by_idempotency(idempotency_key)
            if existing:
                return ExecutionOutcome(job=existing, state="already_succeeded")
            raise

        self._repo.append_audit(
            proposal.proposal_id,
            "dispatch_job_created",
            "system",
            {
                "job_id": job.job_id,
                "idempotency_key": job.idempotency_key,
                "status_after": "queued",
                "evidence_refs": proposal.evidence_refs,
            },
        )

        return self._run_job(job, proposal)

    def retry_job(self, job: DispatchExecutionJob, proposal: DispatchProposal) -> ExecutionOutcome:
        if job.status != "failed":
            return ExecutionOutcome(job=job, state="invalid_state", reason_code="INVALID_STATE")
        if job.attempt >= job.max_attempts:
            return ExecutionOutcome(job=job, state="max_attempts", reason_code="MAX_ATTEMPTS")
        return self._run_job(job, proposal, is_retry=True)

    def rollback_job(self, job: DispatchExecutionJob, proposal: DispatchProposal) -> ExecutionOutcome:
        if job.status != "succeeded":
            return ExecutionOutcome(job=job, state="invalid_state", reason_code="INVALID_STATE")
        if proposal.proposal_type not in SUPPORTED_EXEC_TYPES:
            return ExecutionOutcome(job=job, state="unsupported", reason_code="UNSUPPORTED_TYPE")

        rollback_job = DispatchRollbackJob(
            rollback_job_id=f"rb_{uuid.uuid4().hex}",
            job_id=job.job_id,
            status="running",
            reason="manual",
            evidence={"proposal_id": proposal.proposal_id},
            created_at=utc_now_ms(),
            updated_at=utc_now_ms(),
        )
        self._repo.create_rollback_job(rollback_job)
        self._repo.append_audit(
            proposal.proposal_id,
            "dispatch_job_rollback_started",
            "system",
            {
                "job_id": job.job_id,
                "rollback_job_id": rollback_job.rollback_job_id,
                "evidence_refs": proposal.evidence_refs,
            },
        )

        success, reason_code, message = self._apply_rollback(proposal, job)
        status = "succeeded" if success else "failed"
        self._repo.update_rollback_job_status(
            rollback_job.rollback_job_id,
            status,
            evidence={"reason_code": reason_code, "message": message},
        )
        if success:
            self._repo.update_job_status(
                job.job_id,
                "rolled_back",
                job.started_at,
                utc_now_ms(),
                job.attempt,
                job.last_error_code,
                job.last_error_message,
                evidence=job.evidence,
            )

        self._repo.append_audit(
            proposal.proposal_id,
            "dispatch_job_rollback_" + ("succeeded" if success else "failed"),
            "system",
            {
                "job_id": job.job_id,
                "rollback_job_id": rollback_job.rollback_job_id,
                "reason_code": reason_code,
                "message": message,
                "evidence_refs": proposal.evidence_refs,
            },
        )
        return ExecutionOutcome(job=job, state="rolled_back" if success else "rollback_failed", reason_code=reason_code)

    def _run_job(self, job: DispatchExecutionJob, proposal: DispatchProposal, is_retry: bool = False) -> ExecutionOutcome:
        now = utc_now_ms()
        attempt = job.attempt + 1
        self._repo.update_job_status(
            job.job_id,
            "running",
            now,
            None,
            attempt,
            None,
            None,
        )
        self._repo.append_audit(
            proposal.proposal_id,
            "dispatch_job_started",
            "system",
            {
                "job_id": job.job_id,
                "attempt": attempt,
                "evidence_refs": proposal.evidence_refs,
            },
        )

        success, before_state, after_state, reason_code, message = self._execute_handler(proposal)
        ended_at = utc_now_ms()
        status = "succeeded" if success else "failed"

        evidence = {
            "proposal_id": proposal.proposal_id,
            "before": before_state,
            "after": after_state,
            "reason_code": reason_code,
            "message": message,
        }

        self._repo.update_job_status(
            job.job_id,
            status,
            now,
            ended_at,
            attempt,
            None if success else reason_code,
            None if success else message,
            evidence=evidence,
        )

        self._repo.append_audit(
            proposal.proposal_id,
            "dispatch_job_" + ("succeeded" if success else "failed"),
            "system",
            {
                "job_id": job.job_id,
                "status_after": status,
                "reason_code": reason_code,
                "message": message,
                "evidence_refs": proposal.evidence_refs,
            },
        )

        return ExecutionOutcome(job=self._repo.get_job(job.job_id), state=status, reason_code=reason_code, message=message)

    def _execute_handler(
        self,
        proposal: DispatchProposal,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        if proposal.proposal_type == "reassign_task":
            return self._execute_reassign_task(proposal)
        if proposal.proposal_type == "reprioritize_task":
            return self._execute_reprioritize_task(proposal)
        if proposal.proposal_type == "pause_agent":
            return self._execute_pause_agent(proposal)
        if proposal.proposal_type == "resume_agent":
            return self._execute_resume_agent(proposal)
        return False, None, None, "UNSUPPORTED_TYPE", "Unsupported proposal type"

    def _apply_rollback(
        self,
        proposal: DispatchProposal,
        job: DispatchExecutionJob,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        evidence = job.evidence or {}
        before_state = evidence.get("before")
        if proposal.proposal_type == "reassign_task":
            return self._rollback_reassign_task(proposal, before_state)
        if proposal.proposal_type == "reprioritize_task":
            return self._rollback_reprioritize_task(proposal, before_state)
        if proposal.proposal_type in {"pause_agent", "resume_agent"}:
            return self._rollback_agent_state(proposal, before_state)
        return False, "UNSUPPORTED_TYPE", "Rollback unsupported"

    def _execute_reassign_task(
        self,
        proposal: DispatchProposal,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        payload = proposal.payload or {}
        task_id = payload.get("task_id")
        to_agent = payload.get("to_agent")
        from_agent = payload.get("from_agent")

        if not task_id or not to_agent:
            return False, None, None, "INVALID_PAYLOAD", "task_id and to_agent required"

        try:
            row = registry_db.query_one(
                "SELECT task_id, selected_instance_id, route_plan_json FROM tasks WHERE task_id = ?",
                (task_id,),
            )
        except sqlite3.Error:
            return False, None, None, "SCHEMA_MISSING", "tasks table missing or invalid schema"
        if not row:
            return False, None, None, "NOT_FOUND", "Task not found"

        current_agent = row["selected_instance_id"]
        if from_agent and current_agent and current_agent != from_agent:
            return False, None, None, "PRECONDITION_FAILED", "from_agent mismatch"

        before_state = {
            "selected_instance_id": current_agent,
            "route_plan_json": row["route_plan_json"],
        }

        route_plan = None
        if row["route_plan_json"]:
            try:
                route_plan = json.loads(row["route_plan_json"])
            except json.JSONDecodeError:
                route_plan = None

        if route_plan and isinstance(route_plan, dict):
            route_plan["selected"] = to_agent

        now = utc_now_iso()

        def _update(conn):
            conn.execute(
                """
                UPDATE tasks
                SET selected_instance_id = ?, route_plan_json = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    to_agent,
                    json.dumps(route_plan) if route_plan is not None else row["route_plan_json"],
                    now,
                    task_id,
                ),
            )

        self._writer.submit(_update, timeout=5.0)

        after_state = {
            "selected_instance_id": to_agent,
            "route_plan_json": json.dumps(route_plan) if route_plan is not None else row["route_plan_json"],
        }
        return True, before_state, after_state, None, None

    def _execute_reprioritize_task(
        self,
        proposal: DispatchProposal,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        payload = proposal.payload or {}
        task_id = payload.get("task_id")
        priority = self._normalize_priority(payload.get("priority"))

        if not task_id or priority is None:
            return False, None, None, "INVALID_PAYLOAD", "task_id and priority required"

        try:
            rows = registry_db.query_all(
                "SELECT work_item_id, priority FROM work_items WHERE task_id = ?",
                (task_id,),
            )
        except sqlite3.Error:
            return False, None, None, "SCHEMA_MISSING", "work_items table missing"

        if not rows:
            return False, None, None, "PRECONDITION_FAILED", "No work_items for task"

        before_state = {
            "work_items": [{"work_item_id": r["work_item_id"], "priority": r["priority"]} for r in rows]
        }

        def _update(conn):
            conn.execute(
                "UPDATE work_items SET priority = ? WHERE task_id = ?",
                (priority, task_id),
            )

        self._writer.submit(_update, timeout=5.0)

        after_state = {"priority": priority, "count": len(rows)}
        return True, before_state, after_state, None, None

    def _execute_pause_agent(
        self,
        proposal: DispatchProposal,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        agent_id = (proposal.payload or {}).get("agent_id")
        if not agent_id:
            return False, None, None, "INVALID_PAYLOAD", "agent_id required"
        before_state = self._get_agent_state(agent_id)
        self._set_agent_state(agent_id, "paused")
        after_state = {"agent_id": agent_id, "status": "paused"}
        return True, before_state, after_state, None, None

    def _execute_resume_agent(
        self,
        proposal: DispatchProposal,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        agent_id = (proposal.payload or {}).get("agent_id")
        if not agent_id:
            return False, None, None, "INVALID_PAYLOAD", "agent_id required"
        before_state = self._get_agent_state(agent_id)
        self._set_agent_state(agent_id, "active")
        after_state = {"agent_id": agent_id, "status": "active"}
        return True, before_state, after_state, None, None

    def _rollback_reassign_task(
        self,
        proposal: DispatchProposal,
        before_state: Optional[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        if not before_state:
            return False, "NO_BEFORE_STATE", "Missing rollback state"
        task_id = (proposal.payload or {}).get("task_id")
        if not task_id:
            return False, "INVALID_PAYLOAD", "task_id required"

        def _update(conn):
            conn.execute(
                """
                UPDATE tasks
                SET selected_instance_id = ?, route_plan_json = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    before_state.get("selected_instance_id"),
                    before_state.get("route_plan_json"),
                    utc_now_iso(),
                    task_id,
                ),
            )

        self._writer.submit(_update, timeout=5.0)
        return True, None, None

    def _rollback_reprioritize_task(
        self,
        proposal: DispatchProposal,
        before_state: Optional[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        if not before_state:
            return False, "NO_BEFORE_STATE", "Missing rollback state"
        work_items = before_state.get("work_items") or []
        if not work_items:
            return False, "NO_WORK_ITEMS", "No work_items to rollback"

        def _update(conn):
            for item in work_items:
                conn.execute(
                    "UPDATE work_items SET priority = ? WHERE work_item_id = ?",
                    (item.get("priority"), item.get("work_item_id")),
                )

        self._writer.submit(_update, timeout=5.0)
        return True, None, None

    def _rollback_agent_state(
        self,
        proposal: DispatchProposal,
        before_state: Optional[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        agent_id = (proposal.payload or {}).get("agent_id")
        if not agent_id:
            return False, "INVALID_PAYLOAD", "agent_id required"
        status = (before_state or {}).get("status") or "active"
        self._set_agent_state(agent_id, status)
        return True, None, None

    def _get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        row = registry_db.query_one(
            "SELECT agent_id, status, updated_at_ms FROM dispatch_agent_state WHERE agent_id = ?",
            (agent_id,),
        )
        if not row:
            return {"agent_id": agent_id, "status": "active"}
        return {
            "agent_id": row["agent_id"],
            "status": row["status"],
            "updated_at_ms": row["updated_at_ms"],
        }

    def _set_agent_state(self, agent_id: str, status: str) -> None:
        now = utc_now_ms()

        def _upsert(conn):
            conn.execute(
                """
                INSERT INTO dispatch_agent_state (agent_id, status, updated_at_ms)
                VALUES (?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET status = excluded.status, updated_at_ms = excluded.updated_at_ms
                """,
                (agent_id, status, now),
            )

        self._writer.submit(_upsert, timeout=5.0)

    def _action_signature(self, proposal: DispatchProposal) -> str:
        payload = proposal.payload or {}
        return f"{proposal.proposal_type}:{json.dumps(payload, sort_keys=True)}"

    @staticmethod
    def _risk_allowed(actual: str, max_risk: str) -> bool:
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return order.get(actual, 4) <= order.get(max_risk, 2)

    @staticmethod
    def _normalize_priority(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            normalized = value.strip().upper()
            mapping = {"P0": 100, "P1": 80, "P2": 60, "P3": 40}
            if normalized in mapping:
                return mapping[normalized]
            try:
                return int(normalized)
            except ValueError:
                return None
        return None
