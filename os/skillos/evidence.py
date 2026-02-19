from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .contracts.models import SkillContract
from .decision import SkillDecision


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _skill_snapshot(contract: SkillContract) -> Dict[str, Any]:
    return {
        "skill_id": contract.skill_id,
        "name": contract.name,
        "version": contract.version,
        "risk_tier": contract.risk_tier.value,
        "required_permissions": list(contract.required_permissions or []),
        "budget": asdict(contract.budget),
        "enabled_conditions": {
            "mode": contract.enabled_conditions.mode.value,
            "trust_tier": contract.enabled_conditions.trust_tier,
            "feature_flags": list(contract.enabled_conditions.feature_flags or []),
        },
        "audit_tags": list(contract.audit_tags or []),
        "approval_policy": {
            "require_confirmation_for": [tier.value for tier in contract.approval_policy.require_confirmation_for],
        },
        "dispatch": {
            "dispatch_type": contract.dispatch.dispatch_type,
            "tool_id": contract.dispatch.tool_id,
            "extension_id": contract.dispatch.extension_id,
            "action_id": contract.dispatch.action_id,
            "runner": contract.dispatch.runner,
            "mcp_server_id": contract.dispatch.mcp_server_id,
            "mcp_tool_name": contract.dispatch.mcp_tool_name,
        },
        "origin": contract.origin,
    }


def _decision_snapshot(decision: SkillDecision, *, decision_id: str, correlation_id: str) -> Dict[str, Any]:
    return {
        "decision_id": decision_id,
        "correlation_id": correlation_id,
        "skill_id": decision.skill_id,
        "allowed": decision.allowed,
        "risk_tier": decision.risk_tier.value,
        "reason_code": decision.reason_code,
        "reason_hints": list(decision.reason_hints or []),
        "approval_required": decision.approval_required,
        "required_approvals": list(decision.required_approvals or []),
        "budget_snapshot": dict(decision.budget_snapshot or {}),
        "budget_check_result": decision.budget_check_result,
        "audit_tags": list(decision.audit_tags_resolved or []),
        "tenant_id": decision.tenant_id,
        "workspace_id": decision.workspace_id,
        "decision_reason": decision.decision_reason,
        "triggered_policy": decision.triggered_policy,
        "risk_score": float(decision.risk_score),
    }


def write_evidence_bundle(
    *,
    contract: SkillContract,
    decision: SkillDecision,
    events: List[Dict[str, Any]],
    correlation_id: str,
    decision_id: str,
    invocation_id: Optional[str] = None,
    task_id: Optional[str] = None,
    plan_version: Optional[str] = None,
) -> Path:
    """Write standardized evidence bundle for a SkillOS invocation."""
    root = Path("evidence") / "skill" / correlation_id
    root.mkdir(parents=True, exist_ok=True)
    bundle: Dict[str, Any] = {
        "bundle_version": "1.0",
        "generated_at": _iso_now(),
        "correlation_id": correlation_id,
        "decision_id": decision_id,
        "invocation_id": invocation_id,
        "task_id": task_id,
        "plan_version": plan_version,
        "skill_snapshot": _skill_snapshot(contract),
        "decision_snapshot": _decision_snapshot(decision, decision_id=decision_id, correlation_id=correlation_id),
        "events": events,
    }
    canonical = json.dumps(bundle, ensure_ascii=False, sort_keys=True).encode("utf-8")
    bundle_hash = hashlib.sha256(canonical).hexdigest()
    bundle["bundle_hash"] = f"sha256:{bundle_hash}"
    bundle["hash_algorithm"] = "sha256"

    out_path = root / "evidence.json"
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "evidence.sha256").write_text(bundle_hash, encoding="utf-8")
    return out_path
