"""Mode Monitoring API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, Query

from octopusos.core.mode.mode_alerts import AlertSeverity, get_alert_aggregator

router = APIRouter(prefix="/api/mode", tags=["mode"])


@router.get("/alerts")
def list_alerts(
    severity: Optional[AlertSeverity] = Query(default=None),
    limit: Optional[int] = Query(default=None, ge=1, le=1000),
):
    aggregator = get_alert_aggregator()
    alerts = aggregator.get_recent_alerts(limit=limit)
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    return {
        "status": "ok",
        "alerts": [a.to_dict() for a in alerts],
        "stats": aggregator.get_stats(),
    }


@router.get("/stats")
def get_stats():
    aggregator = get_alert_aggregator()
    return {"status": "ok", "stats": aggregator.get_stats()}


@router.post("/alerts/clear")
def clear_alerts():
    aggregator = get_alert_aggregator()
    cleared = len(aggregator.recent_alerts)
    aggregator.clear_recent()
    return {
        "status": "ok",
        "cleared_count": cleared,
        "message": "Recent alerts cleared",
    }


def register_routes(app: FastAPI) -> None:
    app.include_router(router)


__all__ = ["router", "register_routes"]
