"""No-op plugin for public shell extension example."""

from __future__ import annotations

from typing import Any, Dict


def create_web_search_backend(config: Dict[str, Any]):
    raise NotImplementedError(
        "This is a shell example only. Install private package 'octopusos-ext-websearch' "
        "for executable web_search backend."
    )
