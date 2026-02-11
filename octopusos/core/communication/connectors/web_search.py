"""Web search connector for searching the internet."""

from __future__ import annotations

import asyncio
import copy
import importlib
import logging
import os
from time import monotonic
from typing import Any, Dict, List, Optional, Set
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from octopusos.core.communication.connectors.base import BaseConnector
from octopusos.core.communication.connectors.html_search_client import (
    BlockedError as HtmlBlockedError,
    HTTPError,
    URLError,
)
from octopusos.core.communication.priority import calculate_priority_score
from octopusos.core.communication.config import load_trusted_sources

logger = logging.getLogger(__name__)
TRACKING_QUERY_PREFIXES = ("utm_", "ga_", "pk_")
TRACKING_QUERY_KEYS = {
    "gclid",
    "fbclid",
    "msclkid",
    "mc_eid",
    "mc_cid",
    "igshid",
    "ref",
    "ref_src",
    "source",
}


class WebSearchError(Exception):
    """Base exception for web search errors."""


class APIError(WebSearchError):
    """API-related errors."""


class NetworkError(WebSearchError):
    """Network-related errors."""


class RateLimitError(WebSearchError):
    """Rate limit errors."""


class BlockedError(WebSearchError):
    """Blocked/challenge responses that prevented parsing."""


class WebSearchConnector(BaseConnector):
    """Connector for web search operations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize web search connector."""
        super().__init__(config)
        self.api_key = self.config.get("api_key")
        self.engine = self.config.get("engine", "duckduckgo")
        self.max_results = self.config.get("max_results", 10)
        self.timeout = self.config.get("timeout", 30)
        self.deduplicate = self.config.get("deduplicate", True)
        self.google_mode = (self.config.get("google_mode", "auto") or "auto").strip().lower()
        self.success_cache_ttl = int(self.config.get("success_cache_ttl", 60))
        self.failure_cache_ttl = int(self.config.get("failure_cache_ttl", 10))
        self.extension_entrypoint = (
            self.config.get("extension_entrypoint")
            or os.getenv("WEB_SEARCH_EXTENSION_ENTRYPOINT", "octopus_ext_websearch.plugin:create_web_search_backend")
        )
        self.search_backend = self._load_search_backend()
        self._success_cache: Dict[str, Any] = {}
        self._failure_cache: Dict[str, Any] = {}

        try:
            self.trusted_sources = load_trusted_sources()
        except Exception as e:
            logger.warning(f"Failed to load trusted sources: {e}")
            self.trusted_sources = {
                "official_policy": [],
                "recognized_ngo": [],
            }

    def _load_search_backend(self) -> Optional[Any]:
        """Load internal extension backend for web search implementation."""
        if not self.extension_entrypoint:
            logger.warning("WEB_SEARCH_EXTENSION_ENTRYPOINT is empty; web search backend disabled")
            return None

        try:
            module_name, factory_name = self.extension_entrypoint.split(":", 1)
            module = importlib.import_module(module_name)
            factory = getattr(module, factory_name)
            backend = factory({
                "engine": self.engine,
                "timeout": self.timeout,
                "google_mode": self.google_mode,
            })
            logger.info("Loaded web search backend from extension entrypoint: %s", self.extension_entrypoint)
            return backend
        except Exception as e:
            logger.warning(
                "Web search extension backend unavailable (%s): %s",
                self.extension_entrypoint,
                e,
            )
            return None

    async def execute(self, operation: str, params: Dict[str, Any]) -> Any:
        """Execute a web search operation."""
        if not self.enabled:
            raise Exception("Web search connector is disabled")

        if operation == "search":
            return await self._search(params)
        raise ValueError(f"Unsupported operation: {operation}")

    async def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search."""
        query = params.get("query")
        if not query:
            raise ValueError("Search query is required")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query must be a non-empty string")

        max_results = params.get("max_results", self.max_results)
        language = params.get("language", "en")
        cache_key = self._build_cache_key(query, max_results, language)

        failure = self._get_cached_failure(cache_key)
        if failure is not None:
            raise failure

        cached = self._get_cached_success(cache_key)
        if cached is not None:
            return cached

        logger.info(f"Performing {self.engine} search: {query}")

        try:
            if self.engine in ("google", "googlesearch"):
                raw_results = await self._search_google(query, max_results, language)
                engine_used = "google"
            elif self.engine == "bing":
                raw_results = await self._search_bing(query, max_results, language)
                engine_used = "bing"
            elif self.engine == "duckduckgo":
                raw_results = await self._search_duckduckgo(query, max_results, language)
                engine_used = "duckduckgo"
            else:
                raise ValueError(f"Unsupported search engine: {self.engine}")

            results = self._standardize_results(raw_results)
            if self.deduplicate:
                results = self._deduplicate_results(results)
            results = results[:max_results]
            for index, result in enumerate(results, start=1):
                result["rank"] = index

            response = {
                "query": query,
                "results": results,
                "total_results": len(results),
                "engine": engine_used,
            }
            self._set_cached_success(cache_key, response)
            self._failure_cache.pop(cache_key, None)
            return response

        except WebSearchError as e:
            self._set_cached_failure(cache_key, e)
            raise
        except Exception as e:
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            wrapped = WebSearchError(f"Search failed: {str(e)}")
            self._set_cached_failure(cache_key, wrapped)
            raise wrapped from e

    async def _search_google(self, query: str, max_results: int, language: str) -> List[Dict[str, Any]]:
        return await self._search_html_engine("google", query, max_results, language)

    async def _search_bing(self, query: str, max_results: int, language: str) -> List[Dict[str, Any]]:
        return await self._search_html_engine("bing", query, max_results, language)

    async def _search_duckduckgo(self, query: str, max_results: int, language: str) -> List[Dict[str, Any]]:
        return await self._search_html_engine("duckduckgo", query, max_results, language)

    async def _search_html_engine(
        self,
        engine: str,
        query: str,
        max_results: int,
        language: str,
    ) -> List[Dict[str, Any]]:
        if self.search_backend is None:
            raise APIError(
                "Web search backend is disabled in open-source runtime. "
                "Install internal extension and configure WEB_SEARCH_EXTENSION_ENTRYPOINT."
            )
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: self.search_backend.search(
                    engine=engine,
                    query=query,
                    max_results=max_results,
                    language=language,
                    google_mode=self.google_mode,
                ),
            )
        except HtmlBlockedError as e:
            raise BlockedError(f"{engine} blocked/challenge response: {e}") from e
        except HTTPError as e:
            if e.code == 429:
                raise RateLimitError(f"{engine} rate limit exceeded: HTTP {e.code}") from e
            raise APIError(f"{engine} HTTP error: {e.code}") from e
        except URLError as e:
            raise NetworkError(f"Network error during {engine} search: {e.reason}") from e
        except TimeoutError as e:
            raise NetworkError(f"Timeout during {engine} search") from e
        except ValueError:
            raise
        except Exception as e:
            error_text = str(e).lower()
            if "429" in error_text or "rate" in error_text:
                raise RateLimitError(f"{engine} rate limit exceeded: {e}") from e
            raise APIError(f"{engine} search failed: {e}") from e

    def _standardize_results(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Standardize search results to uniform format with priority scoring."""
        standardized = []

        for result in raw_results:
            try:
                title = result.get("title") or result.get("name", "")
                url = result.get("href") or result.get("url") or result.get("link", "")
                snippet = result.get("body") or result.get("snippet", "")
                source = result.get("source") or f"{self.engine}_raw"
                published_at = result.get("published_at", "")

                if not url:
                    logger.warning(f"Skipping result without URL: {result}")
                    continue

                try:
                    normalized_url = self._canonicalize_url(url.strip())
                    parsed = urlparse(normalized_url)
                    if not parsed.scheme or not parsed.netloc:
                        logger.warning(f"Invalid URL format: {url}")
                        continue
                    domain = parsed.netloc
                except Exception:
                    logger.warning(f"Failed to parse URL: {url}")
                    continue

                try:
                    priority_score_obj = calculate_priority_score(
                        url=normalized_url,
                        snippet=snippet.strip() if snippet else "",
                        trusted_sources=self.trusted_sources,
                    )
                    priority_score = priority_score_obj.total_score
                    priority_reasons = [reason.value for reason in priority_score_obj.reasons]
                except Exception as e:
                    logger.warning(f"Failed to calculate priority score for {url}: {e}")
                    priority_score = 0
                    priority_reasons = []

                standardized.append(
                    {
                        "title": title.strip() if title else "",
                        "url": normalized_url,
                        "snippet": snippet.strip() if snippet else "",
                        "source": source,
                        "published_at": published_at.strip() if isinstance(published_at, str) else "",
                        "domain": domain,
                        "priority_score": priority_score,
                        "priority_reasons": priority_reasons,
                    }
                )

            except Exception as e:
                logger.warning(f"Failed to standardize result: {e}")
                continue

        standardized.sort(key=lambda x: x["priority_score"], reverse=True)
        return standardized

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on URL."""
        seen_urls: Set[str] = set()
        deduplicated = []

        for result in results:
            url = result["url"].lower().rstrip("/")
            normalized_url = self._canonicalize_url(url)

            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                deduplicated.append(result)
            else:
                logger.debug(f"Skipping duplicate URL: {url}")

        return deduplicated

    def get_supported_operations(self) -> List[str]:
        """Get list of supported operations."""
        return ["search"]

    def validate_config(self) -> bool:
        """Validate connector configuration."""
        if self.engine not in ["google", "googlesearch", "duckduckgo", "bing"]:
            logger.error(f"Unsupported search engine: {self.engine}")
            return False
        if self.google_mode not in ["auto", "web_html", "news_rss"]:
            logger.error(f"Unsupported google_mode: {self.google_mode}")
            return False

        return True

    @staticmethod
    def _now() -> float:
        return monotonic()

    def _build_cache_key(self, query: str, max_results: int, language: str) -> str:
        normalized_query = query.strip().lower()
        normalized_language = (language or "en").strip().lower()
        return f"{self.engine}|{self.google_mode}|{normalized_language}|{max_results}|{normalized_query}"

    def _get_cached_success(self, key: str) -> Optional[Dict[str, Any]]:
        record = self._success_cache.get(key)
        if not record:
            return None
        expires_at, payload = record
        if self._now() >= expires_at:
            self._success_cache.pop(key, None)
            return None
        return copy.deepcopy(payload)

    def _set_cached_success(self, key: str, payload: Dict[str, Any]) -> None:
        self._success_cache[key] = (
            self._now() + max(self.success_cache_ttl, 0),
            copy.deepcopy(payload),
        )

    def _get_cached_failure(self, key: str) -> Optional[WebSearchError]:
        record = self._failure_cache.get(key)
        if not record:
            return None
        expires_at, error_type, message = record
        if self._now() >= expires_at:
            self._failure_cache.pop(key, None)
            return None
        return error_type(message)

    def _set_cached_failure(self, key: str, error: WebSearchError) -> None:
        self._failure_cache[key] = (
            self._now() + max(self.failure_cache_ttl, 0),
            type(error),
            str(error),
        )

    def _canonicalize_url(self, url: str) -> str:
        try:
            parsed = urlparse(url.strip())
            query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
            filtered_pairs = []
            for key, value in query_pairs:
                key_lower = key.lower()
                if key_lower in TRACKING_QUERY_KEYS:
                    continue
                if any(key_lower.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
                    continue
                filtered_pairs.append((key, value))

            normalized_query = urlencode(filtered_pairs, doseq=True)
            normalized = parsed._replace(
                scheme=parsed.scheme.lower(),
                netloc=parsed.netloc.lower(),
                fragment="",
                query=normalized_query,
            )
            rebuilt = urlunparse(normalized)
            if rebuilt.endswith("/"):
                rebuilt = rebuilt.rstrip("/")
            return rebuilt
        except Exception:
            return url.strip().rstrip("/")
