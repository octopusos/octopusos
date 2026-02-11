"""Structured index provider for major market indices (MVP)."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
from typing import Any, Dict, Tuple
from urllib.parse import quote
from urllib.request import Request, urlopen

from ..types import LegacyFactResult, GenericFactData, SourceRef

logger = logging.getLogger(__name__)


class IndexStructuredProvider:
    """Read-only index quote provider with multi-source fallback."""

    kind = "index"

    _YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
    _STOOQ_CSV = "https://stooq.com/q/l/?s={symbol}&i=d"

    async def resolve(self, query: str, context: Dict[str, Any]) -> LegacyFactResult:
        symbol, label = self._parse_symbol(query)
        now_iso = context.get("now_iso")

        yahoo = await self._try_yahoo(symbol=symbol)
        if yahoo is not None:
            value, day_change, day_pct, series, as_of = yahoo
            return self._build_ok_result(
                query=query,
                label=label,
                value=value,
                day_change=day_change,
                day_pct=day_pct,
                trend=series,
                source_name="finance.yahoo.com",
                source_url=self._YAHOO_CHART.format(symbol=quote(symbol)),
                as_of=as_of or now_iso,
            )

        stooq = await self._try_stooq(symbol=symbol)
        if stooq is not None:
            value, day_change, day_pct, series, as_of = stooq
            return self._build_ok_result(
                query=query,
                label=label,
                value=value,
                day_change=day_change,
                day_pct=day_pct,
                trend=series,
                source_name="stooq.com",
                source_url=self._STOOQ_CSV.format(symbol=quote(self._to_stooq_symbol(symbol))),
                as_of=as_of or now_iso,
            )

        return LegacyFactResult(
            kind="index",
            status="unavailable",
            data=GenericFactData(
                query=query,
                title=f"Index · {label}",
                summary="I couldn't fetch a verified index quote from structured providers.",
                metrics=[],
                trend=[],
            ),
            as_of=now_iso,
            confidence="low",
            sources=[SourceRef(name="index-provider", type="api", retrieved_at=now_iso or "")],
            render_hint="text",
            fallback_text="I couldn't fetch a verified index quote from structured providers.",
            confidence_reason="index_provider_unavailable",
        )

    async def _try_yahoo(self, symbol: str) -> Tuple[float, float, float, list[dict[str, Any]], str | None] | None:
        url = self._YAHOO_CHART.format(symbol=quote(symbol))
        try:
            payload = await asyncio.to_thread(self._fetch_json, url)
            result = ((payload.get("chart") or {}).get("result") or [None])[0]
            if not isinstance(result, dict):
                return None
            meta = result.get("meta") or {}
            indicators = (result.get("indicators") or {}).get("quote") or []
            quote_obj = indicators[0] if indicators else {}
            closes = quote_obj.get("close") or []
            opens = quote_obj.get("open") or []
            timestamps = result.get("timestamp") or []
            values = [float(v) for v in closes if isinstance(v, (int, float))]
            if not values:
                return None
            current = float(meta.get("regularMarketPrice") or values[-1])
            prev_close = float(meta.get("chartPreviousClose") or opens[-1] or current)
            day_change = current - prev_close
            day_pct = (day_change / prev_close * 100.0) if prev_close else 0.0
            series = self._build_series_from_values(timestamps, closes)
            return current, day_change, day_pct, series, str(meta.get("regularMarketTime") or "")
        except Exception as exc:
            logger.debug("Index yahoo fetch failed", extra={"symbol": symbol, "error": str(exc)})
            return None

    async def _try_stooq(self, symbol: str) -> Tuple[float, float, float, list[dict[str, Any]], str | None] | None:
        stooq_symbol = self._to_stooq_symbol(symbol)
        url = self._STOOQ_CSV.format(symbol=quote(stooq_symbol))
        try:
            raw = await asyncio.to_thread(self._fetch_text, url)
            reader = csv.reader(io.StringIO(raw))
            row = next(reader, None)
            if not row or len(row) < 8:
                return None
            close = self._parse_float(row[6])
            open_price = self._parse_float(row[3])
            low = self._parse_float(row[5])
            high = self._parse_float(row[4])
            if close is None:
                return None
            prev = open_price or close
            day_change = close - prev
            day_pct = (day_change / prev * 100.0) if prev else 0.0
            series = []
            if low is not None:
                series.append({"time": "Low", "value": round(low, 2)})
            series.append({"time": "Open", "value": round(prev, 2)})
            if high is not None:
                series.append({"time": "High", "value": round(high, 2)})
            series.append({"time": "Close", "value": round(close, 2)})
            as_of = f"{row[1]}T{row[2]}Z" if row[1] and row[2] else None
            return close, day_change, day_pct, series, as_of
        except Exception as exc:
            logger.debug("Index stooq fetch failed", extra={"symbol": symbol, "error": str(exc)})
            return None

    def _build_ok_result(
        self,
        *,
        query: str,
        label: str,
        value: float,
        day_change: float,
        day_pct: float,
        trend: list[dict[str, Any]],
        source_name: str,
        source_url: str,
        as_of: str | None,
    ) -> LegacyFactResult:
        sign = "+" if day_change >= 0 else ""
        data = GenericFactData(
            query=query,
            value=f"{value:.2f}",
            title=f"Index · {label}",
            summary=f"{label} quote snapshot",
            unit="points",
            metrics=[
                {"label": "Day Change", "value": f"{sign}{day_change:.2f}"},
                {"label": "Day %", "value": f"{sign}{day_pct:.2f}%"},
                {"label": "Provider", "value": source_name},
                {"label": "Market", "value": "US"},
            ],
            trend=trend[:8],
        )
        return LegacyFactResult(
            kind="index",
            status="ok",
            data=data,
            as_of=as_of,
            confidence="high",
            sources=[SourceRef(name=source_name, type="api", url=source_url)],
            render_hint="card",
            fallback_text=f"{label}: {value:.2f} ({sign}{day_pct:.2f}%).",
        )

    @staticmethod
    def _parse_symbol(query: str) -> Tuple[str, str]:
        text = (query or "").strip().lower()
        if any(token in text for token in ("标普", "s&p", "sp500", "spx")):
            return "^GSPC", "S&P 500"
        if any(token in text for token in ("纳斯达克", "纳指", "nasdaq", "ndx")):
            return "^NDX", "NASDAQ 100"
        if any(token in text for token in ("道琼斯", "dow", "djia")):
            return "^DJI", "Dow Jones"
        return "^GSPC", "S&P 500"

    @staticmethod
    def _to_stooq_symbol(symbol: str) -> str:
        mapping = {
            "^GSPC": "^spx",
            "^NDX": "^ndq",
            "^DJI": "^dji",
        }
        return mapping.get(symbol, "^spx")

    @staticmethod
    def _fetch_json(url: str) -> Dict[str, Any]:
        req = Request(url, headers={"User-Agent": "OctopusOS ExternalFacts/1.0"})
        with urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _fetch_text(url: str) -> str:
        req = Request(url, headers={"User-Agent": "OctopusOS ExternalFacts/1.0"})
        with urlopen(req, timeout=8) as resp:
            return resp.read().decode("utf-8")

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _build_series_from_values(timestamps: list[Any], closes: list[Any]) -> list[dict[str, Any]]:
        series: list[dict[str, Any]] = []
        for i, value in enumerate(closes):
            if not isinstance(value, (int, float)):
                continue
            ts = timestamps[i] if i < len(timestamps) else i
            series.append({"time": str(ts), "value": round(float(value), 2)})
        return series[-8:]
