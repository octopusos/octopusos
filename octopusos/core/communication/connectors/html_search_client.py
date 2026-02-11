"""Open-source contract placeholder for HTML web search backend.

Implementation intentionally lives in an internal extension package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError


class BlockedError(Exception):
    """Raised when an engine returns a challenge/bot-detection page."""


@dataclass
class HtmlSearchClient:
    """Contract placeholder.

    Real implementation is provided by an internal extension package such as:
    `octopus_ext_websearch`.
    """

    timeout: int = 30

    def search(
        self,
        engine: str,
        query: str,
        max_results: int,
        language: str = "en",
        google_mode: str = "auto",
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "HTML web search implementation is not available in open-source runtime. "
            "Install internal extension 'octopusos-ext-websearch' and configure "
            "WEB_SEARCH_EXTENSION_ENTRYPOINT."
        )


__all__ = ["HtmlSearchClient", "BlockedError", "HTTPError", "URLError"]
