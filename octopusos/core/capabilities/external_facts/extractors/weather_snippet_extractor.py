"""Weather snippet extractor."""

from __future__ import annotations

import re

from ..types import EvidenceItem, ExtractionRecord


class WeatherSnippetExtractor:
    """Rule-based weather field extraction from text snippets."""

    def extract(self, evidence: EvidenceItem) -> ExtractionRecord:
        text = (evidence.content_snippet or "").strip()
        temp = self._extract_temp(text)
        condition = self._extract_condition(text)

        extracted = {
            "temp_c": temp,
            "condition": condition,
        }
        missing = [k for k, v in extracted.items() if v in (None, "")]
        if len(missing) == 0:
            status = "ok"
            notes = "weather_fields_extracted"
        elif len(missing) == len(extracted):
            status = "failed"
            notes = "no_weather_fields_extracted"
        else:
            status = "partial"
            notes = "partial_weather_fields_extracted"

        return ExtractionRecord(
            evidence_id=evidence.evidence_id,
            kind="weather",
            schema_version="v1",
            status=status,
            extracted=extracted,
            missing_fields=missing,
            notes=notes,
        )

    @staticmethod
    def _extract_temp(text: str):
        match = re.search(r"(-?\d+(?:\.\d+)?)\s*°?\s*C\b", text, flags=re.IGNORECASE)
        if not match:
            f_match = re.search(r"(-?\d+(?:\.\d+)?)\s*°?\s*F\b", text, flags=re.IGNORECASE)
            if not f_match:
                return None
            f_value = float(f_match.group(1))
            return round((f_value - 32.0) * (5.0 / 9.0), 1)
        return float(match.group(1))

    @staticmethod
    def _extract_condition(text: str):
        lower = text.lower()
        for token in ("sunny", "clear", "cloudy", "rain", "storm", "windy", "fog"):
            if token in lower:
                return token
        return None

