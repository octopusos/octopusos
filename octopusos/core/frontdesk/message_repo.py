"""Frontdesk message persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from octopusos.core.db import registry_db, SQLiteWriter


def generate_message_id() -> str:
    return f"fdm_{uuid.uuid4().hex}"


@dataclass
class FrontdeskMessageRecord:
    id: str
    role: str
    text: str
    created_at: int
    evidence_refs: List[str]
    meta: Optional[Dict[str, Any]]
    scope: Optional[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "text": self.text,
            "created_at": self.created_at,
            "evidence_refs": self.evidence_refs,
            "meta": self.meta,
            "scope": self.scope,
        }


class FrontdeskMessageRepo:
    """Repository for frontdesk_messages table."""

    def create(self, record: FrontdeskMessageRecord) -> None:
        # Use the same DB path as registry_db (respects OCTOPUSOS_DB_PATH in tests)
        writer = SQLiteWriter(registry_db._get_db_path())

        def _insert(conn):
            conn.execute(
                """
                INSERT INTO frontdesk_messages (
                    id, role, text, created_at, evidence_json, meta_json, scope_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.role,
                    record.text,
                    record.created_at,
                    json.dumps(record.evidence_refs),
                    json.dumps(record.meta) if record.meta is not None else None,
                    json.dumps(record.scope) if record.scope is not None else None,
                ),
            )

        writer.submit(_insert, timeout=5.0)

    def list_recent(self, limit: int = 200) -> List[FrontdeskMessageRecord]:
        rows = registry_db.query_all(
            """
            SELECT id, role, text, created_at, evidence_json, meta_json, scope_json
            FROM frontdesk_messages
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        records: List[FrontdeskMessageRecord] = []
        for row in rows:
            evidence_refs = json.loads(row["evidence_json"]) if row["evidence_json"] else []
            meta = json.loads(row["meta_json"]) if row["meta_json"] else None
            scope = json.loads(row["scope_json"]) if row["scope_json"] else None
            records.append(
                FrontdeskMessageRecord(
                    id=row["id"],
                    role=row["role"],
                    text=row["text"],
                    created_at=row["created_at"],
                    evidence_refs=evidence_refs,
                    meta=meta,
                    scope=scope,
                )
            )

        records.reverse()
        return records
