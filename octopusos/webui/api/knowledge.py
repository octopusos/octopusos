"""Knowledge API (optional, feature-gated)."""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter()


def _enabled() -> bool:
    return os.getenv("FEATURE_KNOWLEDGE", "0").strip().lower() in {"1", "true", "yes", "on"}


@router.post("/sources/{source_id}/sync")
def sync_source(source_id: str) -> Dict[str, Any]:
    if not _enabled():
        raise HTTPException(status_code=403, detail="Knowledge feature disabled")
    return {
        "ok": False,
        "data": {
            "source_id": source_id,
            "chunk_count": 0,
            "duration_ms": 0,
            "message": "Feature not implemented",
        },
    }


@router.post("/sources/sync-all")
def sync_all_sources() -> Dict[str, Any]:
    if not _enabled():
        raise HTTPException(status_code=403, detail="Knowledge feature disabled")
    return {"ok": False, "data": {"sources": [], "message": "Feature not implemented"}}


@router.post("/jobs")
def create_job() -> Dict[str, Any]:
    if not _enabled():
        raise HTTPException(status_code=403, detail="Knowledge feature disabled")
    return {"ok": False, "data": {"message": "Feature not implemented"}}


__all__ = ["router"]
