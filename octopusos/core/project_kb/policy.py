"""Retrieval policy model and snapshot utilities."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RetrievalPolicy:
    retrieval_mode: str = "keyword"  # keyword|hybrid
    top_k: int = 10
    min_score: float = 0.0
    use_rerank: bool = False
    candidate_k: int = 50
    keyword_weight: float = 1.0
    vector_weight: float = 1.0
    timeout_ms: int = 800
    evidence_required: bool = True

    def snapshot(self) -> dict:
        return asdict(self)

    def snapshot_hash(self) -> str:
        encoded = json.dumps(
            self.snapshot(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def resolve_retrieval_policy(
    *,
    top_k: int,
    use_rerank: bool,
    candidate_k: int,
) -> RetrievalPolicy:
    mode = os.getenv("OCTOPUSOS_RETRIEVAL_MODE", "keyword").strip().lower()
    if mode not in {"keyword", "hybrid"}:
        mode = "keyword"

    min_score_raw = os.getenv("OCTOPUSOS_RETRIEVAL_MIN_SCORE", "0.0")
    timeout_raw = os.getenv("OCTOPUSOS_RETRIEVAL_TIMEOUT_MS", "800")
    keyword_weight_raw = os.getenv("OCTOPUSOS_RETRIEVAL_KEYWORD_WEIGHT", "1.0")
    vector_weight_raw = os.getenv("OCTOPUSOS_RETRIEVAL_VECTOR_WEIGHT", "1.0")
    evidence_required_raw = os.getenv("OCTOPUSOS_RETRIEVAL_EVIDENCE_REQUIRED", "true")

    try:
        min_score = float(min_score_raw)
    except ValueError:
        min_score = 0.0
    try:
        timeout_ms = int(timeout_raw)
    except ValueError:
        timeout_ms = 800
    try:
        keyword_weight = float(keyword_weight_raw)
    except ValueError:
        keyword_weight = 1.0
    try:
        vector_weight = float(vector_weight_raw)
    except ValueError:
        vector_weight = 1.0

    evidence_required = evidence_required_raw.strip().lower() not in {"0", "false", "no"}

    return RetrievalPolicy(
        retrieval_mode=mode,
        top_k=top_k,
        min_score=min_score,
        use_rerank=bool(use_rerank),
        candidate_k=candidate_k,
        keyword_weight=keyword_weight,
        vector_weight=vector_weight,
        timeout_ms=timeout_ms,
        evidence_required=evidence_required,
    )
