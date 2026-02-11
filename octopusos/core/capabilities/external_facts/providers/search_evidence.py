"""Search provider that only emits evidence, never structured facts."""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import urlparse

from octopusos.core.chat.communication_adapter import CommunicationAdapter

from ..types import EvidenceItem, FactKind, SourcePolicy, SourceRef

logger = logging.getLogger(__name__)


class SearchEvidenceProvider:
    """Collect external materials as evidence for later verification."""

    def __init__(self, adapter: CommunicationAdapter | None = None) -> None:
        self.adapter = adapter or CommunicationAdapter()

    async def collect(
        self,
        kind: FactKind,
        query: str,
        policy: SourcePolicy,
        context: Dict[str, Any],
    ) -> List[EvidenceItem]:
        session_id = str(context.get("session_id") or "external_facts")
        task_id = str(context.get("task_id") or "external_facts")
        max_results = max(1, min(6, policy.max_sources * 2))
        items: List[EvidenceItem] = []
        seen_sources: set[str] = set()
        site_scopes = list(policy.source_whitelist[: max(1, policy.max_sources)]) or [None]

        for site in site_scopes:
            scoped_query = f"{query} site:{site}" if site else query
            response = await self.adapter.search(
                query=scoped_query,
                session_id=session_id,
                task_id=task_id,
                max_results=max_results,
            )
            results = response.get("results") if isinstance(response, dict) else []
            if not isinstance(results, list):
                continue
            for result in results:
                if not isinstance(result, dict):
                    continue
                url = str(result.get("url") or "").strip() or None
                source_name = self._source_name(url, result)
                if source_name in seen_sources:
                    continue
                if self._blocked(source_name, policy):
                    continue
                snippet = str(result.get("snippet") or result.get("title") or "").strip()
                if not snippet:
                    continue
                items.append(
                    EvidenceItem(
                        kind=kind,
                        query=query,
                        type="search_result",
                        source=SourceRef(name=source_name, type="search", url=url),
                        content_snippet=snippet[:2048],
                        raw_ref=url,
                    )
                )
                seen_sources.add(source_name)
                if len(items) >= policy.max_sources:
                    return items

        return items

    @staticmethod
    def _source_name(url: str | None, result: Dict[str, Any]) -> str:
        if url:
            try:
                host = urlparse(url).netloc.lower()
                if host:
                    return host
            except Exception:
                pass
        source = str(result.get("source") or "").strip().lower()
        return source or "unknown"

    @staticmethod
    def _blocked(source_name: str, policy: SourcePolicy) -> bool:
        source = source_name.lower()
        if policy.source_whitelist:
            if not any(source.endswith(item.lower()) for item in policy.source_whitelist):
                return True
        if policy.source_blacklist:
            if any(source.endswith(item.lower()) for item in policy.source_blacklist):
                return True
        return False
