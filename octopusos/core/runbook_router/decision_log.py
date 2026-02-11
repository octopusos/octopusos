from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DecisionRecord:
    ts: str
    pending_type: str
    intent_type: str
    decision: str
    reason: str
    selected_runbook: str
    selected_step: str
    blocked_by: str
    next_pending: str


def log_decision(
    *,
    pending_type: str,
    intent_type: str,
    decision: str,
    reason: str,
    selected_runbook: str = "",
    selected_step: str = "",
    blocked_by: str = "",
    next_pending: str = "",
) -> Dict[str, Any]:
    rec = DecisionRecord(
        ts=datetime.now(timezone.utc).isoformat(),
        pending_type=pending_type,
        intent_type=intent_type,
        decision=decision,
        reason=reason,
        selected_runbook=selected_runbook,
        selected_step=selected_step,
        blocked_by=blocked_by,
        next_pending=next_pending,
    )
    payload = asdict(rec)
    logger.info("runbook_router_decision=%s", payload)
    return payload
