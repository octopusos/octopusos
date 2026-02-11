"""Streaming evidence gate primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from octopusos.core.time import utc_now_iso


@dataclass(frozen=True)
class StreamGateDecision:
    decision: Literal["allow", "hold", "reject"]
    reason_code: str
    used_kb: bool
    retrieval_run_id: str | None
    policy_snapshot_hash: str | None
    evidence_count: int
    mode: str
    action_taken: str
    timestamp: str
    output_text: str | None = None

    @classmethod
    def build(
        cls,
        *,
        decision: Literal["allow", "hold", "reject"],
        reason_code: str,
        used_kb: bool,
        retrieval_run_id: str | None,
        policy_snapshot_hash: str | None,
        evidence_count: int,
        mode: str,
        action_taken: str,
        output_text: str | None = None,
    ) -> "StreamGateDecision":
        return cls(
            decision=decision,
            reason_code=reason_code,
            used_kb=used_kb,
            retrieval_run_id=retrieval_run_id,
            policy_snapshot_hash=policy_snapshot_hash,
            evidence_count=evidence_count,
            mode=mode,
            action_taken=action_taken,
            timestamp=utc_now_iso(),
            output_text=output_text,
        )


class BufferedStreamer:
    """Buffer streaming tokens before gate release."""

    def __init__(self, max_chars: int = 8192):
        self.max_chars = max_chars
        self._chunks: list[str] = []
        self._chars = 0

    def append(self, chunk: str) -> bool:
        size = len(chunk)
        if self._chars + size > self.max_chars:
            return False
        self._chunks.append(chunk)
        self._chars += size
        return True

    def flush(self) -> list[str]:
        out = list(self._chunks)
        self._chunks.clear()
        self._chars = 0
        return out

