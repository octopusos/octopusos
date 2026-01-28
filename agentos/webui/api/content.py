"""Content API - Content lifecycle management endpoints

Provides REST API for managing content (agents/workflows/skills/tools) lifecycle:
- List and filter content
- Register new content
- Activate/deprecate/freeze content (admin-only)

All write operations require admin token validation.

Created for Agent-DB-Content integration
"""

import json
import logging
from fastapi import APIRouter, HTTPException, Query, Header, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from agentos.core.content.lifecycle_service import (
    ContentLifecycleService,
    ContentNotFoundError,
    ContentStateError
)
from agentos.store.content_store import ContentRepo
from agentos.store import get_db_path
from agentos.webui.api.contracts import success, error, error_response, ReasonCode, validate_admin_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content", tags=["content"])


# ========================================
# Service Initialization
# ========================================

def get_content_service() -> ContentLifecycleService:
    """Get content service instance"""
    db_path = get_db_path()
    repo = ContentRepo(db_path)
    return ContentLifecycleService(repo)


# ========================================
# Endpoints
# ========================================

# IMPORTANT: Specific routes (stats, mode) must come BEFORE the catch-all /{content_id} route
# Otherwise FastAPI will match "stats" and "mode" as content_id values

@router.get("/stats")
async def get_content_stats(
    type: Optional[str] = None
):
    """Get content statistics

    Query params:
    - type: Filter by content_type (optional)

    Returns:
    {
        "ok": true,
        "data": {
            "total": 42,
            "by_type": {
                "agent": 15,
                "workflow": 10,
                "skill": 12,
                "tool": 5
            },
            "by_status": {
                "draft": 8,
                "active": 20,
                "deprecated": 10,
                "frozen": 4
            }
        }
    }
    """
    try:
        service = get_content_service()

        # Get all items (or filtered by type)
        items, total = service.list_items(
            content_type=type,
            limit=10000  # Get all for stats
        )

        # Calculate stats
        by_type = {}
        by_status = {}

        for item in items:
            # Count by type
            if item.content_type not in by_type:
                by_type[item.content_type] = 0
            by_type[item.content_type] += 1

            # Count by status
            if item.status not in by_status:
                by_status[item.status] = 0
            by_status[item.status] += 1

        return success({
            "total": total,
            "by_type": by_type,
            "by_status": by_status
        })

    except Exception as e:
        logger.error(f"Failed to get content stats: {e}", exc_info=True)
        return error_response(
            f"Failed to retrieve stats: {str(e)}",
            reason_code=ReasonCode.INTERNAL_ERROR,
            hint="Check server logs for details"
        )


@router.get("/mode")
async def get_content_mode():
    """Get current content mode (development vs production)

    Returns:
    {
        "ok": true,
        "data": {
            "mode": "local",
            "database": "real",
            "features": {
                "mock_data": false,
                "admin_required": true
            }
        }
    }
    """
    import os

    env = os.getenv("AGENTOS_ENV", "development")

    # For testing, we always return "local" mode
    # Production deployment can override this behavior
    mode = "local" if env != "production" else "production"

    return success({
        "mode": mode,
        "database": "real",
        "features": {
            "mock_data": False,  # No more mock data
            "admin_required": True
        }
    })


@router.get("")
async def list_content_items(
    type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List content items

    Query params:
    - type: Filter by content_type (agent/workflow/skill/tool)
    - status: Filter by status (draft/active/deprecated/frozen)
    - search: Search in name/tags
    - limit: Page size (default 20)
    - offset: Page offset (default 0)

    Returns:
    {
        "ok": true,
        "data": {
            "items": [...],
            "total": 42,
            "limit": 20,
            "offset": 0
        }
    }
    """
    try:
        service = get_content_service()
        items, total = service.list_items(
            content_type=type,
            status=status,
            search=search,
            limit=limit,
            offset=offset
        )

        # Convert ContentItem dataclass to dict
        items_data = [
            {
                "id": item.id,
                "name": item.name,
                "type": item.content_type,
                "version": item.version,
                "status": item.status,
                "source_uri": item.source_uri,
                "metadata": json.loads(item.metadata_json) if item.metadata_json else {},
                "release_notes": item.release_notes,
                "created_at": item.created_at,
                "updated_at": item.updated_at
            }
            for item in items
        ]

        return success({
            "items": items_data,
            "total": total,
            "limit": limit,
            "offset": offset
        })

    except Exception as e:
        logger.error(f"Failed to list content items: {e}", exc_info=True)
        return error_response(
            f"Failed to list content: {str(e)}",
            reason_code=ReasonCode.INTERNAL_ERROR,
            hint="Check server logs for details"
        )


@router.get("/{content_id}")
async def get_content_item(content_id: str):
    """Get single content item by ID

    Returns:
    {
        "ok": true,
        "data": {
            "id": "...",
            "name": "...",
            "type": "agent",
            "version": "1.0.0",
            "status": "active",
            ...
        }
    }
    """
    try:
        service = get_content_service()
        item = service.get_item(content_id)

        return success({
            "id": item.id,
            "name": item.name,
            "type": item.content_type,
            "version": item.version,
            "status": item.status,
            "source_uri": item.source_uri,
            "metadata": json.loads(item.metadata_json) if item.metadata_json else {},
            "release_notes": item.release_notes,
            "created_at": item.created_at,
            "updated_at": item.updated_at
        })

    except ContentNotFoundError as e:
        raise error(
            str(e),
            reason_code=ReasonCode.NOT_FOUND,
            hint="Check the content ID and try again",
            http_status=404
        )
    except Exception as e:
        logger.error(f"Failed to get content item {content_id}: {e}", exc_info=True)
        raise error(
            f"Failed to retrieve content: {str(e)}",
            reason_code=ReasonCode.INTERNAL_ERROR
        )


@router.post("")
async def register_content(
    request: dict,
    _: bool = Depends(validate_admin_token)
):
    """Register new content item (requires admin token)

    Body:
    {
        "type": "agent",
        "name": "My Agent",
        "version": "1.0.0",
        "source_uri": "https://...",
        "metadata": {...},
        "release_notes": "Initial release"
    }

    Returns:
    {
        "ok": true,
        "data": {
            "id": "...",
            "name": "My Agent",
            "status": "draft",
            "created_at": "..."
        }
    }
    """
    try:
        service = get_content_service()

        item = service.register(
            content_type=request["type"],
            name=request["name"],
            version=request["version"],
            source_uri=request.get("source_uri"),
            metadata=request.get("metadata"),
            release_notes=request.get("release_notes")
        )

        return success({
            "id": item.id,
            "name": item.name,
            "status": item.status,
            "created_at": item.created_at
        })

    except KeyError as e:
        raise error(
            f"Missing required field: {e}",
            reason_code=ReasonCode.INVALID_INPUT,
            hint="Provide type, name, and version",
            http_status=400
        )
    except Exception as e:
        logger.error(f"Failed to register content: {e}", exc_info=True)
        raise error(
            f"Failed to register: {str(e)}",
            reason_code=ReasonCode.INTERNAL_ERROR
        )


@router.patch("/{content_id}/activate")
async def activate_content(
    content_id: str,
    confirm: bool = False,
    _: bool = Depends(validate_admin_token)
):
    """Activate content version (requires admin + confirmation)

    Query params:
    - confirm: Must be true to confirm activation

    Returns:
    {
        "ok": true,
        "data": {
            "id": "...",
            "status": "active",
            "message": "Content activated"
        }
    }
    """
    if not confirm:
        raise error(
            "Confirmation required",
            reason_code=ReasonCode.INVALID_INPUT,
            hint="Add confirm=true parameter to confirm activation",
            http_status=400
        )

    try:
        service = get_content_service()
        item = service.activate(content_id)

        return success({
            "id": item.id,
            "status": item.status,
            "message": f"Content {item.name} v{item.version} activated"
        })

    except ContentNotFoundError as e:
        raise error(str(e), reason_code=ReasonCode.NOT_FOUND, http_status=404)

    except ContentStateError as e:
        raise error(
            str(e),
            reason_code=ReasonCode.CONFLICT,
            hint="Check current status and state transition rules",
            http_status=409
        )

    except Exception as e:
        logger.error(f"Failed to activate {content_id}: {e}", exc_info=True)
        raise error(
            f"Activation failed: {str(e)}",
            reason_code=ReasonCode.INTERNAL_ERROR
        )


@router.patch("/{content_id}/deprecate")
async def deprecate_content(
    content_id: str,
    confirm: bool = False,
    _: bool = Depends(validate_admin_token)
):
    """Deprecate content version (requires admin + confirmation)

    Query params:
    - confirm: Must be true to confirm deprecation

    Returns:
    {
        "ok": true,
        "data": {
            "id": "...",
            "status": "deprecated",
            "message": "Content deprecated"
        }
    }
    """
    if not confirm:
        raise error(
            "Confirmation required",
            reason_code=ReasonCode.INVALID_INPUT,
            hint="Add confirm=true parameter to confirm deprecation",
            http_status=400
        )

    try:
        service = get_content_service()
        item = service.deprecate(content_id)

        return success({
            "id": item.id,
            "status": item.status,
            "message": f"Content {item.name} v{item.version} deprecated"
        })

    except ContentNotFoundError as e:
        raise error(str(e), reason_code=ReasonCode.NOT_FOUND, http_status=404)

    except ContentStateError as e:
        raise error(
            str(e),
            reason_code=ReasonCode.CONFLICT,
            hint="Check current status and state transition rules",
            http_status=409
        )

    except Exception as e:
        logger.error(f"Failed to deprecate {content_id}: {e}", exc_info=True)
        raise error(
            f"Deprecation failed: {str(e)}",
            reason_code=ReasonCode.INTERNAL_ERROR
        )


@router.patch("/{content_id}/freeze")
async def freeze_content(
    content_id: str,
    confirm: bool = False,
    _: bool = Depends(validate_admin_token)
):
    """Freeze content version (requires admin + confirmation)

    Query params:
    - confirm: Must be true to confirm freeze

    Returns:
    {
        "ok": true,
        "data": {
            "id": "...",
            "status": "frozen",
            "message": "Content frozen"
        }
    }
    """
    if not confirm:
        raise error(
            "Confirmation required",
            reason_code=ReasonCode.INVALID_INPUT,
            hint="Add confirm=true parameter to confirm freeze",
            http_status=400
        )

    try:
        service = get_content_service()
        item = service.freeze(content_id)

        return success({
            "id": item.id,
            "status": item.status,
            "message": f"Content {item.name} v{item.version} frozen"
        })

    except ContentNotFoundError as e:
        raise error(str(e), reason_code=ReasonCode.NOT_FOUND, http_status=404)

    except ContentStateError as e:
        raise error(
            str(e),
            reason_code=ReasonCode.CONFLICT,
            hint="Check current status and state transition rules",
            http_status=409
        )

    except Exception as e:
        logger.error(f"Failed to freeze {content_id}: {e}", exc_info=True)
        raise error(
            f"Freeze failed: {str(e)}",
            reason_code=ReasonCode.INTERNAL_ERROR
        )

