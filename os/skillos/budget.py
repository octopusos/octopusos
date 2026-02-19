from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .contracts.models import SkillBudget


@dataclass
class BudgetReservation:
    ok: bool
    reason: str
    remaining: Dict[str, int]
    before: Dict[str, int]
    after: Dict[str, int]
    requested: Dict[str, int]


class SkillBudgetManager:
    """In-memory budget enforcement per (tenant, workspace, skill)."""

    def __init__(self) -> None:
        self._remaining: Dict[Tuple[str, str, str], Dict[str, int]] = {}

    def reserve(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        skill_id: str,
        budget: SkillBudget,
        requested_tokens: int,
        requested_runtime_ms: int,
        requested_network_calls: int,
    ) -> BudgetReservation:
        key = (tenant_id, workspace_id, skill_id)
        if key not in self._remaining:
            self._remaining[key] = {
                "tokens": budget.max_tokens,
                "runtime_ms": budget.max_runtime_ms,
                "network_calls": budget.max_network_calls,
            }
        remaining = self._remaining[key]
        before = dict(remaining)
        requested = {
            "tokens": max(0, int(requested_tokens)),
            "runtime_ms": max(0, int(requested_runtime_ms)),
            "network_calls": max(0, int(requested_network_calls)),
        }
        if requested["tokens"] > remaining["tokens"]:
            return BudgetReservation(False, "BUDGET_TOKENS_EXCEEDED", dict(remaining), before, dict(remaining), requested)
        if requested["runtime_ms"] > remaining["runtime_ms"]:
            return BudgetReservation(False, "BUDGET_RUNTIME_EXCEEDED", dict(remaining), before, dict(remaining), requested)
        if requested["network_calls"] > remaining["network_calls"]:
            return BudgetReservation(False, "BUDGET_NETWORK_EXCEEDED", dict(remaining), before, dict(remaining), requested)

        remaining["tokens"] -= requested["tokens"]
        remaining["runtime_ms"] -= requested["runtime_ms"]
        remaining["network_calls"] -= requested["network_calls"]
        after = dict(remaining)
        return BudgetReservation(True, "OK", dict(remaining), before, after, requested)

    def refund(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        skill_id: str,
        requested: Dict[str, int],
    ) -> BudgetReservation:
        key = (tenant_id, workspace_id, skill_id)
        if key not in self._remaining:
            self._remaining[key] = {
                "tokens": 0,
                "runtime_ms": 0,
                "network_calls": 0,
            }
        remaining = self._remaining[key]
        before = dict(remaining)
        requested_norm = {
            "tokens": max(0, int(requested.get("tokens", 0))),
            "runtime_ms": max(0, int(requested.get("runtime_ms", 0))),
            "network_calls": max(0, int(requested.get("network_calls", 0))),
        }
        remaining["tokens"] += requested_norm["tokens"]
        remaining["runtime_ms"] += requested_norm["runtime_ms"]
        remaining["network_calls"] += requested_norm["network_calls"]
        after = dict(remaining)
        return BudgetReservation(True, "REFUND_OK", dict(remaining), before, after, requested_norm)
