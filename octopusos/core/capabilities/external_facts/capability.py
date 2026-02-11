"""ExternalFactsCapability implementation."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .evidence_store import EvidenceStore
from .extractors import FxSnippetExtractor, WeatherSnippetExtractor
from .providers.fx_structured import FxStructuredProvider
from .providers.configured_api import ConfiguredApiProvider
from .providers.index_structured import IndexStructuredProvider
from .providers.search_evidence import SearchEvidenceProvider
from .providers.weather_structured import WeatherStructuredProvider
from .provider_store import ExternalFactsProviderStore
from .replay_store import ReplayStore
from .fx_timeseries_store import FxTimeSeriesStore
from .source_catalog import merge_with_catalog
from .types import (
    EvidenceItem,
    FactResult,
    FactKind,
    LegacyFactResult,
    FxData,
    GenericFactData,
    SourcePolicy,
    SourceRef,
    WeatherData,
    utc_now_iso,
    validate_fx_complete,
    validate_weather_complete,
)
from .verifiers import FxVerifier, WeatherVerifier


class ExternalFactsCapability:
    """Resolve read-only external facts into normalized legacy FactResult objects."""

    def __init__(
        self,
        weather_provider: Optional[WeatherStructuredProvider] = None,
        fx_provider: Optional[FxStructuredProvider] = None,
        index_provider: Optional[IndexStructuredProvider] = None,
        search_provider: Optional[SearchEvidenceProvider] = None,
        evidence_store: Optional[EvidenceStore] = None,
        replay_store: Optional[ReplayStore] = None,
    ) -> None:
        self._providers = {
            "weather": weather_provider or WeatherStructuredProvider(),
            "fx": fx_provider or FxStructuredProvider(),
            "index": index_provider or IndexStructuredProvider(),
        }
        self._search_provider = search_provider or SearchEvidenceProvider()
        self._configured_provider = ConfiguredApiProvider()
        self._provider_store = ExternalFactsProviderStore()
        self._fx_timeseries_store = FxTimeSeriesStore()
        self._evidence_store = evidence_store or EvidenceStore()
        self._replay_store = replay_store or ReplayStore()
        self._extractors = {
            "weather": WeatherSnippetExtractor(),
            "fx": FxSnippetExtractor(),
        }
        self._verifiers = {
            "weather": WeatherVerifier(),
            "fx": FxVerifier(),
        }

    async def resolve(
        self,
        kind: FactKind,
        query: str,
        context: Dict[str, Any],
        policy: Optional[SourcePolicy] = None,
    ) -> LegacyFactResult:
        policy = policy or self.default_policy_for(kind)
        provider = self._providers.get(kind)
        now_iso = context.get("now_iso") or utc_now_iso()
        effective_policy = self._ensure_policy_sources(kind, policy)
        custom_result = await self._resolve_custom_provider_result(
            kind=kind,
            query=query,
            context={**context, "now_iso": now_iso},
        )
        if custom_result is not None:
            result = custom_result
        elif provider is None:
            result = self._unavailable(kind, query, now_iso)
        else:
            result = await provider.resolve(query=query, context={**context, "now_iso": now_iso})
        normalized = self.validate_and_normalize(
            result=result,
            query=query,
            now_iso=now_iso,
            policy=effective_policy,
        )
        self._persist_fx_sample(normalized)
        if normalized.status == "ok":
            return normalized
        if not effective_policy.allow_search_fallback:
            return normalized

        evidence_items = await self._search_provider.collect(
            kind=kind,
            query=query,
            policy=effective_policy,
            context={**context, "now_iso": now_iso},
        )
        filtered_items = self._apply_source_policy(evidence_items, effective_policy)
        replay_ids = self._build_replay_chain(filtered_items, kind=kind, policy=effective_policy)
        evidence_ids = replay_ids["evidence_ids"]
        if not evidence_ids:
            return normalized

        return replace(
            normalized,
            status="unavailable",
            render_hint="text",
            confidence="low",
            evidence_ids=evidence_ids,
            confidence_reason=(
                replay_ids["confidence_reason"]
                or normalized.confidence_reason
                or "structured_unavailable_or_incomplete_with_search_materials"
            ),
            extraction_ids=replay_ids["extraction_ids"],
            verification_ids=replay_ids["verification_ids"],
            fallback_text=(
                "I found related external materials, but I couldn't reliably verify "
                "them into a structured fact value yet."
            ),
        )

    def get_fx_window_samples(
        self,
        *,
        base: str,
        quote: str,
        window_minutes: int,
        now_iso: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        now_iso = now_iso or utc_now_iso()
        return self._fx_timeseries_store.list_window(
            base=base,
            quote=quote,
            window_minutes=window_minutes,
            now_iso=now_iso,
        )

    async def compat_resolve_exchange_rate_window_samples(
        self,
        *,
        query: str,
        window_minutes: int,
        context: Dict[str, Any],
        require_historical_endpoint: bool = False,
    ) -> list[Dict[str, Any]]:
        """COMPAT ONLY — DO NOT USE IN MAIN PATH."""
        base, quote = ConfiguredApiProvider._parse_fx_pair(query)
        now_iso = str(context.get("now_iso") or utc_now_iso())
        providers = self._provider_store.list_enabled_for_kind("fx")
        has_series_provider = False
        for provider in providers:
            config = provider.get("config") if isinstance(provider.get("config"), dict) else {}
            if str(config.get("series_endpoint_url") or "").strip():
                has_series_provider = True
            try:
                series = await self._configured_provider.compat_resolve_exchange_rate_series(
                    query=query,
                    window_minutes=window_minutes,
                    context={**context, "now_iso": now_iso},
                    provider=provider,
                    strict_series_endpoint=require_historical_endpoint,
                )
                if series:
                    for point in series:
                        try:
                            self._fx_timeseries_store.add_sample(
                                pair=f"{base}{quote}",
                                base=base,
                                quote=quote,
                                rate=float(point.get("rate")),
                                as_of=str(point.get("as_of") or now_iso),
                                source_name=str(point.get("source") or provider.get("name") or provider.get("provider_id") or ""),
                            )
                        except Exception:
                            continue
            except Exception:
                continue
        if require_historical_endpoint and not has_series_provider:
            return []
        return self._fx_timeseries_store.list_window(
            base=base,
            quote=quote,
            window_minutes=window_minutes,
            now_iso=now_iso,
        )

    def _persist_fx_sample(self, result: LegacyFactResult) -> None:
        if result.kind != "fx":
            return
        data = result.data
        if not isinstance(data, FxData) or data.rate is None:
            return
        as_of = result.as_of or utc_now_iso()
        source_name = ""
        if result.sources:
            source_name = str((result.sources[0].name or "")).strip()
        try:
            self._fx_timeseries_store.add_sample(
                pair=str(data.pair or f"{data.base}{data.quote}"),
                base=str(data.base),
                quote=str(data.quote),
                rate=float(data.rate),
                as_of=str(as_of),
                source_name=source_name,
            )
        except Exception:
            # Sampling should never break response flow.
            pass

    @staticmethod
    def _capability_id_for_kind(kind: FactKind) -> str:
        return "exchange_rate" if str(kind) == "fx" else str(kind)

    @staticmethod
    def default_policy_for(kind: FactKind) -> SourcePolicy:
        default_sources = merge_with_catalog(kind, [])
        policy = SourcePolicy(
            prefer_structured=True,
            allow_search_fallback=True,
            max_sources=3,
            require_freshness_seconds=1800 if ExternalFactsCapability._capability_id_for_kind(kind) == "exchange_rate" else 3600,
            source_whitelist=default_sources,
            source_blacklist=["reddit.com"],
        )
        return policy

    def validate_and_normalize(
        self,
        result: LegacyFactResult,
        query: str,
        now_iso: str,
        policy: SourcePolicy,
    ) -> LegacyFactResult:
        """Normalize provider output and enforce rendering/completeness rules."""
        as_of = result.as_of or now_iso
        sources = list(result.sources or [])
        if not sources:
            sources = [SourceRef(name="unknown", type="api", retrieved_at=now_iso)]

        normalized = replace(result, as_of=as_of, sources=sources, evidence_ids=list(result.evidence_ids))
        freshness_ok = self._is_fresh(as_of, now_iso, policy.require_freshness_seconds)
        if normalized.kind == "weather":
            if not validate_weather_complete(normalized.data if isinstance(normalized.data, WeatherData) else None):
                return replace(
                    normalized,
                    status="partial" if normalized.data else "unavailable",
                    render_hint="text",
                    confidence="low",
                    confidence_reason="weather_fields_incomplete",
                    fallback_text=(
                        f"I can't fetch reliable live weather fields for {query} right now. "
                        "I can provide a general reference or retry."
                    ),
                )
            if not freshness_ok:
                return replace(
                    normalized,
                    status="partial",
                    render_hint="text",
                    confidence="low",
                    confidence_reason="weather_data_stale",
                    fallback_text=(
                        f"I found weather data for {query}, but it is not fresh enough "
                        "to present as a verified real-time value."
                    ),
                )
            return replace(normalized, status="ok", render_hint="card")

        if self._capability_id_for_kind(normalized.kind) == "exchange_rate":
            if not validate_fx_complete(normalized.data if isinstance(normalized.data, FxData) else None):
                return replace(
                    normalized,
                    status="unavailable",
                    render_hint="text",
                    confidence="low",
                    confidence_reason="fx_rate_missing",
                    fallback_text=(
                        "I can't fetch a reliable live FX quote right now. "
                        "Tell me a pair like AUD/USD and I can retry."
                    ),
                )
            fx_freshness_ok = freshness_ok or self._is_fx_reference_fresh(as_of, now_iso)
            if not fx_freshness_ok:
                return replace(
                    normalized,
                    status="partial",
                    render_hint="text",
                    confidence="low",
                    confidence_reason="fx_data_stale",
                    fallback_text=(
                        "I found an FX quote, but it's stale and I can't verify it as current."
                    ),
                )
            return replace(normalized, status="ok", render_hint="table")

        if not freshness_ok:
            return replace(
                normalized,
                status="partial",
                render_hint="text",
                confidence="low",
                confidence_reason=f"{normalized.kind}_data_stale",
                fallback_text=(
                    f"I found {normalized.kind} materials for {query}, but they are not fresh enough "
                    "to present as a verified value."
                ),
            )
        if normalized.status == "ok" and normalized.data is not None:
            return replace(
                normalized,
                status="ok",
                render_hint=normalized.render_hint or "card",
            )
        return replace(
            normalized,
            status="partial" if normalized.data else "unavailable",
            render_hint="text",
            confidence=normalized.confidence or "low",
            confidence_reason=normalized.confidence_reason or f"{normalized.kind}_structured_not_available",
            fallback_text=normalized.fallback_text
            or f"I can collect materials for {normalized.kind}, but I can't verify a structured value yet.",
        )

    def _unavailable(self, kind: FactKind, query: str, now_iso: str) -> LegacyFactResult:
        if kind == "weather":
            return LegacyFactResult(
                kind="weather",
                status="unavailable",
                data=WeatherData(location=query or "unknown"),
                as_of=now_iso,
                confidence="low",
                sources=[SourceRef(name="none", type="api", retrieved_at=now_iso)],
                render_hint="text",
                fallback_text=(
                    "I can't fetch reliable real-time weather data right now. "
                    "I can retry shortly."
                ),
                confidence_reason="provider_unavailable",
            )
        if self._capability_id_for_kind(kind) == "exchange_rate":
            return LegacyFactResult(
                kind="fx",
                status="unavailable",
                data=FxData(base="AUD", quote="USD", pair="AUDUSD", rate=None),
                as_of=now_iso,
                confidence="low",
                sources=[SourceRef(name="none", type="api", retrieved_at=now_iso)],
                render_hint="text",
                fallback_text=(
                    "I can't fetch a reliable live FX quote right now. "
                    "Tell me a pair like AUD/USD and I can retry."
                ),
                confidence_reason="provider_unavailable",
            )
        return LegacyFactResult(
            kind=kind,
            status="unavailable",
            data=GenericFactData(query=query),
            as_of=now_iso,
            confidence="low",
            sources=[SourceRef(name="none", type="api", retrieved_at=now_iso)],
            render_hint="text",
            fallback_text=(
                f"I can search and verify {kind} materials, but no structured provider is configured yet."
            ),
            confidence_reason="provider_unavailable",
        )

    @staticmethod
    def _ensure_policy_sources(kind: FactKind, policy: SourcePolicy) -> SourcePolicy:
        merged_whitelist = merge_with_catalog(kind, policy.source_whitelist)
        max_sources = max(3, int(policy.max_sources or 3))
        return replace(
            policy,
            source_whitelist=merged_whitelist,
            max_sources=max_sources,
        )

    @staticmethod
    def _is_fresh(as_of: Optional[str], now_iso: str, max_age_seconds: Optional[int]) -> bool:
        if not as_of or max_age_seconds is None:
            return True
        try:
            now = ExternalFactsCapability._parse_datetime(now_iso)
            then = ExternalFactsCapability._parse_datetime(as_of)
            age = (now - then).total_seconds()
            return age <= max_age_seconds
        except Exception:
            return True

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        value = value.strip()
        if "T" not in value and len(value) == 10:
            value = f"{value}T00:00:00+00:00"
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _is_fx_reference_fresh(as_of: Optional[str], now_iso: str) -> bool:
        """Allow daily FX references to remain usable across weekends/market close."""
        if not as_of:
            return False
        try:
            now = ExternalFactsCapability._parse_datetime(now_iso)
            then = ExternalFactsCapability._parse_datetime(as_of)
            return (now - then).total_seconds() <= 72 * 3600
        except Exception:
            return False

    @staticmethod
    def _apply_source_policy(items, policy: SourcePolicy):
        if not items:
            return []
        filtered = []
        for item in items:
            name = (item.source.name or "").lower()
            if policy.source_blacklist and any(name.endswith(v.lower()) for v in policy.source_blacklist):
                continue
            if policy.source_whitelist and not any(name.endswith(v.lower()) for v in policy.source_whitelist):
                continue
            filtered.append(item)
            if len(filtered) >= policy.max_sources:
                break
        return filtered

    def _build_replay_chain(
        self,
        evidence_items: list[EvidenceItem],
        kind: FactKind,
        policy: SourcePolicy,
    ) -> Dict[str, Any]:
        evidence_ids: list[str] = []
        extraction_ids: list[str] = []
        verification_ids: list[str] = []
        confidence_reasons: list[str] = []

        extractor = self._extractors.get(kind)
        verifier = self._verifiers.get(kind)

        for item in evidence_items:
            evidence_id = self._evidence_store.save(item)
            evidence_ids.append(evidence_id)
            if extractor is None or verifier is None:
                continue
            extraction = extractor.extract(item)
            extraction_id = self._replay_store.save_extraction(extraction)
            extraction_ids.append(extraction_id)

            verification = verifier.verify(item, extraction, policy)
            verification_id = self._replay_store.save_verification(verification)
            verification_ids.append(verification_id)
            if verification.confidence_reason:
                confidence_reasons.append(verification.confidence_reason)

        return {
            "evidence_ids": evidence_ids,
            "extraction_ids": extraction_ids,
            "verification_ids": verification_ids,
            "confidence_reason": ";".join(confidence_reasons[:3]),
        }

    async def _resolve_custom_provider_result(
        self,
        *,
        kind: FactKind,
        query: str,
        context: Dict[str, Any],
    ) -> Optional[LegacyFactResult]:
        # Prefer connector bindings first so runtime follows explicit capability/item bindings.
        binding_result = await self._resolve_binding_first(kind=kind, query=query, context=context)
        if binding_result is not None:
            return binding_result

        providers = self._provider_store.list_enabled_for_kind(kind)
        if not providers:
            return None
        for provider in providers:
            try:
                result = await self._configured_provider.resolve(
                    kind=kind,
                    query=query,
                    context=context,
                    provider=provider,
                )
                if result is not None and result.status in {"ok", "partial", "unavailable"}:
                    return result
            except Exception:
                continue
        return None

    async def _resolve_binding_first(
        self,
        *,
        kind: FactKind,
        query: str,
        context: Dict[str, Any],
    ) -> Optional[LegacyFactResult]:
        if kind != "fx":
            return None
        base, quote = ConfiguredApiProvider._parse_fx_pair(query)
        bound = await self._configured_provider.resolve_binding_item(
            capability_id="exchange_rate",
            item_id="spot",
            params={
                "base": base,
                "quote": quote,
                "query": query,
                "query_raw": query,
                "now_iso": str(context.get("now_iso") or utc_now_iso()),
            },
            context=context,
        )
        return self._legacy_result_from_binding(bound=bound, kind=kind, query=query)

    @staticmethod
    def _legacy_result_from_binding(
        *,
        bound: Optional[FactResult],
        kind: FactKind,
        query: str,
    ) -> Optional[LegacyFactResult]:
        if not bound:
            return None
        if kind == "fx" and bound.kind == "point":
            data = bound.data if isinstance(bound.data, dict) else {}
            value = ConfiguredApiProvider._to_float(data.get("v"))
            as_of = str(data.get("t") or (bound.metadata or {}).get("as_of") or utc_now_iso())
            base, quote = ConfiguredApiProvider._parse_fx_pair(query)
            if value is None:
                return None
            source_name = str((bound.metadata or {}).get("source") or bound.provider_id or "connector")
            return LegacyFactResult(
                kind="fx",
                status="ok",
                data=FxData(base=base, quote=quote, pair=f"{base}{quote}", rate=value),
                as_of=as_of,
                confidence="high",
                sources=[SourceRef(name=source_name, type="api")],
                render_hint="table",
                fallback_text=f"{base}/{quote} is {value} as of {as_of}.",
            )
        return None
