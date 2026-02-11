"""Execute user-configured external fact provider (URL + API key)."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote
from urllib.request import Request, urlopen

from octopusos.connectoros.core import ConnectorStore

from ..fact_bindings_store import FactBindingsStore
from ..mapping_store import ExternalFactsMappingStore
from ..provider_store import ExternalFactsProviderStore
from ..types import FactKind, FactResult, LegacyFactResult, FxData, GenericFactData, SourceRef


class ConfiguredApiProvider:
    """Lightweight adapter for custom providers configured in WebUI."""

    def __init__(self) -> None:
        self._mapping_store = ExternalFactsMappingStore()
        self._provider_store = ExternalFactsProviderStore()
        self._bindings_store = FactBindingsStore()
        self._connector_store = ConnectorStore()

    async def resolve_binding_item(
        self,
        *,
        capability_id: str,
        item_id: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> FactResult | None:
        binding = self._bindings_store.get(capability_id, item_id)
        if not binding:
            return None
        connector_id = str(binding.get("connector_id") or "").strip()
        endpoint_id = str(binding.get("endpoint_id") or "").strip()
        if not connector_id or not endpoint_id:
            return None
        connector = self._connector_store.get_connector(connector_id, mask_secret=False)
        endpoint = self._connector_store.get_endpoint(connector_id, endpoint_id)
        if not connector or not endpoint:
            return None

        endpoint_key = str(endpoint.get("endpoint_key") or f"{capability_id}:{item_id}")
        profile_version_id = str(binding.get("profile_version_id") or "").strip()
        version = self._connector_store.get_version(profile_version_id) if profile_version_id else None
        if not version:
            bundle = self._connector_store.list_profiles(connector_id, endpoint_key, limit=50)
            active_id = str(bundle.get("active_version_id") or "")
            version = self._connector_store.get_version(active_id) if active_id else None
        profile_json = (version or {}).get("profile") if isinstance((version or {}).get("profile"), dict) else {}

        endpoint_url = str(profile_json.get("url") or "").strip()
        if not endpoint_url:
            base_url = str(connector.get("base_url") or "").strip().rstrip("/")
            path = str(endpoint.get("path") or "").strip()
            endpoint_url = path if path.startswith("http") else f"{base_url}/{path.lstrip('/')}"
        if not endpoint_url:
            return None
        method = str(profile_json.get("method") or endpoint.get("method") or "GET").upper()

        headers: Dict[str, str] = {"Accept": "application/json"}
        api_key = str(connector.get("api_key") or "").strip()
        if api_key:
            auth_header = str(connector.get("auth_header") or "Authorization").strip() or "Authorization"
            headers[auth_header] = api_key
        profile_headers = profile_json.get("headers")
        if isinstance(profile_headers, dict):
            for hk, hv in profile_headers.items():
                headers[str(hk)] = self._render_template(str(hv), params)

        profile_query = profile_json.get("query")
        if isinstance(profile_query, dict) and profile_query:
            query_string = "&".join(
                f"{quote(str(k))}={quote(self._render_template(str(v), params))}"
                for k, v in profile_query.items()
            )
            endpoint_url = endpoint_url + ("&" if "?" in endpoint_url else "?") + query_string
        endpoint_url = self._render_template(endpoint_url, params)
        payload = await asyncio.to_thread(self._request_json, endpoint_url, method, headers)

        response_block = profile_json.get("response") if isinstance(profile_json.get("response"), dict) else {}
        if not response_block:
            endpoint_key = str(endpoint.get("endpoint_key") or f"{capability_id}:{item_id}")
            response_block = self._default_response_block(
                capability_id=capability_id,
                item_id=item_id,
                endpoint_key=endpoint_key,
            )
        rendered_response_block = self._render_response_block(response_block, params)
        return self._build_fact_result_from_payload(
            payload=payload,
            response_block=rendered_response_block,
            capability_id=capability_id,
            item_id=item_id,
            provider_id=f"connector:{connector_id}:{endpoint_id}",
            source_name=str(connector.get("name") or connector_id),
            context=context,
        )

    @staticmethod
    def _is_exchange_rate_kind(kind: FactKind) -> bool:
        return str(kind) in {"fx", "exchange_rate"}

    async def resolve_item(
        self,
        *,
        capability_id: str,
        item_id: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
        provider: Dict[str, Any],
        strict: bool = False,
    ) -> FactResult | None:
        endpoint_key = f"{capability_id}:{item_id}"
        active_version_id: Optional[str] = None
        endpoint_map = provider.get("endpoint_map")
        if not isinstance(endpoint_map, dict) or not endpoint_map:
            endpoint_map = {}
        item_map: Dict[str, Any] = {}

        # Prefer versioned active mapping (runtime contract).
        active_versions = provider.get("active_mapping_versions") if isinstance(provider.get("active_mapping_versions"), dict) else {}
        if endpoint_key in active_versions:
            active_version_id = str(active_versions.get(endpoint_key) or "")
            if active_version_id:
                version_row = self._mapping_store.get_version(active_version_id)
                if version_row and isinstance(version_row.get("mapping_json"), dict):
                    item_map = dict(version_row.get("mapping_json") or {})

        if not item_map:
            capability_block = endpoint_map.get(capability_id) if isinstance(endpoint_map.get(capability_id), dict) else {}
            items_block = capability_block.get("items") if isinstance(capability_block.get("items"), dict) else {}
            item_map = items_block.get(item_id) if isinstance(items_block.get(item_id), dict) else {}
        if not item_map:
            if strict:
                return None
            return None

        endpoint = str(item_map.get("url") or "").strip()
        if not endpoint:
            return None
        method = str(item_map.get("method") or "GET").upper()
        headers: Dict[str, str] = {"Accept": "application/json"}
        # provider credentials
        api_key = str(provider.get("api_key") or "").strip()
        if api_key:
            api_key_header = str(provider.get("api_key_header") or "Authorization").strip() or "Authorization"
            headers[api_key_header] = api_key
        # explicit mapping headers
        mapped_headers = item_map.get("headers")
        if isinstance(mapped_headers, dict):
            for hk, hv in mapped_headers.items():
                headers[str(hk)] = self._render_template(str(hv), params)
        # query mapping
        query = item_map.get("query")
        if isinstance(query, dict) and query:
            query_string = "&".join(
                f"{quote(str(k))}={quote(self._render_template(str(v), params))}"
                for k, v in query.items()
            )
            endpoint = endpoint + ("&" if "?" in endpoint else "?") + query_string
        endpoint = self._render_template(endpoint, params)

        payload = await asyncio.to_thread(self._request_json, endpoint, method, headers)
        response_block = item_map.get("response") if isinstance(item_map.get("response"), dict) else {}
        rendered_response_block = self._render_response_block(response_block, params)
        source_name = str(provider.get("name") or provider.get("provider_id") or "custom-provider")
        result = self._build_fact_result_from_payload(
            payload=payload,
            response_block=rendered_response_block,
            capability_id=capability_id,
            item_id=item_id,
            provider_id=str(provider.get("provider_id") or source_name),
            source_name=source_name,
            context=context,
        )
        if not result:
            return None
        if result.kind == "series":
            points = result.data.get("series") if isinstance(result.data, dict) else []
            if active_version_id and not points:
                self._handle_active_mapping_failure(
                    provider=provider,
                    endpoint_key=endpoint_key,
                    failed_version_id=active_version_id,
                )
            return result
        if result.kind == "table":
            rows = result.data.get("rows") if isinstance(result.data, dict) else []
            if active_version_id and not rows:
                self._handle_active_mapping_failure(
                    provider=provider,
                    endpoint_key=endpoint_key,
                    failed_version_id=active_version_id,
                )
            return result
        value = result.data.get("v") if isinstance(result.data, dict) else None
        if active_version_id and value is None:
            self._handle_active_mapping_failure(
                provider=provider,
                endpoint_key=endpoint_key,
                failed_version_id=active_version_id,
            )
        return result

    def _build_fact_result_from_payload(
        self,
        *,
        payload: Dict[str, Any],
        response_block: Dict[str, Any],
        capability_id: str,
        item_id: str,
        provider_id: str,
        source_name: str,
        context: Dict[str, Any],
    ) -> FactResult | None:
        output_kind = str(response_block.get("kind") or "").strip().lower()
        as_of = self._normalize_timestamp(self._extract(payload, str(response_block.get("time_path") or "")))
        if not as_of:
            as_of = str(context.get("now_iso") or datetime.now(timezone.utc).isoformat())
        if output_kind == "series":
            points_path = str(response_block.get("points_path") or "").strip()
            raw_points = self._extract(payload, points_path) if points_path else payload
            if isinstance(raw_points, dict):
                raw_points = [{**v, "key": k} for k, v in raw_points.items() if isinstance(v, dict)]
            points = []
            quote_hint = self._extract_quote_from_value_path(str(response_block.get("value_path") or ""))
            if isinstance(raw_points, list):
                for point in raw_points:
                    if not isinstance(point, dict):
                        continue
                    t_raw = self._extract(point, str(response_block.get("time_path") or "timestamp")) or point.get("key")
                    v_raw = self._extract(point, str(response_block.get("value_path") or "value"))
                    if t_raw is None:
                        t_raw = self._guess_timestamp(point) or self._guess_timestamp(payload)
                    if v_raw is None:
                        v_raw = self._guess_fx_rate(point, quote_hint) or self._guess_fx_rate(payload, quote_hint)
                    t = self._normalize_timestamp(t_raw) or str(t_raw or "")
                    v = self._to_float(v_raw)
                    if not t or v is None:
                        continue
                    points.append({"t": t, "v": v})
            return FactResult(
                kind="series",
                capability_id=capability_id,
                item_id=item_id,
                provider_id=provider_id,
                data={"series": points},
                metadata={"as_of": as_of, "source": source_name},
            )
        if output_kind == "table":
            rows_path = str(response_block.get("rows_path") or "").strip()
            rows = self._extract(payload, rows_path) if rows_path else []
            if not isinstance(rows, list):
                rows = []
            return FactResult(
                kind="table",
                capability_id=capability_id,
                item_id=item_id,
                provider_id=provider_id,
                data={"rows": rows},
                metadata={"as_of": as_of, "source": source_name},
            )
        value_path = str(response_block.get("value_path") or "value").strip()
        value = self._to_float(self._extract(payload, value_path))
        return FactResult(
            kind="point",
            capability_id=capability_id,
            item_id=item_id,
            provider_id=provider_id,
            data={"t": as_of, "v": value},
            metadata={"as_of": as_of, "source": source_name},
        )

    def _handle_active_mapping_failure(self, *, provider: Dict[str, Any], endpoint_key: str, failed_version_id: str) -> None:
        provider_id = str(provider.get("provider_id") or "")
        if not provider_id:
            return
        rollback_version_id = self._mapping_store.record_failure_and_maybe_rollback(
            provider_id=provider_id,
            endpoint_key=endpoint_key,
            failed_version_id=failed_version_id,
            threshold=3,
        )
        if rollback_version_id:
            try:
                self._provider_store.set_active_mapping_version(provider_id, endpoint_key, rollback_version_id)
            except Exception:
                return

    async def resolve(
        self,
        *,
        kind: FactKind,
        query: str,
        context: Dict[str, Any],
        provider: Dict[str, Any],
    ) -> Optional[LegacyFactResult]:
        if self._is_exchange_rate_kind(kind):
            # Platform path first: capability/item mapping.
            base, quote_ccy = self._parse_fx_pair(query)
            item_result = await self.resolve_item(
                capability_id="exchange_rate",
                item_id="spot",
                params={
                    "base": base,
                    "quote": quote_ccy,
                    "query": query,
                    "query_raw": query,
                    "now_iso": str(context.get("now_iso") or datetime.now(timezone.utc).isoformat()),
                },
                context=context,
                provider=provider,
                strict=False,
            )
            if item_result and item_result.kind == "point":
                point_data = item_result.data if isinstance(item_result.data, dict) else {}
                point_value = self._to_float(point_data.get("v"))
                as_of_value = point_data.get("t")
                source_name = str(
                    (item_result.metadata or {}).get("source")
                    if isinstance(item_result.metadata, dict)
                    else provider.get("name") or provider.get("provider_id") or "custom-provider"
                )
                if point_value is not None:
                    return LegacyFactResult(
                        kind="fx",
                        status="ok",
                        data=FxData(base=base, quote=quote_ccy, pair=f"{base}{quote_ccy}", rate=point_value),
                        as_of=str(as_of_value) if as_of_value else str(context.get("now_iso") or ""),
                        confidence="high",
                        sources=[SourceRef(name=source_name, type="api", url=str(provider.get("endpoint_url") or ""))],
                        render_hint="table",
                        fallback_text=f"{base}/{quote_ccy} is {point_value} as of {as_of_value}.",
                    )

        endpoint = self._select_endpoint_for_task(
            provider=provider,
            task="snapshot",
            kind=kind,
            query=query,
        )
        if not endpoint:
            return None
        config = provider.get("config") or {}
        if not isinstance(config, dict):
            config = {}

        final_url = self._build_url(endpoint, kind=kind, query=query, config=config)
        method = str(config.get("method") or "GET").upper()
        headers: Dict[str, str] = {"Accept": "application/json"}

        api_key = str(provider.get("api_key") or "").strip()
        if api_key:
            api_key_header = str(provider.get("api_key_header") or "Authorization").strip() or "Authorization"
            api_key_prefix = str(config.get("api_key_prefix") or "").strip()
            headers[api_key_header] = f"{api_key_prefix}{api_key}" if api_key_prefix else api_key

        extra_headers = config.get("headers") or {}
        if isinstance(extra_headers, dict):
            for k, v in extra_headers.items():
                key = str(k).strip()
                if key:
                    headers[key] = str(v)

        payload = await asyncio.to_thread(self._request_json, final_url, method, headers)
        return self._to_fact_result(kind=kind, query=query, provider=provider, payload=payload, context=context)

    async def compat_resolve_exchange_rate_series(
        self,
        *,
        query: str,
        window_minutes: int,
        context: Dict[str, Any],
        provider: Dict[str, Any],
        strict_series_endpoint: bool = False,
    ) -> list[Dict[str, Any]]:
        base, quote_ccy = self._parse_fx_pair(query)
        item_result = await self.resolve_item(
            capability_id="exchange_rate",
            item_id="series",
            params={
                "base": base,
                "quote": quote_ccy,
                "query": query,
                "query_raw": query,
                "window_minutes": max(1, int(window_minutes)),
                "from_iso": self._shift_iso_minutes(str(context.get("now_iso") or datetime.now(timezone.utc).isoformat()), -max(1, int(window_minutes))),
                "to_iso": str(context.get("now_iso") or datetime.now(timezone.utc).isoformat()),
                "now_iso": str(context.get("now_iso") or datetime.now(timezone.utc).isoformat()),
                "from_iso_z": self._iso_to_utc_z(self._shift_iso_minutes(str(context.get("now_iso") or datetime.now(timezone.utc).isoformat()), -max(1, int(window_minutes)))),
                "to_iso_z": self._iso_to_utc_z(str(context.get("now_iso") or datetime.now(timezone.utc).isoformat())),
                "now_iso_z": self._iso_to_utc_z(str(context.get("now_iso") or datetime.now(timezone.utc).isoformat())),
            },
            context=context,
            provider=provider,
            strict=strict_series_endpoint,
        )
        if item_result and item_result.kind == "series":
            data = item_result.data if isinstance(item_result.data, dict) else {}
            points = data.get("series") if isinstance(data.get("series"), list) else []
            source_name = str(
                (item_result.metadata or {}).get("source")
                if isinstance(item_result.metadata, dict)
                else provider.get("name") or provider.get("provider_id") or "custom-provider"
            )
            converted = []
            for point in points:
                if not isinstance(point, dict):
                    continue
                t = self._normalize_timestamp(point.get("t")) or str(point.get("t") or "")
                v = self._to_float(point.get("v"))
                if not t or v is None:
                    continue
                converted.append({"as_of": t, "rate": v, "source": source_name})
            if converted:
                return converted

        config = provider.get("config") or {}
        if not isinstance(config, dict):
            config = {}
        endpoint = self._select_endpoint_for_task(
            provider=provider,
            task="fx_window_analysis",
            kind="fx",
            query=query,
        )
        if not endpoint and not strict_series_endpoint:
            endpoint = str(provider.get("endpoint_url") or "").strip()
        if not endpoint:
            return []
        if strict_series_endpoint and self._is_snapshot_only_endpoint(endpoint):
            return []
        now_iso = str(context.get("now_iso") or datetime.now(timezone.utc).isoformat())
        from_iso = self._shift_iso_minutes(now_iso, -max(1, int(window_minutes)))
        from_iso_z = self._iso_to_utc_z(from_iso)
        to_iso_z = self._iso_to_utc_z(now_iso)
        base, quote_ccy = self._parse_fx_pair(query)
        final_url = endpoint
        substitutions = {
            "{query}": quote(query),
            "{query_raw}": query,
            "{kind}": "fx",
            "{base}": base,
            "{quote}": quote_ccy,
            "{window_minutes}": str(window_minutes),
            "{from_iso}": from_iso,
            "{to_iso}": now_iso,
            "{from_iso_z}": from_iso_z,
            "{to_iso_z}": to_iso_z,
            "{now_iso_z}": to_iso_z,
            "{from_unix}": str(self._iso_to_unix(from_iso)),
            "{to_unix}": str(self._iso_to_unix(now_iso)),
        }
        for key, value in substitutions.items():
            final_url = final_url.replace(key, str(value))
        method = str(config.get("method") or "GET").upper()
        headers: Dict[str, str] = {"Accept": "application/json"}
        api_key = str(provider.get("api_key") or "").strip()
        if api_key:
            api_key_header = str(provider.get("api_key_header") or "Authorization").strip() or "Authorization"
            api_key_prefix = str(config.get("api_key_prefix") or "").strip()
            headers[api_key_header] = f"{api_key_prefix}{api_key}" if api_key_prefix else api_key
        payload = await asyncio.to_thread(self._request_json, final_url, method, headers)
        points_path = str(config.get("series_points_path") or "data").strip()
        time_path = str(config.get("series_time_path") or "timestamp").strip()
        rate_path = str(config.get("series_rate_path") or f"{quote_ccy}.value").strip()
        source_name = str(provider.get("name") or provider.get("provider_id") or "custom-provider")
        raw_points = self._extract(payload, points_path) if points_path else payload
        if isinstance(raw_points, dict):
            if all(isinstance(v, dict) for v in raw_points.values()):
                raw_points = [{**v, "key": k} for k, v in raw_points.items() if isinstance(v, dict)]
            else:
                raw_points = [raw_points]
        if not isinstance(raw_points, list):
            return []
        series: list[Dict[str, Any]] = []
        for item in raw_points:
            if not isinstance(item, dict):
                continue
            as_of_raw = self._extract(item, time_path) if time_path else None
            if as_of_raw is None:
                as_of_raw = self._extract(payload, str(config.get("as_of_path") or ""))
            rate_raw = self._extract(item, rate_path) if rate_path else None
            if rate_raw is None:
                rate_raw = self._guess_fx_rate(item, quote_ccy) or self._guess_fx_rate(payload, quote_ccy)
            rate = self._to_float(rate_raw)
            as_of = self._normalize_timestamp(as_of_raw)
            if rate is None or not as_of:
                continue
            series.append({"as_of": as_of, "rate": rate, "source": source_name})
        return series

    def _select_endpoint_for_task(
        self,
        *,
        provider: Dict[str, Any],
        task: str,
        kind: FactKind | str,
        query: str,
    ) -> str:
        config = provider.get("config") if isinstance(provider.get("config"), dict) else {}
        endpoint_map = provider.get("endpoint_map") if isinstance(provider.get("endpoint_map"), dict) else {}
        if not endpoint_map:
            endpoint_map = config.get("endpoint_map") if isinstance(config.get("endpoint_map"), dict) else {}
        if isinstance(endpoint_map, dict) and endpoint_map:
            op = self._select_operation_via_llm(
                provider_name=str(provider.get("name") or provider.get("provider_id") or "provider"),
                task=task,
                kind=str(kind),
                query=query,
                operations=list(endpoint_map.keys()),
                capability_text=str(config.get("capability_text") or ""),
            )
            if op in endpoint_map and str(endpoint_map.get(op) or "").strip():
                return str(endpoint_map.get(op) or "").strip()
            # deterministic fallback for reliability
            fallback_order = (
                ["range_historical", "historical", "latest"]
                if task == "fx_window_analysis"
                else ["latest", "convert", "historical"]
            )
            for key in fallback_order:
                value = str(endpoint_map.get(key) or "").strip()
                if value:
                    return value

        # Backward-compatible fields
        if task == "fx_window_analysis":
            return str(config.get("series_endpoint_url") or "").strip()
        return str(provider.get("endpoint_url") or "").strip()

    def _select_operation_via_llm(
        self,
        *,
        provider_name: str,
        task: str,
        kind: str,
        query: str,
        operations: list[str],
        capability_text: str,
    ) -> str:
        try:
            from octopusos.core.chat.adapters import get_adapter

            adapter = get_adapter("ollama", "qwen2.5:14b")
            prompt = (
                "You route provider operations for external facts.\n"
                "Choose exactly one operation from provided operations.\n"
                "Return STRICT JSON only: {\"operation\":\"...\"}.\n"
                f"Provider: {provider_name}\n"
                f"Task: {task}\n"
                f"Kind: {kind}\n"
                f"Query: {query}\n"
                f"Operations: {json.dumps(operations, ensure_ascii=False)}\n"
                f"Provider capabilities: {capability_text}"
            )
            response, _ = adapter.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=80,
                stream=False,
            )
            content = str(response or "").strip()
            json_match = re.search(r"\{[\s\S]*\}", content)
            payload = json.loads(json_match.group(0) if json_match else content)
            operation = str(payload.get("operation") or "").strip()
            if operation in operations:
                return operation
        except Exception:
            pass
        return ""

    @staticmethod
    def _is_snapshot_only_endpoint(endpoint: str) -> bool:
        value = (endpoint or "").lower()
        if not value:
            return True
        has_window_tokens = any(token in value for token in ("{from_iso}", "{to_iso}", "start_date", "end_date", "range", "historical"))
        if has_window_tokens:
            return False
        return any(token in value for token in ("/latest", "/live", "latest?"))

    @staticmethod
    def _render_template(template: str, params: Dict[str, Any]) -> str:
        text = template
        for key, value in params.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text

    def _render_response_block(self, response_block: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(response_block, dict):
            return {}
        rendered = dict(response_block)
        for key in ("time_path", "value_path", "points_path", "rows_path", "summary_path"):
            value = rendered.get(key)
            if isinstance(value, str):
                rendered[key] = self._render_template(value, params)
        return rendered

    @staticmethod
    def _default_response_block(
        *,
        capability_id: str,
        item_id: str,
        endpoint_key: str,
    ) -> Dict[str, Any]:
        key = str(endpoint_key or "").lower()
        if capability_id == "exchange_rate" and item_id == "series":
            return {
                "kind": "series",
                "points_path": "data",
                "time_path": "key",
                "value_path": "{quote}.value",
            }
        if capability_id == "exchange_rate" and item_id == "spot":
            if "convert" in key:
                return {
                    "kind": "point",
                    "time_path": "meta.last_updated_at",
                    "value_path": "data.{quote}.value",
                }
            return {
                "kind": "point",
                "time_path": "meta.last_updated_at",
                "value_path": "data.{quote}.value",
            }
        return {"kind": "point", "time_path": "timestamp", "value_path": "value"}

    def _to_fact_result(
        self,
        *,
        kind: FactKind,
        query: str,
        provider: Dict[str, Any],
        payload: Dict[str, Any],
        context: Dict[str, Any],
    ) -> LegacyFactResult:
        config = provider.get("config") or {}
        source_name = str(provider.get("name") or provider.get("provider_id") or "custom-provider")
        source_url = str(provider.get("endpoint_url") or "")

        as_of_path = str(config.get("as_of_path") or "").strip()
        as_of = self._extract(payload, as_of_path) if as_of_path else None
        if as_of is None:
            as_of = self._guess_timestamp(payload) or context.get("now_iso")

        if self._is_exchange_rate_kind(kind):
            fx_query = self._parse_fx_pair(query)
            path_tokens = {
                "query": quote(query),
                "query_raw": query,
                "kind": kind,
                "base": fx_query[0],
                "quote": fx_query[1],
            }
            rate_path = self._resolve_path_template(str(config.get("rate_path") or "").strip(), path_tokens)
            rate_value = self._extract(payload, rate_path) if rate_path else self._guess_fx_rate(payload, fx_query[1])
            rate = self._to_float(rate_value)
            if rate is not None:
                data = FxData(base=fx_query[0], quote=fx_query[1], pair=f"{fx_query[0]}{fx_query[1]}", rate=rate)
                return LegacyFactResult(
                    kind="fx",
                    status="ok",
                    data=data,
                    as_of=str(as_of) if as_of else None,
                    confidence="high",
                    sources=[SourceRef(name=source_name, type="api", url=source_url)],
                    render_hint="table",
                    fallback_text=f"{fx_query[0]}/{fx_query[1]} is {rate} as of {as_of}.",
                )

        fx_pair = self._parse_fx_pair(query) if self._is_exchange_rate_kind(kind) else ("", "")
        path_tokens = {
            "query": quote(query),
            "query_raw": query,
            "kind": kind,
            "base": fx_pair[0],
            "quote": fx_pair[1],
        }
        value_path = self._resolve_path_template(str(config.get("value_path") or "").strip(), path_tokens)
        summary_path = self._resolve_path_template(str(config.get("summary_path") or "").strip(), path_tokens)
        unit = str(config.get("unit") or "").strip() or None
        title = str(config.get("title") or f"{kind.title()} · {query}")

        value = self._extract(payload, value_path) if value_path else None
        summary = self._extract(payload, summary_path) if summary_path else None
        if summary is None:
            summary = str(config.get("summary") or f"{kind} snapshot from {source_name}")

        metrics = []
        metrics_map = config.get("metrics") or {}
        if isinstance(metrics_map, dict):
            for label, path in metrics_map.items():
                path_value = self._extract(payload, str(path))
                if path_value is not None:
                    metrics.append({"label": str(label), "value": str(path_value)})

        data = GenericFactData(
            query=query,
            value=str(value) if value is not None else None,
            title=title,
            summary=str(summary),
            unit=unit,
            metrics=metrics,
            trend=[],
        )

        return LegacyFactResult(
            kind=kind,
            status="ok" if value is not None or bool(metrics) else "partial",
            data=data,
            as_of=str(as_of) if as_of else None,
            confidence="high" if value is not None else "medium",
            sources=[SourceRef(name=source_name, type="api", url=source_url)],
            render_hint="card" if value is not None else "text",
            fallback_text=str(summary),
            confidence_reason="custom_provider_partial" if value is None else "",
        )

    @staticmethod
    def _request_json(url: str, method: str, headers: Dict[str, str]) -> Dict[str, Any]:
        req = Request(url, method=method, headers=headers)
        with urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else {"data": data}

    @staticmethod
    def _extract(payload: Dict[str, Any], path: str) -> Any:
        if not path:
            return None
        cursor: Any = payload
        for part in path.split("."):
            key = part.strip()
            if not key:
                continue
            if isinstance(cursor, list):
                try:
                    idx = int(key)
                    cursor = cursor[idx]
                except Exception:
                    return None
            elif isinstance(cursor, dict):
                if key not in cursor:
                    return None
                cursor = cursor.get(key)
            else:
                return None
        return cursor

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _parse_fx_pair(query: str) -> Tuple[str, str]:
        text = (query or "").upper()
        match = re.search(r"(?<![A-Z])([A-Z]{3})\s*(?:/|TO|->|兑|对|和|-)\s*([A-Z]{3})(?![A-Z])", text)
        if match:
            return match.group(1), match.group(2)
        codes = re.findall(r"(?<![A-Z])([A-Z]{3})(?![A-Z])", text)
        if len(codes) >= 2:
            return codes[0], codes[1]
        return "AUD", "USD"

    @staticmethod
    def _guess_fx_rate(payload: Dict[str, Any], quote: str) -> Any:
        quote = quote.upper()
        for path in (
            f"rates.{quote}",
            f"currencies.{quote}.value",
            f"currencies.{quote}.rate",
            f"data.{quote}.value",
            f"data.{quote}.rate",
            f"{quote}.value",
            f"{quote}.rate",
            "rate",
            "value",
        ):
            value = ConfiguredApiProvider._extract(payload, path)
            if value is not None:
                return value
        return None

    @staticmethod
    def _extract_quote_from_value_path(path: str) -> str:
        parts = [p.strip() for p in str(path or "").split(".") if p.strip()]
        for token in parts:
            if len(token) == 3 and token.isalpha() and token.upper() == token:
                return token
        return ""

    @staticmethod
    def _guess_timestamp(payload: Dict[str, Any]) -> Optional[str]:
        candidates = [
            "meta.last_updated_at",
            "datetime",
            "time_last_update_utc",
            "time_last_update_unix",
            "updated_at",
            "timestamp",
            "date",
        ]
        for key in candidates:
            value = ConfiguredApiProvider._extract(payload, key)
            if value is None:
                continue
            if key.endswith("_unix"):
                try:
                    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
                except Exception:
                    continue
            return str(value)
        return None

    @staticmethod
    def _normalize_timestamp(value: Any) -> Optional[str]:
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                ts = float(value)
                if ts > 1_000_000_000_000:
                    ts = ts / 1000.0
                return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            text = str(value).strip()
            if text.isdigit():
                ts = float(text)
                if ts > 1_000_000_000_000:
                    ts = ts / 1000.0
                return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            return datetime.fromisoformat(text).astimezone(timezone.utc).isoformat()
        except Exception:
            return str(value) if value else None

    @staticmethod
    def _shift_iso_minutes(now_iso: str, delta_minutes: int) -> str:
        try:
            text = str(now_iso).strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (dt.astimezone(timezone.utc) + timedelta(minutes=delta_minutes)).isoformat()
        except Exception:
            return now_iso

    @staticmethod
    def _iso_to_unix(value: str) -> int:
        try:
            text = value.strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            return 0

    @staticmethod
    def _iso_to_utc_z(value: str) -> str:
        try:
            text = str(value).strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return str(value)

    @staticmethod
    def _build_url(endpoint: str, *, kind: FactKind, query: str, config: Dict[str, Any]) -> str:
        base, quote_ccy = ConfiguredApiProvider._parse_fx_pair(query) if ConfiguredApiProvider._is_exchange_rate_kind(kind) else ("", "")
        url = endpoint
        substitutions = {
            "{query}": quote(query),
            "{query_raw}": query,
            "{kind}": kind,
            "{base}": base,
            "{quote}": quote_ccy,
        }
        for key, value in substitutions.items():
            url = url.replace(key, str(value))
        extra_query = str(config.get("query_suffix") or "").strip()
        if extra_query:
            connector = "&" if "?" in url else "?"
            url = f"{url}{connector}{extra_query}"
        return url

    @staticmethod
    def _resolve_path_template(path: str, tokens: Dict[str, str]) -> str:
        if not path:
            return ""
        resolved = path
        for key, value in tokens.items():
            resolved = resolved.replace(f"{{{key}}}", str(value))
        return resolved
