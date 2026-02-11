"""External facts capability for structured read-only real-time facts."""

from .capability import ExternalFactsCapability
from .evidence_store import EvidenceStore
from .policy_store import ExternalFactsPolicyStore
from .intent_plan import IntentPlan
from .plan_executor import ExternalFactsPlanExecutor
from .replay_store import ReplayStore
from .registry import CAPABILITY_REGISTRY, CapabilityDef, ItemSchema, get_capability, list_capabilities
from .types import (
    Confidence,
    EvidenceItem,
    EvidenceType,
    ExtractionRecord,
    ExtractionStatus,
    FactKind,
    FactResult,
    LegacyFactResult,
    FactStatus,
    SourcePolicy,
    SourceRef,
    SUPPORTED_FACT_KINDS,
    VerificationRecord,
    VerificationStatus,
)

__all__ = [
    "ExternalFactsCapability",
    "EvidenceStore",
    "EvidenceItem",
    "EvidenceType",
    "ExtractionStatus",
    "VerificationStatus",
    "Confidence",
    "ExtractionRecord",
    "VerificationRecord",
    "FactKind",
    "FactResult",
    "LegacyFactResult",
    "FactStatus",
    "SourcePolicy",
    "SourceRef",
    "SUPPORTED_FACT_KINDS",
    "ReplayStore",
    "ExternalFactsPolicyStore",
    "IntentPlan",
    "ExternalFactsPlanExecutor",
    "ItemSchema",
    "CapabilityDef",
    "CAPABILITY_REGISTRY",
    "get_capability",
    "list_capabilities",
]
