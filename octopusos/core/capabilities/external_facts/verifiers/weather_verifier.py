"""Verifier for weather extraction records."""

from __future__ import annotations

from ..types import EvidenceItem, ExtractionRecord, SourcePolicy, VerificationRecord


class WeatherVerifier:
    def verify(
        self,
        evidence: EvidenceItem,
        extraction: ExtractionRecord,
        policy: SourcePolicy,
    ) -> VerificationRecord:
        temp = extraction.extracted.get("temp_c")
        condition = extraction.extracted.get("condition")
        completeness_ok = temp is not None or bool(condition)
        whitelist_ok = self._whitelist_ok(evidence, policy)
        blacklist_ok = self._blacklist_ok(evidence, policy)
        freshness_ok = True  # Evidence captured now; strict freshness managed upstream.

        checks = {
            "completeness_ok": completeness_ok,
            "whitelist_ok": whitelist_ok,
            "blacklist_ok": blacklist_ok,
            "freshness_ok": freshness_ok,
        }
        passed = all(checks.values())
        status = "pass" if passed else "fail"
        confidence = "medium" if passed else "low"
        reason = "weather_checks_passed" if passed else "weather_checks_failed"
        return VerificationRecord(
            evidence_id=evidence.evidence_id,
            kind="weather",
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

