"""Read-only registry endpoint for external facts capability-item editor."""

from __future__ import annotations

from fastapi import APIRouter

from octopusos.core.capabilities.external_facts.registry import list_capabilities

router = APIRouter(prefix="/api/compat/external-facts", tags=["compat"])


@router.get("/registry")
async def get_external_facts_registry():
    capabilities = []
    for cap in list_capabilities():
        items = []
        for item in cap.items:
            input_schema = item.input_schema or {}
            props = input_schema.get("properties") if isinstance(input_schema.get("properties"), dict) else {}
            items.append(
                {
                    "item_id": item.item_id,
                    "output_kind": item.output_kind,
                    "required": list(input_schema.get("required") or []),
                    "placeholders": sorted(list(props.keys())),
                }
            )
        capabilities.append(
            {
                "capability_id": cap.capability_id,
                "description": cap.description,
                "items": items,
            }
        )
    return {"ok": True, "data": capabilities}
