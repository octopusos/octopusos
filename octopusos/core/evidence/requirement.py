"""Evidence enforcement policy for KB-backed responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DEFAULT_MISSING_REASON = "EVIDENCE_REQUIRED_MISSING"


@dataclass(frozen=True)
class EnforcementResult:
    ok: bool
    action_taken: Literal["none", "reject", "degrade", "mark"]
    reason_code: str | None = None
    sanitized_response: str | None = None


def enforce_evidence(
    mode: str,
    used_kb: bool,
    evidence_refs: list,
    action: Literal["reject", "degrade", "mark", None] = None,
) -> EnforcementResult:
    if not used_kb:
        return EnforcementResult(ok=True, action_taken="none")

    if evidence_refs:
        return EnforcementResult(ok=True, action_taken="none")

    chosen_action = action or _default_action_for_mode(mode)

    if chosen_action == "reject":
        return EnforcementResult(
            ok=False,
            action_taken="reject",
            reason_code=DEFAULT_MISSING_REASON,
            sanitized_response=(
                "Response blocked: KB retrieval was used but no evidence references were attached. "
                "Please retry with citations."
            ),
        )

    if chosen_action == "degrade":
        return EnforcementResult(
            ok=True,
            action_taken="degrade",
            reason_code=DEFAULT_MISSING_REASON,
            sanitized_response=(
                "I cannot provide a grounded answer right now because evidence references are missing. "
                "Please retry or provide more context."
            ),
        )

    return EnforcementResult(
        ok=True,
        action_taken="mark",
        reason_code=DEFAULT_MISSING_REASON,
        sanitized_response=None,
    )


def _default_action_for_mode(mode: str) -> Literal["reject", "degrade", "mark"]:
    mode_lower = (mode or "").lower()
    if mode_lower == "local_open":
        return "mark"
    if mode_lower in {"local_locked", "remote_exposed"}:
        return "reject"
    return "mark"
