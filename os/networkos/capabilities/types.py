"""NetworkOS capability types (M2).

These types intentionally live under NetworkOS and must not be reused for
CommunicationOS message audit semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class GateDecision(str, Enum):
    SILENT_ALLOW = "silent_allow"
    EXPLAIN_CONFIRM = "explain_confirm"
    BLOCK = "block"


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    FAILED = "failed"
    REVOKED = "revoked"


class RiskLevel(str, Enum):
    HIGH = "high"


@dataclass(frozen=True)
class CapabilitySpec:
    capability: str
    risk: RiskLevel
    default_gate: GateDecision
    allowed_scopes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability,
            "risk": self.risk.value,
            "default_gate": self.default_gate.value,
            "allowed_scopes": list(self.allowed_scopes),
        }

