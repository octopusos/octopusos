from __future__ import annotations

from .adapter import build_dispatch
from .audit import build_audit_record
from .models import OperationPlan, OperationRequest
from .registry import DBProviderCatalog
from .risk import assess_operation_risk
from .selection import parse_intent_from_text, select_instance


class DBOperationsOrchestrator:
    """Plan-only orchestrator: select instance -> assess risk -> build dispatch/audit envelope."""

    def __init__(self, catalog: DBProviderCatalog):
        self.catalog = catalog

    def plan_from_nl(self, text: str, request: OperationRequest) -> OperationPlan:
        intent = parse_intent_from_text(text, request.action_id)
        selection = select_instance(intent, self.catalog.list_instances())

        if not selection.selected:
            raise ValueError("no eligible db instance found")

        risk = assess_operation_risk(
            request.action_id,
            estimated_rows=request.parameters.get("estimated_rows"),
            rollback_possible=request.parameters.get("rollback_possible"),
            dry_run=request.dry_run,
        )

        dispatch = build_dispatch(request.action_id, selection.selected.engine)
        query_shape = dispatch.template

        return OperationPlan(
            instance=selection.selected,
            request=request,
            risk=risk,
            query_shape=query_shape,
            why_this_instance=selection.reason,
        )

    def build_audit(self, plan: OperationPlan, executed_via: str, approved_by: str | None = None):
        return build_audit_record(
            instance=plan.instance,
            request=plan.request,
            risk=plan.risk,
            query_shape=plan.query_shape,
            estimated_rows=plan.risk.estimated_rows,
            actual_rows=None,
            executed_via=executed_via,
            approved_by=approved_by,
        )
