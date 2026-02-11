"""MCP marketplace APIs backed by real MCP config persistence."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from octopusos.core.capabilities.admin_token import validate_admin_token
from octopusos.core.mcp.marketplace_service import (
    attach_package,
    get_governance_preview,
    get_package_detail,
    list_catalog,
    uninstall_package,
)
from octopusos.core.mcp.marketplace_registry import MCPMarketplaceRegistry

router = APIRouter(prefix="/api", tags=["mcp-marketplace"])
_marketplace_registry: Optional[MCPMarketplaceRegistry] = None


def _get_registry() -> MCPMarketplaceRegistry:
    global _marketplace_registry
    if _marketplace_registry is None:
        _marketplace_registry = MCPMarketplaceRegistry()
    else:
        # Best-effort reload during local dev / iterative UI work.
        # Avoids needing a restart when data/mcp_registry.yaml changes.
        try:
            _marketplace_registry.maybe_reload()
        except Exception:
            pass
    return _marketplace_registry


def _require_admin_token(token: Optional[str]) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="Admin token required")
    if not validate_admin_token(token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return "admin"


class AttachRequest(BaseModel):
    package_id: str = Field(..., description="Marketplace package ID")
    override_trust_tier: Optional[str] = Field(default=None)
    config: Dict[str, Any] = Field(default_factory=dict)


@router.get("/mcp/marketplace/catalog")
def get_mcp_catalog(
    connected_only: bool = Query(default=False),
    tag: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    data = list_catalog(
        connected_only=connected_only,
        tag=tag,
        search=search,
        registry=_get_registry(),
    )
    return {"packages": data["catalog"]}


@router.get("/mcp/marketplace/packages")
def list_mcp_packages(
    connected_only: bool = Query(default=False),
    tag: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    data = list_catalog(
        connected_only=connected_only,
        tag=tag,
        search=search,
        registry=_get_registry(),
    )
    return {"packages": data["packages"], "total": data["total"], "source": "real"}


@router.get("/mcp/marketplace/packages/{package_id:path}")
def get_mcp_package(package_id: str) -> Dict[str, Any]:
    try:
        detail = get_package_detail(package_id, registry=_get_registry())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "data": detail, "source": "real"}


@router.get("/mcp/marketplace/governance-preview/{package_id:path}")
def get_mcp_preview(package_id: str) -> Dict[str, Any]:
    try:
        preview = get_governance_preview(package_id, registry=_get_registry())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "data": preview, "source": "real"}


@router.post("/mcp/marketplace/attach")
def attach_mcp_package(
    payload: AttachRequest,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin_token(admin_token)
    config = payload.config or {}
    profile = str(config.get("profile") or "default")
    region = config.get("region")

    try:
        result = attach_package(
            package_id=payload.package_id,
            profile=profile,
            region=str(region) if region else None,
            override_trust_tier=payload.override_trust_tier,
            custom_config=config.get("connection") if isinstance(config.get("connection"), dict) else None,
            registry=_get_registry(),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True, "data": result, "source": "real"}


def _uninstall_package_handler(
    package_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin_token(admin_token)
    result = uninstall_package(package_id)
    return {
        "ok": True,
        "data": {
            "audit_id": result["audit_id"],
            "warnings": [] if result["removed_server_ids"] else ["No matching attached server found."],
            "removed_server_ids": result["removed_server_ids"],
        },
        "source": "real",
    }


@router.delete("/mcp/marketplace/packages/{package_id:path}")
def uninstall_mcp_package_canonical(
    package_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    response = _uninstall_package_handler(package_id=package_id, admin_token=admin_token)
    response["canonical"] = f"/api/mcp/marketplace/packages/{package_id}"
    return response


@router.delete(
    "/communicationos/mcp/packages/{package_id}/uninstall",
    deprecated=True,
    summary="Uninstall MCP package (Deprecated Alias)",
    description="Deprecated alias. Use DELETE /api/mcp/marketplace/packages/{package_id}.",
)
def uninstall_mcp_package_alias(
    package_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    response = _uninstall_package_handler(package_id=package_id, admin_token=admin_token)
    response["deprecated"] = True
    response["canonical"] = f"/api/mcp/marketplace/packages/{package_id}"
    return response
