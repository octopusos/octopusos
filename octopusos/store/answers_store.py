"""
Answer Packs Repository (v23 schema)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from octopusos.core.db.conn_scope import db_conn_scope

logger = logging.getLogger(__name__)


class AnswerNotFoundError(Exception):
    """Raised when answer pack is not found."""


class AnswerIntegrityError(Exception):
    """Raised when integrity constraint is violated."""


@dataclass
class AnswerPack:
    """Answer pack data model."""

    id: str
    name: str
    status: str
    items_json: str
    metadata_json: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class AnswerPackLink:
    """Link between answer pack and entity (task/intent)."""

    id: str
    pack_id: str
    entity_type: str
    entity_id: str
    created_at: str


class AnswersRepo:
    """Repository for answer pack management."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def list(
        self,
        status: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[AnswerPack], int]:
        with db_conn_scope(str(self.db_path)) as conn:
            cursor = conn.cursor()

            where_clauses = []
            params: List[str] = []

            if status:
                where_clauses.append("status = ?")
                params.append(status)

            if q:
                where_clauses.append("(name LIKE ?)")
                params.append(f"%{q}%")

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            cursor.execute(f"SELECT COUNT(*) FROM answer_packs {where_sql}", params)
            total = cursor.fetchone()[0]

            cursor.execute(
                f"""
                SELECT id, name, status, items_json, metadata_json, created_at, updated_at
                FROM answer_packs
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            )

            packs = [
                AnswerPack(
                    id=row["id"],
                    name=row["name"],
                    status=row["status"],
                    items_json=row["items_json"],
                    metadata_json=row["metadata_json"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in cursor.fetchall()
            ]

            return packs, total

    def get(self, pack_id: str) -> Optional[AnswerPack]:
        with db_conn_scope(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, status, items_json, metadata_json, created_at, updated_at
                FROM answer_packs
                WHERE id = ?
                """,
                [pack_id],
            )
            row = cursor.fetchone()
            if not row:
                return None
            return AnswerPack(
                id=row["id"],
                name=row["name"],
                status=row["status"],
                items_json=row["items_json"],
                metadata_json=row["metadata_json"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def create(self, pack: AnswerPack) -> AnswerPack:
        now = datetime.now(timezone.utc).isoformat()
        pack_id = pack.id or f"pack_{uuid.uuid4().hex}"
        created_at = pack.created_at or now
        updated_at = pack.updated_at or now

        try:
            with db_conn_scope(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO answer_packs (
                        id, name, status, items_json, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        pack_id,
                        pack.name,
                        pack.status,
                        pack.items_json,
                        pack.metadata_json,
                        created_at,
                        updated_at,
                    ],
                )
                conn.commit()
        except sqlite3.IntegrityError as exc:
            raise AnswerIntegrityError(str(exc)) from exc

        return AnswerPack(
            id=pack_id,
            name=pack.name,
            status=pack.status,
            items_json=pack.items_json,
            metadata_json=pack.metadata_json,
            created_at=created_at,
            updated_at=updated_at,
        )

    def update(self, pack_id: str, items_json: str, metadata_json: Optional[str]) -> AnswerPack:
        now = datetime.now(timezone.utc).isoformat()
        with db_conn_scope(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE answer_packs
                SET items_json = ?, metadata_json = ?, updated_at = ?
                WHERE id = ?
                """,
                [items_json, metadata_json, now, pack_id],
            )
            if cursor.rowcount == 0:
                raise AnswerNotFoundError(f"Answer pack not found: {pack_id}")
            conn.commit()

        updated = self.get(pack_id)
        if not updated:
            raise AnswerNotFoundError(f"Answer pack not found: {pack_id}")
        return updated

    def set_status(self, pack_id: str, status: str) -> AnswerPack:
        now = datetime.now(timezone.utc).isoformat()
        with db_conn_scope(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE answer_packs
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                [status, now, pack_id],
            )
            if cursor.rowcount == 0:
                raise AnswerNotFoundError(f"Answer pack not found: {pack_id}")
            conn.commit()

        updated = self.get(pack_id)
        if not updated:
            raise AnswerNotFoundError(f"Answer pack not found: {pack_id}")
        return updated

    def link(self, pack_id: str, entity_type: str, entity_id: str) -> AnswerPackLink:
        link_id = f"apl_{uuid.uuid4().hex}"
        created_at = datetime.now(timezone.utc).isoformat()
        try:
            with db_conn_scope(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO answer_pack_links (id, pack_id, entity_type, entity_id, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [link_id, pack_id, entity_type, entity_id, created_at],
                )
                conn.commit()
        except sqlite3.IntegrityError as exc:
            raise AnswerIntegrityError(str(exc)) from exc

        return AnswerPackLink(
            id=link_id,
            pack_id=pack_id,
            entity_type=entity_type,
            entity_id=entity_id,
            created_at=created_at,
        )

    def list_links(self, pack_id: str) -> List[AnswerPackLink]:
        with db_conn_scope(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, pack_id, entity_type, entity_id, created_at
                FROM answer_pack_links
                WHERE pack_id = ?
                ORDER BY created_at ASC
                """,
                [pack_id],
            )
            return [
                AnswerPackLink(
                    id=row["id"],
                    pack_id=row["pack_id"],
                    entity_type=row["entity_type"],
                    entity_id=row["entity_id"],
                    created_at=row["created_at"],
                )
                for row in cursor.fetchall()
            ]
