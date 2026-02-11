"""Execution engine for validated external facts intent plans."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from .fact_bindings_store import FactBindingsStore
from .intent_plan import IntentPlan, validate_intent_plan
from .provider_store import ExternalFactsProviderStore
from .providers.configured_api import ConfiguredApiProvider
from .registry import get_capability
from .types import FactResult, utc_now_iso


CAPABILITY_KIND_MAP: dict[str, str] = {
    "exchange_rate": "fx",
    "market_company_research": "company_research",
}


class ExternalFactsPlanExecutor:
    """Execute capability/item intent plans against configured providers."""

    def __init__(
        self,
        provider_store: Optional[ExternalFactsProviderStore] = None,
        configured_provider: Optional[ConfiguredApiProvider] = None,
    ) -> None:
        self._provider_store = provider_store or ExternalFactsProviderStore()
        self._configured_provider = configured_provider or ConfiguredApiProvider()
        self._bindings_store = FactBindingsStore()

    async def execute_plan(
        self,
        plan: IntentPlan,
        *,
        context: Dict[str, Any],
        strict: bool = True,
    ) -> FactResult:
        errors = validate_intent_plan(plan)
        if errors:
            return self._unavailable(
                plan=plan,
                reason="invalid_plan",
                details="; ".join(errors),
                context=context,
            )

        kind = CAPABILITY_KIND_MAP.get(plan.capability_id)
        if not kind:
            return self._unavailable(
                plan=plan,
                reason="unsupported_capability",
                details=f"No kind mapping for capability '{plan.capability_id}'",
                context=context,
            )

        params = self._normalize_params(plan, context)
        binding = self._bindings_store.get(plan.capability_id, plan.item_id)
        if binding:
            bound_result = await self._configured_provider.resolve_binding_item(
                capability_id=plan.capability_id,
                item_id=plan.item_id,
                params=params,
                context=context,
            )
            if bound_result:
                return FactResult(
                    kind=bound_result.kind,
                    capability_id=bound_result.capability_id,
                    item_id=bound_result.item_id,
                    provider_id=bound_result.provider_id,
                    data=bound_result.data,
                    metadata={
                        **(bound_result.metadata or {}),
                        "entity_kind": kind,
                        "bound_via_connector": True,
                        "plan": {
                            "intent": plan.intent,
                            "capability_id": plan.capability_id,
                            "item_id": plan.item_id,
                            "params": params,
                        },
                    },
                    unavailable=bound_result.unavailable,
                    unavailable_reason=bound_result.unavailable_reason,
                )

        provider = self._select_provider(kind=kind, capability_id=plan.capability_id, item_id=plan.item_id, strict=strict)
        if provider is None:
            return self._unavailable(
                plan=plan,
                reason="provider_missing_item",
                details=f"No provider supports {plan.capability_id}.{plan.item_id}",
                context=context,
            )

        platform_result = await self._configured_provider.resolve_item(
            capability_id=plan.capability_id,
            item_id=plan.item_id,
            params=params,
            context=context,
            provider=provider,
            strict=strict,
        )
        if not platform_result:
            return self._unavailable(
                plan=plan,
                reason="runtime_unavailable",
                details="Provider returned no structured result",
                context=context,
                provider=provider,
            )
        return FactResult(
            kind=platform_result.kind,
            capability_id=platform_result.capability_id,
            item_id=platform_result.item_id,
            provider_id=platform_result.provider_id,
            data=platform_result.data,
            metadata={
                **(platform_result.metadata or {}),
                "entity_kind": kind,
                "plan": {
                    "intent": plan.intent,
                    "capability_id": plan.capability_id,
                    "item_id": plan.item_id,
                    "params": params,
                },
            },
            unavailable=platform_result.unavailable,
            unavailable_reason=platform_result.unavailable_reason,
        )

    def _select_provider(
        self,
        *,
        kind: str,
        capability_id: str,
        item_id: str,
        strict: bool,
    ) -> Optional[Dict[str, Any]]:
        providers = self._provider_store.list_enabled_for_kind(kind)  # sorted by priority ASC
        for provider in providers:
            if strict and provider.get("endpoint_map_schema_valid") is not True:
                continue
            supported_items = provider.get("supported_items") if isinstance(provider.get("supported_items"), dict) else {}
            items = supported_items.get(capability_id)
            if isinstance(items, list) and item_id in items:
                return provider
        return None

    @staticmethod
    def _normalize_params(plan: IntentPlan, context: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(plan.params)
        now_iso = str(context.get("now_iso") or utc_now_iso())
        params.setdefault("now_iso", now_iso)
        params.setdefault("now_iso_z", ExternalFactsPlanExecutor._iso_to_utc_z(str(params.get("now_iso") or now_iso)))
        if plan.item_id == "series":
            window = int(params.get("window_minutes") or 5)
            window = max(1, min(1440, window))
            params["window_minutes"] = window
            to_iso = str(params.get("to_iso") or now_iso)
            params["to_iso"] = to_iso
            params["to_iso_z"] = ExternalFactsPlanExecutor._iso_to_utc_z(to_iso)
            if not params.get("from_iso"):
                try:
                    dt_to = datetime.fromisoformat(to_iso.replace("Z", "+00:00"))
                except Exception:
                    dt_to = datetime.now(timezone.utc)
                params["from_iso"] = (dt_to - timedelta(minutes=window)).isoformat()
            params["from_iso_z"] = ExternalFactsPlanExecutor._iso_to_utc_z(str(params.get("from_iso") or ""))
        return params

    @staticmethod
    def _iso_to_utc_z(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return text
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return str(value)

    def _unavailable(
        self,
        *,
        plan: IntentPlan,
        reason: str,
        details: str,
        context: Dict[str, Any],
        provider: Optional[Dict[str, Any]] = None,
    ) -> FactResult:
        source_name = str((provider or {}).get("name") or "none")
        capability = get_capability(plan.capability_id)
        item = capability.item(plan.item_id) if capability else None
        result_kind = item.output_kind if item else "point"
        base_data: Dict[str, Any]
        if result_kind == "series":
            base_data = {"series": []}
        elif result_kind == "table":
            base_data = {"columns": [], "rows": []}
        else:
            base_data = {"t": str(context.get("now_iso") or utc_now_iso()), "v": None}
        return FactResult(
            kind=result_kind,  # type: ignore[arg-type]
            capability_id=plan.capability_id,
            item_id=plan.item_id,
            provider_id=str((provider or {}).get("provider_id") or "none"),
            data=base_data,
            metadata={
                "as_of": str(context.get("now_iso") or utc_now_iso()),
                "source": source_name,
                "plan": {
                    "intent": plan.intent,
                    "capability_id": plan.capability_id,
                    "item_id": plan.item_id,
                    "params": plan.params,
                },
                "details": details,
            },
            unavailable=True,
            unavailable_reason=reason,
        )
