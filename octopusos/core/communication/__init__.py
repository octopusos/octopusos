"""Communication module for external network interactions.

This module provides secure, auditable external communication capabilities
for OctopusOS, including web search, web fetch, RSS feeds, email, and messaging.

Key components:
- CommunicationService: Main service orchestrator
- PolicyEngine: Security policy enforcement
- Connectors: External service integrations
- Evidence: Request/response tracking and audit
- Sanitizers: Input/output security filtering
"""

from octopusos.core.communication.service import CommunicationService
from octopusos.core.communication.policy import PolicyEngine, CommunicationPolicy
from octopusos.core.communication.models import (
    CommunicationRequest,
    CommunicationResponse,
    ConnectorType,
    RequestStatus,
)
from octopusos.core.communication.evidence import EvidenceLogger
from octopusos.core.communication.rate_limit import RateLimiter

__all__ = [
    "CommunicationService",
    "PolicyEngine",
    "CommunicationPolicy",
    "CommunicationRequest",
    "CommunicationResponse",
    "ConnectorType",
    "RequestStatus",
    "EvidenceLogger",
    "RateLimiter",
]
