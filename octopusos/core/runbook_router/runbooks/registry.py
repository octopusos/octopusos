from __future__ import annotations

from typing import Dict, Any

COMMAND_RUNBOOKS: Dict[str, Dict[str, Any]] = {
    "monitor.get_metrics": {"runbook_id": "common.monitor_metrics"},
    "monitor.ensure_agent": {"runbook_id": "common.ensure_monitoring_agent"},
    "billing.get_summary": {"runbook_id": "common.billing_query"},
    "org.get_structure": {"runbook_id": "common.org_query"},
    "inventory.list_resources": {"runbook_id": "common.inventory_query"},
}


def resolve_runbook(intent_type: str) -> Dict[str, Any]:
    return COMMAND_RUNBOOKS.get(intent_type, {"runbook_id": "common.unknown"})
