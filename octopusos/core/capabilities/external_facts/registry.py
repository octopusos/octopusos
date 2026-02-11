"""Capability registry for external facts platform model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional


OutputKind = Literal["point", "series", "table"]


@dataclass(frozen=True)
class ItemSchema:
    item_id: str
    input_schema: Dict[str, Any]
    output_kind: OutputKind
    output_schema: Dict[str, Any]
    analyzable: bool = True


@dataclass(frozen=True)
class CapabilityDef:
    capability_id: str
    items: tuple[ItemSchema, ...]
    description: str = ""

    def item(self, item_id: str) -> Optional[ItemSchema]:
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None


EXCHANGE_RATE_CAPABILITY = CapabilityDef(
    capability_id="exchange_rate",
    description="Exchange rate facts and analytics",
    items=(
        ItemSchema(
            item_id="spot",
            input_schema={
                "type": "object",
                "required": ["base", "quote"],
                "properties": {
                    "base": {"type": "string", "minLength": 3, "maxLength": 3},
                    "quote": {"type": "string", "minLength": 3, "maxLength": 3},
                },
            },
            output_kind="point",
            output_schema={
                "type": "object",
                "required": ["value", "timestamp"],
                "properties": {
                    "value": {"type": "number"},
                    "timestamp": {"type": "string"},
                },
            },
            analyzable=False,
        ),
        ItemSchema(
            item_id="series",
            input_schema={
                "type": "object",
                "required": ["base", "quote"],
                "properties": {
                    "base": {"type": "string", "minLength": 3, "maxLength": 3},
                    "quote": {"type": "string", "minLength": 3, "maxLength": 3},
                    "from_iso": {"type": "string"},
                    "to_iso": {"type": "string"},
                    "window_minutes": {"type": "integer", "minimum": 1, "maximum": 1440},
                },
            },
            output_kind="series",
            output_schema={
                "type": "object",
                "required": ["series"],
                "properties": {
                    "series": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["t", "v"],
                            "properties": {
                                "t": {"type": "string"},
                                "v": {"type": "number"},
                            },
                        },
                    }
                },
            },
            analyzable=True,
        ),
        ItemSchema(
            item_id="convert",
            input_schema={
                "type": "object",
                "required": ["base", "quote", "amount"],
                "properties": {
                    "base": {"type": "string", "minLength": 3, "maxLength": 3},
                    "quote": {"type": "string", "minLength": 3, "maxLength": 3},
                    "amount": {"type": "number"},
                },
            },
            output_kind="point",
            output_schema={
                "type": "object",
                "required": ["value", "timestamp"],
                "properties": {
                    "value": {"type": "number"},
                    "timestamp": {"type": "string"},
                },
            },
            analyzable=False,
        ),
    ),
)

MARKET_COMPANY_RESEARCH_CAPABILITY = CapabilityDef(
    capability_id="market_company_research",
    description="Company background research brief from public sources",
    items=(
        ItemSchema(
            item_id="brief",
            input_schema={
                "type": "object",
                "required": ["company_name"],
                "properties": {
                    "company_name": {"type": "string", "minLength": 1, "maxLength": 120},
                    "alias": {"type": "array", "items": {"type": "string"}},
                    "region": {"type": "string", "maxLength": 10},
                    "depth": {"type": "string", "enum": ["mvp"]},
                },
            },
            output_kind="table",
            output_schema={
                "type": "object",
                "required": ["summary", "sources"],
                "properties": {
                    "summary": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "date": {"type": "string"},
                            },
                        },
                    },
                },
            },
            analyzable=False,
        ),
    ),
)


CAPABILITY_REGISTRY: Dict[str, CapabilityDef] = {
    EXCHANGE_RATE_CAPABILITY.capability_id: EXCHANGE_RATE_CAPABILITY,
    MARKET_COMPANY_RESEARCH_CAPABILITY.capability_id: MARKET_COMPANY_RESEARCH_CAPABILITY,
}


def get_capability(capability_id: str) -> Optional[CapabilityDef]:
    return CAPABILITY_REGISTRY.get((capability_id or "").strip())


def list_capabilities() -> list[CapabilityDef]:
    return list(CAPABILITY_REGISTRY.values())
