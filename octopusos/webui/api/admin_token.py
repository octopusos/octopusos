"""Admin token validation API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException

from octopusos.core.capabilities.admin_token import validate_admin_token

router = APIRouter(prefix="/api", tags=["admin-token"])


@router.get("/admin/token/validate")
def validate_token(
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    if not admin_token:
        raise HTTPException(status_code=401, detail="Admin token required")
    if not validate_admin_token(admin_token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return {"ok": True, "valid": True, "source": "real"}
