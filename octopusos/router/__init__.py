"""
Task Router - Capability-driven routing system for OctopusOS

Provides intelligent instance selection based on task requirements,
with full auditability and explainability.

PR-1: Core router implementation with requirements extraction,
instance profiling, scoring, and routing decisions.
"""

from octopusos.router.router import Router
from octopusos.router.models import (
    RoutePlan,
    TaskRequirements,
    InstanceProfile,
    RerouteReason,
    RerouteEvent,
    RouteDecision,
)
from octopusos.router.requirements_extractor import RequirementsExtractor
from octopusos.router.instance_profiles import InstanceProfileBuilder
from octopusos.router.scorer import RouteScorer, RouteScore
from octopusos.router.persistence import RouterPersistence
from octopusos.router import events as router_events

__all__ = [
    "Router",
    "RoutePlan",
    "TaskRequirements",
    "InstanceProfile",
    "RerouteReason",
    "RerouteEvent",
    "RouteDecision",
    "RequirementsExtractor",
    "InstanceProfileBuilder",
    "RouteScorer",
    "RouteScore",
    "RouterPersistence",
    "router_events",
]
