"""MemoryOS migration wrapper."""

from __future__ import annotations

from octopusos.core.storage.migrations import ensure_component_migrations


def ensure_memoryos_migrations() -> int:
    return ensure_component_migrations("memoryos")
