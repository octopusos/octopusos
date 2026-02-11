"""Evidence normalization, gating, and replay verification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from octopusos.core.db import registry_db


class EvidenceType(str, Enum):
    LOGS = "logs"
    DIFF = "diff"
    STDOUT = "stdout"
    SCREENSHOT = "screenshot"
    TRACE = "trace"
    ARTIFACT = "artifact"


@dataclass
class EvidenceValidationResult:
    ok: bool
    missing_types: List[str]
    missing_paths: List[str]
    found_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "missing_types": self.missing_types,
            "missing_paths": self.missing_paths,
            "found_types": self.found_types,
        }


class EvidenceGate:
    """SUCCESS gating by required evidence completeness."""

    @staticmethod
    def normalize_refs(evidence_refs: Optional[Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for ref in evidence_refs or []:
            raw_type = str(ref.get("type") or "").strip().lower()
            raw_path = str(ref.get("path") or "").strip()
            if not raw_type:
                continue
            normalized.append(
                {
                    "type": raw_type,
                    "path": raw_path,
                    "id": str(ref.get("id") or ""),
                    "meta": ref.get("meta") if isinstance(ref.get("meta"), dict) else {},
                }
            )
        return normalized

    @classmethod
    def validate(
        cls,
        *,
        required_types: Iterable[str],
        evidence_refs: Optional[Iterable[Dict[str, Any]]],
        must_exist_on_disk: bool = True,
    ) -> EvidenceValidationResult:
        refs = cls.normalize_refs(evidence_refs)
        found_types = sorted({str(r.get("type") or "") for r in refs if r.get("type")})
        req = sorted({str(t).strip().lower() for t in required_types if str(t).strip()})

        missing_types = [t for t in req if t not in found_types]
        missing_paths: List[str] = []

        if must_exist_on_disk:
            for ref in refs:
                path = str(ref.get("path") or "").strip()
                if not path:
                    continue
                p = Path(path)
                if not p.is_absolute():
                    p = Path.cwd() / p
                if not p.exists():
                    missing_paths.append(str(p))

        return EvidenceValidationResult(
            ok=(len(missing_types) == 0 and len(missing_paths) == 0),
            missing_types=missing_types,
            missing_paths=missing_paths,
            found_types=found_types,
        )


def _load_task_metadata(task_id: str) -> Dict[str, Any]:
    row = registry_db.query_one("SELECT metadata FROM tasks WHERE task_id = ?", (task_id,))
    if not row:
        return {}
    raw = row["metadata"]
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def replay_verify_task(task_id: str) -> Dict[str, Any]:
    """Replay-level evidence verification for a task."""
    metadata = _load_task_metadata(task_id)
    evidence_refs = metadata.get("evidence_refs") if isinstance(metadata.get("evidence_refs"), list) else []
    required = metadata.get("required_evidence_types") if isinstance(metadata.get("required_evidence_types"), list) else []

    validation = EvidenceGate.validate(
        required_types=required,
        evidence_refs=evidence_refs,
        must_exist_on_disk=True,
    )

    audit_count_row = registry_db.query_one(
        "SELECT COUNT(*) AS c FROM task_audits WHERE task_id = ?",
        (task_id,),
    )
    audit_count = int(audit_count_row["c"] if audit_count_row else 0)
    if audit_count <= 0:
        validation.ok = False

    return {
        "task_id": task_id,
        "ok": validation.ok,
        "audit_event_count": audit_count,
        "evidence_validation": validation.to_dict(),
    }
