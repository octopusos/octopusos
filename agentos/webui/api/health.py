"""
Health API - System health status

GET /api/health - Get system health
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import psutil
import os

from agentos.store import get_db

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response"""
    status: str  # "ok" | "warn" | "down"
    timestamp: str
    uptime_seconds: Optional[float] = None
    components: Dict[str, Any]
    metrics: Dict[str, Any]


@router.get("/health")
async def get_health() -> HealthStatus:
    """
    Get system health status

    Returns:
        HealthStatus with overall status and component details
    """
    try:
        # Check database
        db_status = "ok"
        try:
            conn = get_db()
            conn.execute("SELECT 1")
            conn.close()
        except Exception as e:
            db_status = "down"

        # Get process metrics
        process = psutil.Process(os.getpid())
        uptime = datetime.now(timezone.utc).timestamp() - process.create_time()

        # Determine overall status
        overall_status = "ok"
        if db_status == "down":
            overall_status = "down"

        components = {
            "database": db_status,
            "process": "ok",
        }

        metrics = {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "pid": os.getpid(),
        }

        return HealthStatus(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=uptime,
            components=components,
            metrics=metrics,
        )

    except Exception as e:
        return HealthStatus(
            status="down",
            timestamp=datetime.now(timezone.utc).isoformat(),
            components={"error": str(e)},
            metrics={},
        )
