from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from octopusos.core.storage.paths import component_db_path, ensure_db_exists
from octopusos.core.time import utc_now_ms


@dataclass
class BridgeProfile:
    profile_id: str
    name: str
    provider: str
    bridge_base_url: str
    send_path: str
    webhook_token_ref: Optional[str]
    local_target: Optional[str]
    cloudflare_hostname: Optional[str]
    metadata: Dict[str, Any]
    created_at: int
    updated_at: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "provider": self.provider,
            "bridge_base_url": self.bridge_base_url,
            "send_path": self.send_path,
            "webhook_token_ref": self.webhook_token_ref,
            "local_target": self.local_target,
            "cloudflare_hostname": self.cloudflare_hostname,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class BridgeBinding:
    binding_id: str
    channel_id: str
    profile_id: str
    created_at: int
    updated_at: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "channel_id": self.channel_id,
            "profile_id": self.profile_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class BridgeStore:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS bridge_profiles (
      profile_id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      provider TEXT NOT NULL,
      bridge_base_url TEXT NOT NULL,
      send_path TEXT NOT NULL,
      webhook_token_ref TEXT,
      local_target TEXT,
      cloudflare_hostname TEXT,
      metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS bridge_bindings (
      binding_id TEXT PRIMARY KEY,
      channel_id TEXT NOT NULL UNIQUE,
      profile_id TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL,
      FOREIGN KEY(profile_id) REFERENCES bridge_profiles(profile_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bridge_events (
      event_id TEXT PRIMARY KEY,
      profile_id TEXT,
      channel_id TEXT,
      event_type TEXT NOT NULL,
      payload_json TEXT,
      created_at INTEGER NOT NULL
    );
    """

    def __init__(self, db_path: Optional[str] = None):
        ensure_db_exists("bridgeos")
        self.db_path = db_path or str(component_db_path("bridgeos"))
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(self.SCHEMA)
            conn.commit()

    def create_profile(
        self,
        *,
        name: str,
        provider: str,
        bridge_base_url: str,
        send_path: str,
        webhook_token_ref: Optional[str],
        local_target: Optional[str],
        cloudflare_hostname: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BridgeProfile:
        profile_id = str(uuid.uuid4())
        now = utc_now_ms()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO bridge_profiles(
                  profile_id, name, provider, bridge_base_url, send_path, webhook_token_ref,
                  local_target, cloudflare_hostname, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    name,
                    provider,
                    bridge_base_url,
                    send_path,
                    webhook_token_ref,
                    local_target,
                    cloudflare_hostname,
                    json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_profile(profile_id)  # type: ignore[return-value]

    def update_profile(self, profile_id: str, *, patch: Dict[str, Any]) -> Optional[BridgeProfile]:
        current = self.get_profile(profile_id)
        if not current:
            return None
        allowed = {
            "name",
            "provider",
            "bridge_base_url",
            "send_path",
            "webhook_token_ref",
            "local_target",
            "cloudflare_hostname",
            "metadata",
        }
        fields: List[str] = []
        args: List[Any] = []
        for k, v in (patch or {}).items():
            if k not in allowed:
                continue
            if k == "metadata":
                fields.append("metadata_json = ?")
                args.append(json.dumps(v or {}, ensure_ascii=False, sort_keys=True))
            else:
                fields.append(f"{k} = ?")
                args.append(v)
        if not fields:
            return current
        fields.append("updated_at = ?")
        args.append(utc_now_ms())
        args.append(profile_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE bridge_profiles SET {', '.join(fields)} WHERE profile_id = ?", tuple(args))
            conn.commit()
        return self.get_profile(profile_id)

    def get_profile(self, profile_id: str) -> Optional[BridgeProfile]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM bridge_profiles WHERE profile_id = ?", (profile_id,)).fetchone()
        if not row:
            return None
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except Exception:
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        return BridgeProfile(
            profile_id=row["profile_id"],
            name=row["name"],
            provider=row["provider"],
            bridge_base_url=row["bridge_base_url"],
            send_path=row["send_path"],
            webhook_token_ref=row["webhook_token_ref"],
            local_target=row["local_target"],
            cloudflare_hostname=row["cloudflare_hostname"],
            metadata=metadata,
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    def list_profiles(self) -> List[BridgeProfile]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM bridge_profiles ORDER BY created_at DESC").fetchall()
        out: List[BridgeProfile] = []
        for row in rows:
            try:
                metadata = json.loads(row["metadata_json"] or "{}")
            except Exception:
                metadata = {}
            if not isinstance(metadata, dict):
                metadata = {}
            out.append(
                BridgeProfile(
                    profile_id=row["profile_id"],
                    name=row["name"],
                    provider=row["provider"],
                    bridge_base_url=row["bridge_base_url"],
                    send_path=row["send_path"],
                    webhook_token_ref=row["webhook_token_ref"],
                    local_target=row["local_target"],
                    cloudflare_hostname=row["cloudflare_hostname"],
                    metadata=metadata,
                    created_at=int(row["created_at"]),
                    updated_at=int(row["updated_at"]),
                )
            )
        return out

    def upsert_binding(self, *, channel_id: str, profile_id: str) -> BridgeBinding:
        now = utc_now_ms()
        existing = self.get_binding_by_channel(channel_id)
        with self._connect() as conn:
            if existing:
                conn.execute(
                    "UPDATE bridge_bindings SET profile_id = ?, updated_at = ? WHERE channel_id = ?",
                    (profile_id, now, channel_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO bridge_bindings(binding_id, channel_id, profile_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), channel_id, profile_id, now, now),
                )
            conn.commit()
        return self.get_binding_by_channel(channel_id)  # type: ignore[return-value]

    def get_binding_by_channel(self, channel_id: str) -> Optional[BridgeBinding]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM bridge_bindings WHERE channel_id = ?", (channel_id,)).fetchone()
        if not row:
            return None
        return BridgeBinding(
            binding_id=row["binding_id"],
            channel_id=row["channel_id"],
            profile_id=row["profile_id"],
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    def list_bindings(self) -> List[BridgeBinding]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM bridge_bindings ORDER BY created_at DESC").fetchall()
        return [
            BridgeBinding(
                binding_id=row["binding_id"],
                channel_id=row["channel_id"],
                profile_id=row["profile_id"],
                created_at=int(row["created_at"]),
                updated_at=int(row["updated_at"]),
            )
            for row in rows
        ]

    def append_event(
        self,
        *,
        event_type: str,
        profile_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO bridge_events(event_id, profile_id, channel_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    profile_id,
                    channel_id,
                    event_type,
                    json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
                    utc_now_ms(),
                ),
            )
            conn.commit()
