"""Endpoint map validation for provider capability-item mappings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List

from .registry import get_capability

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


@dataclass(frozen=True)
class EndpointMapValidationResult:
    ok: bool
    errors: List[str]


def _extract_placeholders(value: str) -> set[str]:
    if not value:
        return set()
    return set(_PLACEHOLDER_RE.findall(value))


def validate_endpoint_map(
    *,
    endpoint_map: Dict[str, Any],
    supported_items: Dict[str, List[str]],
    version: int = 1,
) -> EndpointMapValidationResult:
    errors: List[str] = []
    if version != 1:
        errors.append(f"unsupported endpoint_map_version: {version}")
        return EndpointMapValidationResult(ok=False, errors=errors)
    if not isinstance(endpoint_map, dict):
        return EndpointMapValidationResult(ok=False, errors=["endpoint_map must be an object"])
    if not isinstance(supported_items, dict):
        return EndpointMapValidationResult(ok=False, errors=["supported_items must be an object"])

    for capability_id, item_ids in supported_items.items():
        capability = get_capability(capability_id)
        if capability is None:
            errors.append(f"unknown capability_id: {capability_id}")
            continue
        mapping = endpoint_map.get(capability_id)
        if not isinstance(mapping, dict):
            errors.append(f"missing endpoint_map capability mapping: {capability_id}")
            continue
        items_block = mapping.get("items")
        if not isinstance(items_block, dict):
            errors.append(f"missing items block for capability: {capability_id}")
            continue
        for item_id in item_ids:
            item_schema = capability.item(item_id)
            if item_schema is None:
                errors.append(f"unsupported item_id for {capability_id}: {item_id}")
                continue
            item_map = items_block.get(item_id)
            if not isinstance(item_map, dict):
                errors.append(f"missing item mapping: {capability_id}.{item_id}")
                continue
            method = str(item_map.get("method") or "").upper()
            if method not in {"GET", "POST"}:
                errors.append(f"invalid method for {capability_id}.{item_id}: {method or '<empty>'}")
            url = str(item_map.get("url") or "").strip()
            if not url:
                errors.append(f"missing url for {capability_id}.{item_id}")
                continue

            response = item_map.get("response")
            if not isinstance(response, dict):
                errors.append(f"missing response block for {capability_id}.{item_id}")
                continue
            response_kind = str(response.get("kind") or "").strip()
            if response_kind != item_schema.output_kind:
                errors.append(
                    f"response.kind mismatch for {capability_id}.{item_id}: "
                    f"expected {item_schema.output_kind}, got {response_kind or '<empty>'}"
                )
            if response_kind == "series":
                if not str(response.get("points_path") or "").strip():
                    errors.append(f"missing response.points_path for {capability_id}.{item_id}")
                if not str(response.get("time_path") or "").strip():
                    errors.append(f"missing response.time_path for {capability_id}.{item_id}")
                if not str(response.get("value_path") or "").strip():
                    errors.append(f"missing response.value_path for {capability_id}.{item_id}")
            elif response_kind == "point":
                if not str(response.get("time_path") or "").strip():
                    errors.append(f"missing response.time_path for {capability_id}.{item_id}")
                if not str(response.get("value_path") or "").strip():
                    errors.append(f"missing response.value_path for {capability_id}.{item_id}")

            # Placeholder checks against item input schema.
            required_inputs = set(item_schema.input_schema.get("properties", {}).keys())
            placeholders = set()
            placeholders |= _extract_placeholders(url)
            query = item_map.get("query")
            if isinstance(query, dict):
                for qv in query.values():
                    placeholders |= _extract_placeholders(str(qv))
            headers = item_map.get("headers")
            if isinstance(headers, dict):
                for hv in headers.values():
                    placeholders |= _extract_placeholders(str(hv))

            allowed_runtime_tokens = {"api_key", "now_iso"}
            for token in placeholders:
                if token not in required_inputs and token not in allowed_runtime_tokens:
                    errors.append(f"unknown placeholder {{{token}}} in {capability_id}.{item_id}")

    return EndpointMapValidationResult(ok=len(errors) == 0, errors=errors)
