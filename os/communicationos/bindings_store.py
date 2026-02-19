"""Binding store for CommunicationOS channels -> OctopusOS chat sessions.

This persists per-peer bindings:
- Which chat session ID to use for a given channel/session_lookup_key
- Which model route/provider/model to apply (stored into chat session metadata)

Keying:
- We use SessionRouter's frozen session_lookup_key as the stable identifier for a peer binding.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from octopusos.core.storage.paths import component_db_path
from octopusos.core.time import utc_now_ms


@dataclass
class ChannelBinding:
    binding_id: str
    channel_id: str
    session_lookup_key: str
    session_id: str
    model_route: str
    provider: str
    model: str
    user_key: str
    conversation_key: str
    created_at_ms: int
    updated_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "channel_id": self.channel_id,
            "session_lookup_key": self.session_lookup_key,
            "session_id": self.session_id,
            "model_route": self.model_route,
            "provider": self.provider,
            "model": self.model,
            "user_key": self.user_key,
            "conversation_key": self.conversation_key,
            "created_at_ms": self.created_at_ms,
            "updated_at_ms": self.updated_at_ms,
        }


class ChannelBindingsStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(component_db_path("communicationos"))
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_bindings (
                    binding_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    session_lookup_key TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    model_route TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    user_key TEXT NOT NULL,
                    conversation_key TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL,
                    updated_at_ms INTEGER NOT NULL,
                    UNIQUE(channel_id, session_lookup_key)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_channel_bindings_channel ON channel_bindings(channel_id, updated_at_ms DESC)"
            )
            conn.commit()

    def get(self, *, channel_id: str, session_lookup_key: str) -> Optional[ChannelBinding]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM channel_bindings
                WHERE channel_id = ? AND session_lookup_key = ?
                LIMIT 1
                """,
                (channel_id, session_lookup_key),
            ).fetchone()
            if not row:
                return None
            return ChannelBinding(**dict(row))

    def list_by_channel(self, *, channel_id: str, limit: int = 200) -> List[ChannelBinding]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM channel_bindings
                WHERE channel_id = ?
                ORDER BY updated_at_ms DESC
                LIMIT ?
                """,
                (channel_id, int(limit)),
            ).fetchall()
            return [ChannelBinding(**dict(r)) for r in rows]

    def upsert(
        self,
        *,
        channel_id: str,
        session_lookup_key: str,
        session_id: str,
        model_route: str,
        provider: str,
        model: str,
        user_key: str,
        conversation_key: str,
    ) -> ChannelBinding:
        now = utc_now_ms()
        binding_id = f"cb_{uuid.uuid4().hex[:16]}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO channel_bindings
                (binding_id, channel_id, session_lookup_key, session_id, model_route, provider, model, user_key, conversation_key, created_at_ms, updated_at_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id, session_lookup_key) DO UPDATE SET
                    session_id = excluded.session_id,
                    model_route = excluded.model_route,
                    provider = excluded.provider,
                    model = excluded.model,
                    user_key = excluded.user_key,
                    conversation_key = excluded.conversation_key,
                    updated_at_ms = excluded.updated_at_ms
                """,
                (
                    binding_id,
                    channel_id,
                    session_lookup_key,
                    session_id,
                    str(model_route),
                    str(provider),
                    str(model),
                    str(user_key),
                    str(conversation_key),
                    now,
                    now,
                ),
            )
            conn.commit()

            # Fetch current row (existing binding_id preserved if already existed).
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM channel_bindings WHERE channel_id = ? AND session_lookup_key = ? LIMIT 1",
                (channel_id, session_lookup_key),
            ).fetchone()
            assert row is not None
            return ChannelBinding(**dict(row))

    def update_binding(
        self,
        *,
        binding_id: str,
        model_route: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[ChannelBinding]:
        updates: List[str] = []
        params: List[Any] = []
        if model_route is not None:
            updates.append("model_route = ?")
            params.append(str(model_route))
        if provider is not None:
            updates.append("provider = ?")
            params.append(str(provider))
        if model is not None:
            updates.append("model = ?")
            params.append(str(model))
        if not updates:
            return self.get_by_id(binding_id=binding_id)
        updates.append("updated_at_ms = ?")
        params.append(utc_now_ms())
        params.append(binding_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE channel_bindings SET {', '.join(updates)} WHERE binding_id = ?",
                tuple(params),
            )
            conn.commit()
        return self.get_by_id(binding_id=binding_id)

    def get_by_id(self, *, binding_id: str) -> Optional[ChannelBinding]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM channel_bindings WHERE binding_id = ? LIMIT 1",
                (binding_id,),
            ).fetchone()
            if not row:
                return None
            return ChannelBinding(**dict(row))

