"""Content management system for OctopusOS.

This module provides the Content Registry infrastructure for managing
all system content (agents, workflows, commands, rules, policies, memories, facts).

v0.5 establishes the foundation - schema validation, versioning, lineage tracking,
and activation gates - but does NOT implement specific content execution.
"""

__version__ = "0.5.0"

from octopusos.core.content.registry import ContentRegistry
from octopusos.core.content.types import ContentTypeRegistry
from octopusos.core.content.activation import ContentActivationGate, LineageRequiredError
from octopusos.core.content.lineage import ContentLineageTracker
from octopusos.core.content.facade import UnifiedContentFacade

__all__ = [
    "ContentRegistry",
    "ContentTypeRegistry",
    "ContentActivationGate",
    "LineageRequiredError",
    "ContentLineageTracker",
    "UnifiedContentFacade",
]
