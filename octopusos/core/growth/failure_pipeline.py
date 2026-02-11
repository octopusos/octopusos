"""Unified failure summary model and mapping."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class FailureCategory(str, Enum):
    CAPABILITY = "capability"
    ENV = "env"
    INPUT = "input"
    RISK = "risk"
    BUG = "bug"


@dataclass
class FailureSummary:
    category: FailureCategory
    reason: str
    retryable: bool
    evidence_refs: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "reason": self.reason,
            "retryable": self.retryable,
            "evidence_refs": self.evidence_refs,
        }


def _map_exit_reason(exit_reason: str) -> tuple[FailureCategory, bool]:
    normalized = (exit_reason or "unknown").strip().lower()
    if normalized in {"blocked"}:
        return FailureCategory.RISK, False
    if normalized in {"timeout"}:
        return FailureCategory.ENV, True
    if normalized in {"max_iterations"}:
        return FailureCategory.CAPABILITY, True
    if normalized in {"user_cancelled"}:
        return FailureCategory.INPUT, False
    if normalized in {"fatal_error", "unknown"}:
        return FailureCategory.BUG, False
    return FailureCategory.BUG, False


def build_failure_summary(
    *,
    exit_reason: str,
    reason: str,
    evidence_refs: List[Dict[str, Any]],
) -> FailureSummary:
    category, retryable = _map_exit_reason(exit_reason)
    return FailureSummary(
        category=category,
        reason=reason,
        retryable=retryable,
        evidence_refs=evidence_refs,
    )
