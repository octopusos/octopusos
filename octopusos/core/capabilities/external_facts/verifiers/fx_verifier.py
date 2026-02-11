"""Verifier for FX extraction records."""

from __future__ import annotations

from ..types import EvidenceItem, ExtractionRecord, SourcePolicy, VerificationRecord


class FxVerifier:
    def verify(
        self,
        evidence: EvidenceItem,
        extraction: ExtractionRecord,
        policy: SourcePolicy,
    ) -> VerificationRecord:
        rate = extraction.extracted.get("rate")
        completeness_ok = rate is not None
        format_ok = isinstance(rate, (int, float)) and 0 < float(rate) < 10 if rate is not None else False
        whitelist_ok = self._whitelist_ok(evidence, policy)
        blacklist_ok = self._blacklist_ok(evidence, policy)
        freshness_ok = True

        checks = {
            "completeness_ok": completeness_ok,
            "format_ok": format_ok,
            "whitelist_ok": whitelist_ok,
            "blacklist_ok": blacklist_ok,
            "freshness_ok": freshness_ok,
        }
        passed = all(checks.values())
        status = "pass" if passed else "fail"
        confidence = "high" if passed else "low"
        reason = "fx_checks_passed" if passed else "fx_checks_failed"
        return VerificationRecord(
            evidence_id=evidence.evidence_id,
            kind="fx",
            status=status,
            confidence=confidence,
            confidence_reason=reason,
            checks=checks,
        )

    @staticmethod
    def _whitelist_ok(evidence: EvidenceItem, policy: SourcePolicy) -> bool:
        if not policy.source_whitelist:
            return True
        source = (evidence.source.name or "").lower()
        return any(source.endswith(v.lower()) for v in policy.source_whitelist)

    @staticmethod
    def _blacklist_ok(evidence: EvidenceItem, policy: SourcePolicy) -> bool:
        source = (evidence.source.name or "").lower()
        return not any(source.endswith(v.lower()) for v in policy.source_blacklist)

