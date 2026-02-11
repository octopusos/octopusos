"""Twilio Voice API (optional, feature-gated)."""

from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/voice/twilio", tags=["voice"])


def _enabled() -> bool:
    return os.getenv("FEATURE_VOICE", "0").strip().lower() in {"1", "true", "yes", "on"}


@router.post("/inbound")
def inbound():
    if not _enabled():
        raise HTTPException(status_code=403, detail="Voice feature disabled")
    return {"ok": False, "message": "Feature not implemented"}


__all__ = ["router"]
