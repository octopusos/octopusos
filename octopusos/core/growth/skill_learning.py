"""Skill usage statistics and behavior hint lifecycle."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from octopusos.core.db import registry_db


class SkillLearningService:
    def __init__(self):
        self.ensure_schema()

    def ensure_schema(self) -> None:
        with registry_db.transaction() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_execution_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_id TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latency_ms INTEGER,
                    error_code TEXT,
                    evidence_refs_json TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_behavior_hints (
                    hint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_id TEXT NOT NULL,
                    preferred_params_json TEXT NOT NULL,
                    discouraged_params_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_refs_json TEXT NOT NULL,
                    sample_size INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    reviewer TEXT,
                    reviewed_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def record_execution(
        self,
        *,
        skill_id: str,
        params: Dict[str, Any],
        status: str,
        latency_ms: Optional[int],
        error_code: Optional[str],
        evidence_refs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        with registry_db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO skill_execution_events (
                    skill_id, params_json, status, latency_ms, error_code, evidence_refs_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    skill_id,
                    json.dumps(params, ensure_ascii=False, sort_keys=True),
                    status,
                    latency_ms,
                    error_code,
                    json.dumps(evidence_refs or [], ensure_ascii=False),
                ),
            )

    def usage_stats(self, skill_id: str) -> Dict[str, Any]:
        rows = registry_db.query_all(
            """
            SELECT status, latency_ms, error_code, params_json
            FROM skill_execution_events
            WHERE skill_id = ?
            ORDER BY id DESC
            LIMIT 1000
            """,
            (skill_id,),
        )
        total = len(rows)
        success = sum(1 for r in rows if str(r["status"]).lower() == "success")
        failure = sum(1 for r in rows if str(r["status"]).lower() != "success")
        avg_latency = int(sum(int(r["latency_ms"] or 0) for r in rows) / total) if total > 0 else 0

        param_counter: Dict[str, int] = {}
        for row in rows:
            params_sig = str(row["params_json"] or "{}")
            param_counter[params_sig] = param_counter.get(params_sig, 0) + 1

        param_patterns = sorted(
            [{"params_json": k, "count": v} for k, v in param_counter.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        return {
            "skill_id": skill_id,
            "usage_stats": {
                "param_patterns": param_patterns,
                "success_rate": (success / total) if total else 0.0,
                "failure_rate": (failure / total) if total else 0.0,
                "avg_latency": avg_latency,
                "sample_size": total,
            },
        }

    def generate_behavior_hint(self, skill_id: str, *, min_samples: int = 3) -> Optional[Dict[str, Any]]:
        rows = registry_db.query_all(
            """
            SELECT params_json, status, error_code, evidence_refs_json
            FROM skill_execution_events
            WHERE skill_id = ?
            ORDER BY id DESC
            LIMIT 200
            """,
            (skill_id,),
        )
        if len(rows) < min_samples:
            return None

        success_counts: Dict[str, int] = {}
        fail_counts: Dict[str, int] = {}
        evidence_refs: List[Dict[str, Any]] = []

        for row in rows:
            sig = str(row["params_json"] or "{}")
            is_success = str(row["status"]).lower() == "success"
            if is_success:
                success_counts[sig] = success_counts.get(sig, 0) + 1
            else:
                fail_counts[sig] = fail_counts.get(sig, 0) + 1

            try:
                refs = json.loads(row["evidence_refs_json"] or "[]")
                if isinstance(refs, list):
                    evidence_refs.extend([r for r in refs if isinstance(r, dict)])
            except Exception:
                pass

        if not success_counts:
            return None

        preferred_sig = max(success_counts.items(), key=lambda x: x[1])[0]
        discouraged = [sig for sig, count in fail_counts.items() if count >= 2 and count > success_counts.get(sig, 0)]

        try:
            preferred_params = json.loads(preferred_sig)
            if not isinstance(preferred_params, dict):
                preferred_params = {}
        except Exception:
            preferred_params = {}

        discouraged_params: List[Dict[str, Any]] = []
        for sig in discouraged:
            try:
                parsed = json.loads(sig)
                if isinstance(parsed, dict):
                    discouraged_params.append(parsed)
            except Exception:
                continue

        sample_size = len(rows)
        confidence = min(0.95, success_counts.get(preferred_sig, 0) / max(sample_size, 1) + 0.35)

        with registry_db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO skill_behavior_hints (
                    skill_id, preferred_params_json, discouraged_params_json,
                    confidence, evidence_refs_json, sample_size, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'draft')
                """,
                (
                    skill_id,
                    json.dumps(preferred_params, ensure_ascii=False, sort_keys=True),
                    json.dumps(discouraged_params, ensure_ascii=False, sort_keys=True),
                    float(confidence),
                    json.dumps(evidence_refs[:50], ensure_ascii=False),
                    sample_size,
                ),
            )

        return {
            "skill_id": skill_id,
            "preferred_params": preferred_params,
            "discouraged_params": discouraged_params,
            "confidence": confidence,
            "evidence_refs": evidence_refs[:50],
            "sample_size": sample_size,
            "status": "draft",
        }

    def approve_latest_hint(self, skill_id: str, reviewer: str) -> Optional[Dict[str, Any]]:
        row = registry_db.query_one(
            """
            SELECT hint_id FROM skill_behavior_hints
            WHERE skill_id = ?
            ORDER BY hint_id DESC
            LIMIT 1
            """,
            (skill_id,),
        )
        if not row:
            return None

        hint_id = int(row["hint_id"])
        with registry_db.transaction() as conn:
            conn.execute(
                """
                UPDATE skill_behavior_hints
                SET status = 'approved', reviewer = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE hint_id = ?
                """,
                (reviewer, hint_id),
            )
        return self.get_active_hint(skill_id)

    def get_active_hint(self, skill_id: str) -> Optional[Dict[str, Any]]:
        row = registry_db.query_one(
            """
            SELECT preferred_params_json, discouraged_params_json, confidence,
                   evidence_refs_json, sample_size, status
            FROM skill_behavior_hints
            WHERE skill_id = ? AND status = 'approved'
            ORDER BY hint_id DESC
            LIMIT 1
            """,
            (skill_id,),
        )
        if not row:
            return None
        preferred = json.loads(row["preferred_params_json"] or "{}")
        discouraged = json.loads(row["discouraged_params_json"] or "[]")
        evidence_refs = json.loads(row["evidence_refs_json"] or "[]")
        return {
            "skill_id": skill_id,
            "preferred_params": preferred if isinstance(preferred, dict) else {},
            "discouraged_params": discouraged if isinstance(discouraged, list) else [],
            "confidence": float(row["confidence"] or 0.0),
            "evidence_refs": evidence_refs if isinstance(evidence_refs, list) else [],
            "sample_size": int(row["sample_size"] or 0),
            "status": row["status"],
        }

    def explain_hint_usage(self, skill_id: str, hint: Dict[str, Any]) -> str:
        return (
            f"Using approved hint for skill '{skill_id}' based on past "
            f"{int(hint.get('sample_size') or 0)} executions."
        )
