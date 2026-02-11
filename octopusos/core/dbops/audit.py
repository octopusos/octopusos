from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import DBInstance, OperationRequest, RiskAssessment


def build_audit_record(
    *,
    instance: DBInstance,
    request: OperationRequest,
    risk: RiskAssessment,
    query_shape: str,
    estimated_rows: Optional[int],
    actual_rows: Optional[int],
    executed_via: str,
    approved_by: Optional[str],
) -> Dict[str, Any]:
    return {
        "skill": request.action_id,
        "environment": instance.environment.value,
        "reason": request.reason,
        "query_shape": query_shape,
        "parameters": request.parameters,
        "estimated_rows": estimated_rows,
        "actual_rows": actual_rows,
        "rollback_possible": risk.rollback_possible,
        "requested_by": request.requested_by,
        "approved_by": approved_by,
        "executed_via": executed_via,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "risk_level": risk.risk_level.value,
        "decision": risk.decision.value,
    }
