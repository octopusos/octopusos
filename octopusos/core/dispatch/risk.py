"""Deterministic risk rules for dispatch proposals (v3.2 MVP)."""

from __future__ import annotations

from typing import Any, Dict


RISK_LEVELS = {"low", "medium", "high", "critical"}


def calculate_risk(proposal_type: str, payload: Dict[str, Any]) -> str:
    proposal_type = proposal_type.lower()

    if proposal_type == "reassign_task":
        return "medium"

    if proposal_type == "reprioritize_task":
        target = str(payload.get("to_priority", "")).upper()
        if target in {"P0", "P1", "HIGH", "CRITICAL"}:
            return "medium"
        return "low"

    if proposal_type in {"pause_agent", "resume_agent"}:
        return "high"

    if proposal_type == "run_pipeline":
        tag = str(payload.get("pipeline_tag", "")).lower()
        if tag in {"critical", "high"}:
            return "high"
        return "medium"

    if proposal_type in {"provider_enable", "provider_disable"}:
        return "critical"

    return "medium"
