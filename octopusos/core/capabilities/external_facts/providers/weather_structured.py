"""Structured weather provider for ExternalFactsCapability."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict
from urllib.parse import quote
from urllib.request import Request, urlopen

from ..types import LegacyFactResult, SourceRef, WeatherData

logger = logging.getLogger(__name__)


class WeatherStructuredProvider:
    """Read-only weather provider backed by structured JSON endpoint."""

    kind = "weather"
    _BASE_URL = "https://wttr.in/{location}?format=j1"

    async def resolve(self, query: str, context: Dict[str, Any]) -> LegacyFactResult:
        location = (query or "").strip() or "unknown"
        source_url = self._BASE_URL.format(location=quote(location))
        try:
            payload = await asyncio.to_thread(self._fetch_json, source_url)
            current = (payload.get("current_condition") or [{}])[0]
            weather = (payload.get("weather") or [{}])[0]
            hourly = (weather.get("hourly") or [{}])[0]

            temp_c = self._parse_float(current.get("temp_C"))
            condition = str((current.get("weatherDesc") or [{"value": None}])[0].get("value") or "").strip() or None
            wind_kmh = self._parse_float(current.get("windspeedKmph"))
            humidity = self._parse_float(current.get("humidity"))
            high_c = self._parse_float(weather.get("maxtempC"))
            low_c = self._parse_float(weather.get("mintempC"))
            if condition is None:
                condition = str((hourly.get("weatherDesc") or [{"value": None}])[0].get("value") or "").strip() or None

            daily = []
            for day in (payload.get("weather") or [])[:10]:
                daily.append(
                    {
                        "date": day.get("date"),
                        "high_c": self._parse_float(day.get("maxtempC")),
                        "low_c": self._parse_float(day.get("mintempC")),
                        "condition": str((day.get("hourly") or [{}])[0].get("weatherDesc", [{"value": ""}])[0].get("value") or "").strip() or None,
                    }
                )

            hourly_points = []
            for entry in (weather.get("hourly") or [])[:8]:
                hourly_points.append(
                    {
                        "time": str(entry.get("time") or ""),
                        "temp_c": self._parse_float(entry.get("tempC")),
                        "condition": str((entry.get("weatherDesc") or [{"value": ""}])[0].get("value") or "").strip() or None,
                    }
                )

            summary = (
                f"{location} is {temp_c if temp_c is not None else 'N/A'}°C"
                f"{', ' + condition if condition else ''}."
            )

            data = WeatherData(
                location=location,
                temp_c=temp_c,
                condition=condition,
                wind_kmh=wind_kmh,
                humidity_pct=humidity,
                high_c=high_c,
                low_c=low_c,
                summary=summary,
                daily=daily,
                hourly=hourly_points,
            )
            as_of = context.get("now_iso")
            return LegacyFactResult(
                kind="weather",
                status="ok",
                data=data,
                as_of=as_of,
                confidence="high" if (temp_c is not None and condition) else "medium",
                sources=[SourceRef(name="wttr.in", type="api", url=source_url)],
                render_hint="card",
                fallback_text=(
                    f"{location} weather: {temp_c if temp_c is not None else 'N/A'}°C, "
                    f"{condition or 'conditions unavailable'}."
                ),
            )
        except Exception as exc:
            logger.warning("Weather provider failed", extra={"query": query, "error": str(exc)})
            return LegacyFactResult(
                kind="weather",
                status="unavailable",
                data=WeatherData(location=location),
                as_of=context.get("now_iso"),
                confidence="low",
                sources=[SourceRef(name="wttr.in", type="api", url=source_url)],
                render_hint="text",
                fallback_text=(
                    f"I can't fetch reliable real-time weather for {location} right now. "
                    "I can retry in a moment."
                ),
            )

    @staticmethod
    def _fetch_json(url: str) -> Dict[str, Any]:
        request = Request(url, headers={"User-Agent": "OctopusOS ExternalFacts/1.0"})
        with urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
