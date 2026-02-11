"""Base protocol for evidence snippet extractors."""

from __future__ import annotations

from typing import Protocol

from ..types import EvidenceItem, ExtractionRecord


class SnippetExtractor(Protocol):
    def extract(self, evidence: EvidenceItem) -> ExtractionRecord:
        """Extract structured fields from an evidence snippet."""

