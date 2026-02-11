"""Evidence governance primitives."""

from .types import EvidenceRef, normalize_evidence_refs
from .requirement import EnforcementResult, enforce_evidence

__all__ = [
    "EvidenceRef",
    "normalize_evidence_refs",
    "EnforcementResult",
    "enforce_evidence",
]
