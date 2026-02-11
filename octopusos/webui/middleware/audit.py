"""Audit middleware for best-effort request logging."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from octopusos.core.task.audit_service import TaskAuditService

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """Best-effort audit middleware.

    This middleware never blocks responses on audit failures.
    """

    def __init__(self, app=None, max_audit_seconds: float = 0.05):
        self.app = app
        self.max_audit_seconds = max_audit_seconds

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return response

        task_id = self._extract_task_id(getattr(request.url, "path", ""))
        if not task_id:
            return response

        asyncio.create_task(
            self._record_audit(
                task_id=task_id,
                request=request,
                response=response,
                duration_ms=duration_ms,
            )
        )

        return response

    async def _record_audit(self, task_id: str, request, response, duration_ms: int):
        service = TaskAuditService()
        status = "success" if response.status_code < 400 else "failed"
        payload = {
            "path": getattr(request.url, "path", ""),
            "method": getattr(request, "method", ""),
            "query": dict(getattr(request, "query_params", {}) or {}),
            "duration_ms": duration_ms,
            "status_code": response.status_code,
        }
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    service.record_operation,
                    task_id=task_id,
                    operation="api_request",
                    status=status,
                    error_message=None if status == "success" else "request_failed",
                    payload=payload,
                ),
                timeout=self.max_audit_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("Audit timeout (system busy, audit dropped)")
        except Exception as exc:
            logger.warning(f"Audit failed (best-effort, dropped): {exc}")

    @staticmethod
    def _extract_task_id(path: str) -> Optional[str]:
        if not path:
            return None
        if "/api/tasks/" not in path:
            return None
        try:
            suffix = path.split("/api/tasks/", 1)[1]
            parts = [p for p in suffix.split("/") if p]
            return parts[0] if parts else None
        except Exception:
            return None
