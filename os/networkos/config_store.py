"""NetworkOS config store (M2 Part B).

Hard constraints:
- Only non-sensitive config is persisted (KV).
- Secrets (Cloudflare API token, service token secret, etc.) must remain in SecretStore.
- Resolve priority is fixed: env > db > default.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from octopusos.core.storage.migrations import ensure_component_migrations
from octopusos.core.storage.paths import ensure_db_exists, component_db_path
from octopusos.core.time import utc_now_ms


ENV_MAP: Dict[str, str] = {
    # Cloudflare (non-secret)
    "CF_ACCOUNT_ID": "network.cloudflare.account_id",
    "CF_ZONE_ID": "network.cloudflare.zone_id",
    "CF_TEAM_NAME": "network.cloudflare.team_name",
    "CF_PROTECTED_HOSTNAME": "network.cloudflare.hostname",
    "CF_TUNNEL_NAME": "network.cloudflare.tunnel_name",
    "CF_APP_NAME": "network.cloudflare.app_name",
    "NETWORKOS_CLOUDFLARE_HOSTNAME": "network.cloudflare.hostname",
    "OCTOPUSOS_CLOUDFLARE_HOSTNAME": "network.cloudflare.hostname",
    "NETWORKOS_CLOUDFLARE_ENFORCE_ACCESS": "network.cloudflare.enforce_access",
    "NETWORKOS_CLOUDFLARE_HEALTH_PATH": "network.cloudflare.health_path",
}


DEFAULTS: Dict[str, Any] = {
    "network.cloudflare.enforce_access": True,
    "network.cloudflare.health_path": "/api/health",
    "network.cloudflare.tunnel_name": "octopusos",
    "network.cloudflare.app_name": "octopusos-access",
}


ALLOWED_KEYS: set[str] = {
    "network.cloudflare.hostname",
    "network.cloudflare.account_id",
    "network.cloudflare.zone_id",
    "network.cloudflare.team_name",
    "network.cloudflare.enforce_access",
    "network.cloudflare.health_path",
    "network.cloudflare.tunnel_name",
    "network.cloudflare.app_name",
    "network.cloudflare.service_token_id",
}


def _parse_bool(v: str) -> Optional[bool]:
    s = str(v or "").strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off"}:
        return False
    return None


def _normalize_value(key: str, value: Any) -> Any:
    if key.endswith(".enforce_access"):
        if isinstance(value, bool):
            return value
        b = _parse_bool(str(value))
        return bool(b) if b is not None else True
    return value


@dataclass(frozen=True)
class ResolvedValue:
    key: str
    value: Any
    source: str  # env|db|default|missing

    def to_dict(self) -> Dict[str, Any]:
        return {"key": self.key, "value": self.value, "source": self.source}


class NetworkConfigStore:
    def __init__(self, db_path: Optional[str] = None):
        ensure_db_exists("networkos")
        ensure_component_migrations("networkos")
        self.db_path = str(db_path or component_db_path("networkos"))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_db_value(self, key: str) -> Optional[Any]:
        key = str(key or "").strip()
        if not key:
            return None
        with self._connect() as conn:
            row = conn.execute("SELECT value_json FROM network_config_kv WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        try:
            return json.loads(str(row["value_json"] or "null"))
        except Exception:
            return None

    def set_db_value(self, *, key: str, value: Any, updated_by: str | None = None) -> None:
        key = str(key or "").strip()
        if key not in ALLOWED_KEYS:
            raise ValueError(f"key_not_allowed:{key}")
        now = utc_now_ms()
        safe_value = _normalize_value(key, value)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO network_config_kv(key, value_json, updated_at, updated_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at, updated_by=excluded.updated_by
                """,
                (key, json.dumps(safe_value, ensure_ascii=False, sort_keys=True), int(now), updated_by),
            )
            conn.commit()

    def set_many(self, *, items: Dict[str, Any], updated_by: str | None = None) -> None:
        for k, v in (items or {}).items():
            if k in ALLOWED_KEYS:
                self.set_db_value(key=k, value=v, updated_by=updated_by)

    def resolve(self, key: str, default: Any = None) -> ResolvedValue:
        key = str(key or "").strip()
        if not key:
            return ResolvedValue(key="", value=default, source="missing")

        # env
        for env_name, mapped in ENV_MAP.items():
            if mapped != key:
                continue
            raw = os.getenv(env_name)
            if raw is None:
                continue
            if key.endswith(".enforce_access"):
                b = _parse_bool(raw)
                if b is not None:
                    return ResolvedValue(key=key, value=b, source="env")
            return ResolvedValue(key=key, value=str(raw).strip(), source="env")

        # db
        db_v = self.get_db_value(key)
        if db_v is not None:
            return ResolvedValue(key=key, value=_normalize_value(key, db_v), source="db")

        # default
        if key in DEFAULTS:
            return ResolvedValue(key=key, value=_normalize_value(key, DEFAULTS[key]), source="default")
        return ResolvedValue(key=key, value=default, source="missing")

    def resolve_many(self, keys: Tuple[str, ...]) -> Dict[str, ResolvedValue]:
        return {k: self.resolve(k) for k in keys}

    def resolve_cloudflare_config(self) -> Dict[str, ResolvedValue]:
        keys = (
            "network.cloudflare.hostname",
            "network.cloudflare.account_id",
            "network.cloudflare.zone_id",
            "network.cloudflare.team_name",
            "network.cloudflare.enforce_access",
            "network.cloudflare.health_path",
            "network.cloudflare.tunnel_name",
            "network.cloudflare.app_name",
            "network.cloudflare.service_token_id",
        )
        return self.resolve_many(keys)
