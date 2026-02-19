from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from octopusos.store import get_db


def list_skill_audit_events(*, tenant_id: str, workspace_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    """List SkillOS audit events filtered by tenant/workspace."""
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute(
        """
        SELECT event_type, payload, created_at
        FROM task_audits
        WHERE payload LIKE ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (f"%\"tenant_id\":\"{tenant_id}\"%", max(1, int(limit))),
    ).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row[1]) if row[1] else {}
        except Exception:
            payload = {}
        if payload.get("workspace_id") != workspace_id:
            continue
        out.append(
            {
                "event_type": row[0],
                "payload": payload,
                "created_at": row[2],
            }
        )
    return out
