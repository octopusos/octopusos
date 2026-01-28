"""
Content Store - DAO layer for content_items table

Provides CRUD operations for content lifecycle management (agents, workflows, skills, tools).
Uses v23 schema with simplified single-table design (content_items).

Design principles:
1. All write operations use transactions
2. set_active() is atomic: deactivates old version and activates new version
3. ISO 8601 timestamps (YYYY-MM-DDTHH:MM:SSZ)
4. Error handling: IntegrityError -> 409, NotFound -> 404

Created for Agent-DB-Content integration
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from agentos.store.constants import CONTENT_TABLE


class ContentNotFoundError(Exception):
    """Raised when content item is not found"""
    pass


class ContentIntegrityError(Exception):
    """Raised when database integrity constraint is violated"""
    pass


@dataclass
class ContentItem:
    """Content item data model"""
    id: str
    content_type: str  # agent, workflow, skill, tool
    name: str
    version: str
    status: str  # draft, active, deprecated, frozen
    source_uri: Optional[str] = None
    metadata_json: Optional[str] = None
    release_notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ContentRepo:
    """Repository for content_items table"""

    def __init__(self, db_path: str | Path):
        """Initialize repository

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = str(db_path)

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list(
        self,
        content_type: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[ContentItem], int]:
        """List content items with filtering

        Args:
            content_type: Filter by content type
            status: Filter by status
            q: Search query (searches name and release_notes)
            limit: Page size
            offset: Page offset

        Returns:
            Tuple of (items, total_count)
        """
        conn = self._get_conn()

        # Build query
        where_clauses = []
        params = []

        if content_type:
            where_clauses.append("content_type = ?")
            params.append(content_type)

        if status:
            where_clauses.append("status = ?")
            params.append(status)

        if q:
            where_clauses.append("(name LIKE ? OR release_notes LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM {CONTENT_TABLE}
            WHERE {where_sql}
        """
        total = conn.execute(count_query, params).fetchone()["total"]

        # Get items
        query = f"""
            SELECT *
            FROM {CONTENT_TABLE}
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        items = [self._row_to_item(dict(row)) for row in rows]
        conn.close()

        return items, total

    def get(self, item_id: str) -> Optional[ContentItem]:
        """Get content item by ID

        Args:
            item_id: Content ID

        Returns:
            ContentItem or None if not found
        """
        conn = self._get_conn()

        query = f"SELECT * FROM {CONTENT_TABLE} WHERE id = ?"
        cursor = conn.execute(query, [item_id])
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_item(dict(row))
        return None

    def create(self, item: ContentItem) -> ContentItem:
        """Create new content item

        Args:
            item: ContentItem to create

        Returns:
            Created ContentItem

        Raises:
            ContentIntegrityError: If duplicate (type, name, version) exists
        """
        import uuid

        conn = self._get_conn()

        # Auto-generate ID if empty
        item_id = item.id if item.id else f"content-{uuid.uuid4().hex[:12]}"

        now = datetime.now(timezone.utc).isoformat() + "Z"

        try:
            conn.execute(
                f"""
                INSERT INTO {CONTENT_TABLE} (
                    id, content_type, name, version,
                    status, source_uri, metadata_json, release_notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    item_id,
                    item.content_type,
                    item.name,
                    item.version,
                    item.status,
                    item.source_uri,
                    item.metadata_json or "{}",
                    item.release_notes or "",
                    now,
                    now
                ]
            )

            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.close()
            raise ContentIntegrityError(f"Duplicate content: {item.content_type}/{item.name}/{item.version}") from e

        conn.close()

        return self.get(item_id)

    def update_status(self, item_id: str, new_status: str) -> ContentItem:
        """Update content status

        Args:
            item_id: Content ID
            new_status: New status (draft/active/deprecated/frozen)

        Returns:
            Updated ContentItem

        Raises:
            ContentNotFoundError: If content item not found
        """
        conn = self._get_conn()

        # Check if exists
        cursor = conn.execute(f"SELECT id FROM {CONTENT_TABLE} WHERE id = ?", [item_id])
        if not cursor.fetchone():
            conn.close()
            raise ContentNotFoundError(f"Content item not found: {item_id}")

        now = datetime.now(timezone.utc).isoformat() + "Z"

        conn.execute(
            f"""
            UPDATE {CONTENT_TABLE}
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            [new_status, now, item_id]
        )

        conn.commit()
        conn.close()

        return self.get(item_id)

    def set_active(self, content_type: str, name: str, version: str) -> ContentItem:
        """Activate a specific version (transaction-safe)

        This method:
        1. Finds the content by type, name, and version
        2. Deprecates any currently active version of same type+name
        3. Activates the specified version
        4. Updates timestamp

        Args:
            content_type: Content type
            name: Content name
            version: Version number to activate

        Returns:
            Updated ContentItem

        Raises:
            ValueError: If content or version not found
        """
        conn = self._get_conn()

        try:
            conn.execute("BEGIN TRANSACTION")

            # Find content to activate
            cursor = conn.execute(
                f"""
                SELECT id
                FROM {CONTENT_TABLE}
                WHERE content_type = ? AND name = ? AND version = ?
                """,
                [content_type, name, version]
            )
            row = cursor.fetchone()

            if not row:
                raise ContentNotFoundError(f"Content not found: {content_type}/{name}/{version}")

            content_id = row["id"]

            # Check if content is frozen (cannot be activated)
            cursor2 = conn.execute(
                f"SELECT status FROM {CONTENT_TABLE} WHERE id = ?",
                [content_id]
            )
            row2 = cursor2.fetchone()
            if row2 and row2["status"] == "frozen":
                raise ContentIntegrityError(f"Cannot activate frozen content: {content_type}/{name}/{version}")

            now = datetime.now(timezone.utc).isoformat() + "Z"

            # Deprecate other active content with same type/name
            conn.execute(
                f"""
                UPDATE {CONTENT_TABLE}
                SET status = 'deprecated', updated_at = ?
                WHERE content_type = ? AND name = ? AND status = 'active' AND id != ?
                """,
                [now, content_type, name, content_id]
            )

            # Activate target version
            conn.execute(
                f"""
                UPDATE {CONTENT_TABLE}
                SET status = 'active', updated_at = ?
                WHERE id = ?
                """,
                [now, content_id]
            )

            conn.commit()

            result = self.get(content_id)
            conn.close()
            return result

        except Exception as e:
            conn.rollback()
            conn.close()
            raise

    def _row_to_item(self, row: dict) -> ContentItem:
        """Convert database row to ContentItem"""
        return ContentItem(
            id=row["id"],
            content_type=row["content_type"],
            name=row["name"],
            version=row["version"],
            status=row["status"],
            source_uri=row.get("source_uri"),
            metadata_json=row.get("metadata_json"),
            release_notes=row.get("release_notes"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )
