"""Default trusted source catalogs for external fact kinds."""

from __future__ import annotations

from .types import FactKind

DEFAULT_SOURCE_CATALOG: dict[FactKind, tuple[str, str, str]] = {
    "weather": ("weather.gov", "bom.gov.au", "metoffice.gov.uk"),
    "fx": ("frankfurter.app", "exchangerate.host", "ecb.europa.eu"),
    "stock": ("finance.yahoo.com", "marketwatch.com", "reuters.com"),
    "crypto": ("coingecko.com", "coinmarketcap.com", "reuters.com"),
    "index": ("spglobal.com", "finance.yahoo.com", "reuters.com"),
    "etf": ("ishares.com", "vanguard.com", "ssga.com"),
    "bond_yield": ("treasury.gov", "fred.stlouisfed.org", "bloomberg.com"),
    "commodity": ("cmegroup.com", "tradingeconomics.com", "reuters.com"),
    "flight": ("flightaware.com", "flightradar24.com", "flightstats.com"),
    "train": ("amtrak.com", "nationalrail.co.uk", "transportnsw.info"),
    "hotel": ("booking.com", "expedia.com", "tripadvisor.com"),
    "shipping": ("marinetraffic.com", "vesselfinder.com", "fleetmon.com"),
    "package": ("ups.com", "fedex.com", "dhl.com"),
    "fuel_price": ("globalpetrolprices.com", "aaa.com", "nsw.gov.au"),
    "news": ("reuters.com", "apnews.com", "bbc.com"),
    "sports": ("espn.com", "flashscore.com", "sofascore.com"),
    "calendar": ("calendar.google.com", "outlook.office.com", "notion.so"),
    "traffic": ("tomtom.com", "waze.com", "google.com"),
    "air_quality": ("aqicn.org", "airnow.gov", "waqi.info"),
    "earthquake": ("usgs.gov", "emsc-csem.org", "geonet.org.nz"),
    "power_outage": ("poweroutage.us", "aemo.com.au", "energex.com.au"),
    "company_research": ("wikipedia.org", "baike.baidu.com", "news.baidu.com"),
}


def catalog_for(kind: FactKind) -> tuple[str, str, str]:
    return DEFAULT_SOURCE_CATALOG.get(kind, ("reuters.com", "apnews.com", "bbc.com"))


def merge_with_catalog(kind: FactKind, existing: list[str] | None) -> list[str]:
    merged: list[str] = []
    for item in existing or []:
        value = str(item or "").strip().lower()
        if value and value not in merged:
            merged.append(value)
    for item in catalog_for(kind):
        value = item.lower()
        if value not in merged:
            merged.append(value)
        if len(merged) >= 3:
            break
    return merged[:3]
