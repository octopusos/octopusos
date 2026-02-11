"""FX snippet extractor."""

from __future__ import annotations

import re

from ..types import EvidenceItem, ExtractionRecord


class FxSnippetExtractor:
    """Rule-based FX extraction from snippet text."""

    def extract(self, evidence: EvidenceItem) -> ExtractionRecord:
        text = (evidence.content_snippet or "").strip().upper()
        pair_match = re.search(r"(?<![A-Z])([A-Z]{3})\s*(?:/|TO|->|兑|对|-)\s*([A-Z]{3})(?![A-Z])", text)
        if pair_match:
            base, quote = pair_match.group(1), pair_match.group(2)
        else:
            codes = re.findall(r"(?<![A-Z])([A-Z]{3})(?![A-Z])", text)
            base, quote = (codes[0], codes[1]) if len(codes) >= 2 else ("AUD", "USD")

        rate_match = re.search(r"\b([0-9]+\.[0-9]+)\b", text)
        rate = float(rate_match.group(1)) if rate_match else None
        extracted = {"base": base, "quote": quote, "pair": f"{base}{quote}", "rate": rate}
        missing = [k for k, v in extracted.items() if v in (None, "")]
        if rate is not None:
            status = "ok"
            notes = "fx_rate_extracted"
        elif len(missing) < len(extracted):
            status = "partial"
            notes = "fx_partial_extracted"
        else:
            status = "failed"
            notes = "fx_extraction_failed"

        return ExtractionRecord(
            evidence_id=evidence.evidence_id,
            kind="fx",
            schema_version="v1",
            status=status,
            extracted=extracted,
            missing_fields=missing,
            notes=notes,
        )
