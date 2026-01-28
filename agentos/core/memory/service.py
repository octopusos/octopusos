"""Memory Service for external memory storage and retrieval."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console

from agentos.core.memory.budgeter import ContextBudget, ContextBudgeter

console = Console()


class MemoryService:
    """External memory service for storing and retrieving agent memories."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize memory service with database connection."""
        if db_path is None:
            db_path = Path.home() / ".agentos" / "store.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def upsert(self, memory_item: dict) -> str:
        """
        Insert or update memory item.

        Args:
            memory_item: MemoryItem dict (must conform to schema)

        Returns:
            memory_id: The ID of the inserted/updated memory
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        memory_id = memory_item.get("id")
        if not memory_id:
            # Generate ID if not provided
            memory_id = f"mem-{uuid.uuid4().hex[:12]}"
            memory_item["id"] = memory_id

        # Set timestamps
        now = datetime.now(timezone.utc).isoformat()
        if "created_at" not in memory_item:
            memory_item["created_at"] = now
        memory_item["updated_at"] = now

        # Extract fields
        scope = memory_item["scope"]
        mem_type = memory_item["type"]
        content = json.dumps(memory_item["content"])
        tags = json.dumps(memory_item.get("tags", []))
        sources = json.dumps(memory_item.get("sources", []))
        confidence = memory_item.get("confidence", 0.5)
        project_id = memory_item.get("project_id")

        # Upsert
        cursor.execute(
            """
            INSERT INTO memory_items (id, scope, type, content, tags, sources, confidence, project_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                scope = excluded.scope,
                type = excluded.type,
                content = excluded.content,
                tags = excluded.tags,
                sources = excluded.sources,
                confidence = excluded.confidence,
                project_id = excluded.project_id,
                updated_at = excluded.updated_at
        """,
            (
                memory_id,
                scope,
                mem_type,
                content,
                tags,
                sources,
                confidence,
                project_id,
                memory_item["created_at"],
                memory_item["updated_at"],
            ),
        )

        conn.commit()
        conn.close()

        return memory_id

    def get(self, memory_id: str) -> Optional[dict]:
        """Get memory item by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM memory_items WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_dict(row)

    def list(
        self,
        scope: Optional[str] = None,
        project_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        mem_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        List memory items with filters.

        Args:
            scope: Filter by scope (global|project|repo|task|agent)
            project_id: Filter by project ID
            tags: Filter by tags (returns items with ANY of these tags)
            mem_type: Filter by memory type
            limit: Maximum results to return

        Returns:
            List of memory items
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM memory_items WHERE 1=1"
        params = []

        if scope:
            query += " AND scope = ?"
            params.append(scope)

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        if mem_type:
            query += " AND type = ?"
            params.append(mem_type)

        if tags:
            # Filter by tags (JSON contains any of the tags)
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            query += " AND (" + " OR ".join(tag_conditions) + ")"

        query += " ORDER BY confidence DESC, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def search(
        self, query: str, scope: Optional[str] = None, limit: int = 20
    ) -> list[dict]:
        """
        Full-text search memories.

        Args:
            query: Search query string
            scope: Optional scope filter
            limit: Maximum results

        Returns:
            List of matching memory items
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # FTS search
        sql = """
            SELECT m.*
            FROM memory_items m
            JOIN memory_fts fts ON m.rowid = fts.rowid
            WHERE memory_fts MATCH ?
        """
        params = [query]

        if scope:
            sql += " AND m.scope = ?"
            params.append(scope)

        sql += " ORDER BY m.confidence DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def build_context(
        self,
        project_id: str,
        agent_type: str,
        task_id: Optional[str] = None,
        confidence_threshold: float = 0.3,
        budget: Optional[ContextBudget] = None,
    ) -> dict:
        """
        Build MemoryPack context for agent execution.

        Args:
            project_id: Target project ID
            agent_type: Target agent type
            task_id: Optional task ID
            confidence_threshold: Minimum confidence score
            budget: Context budget (defaults to ContextBudget())

        Returns:
            MemoryPack dict
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Query memories by scope hierarchy
        scopes = ["global"]
        if project_id:
            scopes.extend(["project", "repo"])
        if task_id:
            scopes.extend(["task"])
        scopes.append("agent")

        memories = []

        for scope in scopes:
            query = """
                SELECT * FROM memory_items
                WHERE scope = ?
                AND confidence >= ?
            """
            params = [scope, confidence_threshold]

            if scope in ["project", "repo", "task", "agent"]:
                query += " AND (project_id = ? OR project_id IS NULL)"
                params.append(project_id)

            query += " ORDER BY confidence DESC, created_at DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            memories.extend([self._row_to_dict(row) for row in rows])

        conn.close()

        # Apply budget trimming
        budgeter = ContextBudgeter(budget=budget)
        trimmed_memories, budget_stats = budgeter.trim_context(memories)

        # Build summary
        by_type = {}
        by_scope = {}
        for mem in trimmed_memories:
            mem_type = mem["type"]
            mem_scope = mem["scope"]
            by_type[mem_type] = by_type.get(mem_type, 0) + 1
            by_scope[mem_scope] = by_scope.get(mem_scope, 0) + 1

        memory_pack = {
            "schema_version": "1.0.0",
            "project_id": project_id,
            "agent_type": agent_type,
            "task_id": task_id,
            "memories": trimmed_memories,
            "summary": {
                "total_memories": len(trimmed_memories),
                "by_type": by_type,
                "by_scope": by_scope,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "confidence_threshold": confidence_threshold,
                "filters_applied": [f"scope in {scopes}", f"confidence >= {confidence_threshold}"],
                "budget": {
                    "max_tokens": budget.max_tokens if budget else 4000,
                    "max_memories": budget.max_memories if budget else 100,
                    "utilized_tokens": budget_stats["total_tokens"],
                    "utilized_memories": budget_stats["total_memories"],
                    "trimmed": budget_stats["trimmed"],
                    "removed_count": budget_stats.get("removed_count", 0)
                }
            },
        }

        return memory_pack

    def delete(self, memory_id: str) -> bool:
        """Delete memory item by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM memory_items WHERE id = ?", (memory_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert database row to MemoryItem dict."""
        return {
            "id": row["id"],
            "scope": row["scope"],
            "type": row["type"],
            "content": json.loads(row["content"]),
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "sources": json.loads(row["sources"]) if row["sources"] else [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "confidence": row["confidence"],
            "project_id": row["project_id"],
        }
