"""Dispatch proposals repository."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from octopusos.core.db import registry_db, SQLiteWriter
from octopusos.core.time import utc_now_ms


@dataclass
class DispatchProposal:
    proposal_id: str
    source: str
    proposal_type: str
    status: str
    risk_level: str
    scope: Dict[str, Any]
    payload: Dict[str, Any]
    reason: str
    evidence_refs: List[str]
    requested_by: str
    requested_at: int
    reviewed_by: Optional[str]
    reviewed_at: Optional[int]
    review_comment: Optional[str]
    execution_ref: Optional[str]
    created_at: int
    updated_at: int
    auto_execute_eligible: int = 0
    auto_execute_policy: str = "never"
    approved_then_auto_execute: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "source": self.source,
            "proposal_type": self.proposal_type,
            "status": self.status,
            "risk_level": self.risk_level,
            "scope": self.scope,
            "payload": self.payload,
            "reason": self.reason,
            "evidence_refs": self.evidence_refs,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "review_comment": self.review_comment,
            "execution_ref": self.execution_ref,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "auto_execute_eligible": self.auto_execute_eligible,
            "auto_execute_policy": self.auto_execute_policy,
            "approved_then_auto_execute": self.approved_then_auto_execute,
        }


@dataclass
class DispatchExecutionJob:
    job_id: str
    proposal_id: str
    status: str
    idempotency_key: str
    resource_key: str
    execution_mode: str
    started_at: Optional[int]
    ended_at: Optional[int]
    attempt: int
    max_attempts: int
    last_error_code: Optional[str]
    last_error_message: Optional[str]
    evidence: Dict[str, Any]
    created_at: int
    updated_at: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "proposal_id": self.proposal_id,
            "status": self.status,
            "idempotency_key": self.idempotency_key,
            "resource_key": self.resource_key,
            "execution_mode": self.execution_mode,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "last_error_code": self.last_error_code,
            "last_error_message": self.last_error_message,
            "evidence": self.evidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class DispatchRollbackJob:
    rollback_job_id: str
    job_id: str
    status: str
    reason: str
    evidence: Dict[str, Any]
    created_at: int
    updated_at: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rollback_job_id": self.rollback_job_id,
            "job_id": self.job_id,
            "status": self.status,
            "reason": self.reason,
            "evidence": self.evidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

class DispatchRepo:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(registry_db._get_db_path())

    def ensure_tables(self) -> None:
        conn = registry_db.get_db()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatch_proposals (
                proposal_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                proposal_type TEXT NOT NULL,
                status TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                scope_json TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                requested_at INTEGER NOT NULL,
                reviewed_by TEXT,
                reviewed_at INTEGER,
                review_comment TEXT,
                execution_ref TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                auto_execute_eligible INTEGER DEFAULT 0,
                auto_execute_policy TEXT DEFAULT 'never',
                approved_then_auto_execute INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dispatch_proposals_status
            ON dispatch_proposals(status, created_at DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatch_decisions_audit (
                event_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                at INTEGER NOT NULL,
                details_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dispatch_audit_proposal
            ON dispatch_decisions_audit(proposal_id, at DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatch_execution_jobs (
                job_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                status TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                resource_key TEXT NOT NULL,
                execution_mode TEXT NOT NULL,
                started_at INTEGER,
                ended_at INTEGER,
                attempt INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                last_error_code TEXT,
                last_error_message TEXT,
                evidence_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_dispatch_jobs_idempotency
            ON dispatch_execution_jobs(idempotency_key)
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_dispatch_jobs_resource_active
            ON dispatch_execution_jobs(resource_key)
            WHERE status IN ('queued', 'running')
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatch_rollback_jobs (
                rollback_job_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatch_agent_state (
                agent_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
        conn.commit()

    def create_proposal(self, proposal: DispatchProposal) -> None:
        def _insert(conn):
            conn.execute(
                """
                INSERT INTO dispatch_proposals (
                    proposal_id, source, proposal_type, status, risk_level,
                    scope_json, payload_json, reason, evidence_json,
                    requested_by, requested_at, reviewed_by, reviewed_at,
                    review_comment, execution_ref, created_at, updated_at,
                    auto_execute_eligible, auto_execute_policy, approved_then_auto_execute
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.source,
                    proposal.proposal_type,
                    proposal.status,
                    proposal.risk_level,
                    json.dumps(proposal.scope),
                    json.dumps(proposal.payload),
                    proposal.reason,
                    json.dumps(proposal.evidence_refs),
                    proposal.requested_by,
                    proposal.requested_at,
                    proposal.reviewed_by,
                    proposal.reviewed_at,
                    proposal.review_comment,
                    proposal.execution_ref,
                    proposal.created_at,
                    proposal.updated_at,
                    proposal.auto_execute_eligible,
                    proposal.auto_execute_policy,
                    proposal.approved_then_auto_execute,
                ),
            )

        self._writer.submit(_insert, timeout=5.0)

    def list_proposals(self, status: Optional[str] = None, limit: int = 50) -> List[DispatchProposal]:
        params: List[Any] = []
        sql = (
            "SELECT * FROM dispatch_proposals "
        )
        if status:
            sql += "WHERE status = ? "
            params.append(status)
        sql += "ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = registry_db.query_all(sql, tuple(params))
        return [self._row_to_proposal(row) for row in rows]

    def get_proposal(self, proposal_id: str) -> Optional[DispatchProposal]:
        row = registry_db.query_one(
            "SELECT * FROM dispatch_proposals WHERE proposal_id = ?",
            (proposal_id,),
        )
        if not row:
            return None
        return self._row_to_proposal(row)

    def update_status(
        self,
        proposal_id: str,
        status: str,
        reviewer: Optional[str],
        review_comment: Optional[str],
        execution_ref: Optional[str],
        auto_execute_eligible: Optional[int] = None,
        auto_execute_policy: Optional[str] = None,
        approved_then_auto_execute: Optional[int] = None,
    ) -> None:
        now = utc_now_ms()

        def _update(conn):
            updates = [
                "status = ?",
                "reviewed_by = ?",
                "reviewed_at = ?",
                "review_comment = ?",
                "execution_ref = ?",
                "updated_at = ?",
            ]
            params: List[Any] = [
                status,
                reviewer,
                now if reviewer else None,
                review_comment,
                execution_ref,
                now,
            ]
            if auto_execute_eligible is not None:
                updates.append("auto_execute_eligible = ?")
                params.append(auto_execute_eligible)
            if auto_execute_policy is not None:
                updates.append("auto_execute_policy = ?")
                params.append(auto_execute_policy)
            if approved_then_auto_execute is not None:
                updates.append("approved_then_auto_execute = ?")
                params.append(approved_then_auto_execute)

            params.append(proposal_id)

            conn.execute(
                f"""
                UPDATE dispatch_proposals
                SET {', '.join(updates)}
                WHERE proposal_id = ?
                """,
                tuple(params),
            )

        self._writer.submit(_update, timeout=5.0)

    def append_audit(self, proposal_id: str, action: str, actor: str, details: Dict[str, Any]) -> str:
        event_id = f"dpa_{uuid.uuid4().hex}"
        now = utc_now_ms()

        def _insert(conn):
            conn.execute(
                """
                INSERT INTO dispatch_decisions_audit (
                    event_id, proposal_id, action, actor, at, details_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    proposal_id,
                    action,
                    actor,
                    now,
                    json.dumps(details),
                ),
            )

        self._writer.submit(_insert, timeout=5.0)
        return event_id

    def create_job(self, job: DispatchExecutionJob) -> None:
        def _insert(conn):
            conn.execute(
                """
                INSERT INTO dispatch_execution_jobs (
                    job_id, proposal_id, status, idempotency_key, resource_key,
                    execution_mode, started_at, ended_at, attempt, max_attempts,
                    last_error_code, last_error_message, evidence_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.proposal_id,
                    job.status,
                    job.idempotency_key,
                    job.resource_key,
                    job.execution_mode,
                    job.started_at,
                    job.ended_at,
                    job.attempt,
                    job.max_attempts,
                    job.last_error_code,
                    job.last_error_message,
                    json.dumps(job.evidence),
                    job.created_at,
                    job.updated_at,
                ),
            )

        self._writer.submit(_insert, timeout=5.0)

    def update_job_status(
        self,
        job_id: str,
        status: str,
        started_at: Optional[int],
        ended_at: Optional[int],
        attempt: int,
        last_error_code: Optional[str],
        last_error_message: Optional[str],
        evidence: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = utc_now_ms()

        def _update(conn):
            updates = [
                "status = ?",
                "started_at = ?",
                "ended_at = ?",
                "attempt = ?",
                "last_error_code = ?",
                "last_error_message = ?",
                "updated_at = ?",
            ]
            params: List[Any] = [
                status,
                started_at,
                ended_at,
                attempt,
                last_error_code,
                last_error_message,
                now,
            ]
            if evidence is not None:
                updates.append("evidence_json = ?")
                params.append(json.dumps(evidence))

            params.append(job_id)
            conn.execute(
                f"""
                UPDATE dispatch_execution_jobs
                SET {', '.join(updates)}
                WHERE job_id = ?
                """,
                tuple(params),
            )

        self._writer.submit(_update, timeout=5.0)

    def get_job_by_idempotency(self, idempotency_key: str) -> Optional[DispatchExecutionJob]:
        row = registry_db.query_one(
            "SELECT * FROM dispatch_execution_jobs WHERE idempotency_key = ?",
            (idempotency_key,),
        )
        if not row:
            return None
        return self._row_to_job(row)

    def get_active_job_by_resource(self, resource_key: str) -> Optional[DispatchExecutionJob]:
        row = registry_db.query_one(
            """
            SELECT * FROM dispatch_execution_jobs
            WHERE resource_key = ? AND status IN ('queued', 'running')
            """,
            (resource_key,),
        )
        if not row:
            return None
        return self._row_to_job(row)

    def get_job(self, job_id: str) -> Optional[DispatchExecutionJob]:
        row = registry_db.query_one(
            "SELECT * FROM dispatch_execution_jobs WHERE job_id = ?",
            (job_id,),
        )
        if not row:
            return None
        return self._row_to_job(row)

    def list_jobs(
        self,
        status: Optional[str] = None,
        proposal_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DispatchExecutionJob]:
        params: List[Any] = []
        sql = "SELECT * FROM dispatch_execution_jobs "
        clauses = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if proposal_id:
            clauses.append("proposal_id = ?")
            params.append(proposal_id)
        if clauses:
            sql += "WHERE " + " AND ".join(clauses) + " "
        sql += "ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = registry_db.query_all(sql, tuple(params))
        return [self._row_to_job(row) for row in rows]

    def create_rollback_job(self, job: DispatchRollbackJob) -> None:
        def _insert(conn):
            conn.execute(
                """
                INSERT INTO dispatch_rollback_jobs (
                    rollback_job_id, job_id, status, reason, evidence_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.rollback_job_id,
                    job.job_id,
                    job.status,
                    job.reason,
                    json.dumps(job.evidence),
                    job.created_at,
                    job.updated_at,
                ),
            )

        self._writer.submit(_insert, timeout=5.0)

    def update_rollback_job_status(
        self,
        rollback_job_id: str,
        status: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = utc_now_ms()

        def _update(conn):
            updates = ["status = ?", "updated_at = ?"]
            params: List[Any] = [status, now]
            if evidence is not None:
                updates.append("evidence_json = ?")
                params.append(json.dumps(evidence))
            params.append(rollback_job_id)
            conn.execute(
                f"""
                UPDATE dispatch_rollback_jobs
                SET {', '.join(updates)}
                WHERE rollback_job_id = ?
                """,
                tuple(params),
            )

        self._writer.submit(_update, timeout=5.0)

    def get_rollback_job(self, rollback_job_id: str) -> Optional[DispatchRollbackJob]:
        row = registry_db.query_one(
            "SELECT * FROM dispatch_rollback_jobs WHERE rollback_job_id = ?",
            (rollback_job_id,),
        )
        if not row:
            return None
        return DispatchRollbackJob(
            rollback_job_id=row["rollback_job_id"],
            job_id=row["job_id"],
            status=row["status"],
            reason=row["reason"],
            evidence=json.loads(row["evidence_json"]) if row["evidence_json"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_proposal(self, row) -> DispatchProposal:
        row_dict = dict(row)
        return DispatchProposal(
            proposal_id=row_dict["proposal_id"],
            source=row_dict["source"],
            proposal_type=row_dict["proposal_type"],
            status=row_dict["status"],
            risk_level=row_dict["risk_level"],
            scope=json.loads(row_dict["scope_json"]),
            payload=json.loads(row_dict["payload_json"]),
            reason=row_dict["reason"],
            evidence_refs=json.loads(row_dict["evidence_json"]) if row_dict["evidence_json"] else [],
            requested_by=row_dict["requested_by"],
            requested_at=row_dict["requested_at"],
            reviewed_by=row_dict["reviewed_by"],
            reviewed_at=row_dict["reviewed_at"],
            review_comment=row_dict["review_comment"],
            execution_ref=row_dict["execution_ref"],
            created_at=row_dict["created_at"],
            updated_at=row_dict["updated_at"],
            auto_execute_eligible=row_dict.get("auto_execute_eligible", 0),
            auto_execute_policy=row_dict.get("auto_execute_policy", "never"),
            approved_then_auto_execute=row_dict.get("approved_then_auto_execute", 0),
        )

    def _row_to_job(self, row) -> DispatchExecutionJob:
        return DispatchExecutionJob(
            job_id=row["job_id"],
            proposal_id=row["proposal_id"],
            status=row["status"],
            idempotency_key=row["idempotency_key"],
            resource_key=row["resource_key"],
            execution_mode=row["execution_mode"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            attempt=row["attempt"],
            max_attempts=row["max_attempts"],
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
            evidence=json.loads(row["evidence_json"]) if row["evidence_json"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
