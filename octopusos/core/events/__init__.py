"""
Core Events Module - Event-driven architecture for OctopusOS

Sprint B Task #4: Real-time event streaming infrastructure

Architecture:
- Core emits events to EventBus (zero coupling to WebUI)
- EventBus broadcasts to subscribers (WebUI WS, loggers, etc.)
- Events follow unified envelope protocol v1
"""

from octopusos.core.events.types import Event, EventEntity, EventType
from octopusos.core.events.bus import EventBus, get_event_bus

__all__ = [
    "Event",
    "EventEntity",
    "EventType",
    "EventBus",
    "get_event_bus",
]
