"""Verifier protocol for external facts."""

from __future__ import annotations

from typing import Protocol

from ..types import EvidenceItem, ExtractionRecord, SourcePolicy, VerificationRecord


class ExtractedFactVerifier(Protocol):
    def verify(
        self,
        evidence: EvidenceItem,
        extraction: ExtractionRecord,
        policy: SourcePolicy,
    ) -> VerificationRecord:
        """Verify extracted facts under source policy."""

