"""NetworkOS capability request store (isolated audit).

Note: This is separate from CommunicationOS message_audit by design.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from octopusos.core.storage.migrations import ensure_component_migrations
from octopusos.core.storage.paths import ensure_db_exists, resolve_component_db_path
from octopusos.core.time import utc_now_ms


@dataclass
class CapabilityRequestRow:
    id: str
    capability: str
    params: Dict[str, Any]
    requested_by: str
    decision: str
    decision_reason: str
    status: str
    created_at: int
    updated_at: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "capability": self.capability,
            "params": self.params,
            "requested_by": self.requested_by,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class NetworkCapabilityStore:
    def __init__(self, db_path: Optional[str] = None):
        canonical = resolve_component_db_path("networkos", db_path)
        ensure_db_exists("networkos")
        ensure_component_migrations("networkos")
        self.db_path = str(canonical)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_request(
        self,
        *,
        capability: str,
        params: Dict[str, Any],
        requested_by: str,
        decision: str,
        decision_reason: str,
        status: str,
    ) -> CapabilityRequestRow:
        rid = str(uuid.uuid4())
        now = utc_now_ms()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO network_capability_requests
                (id, capability, params_json, requested_by, decision, decision_reason, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    capability,
                    json.dumps(params or {}, ensure_ascii=False, sort_keys=True),
                    requested_by,
                    decision,
                    decision_reason,
                    status,
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO network_audit_log(request_id, event_type, metadata_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    rid,
                    "REQUESTED",
                    json.dumps(
                        {"capability": capability, "requested_by": requested_by, "decision": decision},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    now,
                ),
            )
            conn.commit()
        return self.get_request(rid)  # type: ignore[return-value]

    def get_request(self, request_id: str) -> Optional[CapabilityRequestRow]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM network_capability_requests WHERE id = ?",
                (str(request_id),),
            ).fetchone()
        if not row:
            return None
        params = {}
        try:
            params = json.loads(row["params_json"] or "{}")
        except Exception:
            params = {}
        return CapabilityRequestRow(
            id=row["id"],
            capability=row["capability"],
            params=params if isinstance(params, dict) else {},
            requested_by=row["requested_by"],
            decision=row["decision"],
            decision_reason=row["decision_reason"],
            status=row["status"],
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    def list_requests(self, *, limit: int = 200) -> List[CapabilityRequestRow]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM network_capability_requests ORDER BY updated_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        out: List[CapabilityRequestRow] = []
        for r in rows:
            params = {}
            try:
                params = json.loads(r["params_json"] or "{}")
            except Exception:
                params = {}
            out.append(
                CapabilityRequestRow(
                    id=r["id"],
                    capability=r["capability"],
                    params=params if isinstance(params, dict) else {},
                    requested_by=r["requested_by"],
                    decision=r["decision"],
                    decision_reason=r["decision_reason"],
                    status=r["status"],
                    created_at=int(r["created_at"]),
                    updated_at=int(r["updated_at"]),
                )
            )
        return out

    def append_audit(self, *, request_id: str, event_type: str, metadata: Dict[str, Any]) -> None:
        now = utc_now_ms()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO network_audit_log(request_id, event_type, metadata_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(request_id), str(event_type), json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True), now),
            )
            conn.commit()

    def update_request_status(
        self,
        *,
        request_id: str,
        status: str,
        decision: Optional[str] = None,
        decision_reason: Optional[str] = None,
    ) -> Optional[CapabilityRequestRow]:
        now = utc_now_ms()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM network_capability_requests WHERE id = ?",
                (str(request_id),),
            ).fetchone()
            if not row:
                return None
            fields = ["status = ?", "updated_at = ?"]
            args: List[Any] = [str(status), now]
            if decision is not None:
                fields.append("decision = ?")
                args.append(str(decision))
            if decision_reason is not None:
                fields.append("decision_reason = ?")
                args.append(str(decision_reason))
            args.append(str(request_id))
            conn.execute(f"UPDATE network_capability_requests SET {', '.join(fields)} WHERE id = ?", tuple(args))
            conn.commit()
        return self.get_request(request_id)

    def list_audit(self, *, request_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, request_id, event_type, metadata_json, created_at
                FROM network_audit_log
                WHERE request_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (str(request_id), int(limit)),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            meta = {}
            try:
                meta = json.loads(r["metadata_json"] or "{}")
            except Exception:
                meta = {}
            out.append(
                {
                    "id": int(r["id"]),
                    "request_id": r["request_id"],
                    "event_type": r["event_type"],
                    "metadata": meta if isinstance(meta, dict) else {},
                    "created_at": int(r["created_at"]),
                }
            )
        return out

