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

from agentos.store import get_db, get_writer

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


@router.get("/writer-stats")
async def get_writer_stats() -> Dict[str, Any]:
    """
    Get SQLiteWriter monitoring statistics

    Returns real-time metrics for the database writer including:
    - Queue status and backlog
    - Write performance metrics
    - Retry and failure counts
    - Throughput and latency statistics

    Returns:
        Dict containing all writer monitoring metrics
        Returns error dict if writer not initialized
    """
    try:
        # Get the global writer instance
        writer = get_writer()

        if writer:
            stats = writer.get_stats()

            # Add health status based on metrics
            status = "ok"
            warnings = []

            if stats["queue_size"] > 100:
                status = "critical"
                warnings.append("Queue backlog critical - immediate action required")
            elif stats["queue_size"] > 50:
                status = "warning"
                warnings.append("Queue backlog detected - consider optimization")

            if stats["failed_writes"] > 0:
                failure_rate = stats["failed_writes"] / max(stats["total_writes"], 1)
                if failure_rate > 0.01:  # >1% failure rate
                    status = "warning"
                    warnings.append(f"High failure rate: {failure_rate*100:.1f}%")

            stats["status"] = status
            if warnings:
                stats["warnings"] = warnings

            return stats
        else:
            return {
                "error": "Writer not initialized",
                "status": "unavailable",
                "message": "SQLiteWriter has not been initialized yet"
            }

    except Exception as e:
        return {
            "error": str(e),
            "status": "error",
            "message": "Failed to retrieve writer statistics"
        }
