"""Knowledge source plugin interfaces for multi-source ingest."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    version: str
    risk_level: str
    origin: str
    content: str
    timestamp_utc: str
    content_hash: str
    license: str | None = None
    meta: dict | None = None


class KnowledgeSource(Protocol):
    source_id: str
    version: str
    risk_level: str

    def fetch(self, query: str) -> list[SourceRecord]:
        ...


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class LocalSource:
    source_id = "local"
    version = "1.0.0"
    risk_level = "low"

    def __init__(self, root: Path):
        self.root = root

    def fetch(self, query: str) -> list[SourceRecord]:
        matches: list[SourceRecord] = []
        for path in self.root.rglob("*.md"):
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if query.lower() not in content.lower():
                continue
            matches.append(
                SourceRecord(
                    source_id=self.source_id,
                    version=self.version,
                    risk_level=self.risk_level,
                    origin=str(path),
                    content=content,
                    timestamp_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    content_hash=_hash_content(content),
                    meta={"path": str(path)},
                )
            )
        return matches


class WebSource:
    source_id = "web"
    version = "1.0.0"
    risk_level = "medium"

    def __init__(self, allowlist_domains: list[str]):
        self.allowlist_domains = {domain.lower() for domain in allowlist_domains}

    def fetch(self, query: str) -> list[SourceRecord]:
        # Network retrieval is intentionally left to higher-level adapters;
        # this record preserves contract shape for governance ingestion.
        return [
            SourceRecord(
                source_id=self.source_id,
                version=self.version,
                risk_level=self.risk_level,
                origin=f"web://query?q={query}",
                content="",
                timestamp_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                content_hash=_hash_content(query),
                meta={"allowlist_domains": sorted(self.allowlist_domains)},
            )
        ]


class RepoSource:
    source_id = "repo"
    version = "1.0.0"
    risk_level = "low"

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def fetch(self, query: str) -> list[SourceRecord]:
        marker = f"repo:{query}"
        return [
            SourceRecord(
                source_id=self.source_id,
                version=self.version,
                risk_level=self.risk_level,
                origin=str(self.repo_root),
                content=marker,
                timestamp_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                content_hash=_hash_content(marker),
                meta={"query": query},
            )
        ]


class KnowledgeSourceRegistry:
    def __init__(self):
        self._sources: dict[str, KnowledgeSource] = {}

    def register(self, source: KnowledgeSource) -> None:
        self._sources[source.source_id] = source

    def get(self, source_id: str) -> KnowledgeSource | None:
        return self._sources.get(source_id)

    def list_ids(self) -> list[str]:
        return sorted(self._sources.keys())
