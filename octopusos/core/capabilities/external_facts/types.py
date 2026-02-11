"""Types for ExternalFactsCapability.

Platform main path uses unified FactResult(kind=point|series|table).
Legacy weather/fx/generic envelopes are kept for compatibility adapters only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

FactKind = Literal[
    "weather",
    "fx",
    "stock",
    "crypto",
    "index",
    "etf",
    "bond_yield",
    "commodity",
    "flight",
    "train",
    "hotel",
    "shipping",
    "package",
    "fuel_price",
    "news",
    "sports",
    "calendar",
    "traffic",
    "air_quality",
    "earthquake",
    "power_outage",
    "company_research",
]
SUPPORTED_FACT_KINDS: tuple[FactKind, ...] = (
    "weather",
    "fx",
    "stock",
    "crypto",
    "index",
    "etf",
    "bond_yield",
    "commodity",
    "flight",
    "train",
    "hotel",
    "shipping",
    "package",
    "fuel_price",
    "news",
    "sports",
    "calendar",
    "traffic",
    "air_quality",
    "earthquake",
    "power_outage",
    "company_research",
)
FactStatus = Literal["ok", "partial", "unavailable"]
Confidence = Literal["high", "medium", "low"]
RenderHint = Literal["card", "text", "table"]
EvidenceType = Literal["search_result", "web_page", "api_response"]
ExtractionStatus = Literal["ok", "partial", "failed"]
VerificationStatus = Literal["pass", "fail", "unknown"]


def utc_now_iso() -> str:
    """Return UTC ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SourceRef:
    name: str
    type: str
    url: Optional[str] = None
    retrieved_at: str = field(default_factory=utc_now_iso)


@dataclass
class SourcePolicy:
    prefer_structured: bool = True
    allow_search_fallback: bool = True
    max_sources: int = 3
    require_freshness_seconds: Optional[int] = 3600
    source_whitelist: List[str] = field(default_factory=list)
    source_blacklist: List[str] = field(default_factory=list)
    min_confidence: Confidence = "low"


@dataclass
class WeatherData:
    location: str
    temp_c: Optional[float] = None
    condition: Optional[str] = None
    wind_kmh: Optional[float] = None
    humidity_pct: Optional[float] = None
    high_c: Optional[float] = None
    low_c: Optional[float] = None
    summary: Optional[str] = None
    daily: List[Dict[str, Any]] = field(default_factory=list)
    hourly: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FxData:
    base: str
    quote: str
    pair: str
    rate: Optional[float] = None


@dataclass
class GenericFactData:
    query: str
    value: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    unit: Optional[str] = None
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    trend: List[Dict[str, Any]] = field(default_factory=list)


FactData = Union[WeatherData, FxData, GenericFactData]


@dataclass
class EvidenceItem:
    kind: FactKind
    query: str
    type: EvidenceType
    source: SourceRef
    content_snippet: str
    captured_at: str = field(default_factory=utc_now_iso)
    raw_ref: Optional[str] = None
    evidence_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ExtractionRecord:
    evidence_id: str
    kind: FactKind
    schema_version: str
    status: ExtractionStatus
    extracted: Dict[str, Any]
    missing_fields: List[str]
    notes: str
    created_at: str = field(default_factory=utc_now_iso)
    extraction_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class VerificationRecord:
    evidence_id: str
    kind: FactKind
    status: VerificationStatus
    confidence: Confidence
    confidence_reason: str
    checks: Dict[str, Any]
    created_at: str = field(default_factory=utc_now_iso)
    verification_id: str = field(default_factory=lambda: str(uuid4()))


class FactSeriesPoint(BaseModel):
    t: str
    v: float


class FactResult(BaseModel):
    """Unified platform fact result used by plan/executor/provider main path."""

    kind: Literal["point", "series", "table"]
    capability_id: str
    item_id: str
    provider_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    unavailable: bool = False
    unavailable_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


@dataclass
class LegacyFactResult:
    """Deprecated legacy envelope. Use FactResult for new main path."""

    kind: FactKind
    status: FactStatus
    data: Optional[FactData]
    as_of: Optional[str]
    confidence: Confidence
    sources: List[SourceRef]
    render_hint: RenderHint
    fallback_text: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence_reason: str = ""
    extraction_ids: List[str] = field(default_factory=list)
    verification_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = asdict(self)
        return payload


@dataclass
class CompatLegacyResult:
    """Legacy alias container for historical reads."""

    result: LegacyFactResult


def validate_weather_complete(data: Optional[WeatherData]) -> bool:
    """Weather is complete only when location exists and temp/condition has at least one value."""
    if data is None:
        return False
    if not data.location:
        return False
    return data.temp_c is not None or bool(data.condition)


def validate_fx_complete(data: Optional[FxData]) -> bool:
    """FX is complete only when rate is present."""
    if data is None:
        return False
    return data.rate is not None
