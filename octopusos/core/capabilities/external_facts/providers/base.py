"""Provider interface for ExternalFactsCapability."""

from __future__ import annotations

from typing import Any, Dict, Protocol

from ..types import FactKind, FactResult


class FactProvider(Protocol):
    """Read-only structured fact provider."""

    kind: FactKind

    async def resolve(self, query: str, context: Dict[str, Any]) -> FactResult:
        """Resolve query into a FactResult."""

