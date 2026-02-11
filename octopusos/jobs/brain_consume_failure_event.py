"""BrainOS failure-consumption job for unified failure decisions."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from octopusos.core.db import registry_db


def _ensure_schema() -> None:
    with registry_db.transaction() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS brain_failure_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                category TEXT NOT NULL,
                retryable INTEGER NOT NULL,
                decision_type TEXT NOT NULL,
                ignore_reason TEXT,
                improvement_candidate TEXT,
                evidence_refs_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def consume_failure_event(
    *,
    task_id: str,
    failure_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Consume a task failure and write BrainOS decision output."""
    _ensure_schema()

    category = str(failure_summary.get("category") or "bug")
    retryable = bool(failure_summary.get("retryable"))
    evidence_refs = failure_summary.get("evidence_refs") if isinstance(failure_summary.get("evidence_refs"), list) else []

    decision_type = "improvement_candidate"
    ignore_reason: Optional[str] = None
    candidate: Optional[Dict[str, Any]] = None

    if category in {"input", "risk"}:
        decision_type = "ignore_reason"
        ignore_reason = (
            "User input insufficient" if category == "input" else "Policy/risk block expected"
        )
    else:
        target = "KB"
        if category == "capability":
            target = "Skill"
        elif category == "bug":
            target = "Tool"
        elif category == "env":
            target = "Policy"

        candidate = {
            "target": target,
            "expected_metric": {
                "success_rate_delta": 0.1,
                "latency_delta_ms": -200,
                "risk_delta": -0.1,
            },
            "source_task_id": task_id,
            "retryable": retryable,
        }

    with registry_db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO brain_failure_decisions (
                task_id, category, retryable, decision_type,
                ignore_reason, improvement_candidate, evidence_refs_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                category,
                1 if retryable else 0,
                decision_type,
                ignore_reason,
                json.dumps(candidate, ensure_ascii=False) if candidate else None,
                json.dumps(evidence_refs, ensure_ascii=False),
            ),
        )

    return {
        "task_id": task_id,
        "decision_type": decision_type,
        "ignore_reason": ignore_reason,
        "improvement_candidate": candidate,
        "category": category,
    }
