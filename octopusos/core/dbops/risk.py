from __future__ import annotations

from .models import Decision, RiskAssessment, RiskLevel


def assess_operation_risk(
    action_id: str,
    *,
    estimated_rows: int | None = None,
    rollback_possible: bool | None = None,
    dry_run: bool = True,
) -> RiskAssessment:
    action = action_id.lower()

    if action.startswith("db.readonly."):
        return RiskAssessment(
            risk_level=RiskLevel.LOW,
            decision=Decision.ALLOW,
            reason="read-only operation",
            requires_confirmation=False,
            estimated_rows=estimated_rows,
            rollback_possible=rollback_possible,
        )

    if action.startswith("db.safe.maintenance"):
        return RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            decision=Decision.CONFIRM,
            reason="maintenance action requires operator confirmation",
            requires_confirmation=True,
            estimated_rows=estimated_rows,
            rollback_possible=rollback_possible,
        )

    if action.startswith("db.migration."):
        if dry_run:
            return RiskAssessment(
                risk_level=RiskLevel.MEDIUM,
                decision=Decision.CONFIRM,
                reason="migration dry-run requires confirmation",
                requires_confirmation=True,
                estimated_rows=estimated_rows,
                rollback_possible=True if rollback_possible is None else rollback_possible,
            )
        return RiskAssessment(
            risk_level=RiskLevel.HIGH,
            decision=Decision.CONFIRM,
            reason="migration execution requires strong confirmation",
            requires_confirmation=True,
            estimated_rows=estimated_rows,
            rollback_possible=rollback_possible,
        )

    if action.startswith("db.data.mutation."):
        if estimated_rows is not None and estimated_rows > 100000:
            level = RiskLevel.CRITICAL
            decision = Decision.BLOCK
            reason = "mutation affects too many rows"
        else:
            level = RiskLevel.HIGH
            decision = Decision.CONFIRM
            reason = "data mutation is high-risk"
        return RiskAssessment(
            risk_level=level,
            decision=decision,
            reason=reason,
            requires_confirmation=True,
            estimated_rows=estimated_rows,
            rollback_possible=rollback_possible,
        )

    if action.startswith("db.admin."):
        return RiskAssessment(
            risk_level=RiskLevel.CRITICAL,
            decision=Decision.BLOCK,
            reason="critical admin actions are blocked by default",
            requires_confirmation=True,
            estimated_rows=estimated_rows,
            rollback_possible=rollback_possible,
        )

    return RiskAssessment(
        risk_level=RiskLevel.MEDIUM,
        decision=Decision.CONFIRM,
        reason="unknown action defaults to confirmation",
        requires_confirmation=True,
        estimated_rows=estimated_rows,
        rollback_possible=rollback_possible,
    )
