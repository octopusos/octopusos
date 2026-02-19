from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..contracts.models import SkillContract, SkillRiskTier


@dataclass(frozen=True)
class SkillDecision:
    skill_id: str
    allowed: bool
    risk_tier: SkillRiskTier
    reason_code: str
    reason_hints: List[str] = field(default_factory=list)
    approval_required: bool = False
    required_approvals: List[str] = field(default_factory=list)
    budget_snapshot: Dict[str, Any] = field(default_factory=dict)
    audit_tags_resolved: List[str] = field(default_factory=list)
    tenant_id: str | None = None
    workspace_id: str | None = None
    decision_reason: str = ""
    triggered_policy: str = "default"
    risk_score: float = 0.0
    budget_check_result: str = "not_checked"


class SkillDecisionEngine:
    """Combine policy, budget, and risk into a decision."""

    def decide(self, *, intent: Dict[str, Any], contract: SkillContract, context: Dict[str, Any]) -> SkillDecision:
        requested = {
            "tokens": int((context or {}).get("requested_tokens") or 0),
            "runtime_ms": int((context or {}).get("requested_runtime_ms") or 0),
            "network_calls": int((context or {}).get("requested_network_calls") or 0),
        }
        budget_check = self._budget_check_result(contract, requested)
        # Role-based access control (IAM mapping)
        role = (context or {}).get("role")
        allowed_skills = (context or {}).get("allowed_skills")
        if role and not allowed_skills:
            allowed_skills = self._load_role_map().get(str(role), [])
        if role and allowed_skills is not None and contract.skill_id not in set(allowed_skills):
            return SkillDecision(
                skill_id=contract.skill_id,
                allowed=False,
                risk_tier=contract.risk_tier,
                reason_code="SKILL_ROLE_DENIED",
                reason_hints=[str(role)],
                approval_required=False,
                required_approvals=[],
                budget_snapshot=self._budget_snapshot(contract),
                audit_tags_resolved=list(contract.audit_tags),
                tenant_id=(context or {}).get("tenant_id"),
                workspace_id=(context or {}).get("workspace_id"),
                decision_reason=f"Role {role} is not authorized for {contract.skill_id}",
                triggered_policy="role_allowlist",
                risk_score=self._risk_score(contract.risk_tier),
                budget_check_result=budget_check,
            )
        # Basic enable check
        mode = (context or {}).get("mode")
        if mode and mode != contract.enabled_conditions.mode.value:
            return SkillDecision(
                skill_id=contract.skill_id,
                allowed=False,
                risk_tier=contract.risk_tier,
                reason_code="SKILL_DISABLED_BY_MODE",
                reason_hints=[f"required={contract.enabled_conditions.mode.value}", f"got={mode}"],
                approval_required=False,
                required_approvals=[],
                budget_snapshot=self._budget_snapshot(contract),
                audit_tags_resolved=list(contract.audit_tags),
                tenant_id=(context or {}).get("tenant_id"),
                workspace_id=(context or {}).get("workspace_id"),
                decision_reason=f"Mode {mode} does not satisfy required {contract.enabled_conditions.mode.value}",
                triggered_policy="enabled_conditions.mode",
                risk_score=self._risk_score(contract.risk_tier),
                budget_check_result=budget_check,
            )

        runtime_risk = str((context or {}).get("runtime_risk_level") or "").strip().upper()
        runtime_force_approval = bool((context or {}).get("runtime_approval_required"))
        dynamic_risk_tier = contract.risk_tier
        if runtime_risk == "LOW":
            dynamic_risk_tier = SkillRiskTier.SILENT
        elif runtime_risk in {"MEDIUM", "HIGH"}:
            dynamic_risk_tier = SkillRiskTier.EXPLAIN_CONFIRM

        required = contract.approval_policy.require_confirmation_for
        approvals = []
        if dynamic_risk_tier in required:
            approvals.append("user_confirmation")
        if runtime_force_approval and "user_confirmation" not in approvals:
            approvals.append("user_confirmation")

        reason_hints: List[str] = []
        if runtime_risk:
            reason_hints.append(f"runtime_risk={runtime_risk}")

        return SkillDecision(
            skill_id=contract.skill_id,
            allowed=True if dynamic_risk_tier != SkillRiskTier.HARD_BLOCK else False,
            risk_tier=dynamic_risk_tier,
            reason_code="SKILL_ALLOWED" if dynamic_risk_tier != SkillRiskTier.HARD_BLOCK else "SKILL_HARD_BLOCK",
            reason_hints=reason_hints,
            approval_required=bool(approvals),
            required_approvals=approvals,
            budget_snapshot=self._budget_snapshot(contract),
            audit_tags_resolved=list(contract.audit_tags),
            tenant_id=(context or {}).get("tenant_id"),
            workspace_id=(context or {}).get("workspace_id"),
            decision_reason=self._decision_reason(
                allowed=dynamic_risk_tier != SkillRiskTier.HARD_BLOCK,
                dynamic_risk_tier=dynamic_risk_tier,
                runtime_risk=runtime_risk,
                approvals=approvals,
            ),
            triggered_policy=self._triggered_policy(runtime_risk=runtime_risk, runtime_force_approval=runtime_force_approval),
            risk_score=self._risk_score(dynamic_risk_tier, runtime_risk=runtime_risk),
            budget_check_result=budget_check,
        )

    @staticmethod
    def _budget_snapshot(contract: SkillContract) -> Dict[str, Any]:
        return {
            "max_tokens": contract.budget.max_tokens,
            "max_runtime_ms": contract.budget.max_runtime_ms,
            "max_network_calls": contract.budget.max_network_calls,
        }

    @staticmethod
    def _load_role_map() -> Dict[str, List[str]]:
        from pathlib import Path
        import json

        path = Path("configs") / "skills" / "roles.json"
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _risk_score(risk_tier: SkillRiskTier, *, runtime_risk: str | None = None) -> float:
        base = {
            SkillRiskTier.SILENT: 0.2,
            SkillRiskTier.EXPLAIN_CONFIRM: 0.6,
            SkillRiskTier.HARD_BLOCK: 0.95,
        }.get(risk_tier, 0.5)
        rr = str(runtime_risk or "").strip().upper()
        if rr == "LOW":
            base -= 0.1
        elif rr == "HIGH":
            base += 0.15
        elif rr == "MEDIUM":
            base += 0.05
        return max(0.0, min(1.0, round(base, 3)))

    @staticmethod
    def _budget_check_result(contract: SkillContract, requested: Dict[str, int]) -> str:
        over = (
            requested.get("tokens", 0) > int(contract.budget.max_tokens)
            or requested.get("runtime_ms", 0) > int(contract.budget.max_runtime_ms)
            or requested.get("network_calls", 0) > int(contract.budget.max_network_calls)
        )
        return "would_exceed_limit" if over else "within_limit"

    @staticmethod
    def _triggered_policy(*, runtime_risk: str, runtime_force_approval: bool) -> str:
        if runtime_force_approval:
            return "runtime.force_approval"
        if runtime_risk:
            return "runtime.risk_override"
        return "default"

    @staticmethod
    def _decision_reason(
        *,
        allowed: bool,
        dynamic_risk_tier: SkillRiskTier,
        runtime_risk: str,
        approvals: List[str],
    ) -> str:
        if not allowed:
            return "Blocked by hard risk tier policy"
        if approvals:
            return f"Allowed with approval: {','.join(approvals)}"
        if runtime_risk:
            return f"Allowed with runtime risk override ({runtime_risk})"
        if dynamic_risk_tier == SkillRiskTier.SILENT:
            return "Allowed in silent tier"
        return "Allowed by default policy"
