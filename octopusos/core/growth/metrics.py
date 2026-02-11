"""Growth health metrics with traceability."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

from octopusos.core.db import registry_db


class GrowthMetricsService:
    def _tasks(self) -> List[Dict[str, Any]]:
        rows = registry_db.query_all(
            "SELECT task_id, title, status, created_at, updated_at, metadata FROM tasks ORDER BY created_at ASC"
        )
        out: List[Dict[str, Any]] = []
        for r in rows:
            metadata = {}
            try:
                metadata = json.loads(r["metadata"] or "{}")
                if not isinstance(metadata, dict):
                    metadata = {}
            except Exception:
                metadata = {}
            out.append(
                {
                    "task_id": r["task_id"],
                    "title": r["title"] or "",
                    "status": (r["status"] or "").lower(),
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "metadata": metadata,
                }
            )
        return out

    def _parse_ts(self, raw: str) -> datetime:
        value = (raw or "").replace("Z", "+00:00")
        return datetime.fromisoformat(value)

    def repeated_task_success_trend(self) -> Dict[str, Any]:
        tasks = self._tasks()
        by_title: Dict[str, List[Dict[str, Any]]] = {}
        for t in tasks:
            title = t["title"].strip().lower()
            if not title:
                continue
            by_title.setdefault(title, []).append(t)

        repeated_total = 0
        repeated_success = 0
        trace: List[Dict[str, Any]] = []
        for title, items in by_title.items():
            if len(items) < 2:
                continue
            for idx, item in enumerate(items, start=1):
                if idx == 1:
                    continue
                repeated_total += 1
                if item["status"] == "succeeded":
                    repeated_success += 1
                trace.append({"task_id": item["task_id"], "title": title, "status": item["status"]})

        return {
            "value": (repeated_success / repeated_total) if repeated_total else 0.0,
            "counts": {"success": repeated_success, "total": repeated_total},
            "traceability": trace[:200],
        }

    def mttr(self) -> Dict[str, Any]:
        tasks = self._tasks()
        by_title: Dict[str, List[Dict[str, Any]]] = {}
        for t in tasks:
            key = t["title"].strip().lower()
            if key:
                by_title.setdefault(key, []).append(t)

        samples: List[Tuple[str, float, str, str]] = []
        for title, items in by_title.items():
            for idx, item in enumerate(items[:-1]):
                if item["status"] != "failed":
                    continue
                for next_item in items[idx + 1 :]:
                    if next_item["status"] == "succeeded":
                        delta = (self._parse_ts(next_item["updated_at"]) - self._parse_ts(item["updated_at"]))
                        samples.append((title, delta.total_seconds(), item["task_id"], next_item["task_id"]))
                        break

        avg = sum(s[1] for s in samples) / len(samples) if samples else 0.0
        return {
            "value_seconds": avg,
            "sample_count": len(samples),
            "traceability": [
                {
                    "title": s[0],
                    "failed_task_id": s[2],
                    "recovered_task_id": s[3],
                    "seconds": s[1],
                }
                for s in samples[:200]
            ],
        }

    def kb_hit_rate(self) -> Dict[str, Any]:
        row_total = registry_db.query_one("SELECT COUNT(*) AS c FROM tasks")
        row_hit = registry_db.query_one(
            """
            SELECT COUNT(DISTINCT task_id) AS c
            FROM task_kb_executions
            WHERE verify_passed = 1
            """
        )
        total = int(row_total["c"] if row_total else 0)
        hit = int(row_hit["c"] if row_hit else 0)
        traces = registry_db.query_all(
            "SELECT task_id, kb_id, executed_at FROM task_kb_executions WHERE verify_passed = 1 ORDER BY execution_id DESC LIMIT 200"
        )
        return {
            "value": (hit / total) if total else 0.0,
            "counts": {"hit": hit, "total": total},
            "traceability": [dict(r) for r in traces],
        }

    def skill_hint_adoption_rate(self) -> Dict[str, Any]:
        total_row = registry_db.query_one(
            "SELECT COUNT(*) AS c FROM task_audits WHERE event_type = 'TASK_ROUTED'"
        )
        adopted_row = registry_db.query_one(
            "SELECT COUNT(*) AS c FROM task_audits WHERE event_type = 'SKILL_HINT_APPLIED'"
        )
        total = int(total_row["c"] if total_row else 0)
        adopted = int(adopted_row["c"] if adopted_row else 0)
        traces = registry_db.query_all(
            "SELECT task_id, payload, created_at FROM task_audits WHERE event_type = 'SKILL_HINT_APPLIED' ORDER BY audit_id DESC LIMIT 200"
        )
        return {
            "value": (adopted / total) if total else 0.0,
            "counts": {"adopted": adopted, "total": total},
            "traceability": [dict(r) for r in traces],
        }

    def brain_proposal_pass_rate(self) -> Dict[str, Any]:
        total_row = registry_db.query_one("SELECT COUNT(*) AS c FROM improvement_proposals")
        accepted_row = registry_db.query_one(
            "SELECT COUNT(*) AS c FROM improvement_proposals WHERE status IN ('accepted', 'implemented')"
        )
        total = int(total_row["c"] if total_row else 0)
        accepted = int(accepted_row["c"] if accepted_row else 0)
        traces = registry_db.query_all(
            """
            SELECT proposal_id, status, affected_version_id, created_at
            FROM improvement_proposals
            ORDER BY created_at DESC
            LIMIT 200
            """
        )
        return {
            "value": (accepted / total) if total else 0.0,
            "counts": {"accepted": accepted, "total": total},
            "traceability": [dict(r) for r in traces],
        }

    def snapshot(self) -> Dict[str, Any]:
        return {
            "repeated_task_success_rate": self.repeated_task_success_trend(),
            "mttr": self.mttr(),
            "kb_hit_rate": self.kb_hit_rate(),
            "skill_hint_adoption_rate": self.skill_hint_adoption_rate(),
            "brain_proposal_pass_rate": self.brain_proposal_pass_rate(),
        }
