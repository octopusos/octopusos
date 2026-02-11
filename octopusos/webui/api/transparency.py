from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import Response

from octopusos.core.work.transparency_bundle import build_transparency_bundle


router = APIRouter(tags=["transparency"])


@router.get("/api/transparency/export")
async def export_transparency_bundle(
    limit: int = Query(default=50, ge=1, le=500),
) -> Response:
    bundle = build_transparency_bundle(limit=int(limit))
    headers = {
        "Content-Disposition": f'attachment; filename="{bundle.filename}"',
        "Cache-Control": "no-store",
    }
    return Response(content=bundle.data, media_type=bundle.content_type, headers=headers)

