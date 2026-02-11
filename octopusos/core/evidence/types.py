"""Evidence reference types and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class EvidenceRef:
    source_id: str
    uri: str
    locator: str
    content_hash: str
    snippet: str = ""
    explanation: str = ""
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.confidence is None:
            data.pop("confidence")
        return data


def normalize_evidence_refs(
    refs: list[EvidenceRef | dict[str, Any]],
    *,
    max_items: int = 20,
    max_snippet_chars: int = 240,
    max_explanation_chars: int = 240,
) -> list[EvidenceRef]:
    """Normalize refs with deterministic dedupe/sort/limits."""
    normalized: list[EvidenceRef] = []

    for ref in refs:
        if isinstance(ref, EvidenceRef):
            item = ref
        else:
            item = EvidenceRef(
                source_id=str(ref.get("source_id", "")),
                uri=str(ref.get("uri", "")),
                locator=str(ref.get("locator", "")),
                content_hash=str(ref.get("content_hash", "")),
                snippet=str(ref.get("snippet", ""))[:max_snippet_chars],
                explanation=str(ref.get("explanation", ""))[:max_explanation_chars],
                confidence=ref.get("confidence"),
            )

        if not item.source_id or not item.uri or not item.locator:
            continue

        normalized.append(
            EvidenceRef(
                source_id=item.source_id,
                uri=item.uri,
                locator=item.locator,
                content_hash=item.content_hash,
                snippet=item.snippet[:max_snippet_chars],
                explanation=item.explanation[:max_explanation_chars],
                confidence=item.confidence,
            )
        )

    dedup: dict[tuple[str, str, str, str], EvidenceRef] = {}
    for item in normalized:
        key = (item.source_id, item.uri, item.locator, item.content_hash)
        if key not in dedup:
            dedup[key] = item
            continue

        existing = dedup[key]
        existing_rank = (
            existing.snippet,
            existing.explanation,
            existing.confidence if existing.confidence is not None else -1.0,
        )
        candidate_rank = (
            item.snippet,
            item.explanation,
            item.confidence if item.confidence is not None else -1.0,
        )
        if candidate_rank < existing_rank:
            dedup[key] = item

    ordered = sorted(
        dedup.values(),
        key=lambda item: (
            item.source_id,
            item.uri,
            item.locator,
            item.content_hash,
            item.snippet,
            item.explanation,
            item.confidence if item.confidence is not None else -1.0,
        ),
    )

    return ordered[:max_items]
