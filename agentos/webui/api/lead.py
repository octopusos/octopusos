"""
Lead Agent API - Risk Mining and Follow-up Task Creation

Endpoints:
- POST /api/lead/scan - Trigger risk scan (manual or cron)
- GET /api/lead/findings - Query recent findings
- GET /api/lead/stats - Lead Agent statistics
"""

from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from agentos.core.lead.service import LeadService, LeadServiceConfig
from agentos.core.lead.models import WindowKind, FindingSeverity
from agentos.core.lead.miner import RiskMiner, MinerConfig
from agentos.core.lead.dedupe import LeadFindingStore
from agentos.core.lead.adapters.storage import LeadStorage
from agentos.core.lead.adapters.task_creator import LeadTaskCreator
from agentos.store import get_db_path


router = APIRouter(prefix="/api/lead", tags=["lead"])


# Request/Response Models
class ScanRequest(BaseModel):
    """Scan request model"""
    window: str = "24h"  # 24h, 7d, 30d
    dry_run: bool = True


class ScanResponse(BaseModel):
    """Scan response model"""
    scan_id: str
    window: Dict[str, Any]
    findings_count: int
    new_findings: int
    tasks_created: int
    dry_run: bool
    top_findings: List[Dict[str, Any]]
    config_info: Optional[Dict[str, Any]] = None


class FindingListResponse(BaseModel):
    """Finding list response model"""
    findings: List[Dict[str, Any]]
    total: int
    window: Optional[str] = None
    severity: Optional[str] = None


class LeadStatsResponse(BaseModel):
    """Lead Agent statistics response"""
    total_findings: int
    by_severity: Dict[str, int]
    by_window: Dict[str, int]
    unlinked_count: int


def _validate_window(window: str) -> None:
    """
    Validate window parameter

    Args:
        window: Window string (24h, 7d, 30d)

    Raises:
        HTTPException: If window is invalid
    """
    valid_windows = ["24h", "7d", "30d"]
    if window not in valid_windows:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window: {window}. Must be one of: {valid_windows}"
        )


def _validate_severity(severity: str) -> None:
    """
    Validate severity parameter

    Args:
        severity: Severity string (LOW, MEDIUM, HIGH, CRITICAL)

    Raises:
        HTTPException: If severity is invalid
    """
    valid_severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if severity.upper() not in valid_severities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity: {severity}. Must be one of: {valid_severities}"
        )


@router.post("/scan", response_model=ScanResponse)
async def scan(
    window: str = Query("24h", pattern="^(24h|7d|30d)$"),
    dry_run: bool = True
) -> ScanResponse:
    """
    Trigger risk scan

    Flow:
    1. Create scan window
    2. Mine risks using 6 rules
    3. Deduplicate findings
    4. Create follow-up tasks (if not dry_run)
    5. Return scan results

    Args:
        window: Scan window (24h, 7d, 30d)
        dry_run: If True, don't create tasks (default: True)

    Returns:
        Scan results with findings and tasks created

    Raises:
        HTTPException: If window is invalid or scan fails
    """
    try:
        # Validate window
        _validate_window(window)

        # Get database path
        db_path = get_db_path()

        # Use LeadScanJob for consistency (provides config_info)
        from agentos.jobs.lead_scan import LeadScanJob

        job = LeadScanJob(db_path=db_path)
        result = job.run_scan(window_kind=window, dry_run=dry_run)

        # Get findings from dedupe store
        dedupe_store = LeadFindingStore(db_path)
        findings_objs = dedupe_store.get_recent_findings(limit=200)
        findings = [f.to_dict() for f in findings_objs]

        # Extract top findings (sorted by severity)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_findings = sorted(
            findings,
            key=lambda f: severity_order.get(f.get("severity", "low").lower(), 999)
        )
        top_findings = sorted_findings[:10]  # Top 10

        return ScanResponse(
            scan_id=f"scan_{result['timestamp']}",
            window={"kind": window, "timestamp": result['timestamp']},
            findings_count=result.get("findings_count", 0),
            new_findings=result.get("findings_count", 0),
            tasks_created=result.get("tasks_created", 0),
            dry_run=dry_run,
            top_findings=top_findings,
            config_info=result.get("config_info")
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.get("/findings", response_model=FindingListResponse)
async def list_findings(
    limit: int = Query(100, ge=1, le=500),
    severity: Optional[str] = None,
    window: Optional[str] = None
) -> FindingListResponse:
    """
    Query recent findings

    Args:
        limit: Maximum number of findings to return (1-500)
        severity: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
        window: Filter by scan window (24h, 7d, 30d)

    Returns:
        List of findings with filters applied

    Raises:
        HTTPException: If parameters are invalid or query fails
    """
    try:
        # Validate filters
        if severity:
            _validate_severity(severity)
        if window:
            _validate_window(window)

        # Get database path
        db_path = get_db_path()

        # Initialize dedupe store
        dedupe_store = LeadFindingStore(db_path)

        # Query findings
        findings_objs = dedupe_store.get_recent_findings(
            limit=limit,
            severity=severity.upper() if severity else None,
            window_kind=window
        )

        # Convert to dicts
        findings = [f.to_dict() for f in findings_objs]

        return FindingListResponse(
            findings=findings,
            total=len(findings),
            window=window,
            severity=severity
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/stats", response_model=LeadStatsResponse)
async def get_stats() -> LeadStatsResponse:
    """
    Get Lead Agent statistics

    Returns:
        Statistics about findings:
        - Total findings
        - Breakdown by severity
        - Breakdown by scan window
        - Unlinked findings count (need follow-up tasks)

    Raises:
        HTTPException: If query fails
    """
    try:
        # Get database path
        db_path = get_db_path()

        # Initialize dedupe store
        dedupe_store = LeadFindingStore(db_path)

        # Get statistics
        stats = dedupe_store.get_stats()

        return LeadStatsResponse(
            total_findings=stats["total_findings"],
            by_severity=stats["by_severity"],
            by_window=stats["by_window"],
            unlinked_count=stats["unlinked_count"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats query failed: {str(e)}")
