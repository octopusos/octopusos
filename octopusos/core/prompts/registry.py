"""Prompt registry for governed prompt specs."""

from __future__ import annotations

from typing import Optional

from .spec import PromptSpec


class PromptRegistryError(Exception):
    """Prompt registry error."""


class PromptSpecNotFoundError(PromptRegistryError):
    """Raised when prompt spec id is missing."""


class PromptRegistry:
    """In-memory registry for prompt specs."""

    def __init__(self):
        self._specs: dict[str, PromptSpec] = {}

    def register(self, spec: PromptSpec) -> None:
        self._specs[spec.id] = spec

    def get(self, spec_id: str) -> PromptSpec:
        spec = self._specs.get(spec_id)
        if spec is None:
            raise PromptSpecNotFoundError(f"Prompt spec not found: {spec_id}")
        return spec

    def maybe_get(self, spec_id: str) -> Optional[PromptSpec]:
        return self._specs.get(spec_id)


_default_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = PromptRegistry()
    return _default_registry
