"""CommunicationOS - Multi-channel communication system for OctopusOS.

This module provides a unified framework for integrating external communication
channels (WhatsApp, Telegram, Slack, etc.) with OctopusOS chat capabilities.

Key Components:
    - ChannelManifest: Declarative channel configuration
    - ChannelRegistry: Dynamic channel loading and management
    - ChannelConfigStore: Persistent storage for configurations

Design Principles:
    - Channel-agnostic core: Session management and commands work across all channels
    - Manifest-driven: New channels are added via manifests, not code changes
    - Security-first: Chat-only by default, execution requires explicit approval
    - Privacy-respecting: No auto-provisioning, local storage, encrypted secrets
"""

from octopusos.communicationos.models import (
    InboundMessage,
    OutboundMessage,
    MessageType,
    Attachment,
    AttachmentType,
)

from octopusos.communicationos.manifest import (
    ChannelManifest,
    ConfigField,
    SetupStep,
    SecurityDefaults,
    SessionScope,
    ChannelCapability,
    SecurityMode,
)

from octopusos.communicationos.registry import (
    ChannelRegistry,
    ChannelConfigStore,
    ChannelStatus,
)

from octopusos.communicationos.session_router import (
    SessionRouter,
    ResolvedContext,
)

from octopusos.communicationos.session_store import (
    SessionStore,
    SessionStatus,
)

from octopusos.communicationos.commands import (
    CommandProcessor,
    SessionInfo,
)

from octopusos.communicationos.message_bus import (
    MessageBus,
    Middleware,
    ProcessingContext,
    ProcessingStatus,
    ChannelAdapter,
)

from octopusos.communicationos.dedupe import (
    DedupeStore,
    DedupeMiddleware,
)

from octopusos.communicationos.rate_limit import (
    RateLimitStore,
    RateLimitMiddleware,
)

from octopusos.communicationos.audit import (
    AuditStore,
    AuditMiddleware,
)

from octopusos.communicationos.security import (
    SecurityPolicy,
    PolicyEnforcer,
    OperationType,
    ViolationType,
    RemoteExposureDetector,
    generate_admin_token,
)

__all__ = [
    "InboundMessage",
    "OutboundMessage",
    "MessageType",
    "Attachment",
    "AttachmentType",
    "ChannelManifest",
    "ConfigField",
    "SetupStep",
    "SecurityDefaults",
    "SessionScope",
    "ChannelCapability",
    "SecurityMode",
    "ChannelRegistry",
    "ChannelConfigStore",
    "ChannelStatus",
    "SessionRouter",
    "ResolvedContext",
    "SessionStore",
    "SessionStatus",
    "CommandProcessor",
    "SessionInfo",
    "MessageBus",
    "Middleware",
    "ProcessingContext",
    "ProcessingStatus",
    "ChannelAdapter",
    "DedupeStore",
    "DedupeMiddleware",
    "RateLimitStore",
    "RateLimitMiddleware",
    "AuditStore",
    "AuditMiddleware",
    "SecurityPolicy",
    "PolicyEnforcer",
    "OperationType",
    "ViolationType",
    "RemoteExposureDetector",
    "generate_admin_token",
]
