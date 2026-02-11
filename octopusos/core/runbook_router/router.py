from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from octopusos.core.runbook_router.intents import Intent
from octopusos.core.runbook_router.decision_log import log_decision


@dataclass
class RouterDecision:
    action: str
    reason: str
    metadata: Dict[str, Any]


class RunbookRouter:
    """Minimal router used by chat dispatch pending flows."""

    def route_pending(self, pending_action: Dict[str, Any], intent: Intent) -> Optional[RouterDecision]:
        ptype = str((pending_action or {}).get("type") or "")

        if ptype == "await_instance_profile_choice":
            if intent.intent_type in {"control.continue", "control.recheck"}:
                return RouterDecision(
                    action="recheck_instance_profile",
                    reason="user_requested_continue_or_recheck",
                    metadata=log_decision(
                        pending_type=ptype,
                        intent_type=intent.intent_type,
                        decision="recheck_instance_profile",
                        reason="continue_alias",
                        selected_runbook="common.ensure_monitoring_agent",
                        selected_step="recheck_instance_profile_binding",
                        next_pending=ptype,
                    ),
                )
            if intent.intent_type == "monitor.ensure_agent":
                return RouterDecision(
                    action="explain_waiting_role_profile",
                    reason="install_requested_but_identity_binding_not_ready",
                    metadata=log_decision(
                        pending_type=ptype,
                        intent_type=intent.intent_type,
                        decision="explain_waiting_role_profile",
                        reason="blocked_by_identity_binding",
                        selected_runbook="common.ensure_monitoring_agent",
                        selected_step="await_role_or_profile_input",
                        blocked_by="identity_binding",
                        next_pending=ptype,
                    ),
                )
        if ptype == "await_iam_permission_grant":
            if intent.intent_type in {"control.continue", "control.recheck"}:
                return RouterDecision(
                    action="resume_after_permission_probe",
                    reason="user_requested_resume_after_permission_update",
                    metadata=log_decision(
                        pending_type=ptype,
                        intent_type=intent.intent_type,
                        decision="resume_after_permission_probe",
                        reason="continue_alias",
                        selected_runbook="common.access_diagnose",
                        selected_step="permission_probe_for_resume",
                        next_pending=ptype,
                    ),
                )
            if intent.intent_type == "monitor.ensure_agent":
                return RouterDecision(
                    action="explain_waiting_permission",
                    reason="install_requested_but_permission_not_confirmed",
                    metadata=log_decision(
                        pending_type=ptype,
                        intent_type=intent.intent_type,
                        decision="explain_waiting_permission",
                        reason="blocked_by_permission_grant",
                        selected_runbook="common.access_diagnose",
                        selected_step="await_permission_grant",
                        blocked_by="permission_grant",
                        next_pending=ptype,
                    ),
                )
        if ptype == "await_cwagent_metrics":
            if intent.intent_type in {"control.continue", "control.recheck", "monitor.ensure_agent"}:
                return RouterDecision(
                    action="poll_cwagent_metrics",
                    reason="user_requested_metric_followup",
                    metadata=log_decision(
                        pending_type=ptype,
                        intent_type=intent.intent_type,
                        decision="poll_cwagent_metrics",
                        reason="followup_poll",
                        selected_runbook="common.ensure_monitoring_agent",
                        selected_step="poll_first_metrics_report",
                        next_pending=ptype,
                    ),
                )
        locally_handled_pending = {
            "install_cwagent",
            "remediate_ssm_prereq",
            "bind_instance_profile",
        }
        if (
            ptype
            and ptype not in locally_handled_pending
            and intent.intent_type in {"control.continue", "control.recheck"}
        ):
            return RouterDecision(
                action="probe_pending_status",
                reason="generic_continue_or_recheck_for_pending",
                metadata=log_decision(
                    pending_type=ptype,
                    intent_type=intent.intent_type,
                    decision="probe_pending_status",
                    reason="generic_continue_fallback",
                    blocked_by="pending_input_required",
                    next_pending=ptype,
                ),
            )
        return None
