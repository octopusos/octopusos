"""Structured FX provider for ExternalFactsCapability."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Dict, Tuple
from urllib.request import Request, urlopen

from ..types import LegacyFactResult, FxData, SourceRef

logger = logging.getLogger(__name__)


class FxStructuredProvider:
    """Read-only FX provider using structured quote endpoint."""

    kind = "fx"
    _BASE_URL = "https://api.frankfurter.app/latest?from={base}&to={quote}"
    _ER_API_URL = "https://open.er-api.com/v6/latest/{base}"

    async def resolve(self, query: str, context: Dict[str, Any]) -> LegacyFactResult:
        base, quote = self._parse_pair(query)
        pair = f"{base}/{quote}"
        source_url = self._ER_API_URL.format(base=base)
        try:
            # Prefer source with explicit update timestamp.
            payload = await asyncio.to_thread(self._fetch_json, source_url)
            rates = payload.get("rates") or {}
            rate = rates.get(quote)
            rate_float = float(rate) if rate is not None else None
            as_of = self._parse_er_api_timestamp(payload) or context.get("now_iso")
            if rate_float is not None:
                return LegacyFactResult(
                    kind="fx",
                    status="ok",
                    data=FxData(base=base, quote=quote, pair=f"{base}{quote}", rate=rate_float),
                    as_of=str(as_of) if as_of else None,
                    confidence="high",
                    sources=[SourceRef(name="open.er-api.com", type="api", url=source_url)],
                    render_hint="table",
                    fallback_text=f"{pair} is {rate_float} as of {as_of}.",
                )
        except Exception as exc:
            logger.debug("ER API provider failed", extra={"query": query, "error": str(exc)})

        source_url = self._BASE_URL.format(base=base, quote=quote)
        try:
            payload = await asyncio.to_thread(self._fetch_json, source_url)
            rates = payload.get("rates") or {}
            rate = rates.get(quote)
            rate_float = float(rate) if rate is not None else None
            as_of = payload.get("date") or context.get("now_iso")
            return LegacyFactResult(
                kind="fx",
                status="ok",
                data=FxData(base=base, quote=quote, pair=f"{base}{quote}", rate=rate_float),
                as_of=str(as_of) if as_of else None,
                confidence="high" if rate_float is not None else "low",
                sources=[SourceRef(name="frankfurter.app", type="api", url=source_url)],
                render_hint="table",
                fallback_text=f"{pair} is {rate_float} as of {as_of}.",
            )
        except Exception as exc:
            logger.warning("FX provider failed", extra={"query": query, "error": str(exc)})
            return LegacyFactResult(
                kind="fx",
                status="unavailable",
                data=FxData(base=base, quote=quote, pair=f"{base}{quote}", rate=None),
                as_of=context.get("now_iso"),
                confidence="low",
                sources=[SourceRef(name="open.er-api.com/frankfurter.app", type="api", url=source_url)],
                render_hint="text",
                fallback_text=(
                    f"I can't fetch a reliable live {pair} quote right now. "
                    "Please retry in a moment."
                ),
            )

    @staticmethod
    def _fetch_json(url: str) -> Dict[str, Any]:
        request = Request(url, headers={"User-Agent": "OctopusOS ExternalFacts/1.0"})
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _parse_pair(query: str) -> Tuple[str, str]:
        text = (query or "").upper()
        match = re.search(r"(?<![A-Z])([A-Z]{3})\s*(?:/|TO|->|兑|对|-)\s*([A-Z]{3})(?![A-Z])", text)
        if match:
            return match.group(1), match.group(2)
        codes = re.findall(r"(?<![A-Z])([A-Z]{3})(?![A-Z])", text)
        if len(codes) >= 2:
            return codes[0], codes[1]
        return "AUD", "USD"

    @staticmethod
    def _parse_er_api_timestamp(payload: Dict[str, Any]) -> str | None:
        ts = payload.get("time_last_update_unix")
        try:
            if ts is None:
                return None
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
        except Exception:
            return None
