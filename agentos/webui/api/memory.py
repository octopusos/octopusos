"""
Memory API - Memory search and management

GET /api/memory/search - Search memory
POST /api/memory/upsert - Upsert memory item
GET /api/memory/{id} - Get memory item details
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

router = APIRouter()


class MemoryItem(BaseModel):
    """Memory item model"""
    id: str
    namespace: str
    key: str
    value: str
    source: Optional[str] = None  # task_id or session_id
    source_type: Optional[str] = None  # "task" | "session" | "manual"
    created_at: str
    ttl: Optional[int] = None  # seconds
    metadata: Dict[str, Any] = {}


class UpsertMemoryRequest(BaseModel):
    """Upsert memory request"""
    namespace: str
    key: str
    value: str
    source: Optional[str] = None
    source_type: Optional[str] = None
    ttl: Optional[int] = None
    metadata: Dict[str, Any] = {}


# In-memory store (TODO: integrate with MemoryOS)
_memory: Dict[str, MemoryItem] = {}


@router.get("/search")
async def search_memory(
    q: Optional[str] = Query(None, description="Search query"),
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
) -> List[MemoryItem]:
    """
    Search memory items

    Args:
        q: Search query (matches key or value)
        namespace: Filter by namespace
        limit: Maximum results

    Returns:
        List of memory items
    """
    items = list(_memory.values())

    # Apply filters
    if namespace:
        items = [m for m in items if m.namespace == namespace]
    if q:
        q_lower = q.lower()
        items = [m for m in items if q_lower in m.key.lower() or q_lower in m.value.lower()]

    # Sort by created_at (newest first) and limit
    items = sorted(items, key=lambda m: m.created_at, reverse=True)[:limit]

    return items


@router.post("/upsert")
async def upsert_memory(req: UpsertMemoryRequest) -> MemoryItem:
    """
    Upsert memory item

    Args:
        req: Upsert request

    Returns:
        Created/updated memory item
    """
    # Generate ID from namespace + key
    item_id = f"{req.namespace}:{req.key}"

    item = MemoryItem(
        id=item_id,
        namespace=req.namespace,
        key=req.key,
        value=req.value,
        source=req.source,
        source_type=req.source_type,
        created_at=datetime.now(timezone.utc).isoformat(),
        ttl=req.ttl,
        metadata=req.metadata,
    )

    _memory[item_id] = item

    return item


@router.get("/{item_id}")
async def get_memory(item_id: str) -> MemoryItem:
    """Get memory item by ID"""
    if item_id not in _memory:
        raise HTTPException(status_code=404, detail="Memory item not found")

    return _memory[item_id]
