"""Guardrails for chat-driven tool dispatch."""

from __future__ import annotations

import re

_WRITE_PATTERNS = [
    r"\bdelete\b",
    r"\bremove\b",
    r"\bdestroy\b",
    r"\bput\b",
    r"\bupdate\b",
    r"\bmodify\b",
    r"\bcreate\b",
    r"\battach\b",
    r"\bdetach\b",
    r"\bterminate\b",
    r"\bstop\b",
    r"\bstart\b",
]

_WRITE_RE = re.compile("|".join(_WRITE_PATTERNS), re.IGNORECASE)


def is_high_risk_aws_intent(text: str) -> bool:
    return bool(_WRITE_RE.search(text or ""))
