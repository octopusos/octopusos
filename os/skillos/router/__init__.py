from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

from octopusos.core.audit import log_audit_event

from ..contracts.models import SkillContract
from ..decision import SkillDecision, SkillDecisionEngine
from ..budget import SkillBudgetManager
from ..dispatch import ExtensionDispatcher, McpDispatcher, DispatchResult
from ..registry import SkillRegistry
from ..evidence import write_evidence_bundle


@dataclass(frozen=True)
class SkillIntent:
    skill_id: str
    operation: str
    args: Dict[str, Any]
    actor: str = "unknown"
    context: Dict[str, Any] = field(default_factory=dict)


class SkillRouter:
    """Single entry for skill execution: decision -> dispatch -> audit."""

    def __init__(self, registry: Optional[SkillRegistry] = None) -> None:
        self.registry = registry or SkillRegistry()
        self.decision_engine = SkillDecisionEngine()
        self.extension_dispatcher = ExtensionDispatcher()
        self.mcp_dispatcher = McpDispatcher()
        self.budget_manager = SkillBudgetManager()

    def invoke(self, intent: SkillIntent) -> Dict[str, Any]:
        if not intent.skill_id:
            raise ValueError("skill_id is required")
        if not (
            intent.skill_id.startswith("skill.")
            or intent.skill_id.startswith("mcp.")
            or intent.skill_id.startswith("kb.")
        ):
            raise ValueError("Only skill_id is allowed (expected prefix: skill., mcp., or kb.)")
        contract = self._require_contract(intent.skill_id)
        if intent.context.get("tenant_id") is None or intent.context.get("workspace_id") is None:
            raise ValueError("tenant_id and workspace_id are required in execution context")
        correlation_id = str(uuid.uuid4())
        decision_id = str(uuid.uuid4())
        events: List[Dict[str, Any]] = []
        decision = self.decision_engine.decide(
            intent={"operation": intent.operation, "args": intent.args},
            contract=contract,
            context=intent.context,
        )
        self._emit_decision(decision, contract, intent, correlation_id, decision_id, events)
        self._emit_cost_tracked(intent, contract, decision, correlation_id, decision_id, events, stage="decision")
        if not decision.allowed:
            self._emit_execution_blocked(decision, contract, intent, reason="not_allowed", correlation_id=correlation_id, decision_id=decision_id, events=events)
            self._emit_audit_written(decision, contract, intent, correlation_id, decision_id, events)
            self._emit_evidence_emitted(decision, contract, intent, correlation_id, decision_id, events)
            write_evidence_bundle(
                contract=contract,
                decision=decision,
                events=events,
                correlation_id=correlation_id,
                decision_id=decision_id,
                task_id=intent.context.get("task_id"),
                plan_version=intent.context.get("plan_version_id"),
            )
            return {
                "ok": False,
                "blocked": True,
                "skill_id": contract.skill_id,
                "reason_code": decision.reason_code,
                "reason_hints": decision.reason_hints,
                "risk_tier": decision.risk_tier.value,
                "correlation_id": correlation_id,
                "decision_id": decision_id,
            }
        if decision.approval_required and not intent.context.get("approval_token"):
            self._emit_approval_required(decision, contract, intent, correlation_id, decision_id, events)
            self._emit_execution_blocked(decision, contract, intent, reason="approval_required", correlation_id=correlation_id, decision_id=decision_id, events=events)
            self._emit_audit_written(decision, contract, intent, correlation_id, decision_id, events)
            self._emit_evidence_emitted(decision, contract, intent, correlation_id, decision_id, events)
            write_evidence_bundle(
                contract=contract,
                decision=decision,
                events=events,
                correlation_id=correlation_id,
                decision_id=decision_id,
                task_id=intent.context.get("task_id"),
                plan_version=intent.context.get("plan_version_id"),
            )
            return {
                "ok": False,
                "blocked": True,
                "skill_id": contract.skill_id,
                "reason_code": "SKILL_APPROVAL_REQUIRED",
                "reason_hints": decision.required_approvals,
                "risk_tier": decision.risk_tier.value,
                "correlation_id": correlation_id,
                "decision_id": decision_id,
            }
        if decision.approval_required and intent.context.get("approval_token"):
            self._emit_approval_granted(decision, contract, intent, correlation_id, decision_id, events)
        reserve = self.budget_manager.reserve(
            tenant_id=str(intent.context.get("tenant_id")),
            workspace_id=str(intent.context.get("workspace_id")),
            skill_id=contract.skill_id,
            budget=contract.budget,
            requested_tokens=int(intent.context.get("requested_tokens") or 0),
            requested_runtime_ms=int(intent.context.get("requested_runtime_ms") or 0),
            requested_network_calls=int(intent.context.get("requested_network_calls") or 0),
        )
        if not reserve.ok:
            self._emit_budget_exceeded(decision, contract, intent, reserve, correlation_id, decision_id, events)
            self._emit_execution_blocked(decision, contract, intent, reason=reserve.reason, correlation_id=correlation_id, decision_id=decision_id, events=events)
            self._emit_audit_written(decision, contract, intent, correlation_id, decision_id, events)
            self._emit_evidence_emitted(decision, contract, intent, correlation_id, decision_id, events)
            write_evidence_bundle(
                contract=contract,
                decision=decision,
                events=events,
                correlation_id=correlation_id,
                decision_id=decision_id,
                task_id=intent.context.get("task_id"),
                plan_version=intent.context.get("plan_version_id"),
            )
            return {
                "ok": False,
                "blocked": True,
                "skill_id": contract.skill_id,
                "reason_code": reserve.reason,
                "reason_hints": [],
                "risk_tier": decision.risk_tier.value,
                "correlation_id": correlation_id,
                "decision_id": decision_id,
            }
        self._emit_budget_reserved(decision, contract, intent, reserve, correlation_id, decision_id, events)
        self._emit_cost_tracked(intent, contract, decision, correlation_id, decision_id, events, stage="budget_reserved")
        return self._dispatch(contract, intent, decision, correlation_id, decision_id, events)

    def _require_contract(self, skill_id: str) -> SkillContract:
        contract = self.registry.get(skill_id)
        if not contract:
            raise ValueError(f"Unknown skill_id: {skill_id}")
        return contract

    def _dispatch(
        self,
        contract: SkillContract,
        intent: SkillIntent,
        decision: SkillDecision,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        invocation_id = str(uuid.uuid4())
        payload = {
            "invocation_id": invocation_id,
            "skill_id": contract.skill_id,
            "operation": intent.operation,
            "args": intent.args,
        }
        tool_id = contract.dispatch.tool_id
        from octopusos.core.capabilities.capability_models import ToolInvocation

        invocation = ToolInvocation(
            invocation_id=invocation_id,
            tool_id=tool_id,
            task_id=intent.context.get("task_id"),
            project_id=intent.context.get("project_id"),
            spec_hash=intent.context.get("spec_hash"),
            spec_frozen=bool(intent.context.get("spec_frozen")),
            actor=intent.actor,
            mode=intent.context.get("execution_mode", "execution"),
            inputs=intent.args,
            session_id=intent.context.get("session_id"),
            user_id=intent.context.get("user_id"),
        )

        self._emit_dispatch_selected(contract, intent, decision, correlation_id, decision_id, events)
        self._emit_execution_start(contract, intent, invocation_id, correlation_id, decision_id, events)
        if contract.dispatch.dispatch_type == "extension":
            self._emit_tool_call_started(contract, intent, decision, invocation_id, correlation_id, decision_id, events)
            result = self.extension_dispatcher.dispatch(
                extension_id=contract.dispatch.extension_id or "",
                action_id=contract.dispatch.action_id or intent.operation,
                invocation=invocation,
                decision_context={
                    "source": "skill_router",
                    "skill_id": contract.skill_id,
                    "task_id": intent.context.get("task_id"),
                    "session_id": intent.context.get("session_id"),
                    "runner": contract.dispatch.runner or intent.context.get("runner"),
                    "run_id": intent.context.get("run_id"),
                    "user_id": intent.context.get("user_id") or intent.actor,
                    "role": intent.context.get("role"),
                    "approval_token": intent.context.get("approval_token"),
                },
            )
        elif contract.dispatch.dispatch_type == "mcp":
            self._emit_tool_call_started(contract, intent, decision, invocation_id, correlation_id, decision_id, events)
            result = self.mcp_dispatcher.dispatch(
                tool_id=tool_id,
                invocation=invocation,
                decision_context={
                    "skill_id": contract.skill_id,
                    "risk_tier": decision.risk_tier.value,
                    "audit_tags": decision.audit_tags_resolved,
                },
            )
        else:
            raise ValueError(f"Unknown dispatch type: {contract.dispatch.dispatch_type}")
        self._emit_tool_call_finished(contract, intent, decision, invocation_id, result, correlation_id, decision_id, events)
        self._emit_cost_tracked(intent, contract, decision, correlation_id, decision_id, events, stage="tool_call_finished")
        self._emit_custom_evidence(contract, intent, decision, result, correlation_id, decision_id, events)
        self._emit_execution_finish(contract, intent, invocation_id, result, correlation_id, decision_id, events)
        self._emit_cost_tracked(intent, contract, decision, correlation_id, decision_id, events, stage="execution_finished")
        if not result.ok:
            refund = self.budget_manager.refund(
                tenant_id=str(intent.context.get("tenant_id")),
                workspace_id=str(intent.context.get("workspace_id")),
                skill_id=contract.skill_id,
                requested=self._last_requested_budget(intent),
            )
            self._emit_budget_refunded(decision, contract, intent, refund, correlation_id, decision_id, events)
        self._emit_audit_written(decision, contract, intent, correlation_id, decision_id, events)
        self._emit_evidence_emitted(decision, contract, intent, correlation_id, decision_id, events)
        write_evidence_bundle(
            contract=contract,
            decision=decision,
            events=events,
            correlation_id=correlation_id,
            decision_id=decision_id,
            invocation_id=invocation_id,
            task_id=intent.context.get("task_id"),
            plan_version=intent.context.get("plan_version_id"),
        )
        return {
            **payload,
            "ok": result.ok,
            "result": result.payload,
            "error": result.error,
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }

    def _emit_custom_evidence(
        self,
        contract: SkillContract,
        intent: SkillIntent,
        decision: SkillDecision,
        result: DispatchResult,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        evidence_payload = None
        if isinstance(result.payload, dict):
            output = result.payload.get("output")
            if isinstance(output, dict):
                evidence_payload = output.get("evidence") or output.get("nlq_evidence")
        if not isinstance(evidence_payload, dict):
            return
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "CUSTOM_EVIDENCE",
            "status": "succeeded",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "evidence": evidence_payload,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }
        SkillRouter._emit_stream_event(intent, "db.nlq.evidence", payload)
        events.append({"type": "SKILL_CUSTOM_EVIDENCE", "payload": payload})

    @staticmethod
    def _last_requested_budget(intent: SkillIntent) -> Dict[str, int]:
        return {
            "tokens": int(intent.context.get("requested_tokens") or 0),
            "runtime_ms": int(intent.context.get("requested_runtime_ms") or 0),
            "network_calls": int(intent.context.get("requested_network_calls") or 0),
        }

    @staticmethod
    def _emit_decision(
        decision: SkillDecision,
        contract: SkillContract,
        intent: SkillIntent,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "DECISION_MADE",
            "status": "succeeded" if decision.allowed else "blocked",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "allowed": decision.allowed,
            "reason_code": decision.reason_code,
            "reason_hints": decision.reason_hints,
            "audit_tags": decision.audit_tags_resolved,
            "approvals": decision.required_approvals,
            "approval_required": decision.approval_required,
            "decision_reason": decision.decision_reason,
            "triggered_policy": decision.triggered_policy,
            "risk_score": decision.risk_score,
            "budget_check_result": decision.budget_check_result,
            "tenant_id": decision.tenant_id,
            "workspace_id": decision.workspace_id,
            "budget_snapshot": decision.budget_snapshot,
            "approval_actor": intent.context.get("approval_actor"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
            "parent_id": intent.context.get("parent_id"),
            "retry_count": int(intent.context.get("retry_count") or 0),
        }
        log_audit_event(
            event_type="SKILL_DECISION_MADE",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.decision", payload)
        events.append({"type": "SKILL_DECISION_MADE", "payload": payload})

    @staticmethod
    def _emit_execution_start(
        contract: SkillContract,
        intent: SkillIntent,
        invocation_id: str,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "EXECUTION_STARTED",
            "status": "running",
            "skill_id": contract.skill_id,
            "invocation_id": invocation_id,
            "operation": intent.operation,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
            "parent_id": intent.context.get("parent_id"),
            "retry_count": int(intent.context.get("retry_count") or 0),
        }
        log_audit_event(
            event_type="SKILL_EXECUTION_STARTED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.execution_started", payload)
        events.append({"type": "SKILL_EXECUTION_STARTED", "payload": payload})

    @staticmethod
    def _emit_execution_finish(
        contract: SkillContract,
        intent: SkillIntent,
        invocation_id: str,
        result: DispatchResult,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "EXECUTION_FINISHED",
            "status": "succeeded" if result.ok else "failed",
            "skill_id": contract.skill_id,
            "invocation_id": invocation_id,
            "operation": intent.operation,
            "ok": result.ok,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
            "parent_id": intent.context.get("parent_id"),
            "retry_count": int(intent.context.get("retry_count") or 0),
        }
        log_audit_event(
            event_type="SKILL_EXECUTION_FINISHED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.execution_finished", payload)
        events.append({"type": "SKILL_EXECUTION_FINISHED", "payload": payload})

    @staticmethod
    def _emit_execution_blocked(
        decision: SkillDecision,
        contract: SkillContract,
        intent: SkillIntent,
        reason: str,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "EXECUTION_BLOCKED",
            "status": "blocked",
            "skill_id": contract.skill_id,
            "operation": intent.operation,
            "reason": reason,
            "reason_code": decision.reason_code,
            "risk_tier": decision.risk_tier.value,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
            "parent_id": intent.context.get("parent_id"),
            "retry_count": int(intent.context.get("retry_count") or 0),
        }
        log_audit_event(
            event_type="SKILL_EXECUTION_BLOCKED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.execution_blocked", payload)
        events.append({"type": "SKILL_EXECUTION_BLOCKED", "payload": payload})

    @staticmethod
    def _emit_approval_required(
        decision: SkillDecision,
        contract: SkillContract,
        intent: SkillIntent,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "APPROVAL_REQUIRED",
            "status": "blocked",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "approvals": decision.required_approvals,
            "approval_required": True,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }
        log_audit_event(
            event_type="SKILL_APPROVAL_REQUIRED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.approval_required", payload)
        events.append({"type": "SKILL_APPROVAL_REQUIRED", "payload": payload})

    @staticmethod
    def _emit_approval_granted(
        decision: SkillDecision,
        contract: SkillContract,
        intent: SkillIntent,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "APPROVAL_GRANTED",
            "status": "succeeded",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "approval_actor": intent.context.get("approval_actor"),
            "approval_token_present": bool(intent.context.get("approval_token")),
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }
        log_audit_event(
            event_type="SKILL_APPROVAL_GRANTED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.approval_granted", payload)
        events.append({"type": "SKILL_APPROVAL_GRANTED", "payload": payload})

    @staticmethod
    def _emit_budget_reserved(
        decision: SkillDecision,
        contract: SkillContract,
        intent: SkillIntent,
        reserve,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "BUDGET_RESERVED",
            "status": "succeeded",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "budget_before": reserve.before,
            "budget_after": reserve.after,
            "requested": reserve.requested,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }
        log_audit_event(
            event_type="SKILL_BUDGET_RESERVED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.budget_reserved", payload)
        events.append({"type": "SKILL_BUDGET_RESERVED", "payload": payload})

    @staticmethod
    def _emit_budget_exceeded(
        decision: SkillDecision,
        contract: SkillContract,
        intent: SkillIntent,
        reserve,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "BUDGET_EXCEEDED",
            "status": "blocked",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "budget_before": reserve.before,
            "budget_after": reserve.after,
            "requested": reserve.requested,
            "reason": reserve.reason,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }
        log_audit_event(
            event_type="SKILL_BUDGET_EXCEEDED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.budget_exceeded", payload)
        events.append({"type": "SKILL_BUDGET_EXCEEDED", "payload": payload})

    def _emit_budget_refunded(
        self,
        decision: SkillDecision,
        contract: SkillContract,
        intent: SkillIntent,
        refund,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "BUDGET_REFUNDED",
            "status": "succeeded",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "budget_before": refund.before,
            "budget_after": refund.after,
            "requested": refund.requested,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }
        log_audit_event(
            event_type="SKILL_BUDGET_REFUNDED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.budget_refunded", payload)
        events.append({"type": "SKILL_BUDGET_REFUNDED", "payload": payload})

    @staticmethod
    def _emit_stream_event(intent: SkillIntent, event_type: str, payload: Dict[str, Any]) -> None:
        session_id = str(intent.context.get("session_id") or "").strip()
        if not session_id:
            return
        run_id = str(intent.context.get("run_id") or intent.context.get("task_id") or session_id)
        try:
            from octopusos.webui.websocket.stream_bus import append_event
        except Exception:
            return
        append_event(
            session_id=session_id,
            run_id=run_id,
            task_id=intent.context.get("task_id"),
            event_type=event_type,
            payload=payload,
        )

    def _emit_dispatch_selected(
        self,
        contract: SkillContract,
        intent: SkillIntent,
        decision: SkillDecision,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        target = (
            f"mcp:{contract.dispatch.mcp_server_id}"
            if contract.dispatch.dispatch_type == "mcp"
            else f"extension:{contract.dispatch.extension_id}"
        )
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "DISPATCH_SELECTED",
            "status": "queued",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "target": target,
            "dispatch_type": contract.dispatch.dispatch_type,
            "tool_id": contract.dispatch.tool_id,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }
        log_audit_event(
            event_type="SKILL_DISPATCH_SELECTED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.dispatch_selected", payload)
        events.append({"type": "SKILL_DISPATCH_SELECTED", "payload": payload})

    def _emit_tool_call_started(
        self,
        contract: SkillContract,
        intent: SkillIntent,
        decision: SkillDecision,
        invocation_id: str,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        target = (
            f"mcp:{contract.dispatch.mcp_server_id}:{contract.dispatch.mcp_tool_name}"
            if contract.dispatch.dispatch_type == "mcp"
            else f"extension:{contract.dispatch.extension_id}:{contract.dispatch.action_id}"
        )
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "TOOL_CALL_STARTED",
            "status": "running",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "target": target,
            "invocation_id": invocation_id,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
            "parent_id": intent.context.get("parent_id"),
            "retry_count": int(intent.context.get("retry_count") or 0),
        }
        log_audit_event(
            event_type="SKILL_TOOL_CALL_STARTED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.tool_call_started", payload)
        events.append({"type": "SKILL_TOOL_CALL_STARTED", "payload": payload})

    def _emit_tool_call_finished(
        self,
        contract: SkillContract,
        intent: SkillIntent,
        decision: SkillDecision,
        invocation_id: str,
        result: DispatchResult,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        target = (
            f"mcp:{contract.dispatch.mcp_server_id}:{contract.dispatch.mcp_tool_name}"
            if contract.dispatch.dispatch_type == "mcp"
            else f"extension:{contract.dispatch.extension_id}:{contract.dispatch.action_id}"
        )
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "TOOL_CALL_FINISHED",
            "status": "succeeded" if result.ok else "failed",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "target": target,
            "invocation_id": invocation_id,
            "ok": result.ok,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
            "parent_id": intent.context.get("parent_id"),
            "retry_count": int(intent.context.get("retry_count") or 0),
        }
        log_audit_event(
            event_type="SKILL_TOOL_CALL_FINISHED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.tool_call_finished", payload)
        events.append({"type": "SKILL_TOOL_CALL_FINISHED", "payload": payload})

    def _emit_audit_written(
        self,
        decision: SkillDecision,
        contract: SkillContract,
        intent: SkillIntent,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "AUDIT_WRITTEN",
            "status": "succeeded",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }
        log_audit_event(
            event_type="SKILL_AUDIT_WRITTEN",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.audit_written", payload)
        events.append({"type": "SKILL_AUDIT_WRITTEN", "payload": payload})

    def _emit_evidence_emitted(
        self,
        decision: SkillDecision,
        contract: SkillContract,
        intent: SkillIntent,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
    ) -> None:
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "EVIDENCE_EMITTED",
            "status": "succeeded",
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "evidence_path": f"evidence/skill/{correlation_id}/evidence.json",
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
        }
        log_audit_event(
            event_type="SKILL_EVIDENCE_EMITTED",
            task_id=intent.context.get("task_id"),
            metadata=payload,
        )
        SkillRouter._emit_stream_event(intent, "skill.evidence_emitted", payload)
        events.append({"type": "SKILL_EVIDENCE_EMITTED", "payload": payload})

    def _emit_cost_tracked(
        self,
        intent: SkillIntent,
        contract: SkillContract,
        decision: SkillDecision,
        correlation_id: str,
        decision_id: str,
        events: List[Dict[str, Any]],
        *,
        stage: str,
    ) -> None:
        token_in = int(intent.context.get("requested_tokens") or 0)
        token_out = int(intent.context.get("token_out") or 0)
        token_price = float(intent.context.get("token_price_usd") or 0.000002)
        cumulative_cost = round((token_in + token_out) * token_price, 8)
        payload = {
            "event_id": str(uuid.uuid4()),
            "phase": "COST_TRACKED",
            "status": "succeeded",
            "stage": stage,
            "skill_id": contract.skill_id,
            "risk_tier": decision.risk_tier.value,
            "token_in": token_in,
            "token_out": token_out,
            "cumulative_cost": cumulative_cost,
            "budget_gate_triggered": stage == "budget_reserved" and decision.budget_check_result != "within_limit",
            "tenant_id": intent.context.get("tenant_id"),
            "workspace_id": intent.context.get("workspace_id"),
            "correlation_id": correlation_id,
            "decision_id": decision_id,
            "parent_id": intent.context.get("parent_id"),
            "retry_count": int(intent.context.get("retry_count") or 0),
        }
        SkillRouter._emit_stream_event(intent, "skill.cost_tracked", payload)
        events.append({"type": "SKILL_COST_TRACKED", "payload": payload})
