"""Actionable KB schema and success enforcement service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from octopusos.core.db import registry_db
from octopusos.core.growth.evidence import EvidenceGate


@dataclass
class KBValidationResult:
    ok: bool
    missing_requirements: List[str]
    missing_verifications: List[str]
    missing_evidence_types: List[str]
    missing_evidence_paths: List[str]
    kb_ids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "missing_requirements": self.missing_requirements,
            "missing_verifications": self.missing_verifications,
            "missing_evidence_types": self.missing_evidence_types,
            "missing_evidence_paths": self.missing_evidence_paths,
            "kb_ids": self.kb_ids,
        }


class ActionableKBService:
    """Stores Action KB entries and enforces execution/verification gates."""

    def __init__(self):
        self.ensure_schema()

    def ensure_schema(self) -> None:
        with registry_db.transaction() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS actionable_kb_entries (
                    kb_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_kb_requirements (
                    task_id TEXT NOT NULL,
                    kb_id TEXT NOT NULL,
                    required_at TEXT NOT NULL,
                    PRIMARY KEY (task_id, kb_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_kb_executions (
                    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    kb_id TEXT NOT NULL,
                    verify_passed INTEGER NOT NULL,
                    evidence_refs TEXT NOT NULL,
                    notes TEXT,
                    executed_at TEXT NOT NULL
                )
                """
            )

    def upsert_entry(self, entry: Dict[str, Any]) -> str:
        required = ["id", "type", "scope", "trigger", "preconditions", "steps", "verify", "rollback", "risk_level", "required_evidence", "source_evidence_refs"]
        for key in required:
            if key not in entry:
                raise ValueError(f"ActionableKnowledgeEntry missing field: {key}")

        kb_id = str(entry["id"]).strip()
        if not kb_id:
            raise ValueError("kb_id cannot be empty")

        now = entry.get("updated_at") or "CURRENT_TIMESTAMP"
        with registry_db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO actionable_kb_entries (kb_id, payload, confidence, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(kb_id) DO UPDATE SET
                  payload = excluded.payload,
                  confidence = excluded.confidence,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (
                    kb_id,
                    json.dumps(entry, ensure_ascii=False),
                    float(entry.get("confidence") or 0.5),
                ),
            )
        return kb_id

    def require_kb_execution(self, task_id: str, kb_id: str) -> None:
        with registry_db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO task_kb_requirements (task_id, kb_id, required_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(task_id, kb_id) DO NOTHING
                """,
                (task_id, kb_id),
            )

    def record_execution(
        self,
        *,
        task_id: str,
        kb_id: str,
        verify_passed: bool,
        evidence_refs: Iterable[Dict[str, Any]],
        notes: str = "",
    ) -> None:
        refs = list(evidence_refs)
        with registry_db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO task_kb_executions (task_id, kb_id, verify_passed, evidence_refs, notes, executed_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    task_id,
                    kb_id,
                    1 if verify_passed else 0,
                    json.dumps(refs, ensure_ascii=False),
                    notes,
                ),
            )

    def get_required_kb_ids(self, task_id: str) -> List[str]:
        rows = registry_db.query_all(
            "SELECT kb_id FROM task_kb_requirements WHERE task_id = ? ORDER BY kb_id",
            (task_id,),
        )
        return [str(r["kb_id"]) for r in rows]

    def get_entry(self, kb_id: str) -> Optional[Dict[str, Any]]:
        row = registry_db.query_one(
            "SELECT payload FROM actionable_kb_entries WHERE kb_id = ?",
            (kb_id,),
        )
        if not row:
            return None
        try:
            payload = json.loads(row["payload"])
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def _latest_execution(self, task_id: str, kb_id: str) -> Optional[Dict[str, Any]]:
        row = registry_db.query_one(
            """
            SELECT verify_passed, evidence_refs, executed_at
            FROM task_kb_executions
            WHERE task_id = ? AND kb_id = ?
            ORDER BY execution_id DESC
            LIMIT 1
            """,
            (task_id, kb_id),
        )
        if not row:
            return None
        try:
            refs = json.loads(row["evidence_refs"] or "[]")
            if not isinstance(refs, list):
                refs = []
        except Exception:
            refs = []
        return {
            "verify_passed": bool(row["verify_passed"]),
            "evidence_refs": refs,
            "executed_at": row["executed_at"],
        }

    def validate_task_success(self, task_id: str) -> KBValidationResult:
        kb_ids = self.get_required_kb_ids(task_id)
        missing_requirements: List[str] = []
        missing_verifications: List[str] = []
        missing_evidence_types: List[str] = []
        missing_evidence_paths: List[str] = []

        for kb_id in kb_ids:
            entry = self.get_entry(kb_id)
            if not entry:
                missing_requirements.append(kb_id)
                continue

            execution = self._latest_execution(task_id, kb_id)
            if not execution:
                missing_verifications.append(kb_id)
                continue
            if not bool(execution.get("verify_passed")):
                missing_verifications.append(kb_id)

            required_types = entry.get("required_evidence") if isinstance(entry.get("required_evidence"), list) else []
            evidence_validation = EvidenceGate.validate(
                required_types=required_types,
                evidence_refs=execution.get("evidence_refs") if isinstance(execution.get("evidence_refs"), list) else [],
                must_exist_on_disk=True,
            )
            missing_evidence_types.extend([f"{kb_id}:{t}" for t in evidence_validation.missing_types])
            missing_evidence_paths.extend([f"{kb_id}:{p}" for p in evidence_validation.missing_paths])

        ok = not any([
            missing_requirements,
            missing_verifications,
            missing_evidence_types,
            missing_evidence_paths,
        ])

        return KBValidationResult(
            ok=ok,
            missing_requirements=missing_requirements,
            missing_verifications=missing_verifications,
            missing_evidence_types=missing_evidence_types,
            missing_evidence_paths=missing_evidence_paths,
            kb_ids=kb_ids,
        )

    def seed_default_entries(self) -> List[str]:
        seeds: List[Dict[str, Any]] = [
            {
                "id": "KB-CLI-DOCKER-BUILD",
                "type": "CLI",
                "scope": "global",
                "trigger": {"task_type": "docker_build"},
                "preconditions": ["Docker daemon available", "Dockerfile present"],
                "steps": ["docker build -t <tag> ."],
                "verify": ["docker image ls | grep <tag>"],
                "rollback": ["docker rmi <tag>"],
                "risk_level": "medium",
                "required_evidence": ["stdout", "artifact"],
                "confidence": 0.8,
                "source_evidence_refs": [{"type": "artifact", "path": "docs/reports/SMOKE_TEST_REPORT.md"}],
            },
            {
                "id": "KB-API-OPENAPI-IMPORT",
                "type": "API",
                "scope": "global",
                "trigger": {"intent": "import_openapi"},
                "preconditions": ["connector exists", "admin token configured"],
                "steps": ["POST /api/compat/connectors/{connector_id}/import/openapi"],
                "verify": ["GET /api/compat/connectors/{connector_id}/endpoints"],
                "rollback": ["DELETE imported endpoints by endpoint_id"],
                "risk_level": "low",
                "required_evidence": ["trace", "stdout"],
                "confidence": 0.85,
                "source_evidence_refs": [{"type": "artifact", "path": "os/octopusos/webui/api/connectors.py"}],
            },
            {
                "id": "KB-SOP-REPLAY-VERIFY",
                "type": "SOP",
                "scope": "project",
                "trigger": {"task_type": "replay_verify"},
                "preconditions": ["task_id exists", "task has evidence bundle"],
                "steps": ["run replay_verify_task(task_id)"],
                "verify": ["evidence refs exist on disk", "audit count > 0"],
                "rollback": ["mark task as failed and request evidence regeneration"],
                "risk_level": "low",
                "required_evidence": ["trace", "artifact"],
                "confidence": 0.9,
                "source_evidence_refs": [{"type": "artifact", "path": "os/octopusos/core/growth/evidence.py"}],
            },
        ]
        created: List[str] = []
        for entry in seeds:
            created.append(self.upsert_entry(entry))
        return created
