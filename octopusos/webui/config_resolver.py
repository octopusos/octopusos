"""Unified config resolver with cache and source attribution."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from octopusos.webui.config_schema import default_value_for_key
from octopusos.webui.config_store import get_config_store


ENV_MAP: Dict[str, str] = {
    "calls.enabled": "OCTOPUSOS_CALLS_ENABLED",
    "calls.provider": "OCTOPUSOS_CALLS_PROVIDER",
    "calls.webhook_base_url": "OCTOPUSOS_CALLS_WEBHOOK_BASE_URL",
    "calls.recording.enabled": "OCTOPUSOS_CALLS_RECORDING_ENABLED",
    "calls.recording.retention_days": "OCTOPUSOS_CALLS_RECORDING_RETENTION_DAYS",
    "calls.volc.access_key_ref": "OCTOPUSOS_CALLS_VOLC_ACCESS_KEY_REF",
    "calls.volc.secret_key_ref": "OCTOPUSOS_CALLS_VOLC_SECRET_KEY_REF",
    "calls.twilio.account_sid_ref": "OCTOPUSOS_CALLS_TWILIO_ACCOUNT_SID_REF",
    "calls.twilio.auth_token_ref": "OCTOPUSOS_CALLS_TWILIO_AUTH_TOKEN_REF",
    "providers.default": "OCTOPUSOS_DEFAULT_PROVIDER",
    "providers.routing.policy": "OCTOPUSOS_PROVIDERS_ROUTING_POLICY",
    "providers.openai.enabled": "OCTOPUSOS_PROVIDERS_OPENAI_ENABLED",
    "providers.openai.base_url": "OCTOPUSOS_PROVIDERS_OPENAI_BASE_URL",
    "providers.openai.model": "OCTOPUSOS_PROVIDERS_OPENAI_MODEL",
    "providers.openai.timeout_ms": "OCTOPUSOS_PROVIDERS_OPENAI_TIMEOUT_MS",
    "providers.openai.retry.max_attempts": "OCTOPUSOS_PROVIDERS_OPENAI_RETRY_MAX_ATTEMPTS",
    "providers.openai.retry.backoff_ms": "OCTOPUSOS_PROVIDERS_OPENAI_RETRY_BACKOFF_MS",
    "providers.openai.concurrency.max": "OCTOPUSOS_PROVIDERS_OPENAI_CONCURRENCY_MAX",
    "providers.openai.api_key_ref": "OCTOPUSOS_PROVIDERS_OPENAI_API_KEY_REF",
    "providers.openai.max_tokens_per_min": "OCTOPUSOS_PROVIDERS_OPENAI_MAX_TOKENS_PER_MIN",
    "providers.openai.daily_cap_tokens": "OCTOPUSOS_PROVIDERS_OPENAI_DAILY_CAP_TOKENS",
    "providers.volc.enabled": "OCTOPUSOS_PROVIDERS_VOLC_ENABLED",
    "providers.volc.base_url": "OCTOPUSOS_PROVIDERS_VOLC_BASE_URL",
    "providers.volc.model": "OCTOPUSOS_PROVIDERS_VOLC_MODEL",
    "providers.volc.timeout_ms": "OCTOPUSOS_PROVIDERS_VOLC_TIMEOUT_MS",
    "providers.volc.retry.max_attempts": "OCTOPUSOS_PROVIDERS_VOLC_RETRY_MAX_ATTEMPTS",
    "providers.volc.retry.backoff_ms": "OCTOPUSOS_PROVIDERS_VOLC_RETRY_BACKOFF_MS",
    "providers.volc.concurrency.max": "OCTOPUSOS_PROVIDERS_VOLC_CONCURRENCY_MAX",
    "providers.volc.app_id": "VOLC_API_APP_ID",
    "providers.volc.resource_id": "VOLC_API_RESOURCE_ID",
    "providers.volc.tts_speaker": "OCTOPUSOS_CALLS_VOLC_TTS_SPEAKER",
    "providers.volc.keep_alive": "OCTOPUSOS_CALLS_VOLC_KEEP_ALIVE",
    "providers.volc.access_key_ref": "OCTOPUSOS_PROVIDERS_VOLC_ACCESS_KEY_REF",
    "providers.volc.app_key_ref": "OCTOPUSOS_PROVIDERS_VOLC_APP_KEY_REF",
    "providers.volc.api_secret_ref": "OCTOPUSOS_PROVIDERS_VOLC_API_SECRET_REF",
    "providers.volc.max_tokens_per_min": "OCTOPUSOS_PROVIDERS_VOLC_MAX_TOKENS_PER_MIN",
    "providers.volc.daily_cap_tokens": "OCTOPUSOS_PROVIDERS_VOLC_DAILY_CAP_TOKENS",
    "providers.ollama.enabled": "OCTOPUSOS_PROVIDERS_OLLAMA_ENABLED",
    "providers.ollama.base_url": "OCTOPUSOS_PROVIDERS_OLLAMA_BASE_URL",
    "providers.ollama.model": "OCTOPUSOS_PROVIDERS_OLLAMA_MODEL",
    "providers.ollama.timeout_ms": "OCTOPUSOS_PROVIDERS_OLLAMA_TIMEOUT_MS",
    "providers.ollama.retry.max_attempts": "OCTOPUSOS_PROVIDERS_OLLAMA_RETRY_MAX_ATTEMPTS",
    "providers.ollama.retry.backoff_ms": "OCTOPUSOS_PROVIDERS_OLLAMA_RETRY_BACKOFF_MS",
    "providers.ollama.concurrency.max": "OCTOPUSOS_PROVIDERS_OLLAMA_CONCURRENCY_MAX",
    "providers.ollama.max_tokens_per_min": "OCTOPUSOS_PROVIDERS_OLLAMA_MAX_TOKENS_PER_MIN",
    "providers.ollama.daily_cap_tokens": "OCTOPUSOS_PROVIDERS_OLLAMA_DAILY_CAP_TOKENS",
    "providers.lmstudio.enabled": "OCTOPUSOS_PROVIDERS_LMSTUDIO_ENABLED",
    "providers.lmstudio.base_url": "OCTOPUSOS_PROVIDERS_LMSTUDIO_BASE_URL",
    "providers.lmstudio.model": "OCTOPUSOS_PROVIDERS_LMSTUDIO_MODEL",
    "providers.lmstudio.timeout_ms": "OCTOPUSOS_PROVIDERS_LMSTUDIO_TIMEOUT_MS",
    "providers.lmstudio.retry.max_attempts": "OCTOPUSOS_PROVIDERS_LMSTUDIO_RETRY_MAX_ATTEMPTS",
    "providers.lmstudio.retry.backoff_ms": "OCTOPUSOS_PROVIDERS_LMSTUDIO_RETRY_BACKOFF_MS",
    "providers.lmstudio.concurrency.max": "OCTOPUSOS_PROVIDERS_LMSTUDIO_CONCURRENCY_MAX",
    "providers.lmstudio.max_tokens_per_min": "OCTOPUSOS_PROVIDERS_LMSTUDIO_MAX_TOKENS_PER_MIN",
    "providers.lmstudio.daily_cap_tokens": "OCTOPUSOS_PROVIDERS_LMSTUDIO_DAILY_CAP_TOKENS",
    "budget.enabled": "OCTOPUSOS_BUDGET_ENABLED",
    "budget.daily_token_limit": "OCTOPUSOS_BUDGET_DAILY_TOKEN_LIMIT",
    "budget.per_minute_token_limit": "OCTOPUSOS_BUDGET_PER_MINUTE_TOKEN_LIMIT",
    "runtime.base_url": "OCTOPUSOS_BASE_URL",
    "runtime.public_url": "OCTOPUSOS_PUBLIC_URL",
    "runtime.timezone": "OCTOPUSOS_TIMEZONE",
    "runtime.web_search_extension_entrypoint": "OCTOPUSOS_RUNTIME_WEB_SEARCH_EXTENSION_ENTRYPOINT",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class CachedItem:
    payload: dict[str, Any]
    expires_at: float


class ConfigCache:
    def __init__(self, ttl_seconds: int = 10) -> None:
        self.ttl_seconds = max(ttl_seconds, 1)
        self._lock = threading.RLock()
        self._items: dict[str, CachedItem] = {}

    def get(self, key: str) -> Optional[dict[str, Any]]:
        now = time.time()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            if item.expires_at <= now:
                self._items.pop(key, None)
                return None
            return item.payload

    def set(self, key: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._items[key] = CachedItem(payload=payload, expires_at=time.time() + self.ttl_seconds)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)
            # Invalidate all scoped cache entries for the logical key.
            suffix = f"::{key}"
            keys = [item_key for item_key in self._items if item_key.endswith(suffix)]
            for item_key in keys:
                self._items.pop(item_key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            keys = [k for k in self._items if k.startswith(prefix)]
            for key in keys:
                self._items.pop(key, None)


_CACHE = ConfigCache(ttl_seconds=int(os.getenv("OCTOPUSOS_CONFIG_CACHE_TTL_SECONDS", "10") or "10"))


def get_config_cache() -> ConfigCache:
    return _CACHE


def _reset_config_cache_for_tests(ttl_seconds: int = 10) -> None:
    global _CACHE
    _CACHE = ConfigCache(ttl_seconds=ttl_seconds)


def _admin_override_allowed(admin_token: Optional[str]) -> bool:
    expected = os.getenv("OCTOPUSOS_ADMIN_TOKEN", "").strip()
    return bool(expected) and bool(admin_token) and admin_token == expected


def _cache_key(key: str, project_id: Optional[str]) -> str:
    return f"{project_id or 'global'}::{key}"


def resolve_config(
    *,
    key: str,
    project_id: Optional[str] = None,
    request_override: Any = None,
    admin_token: Optional[str] = None,
) -> dict[str, Any]:
    if request_override is not None:
        if not _admin_override_allowed(admin_token):
            raise PermissionError("REQUEST_OVERRIDE_FORBIDDEN")
        schema_info = default_value_for_key(key)
        schema_version = schema_info[1] if schema_info else 1
        return {
            "key": key,
            "value": request_override,
            "source": "request_override",
            "schema_version": schema_version,
            "resolved_at": _now_iso(),
        }

    cache_key = _cache_key(key, project_id)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    store_entry = get_config_store().get_entry(key, project_id=project_id)
    if store_entry is not None:
        payload = {
            "key": key,
            "value": store_entry["value"],
            "source": "db",
            "schema_version": int(store_entry.get("schema_version", 1)),
            "resolved_at": _now_iso(),
            "project_id": project_id,
        }
        _CACHE.set(cache_key, payload)
        return payload

    if project_id:
        global_entry = get_config_store().get_entry(key, project_id=None)
        if global_entry is not None:
            payload = {
                "key": key,
                "value": global_entry["value"],
                "source": "db",
                "schema_version": int(global_entry.get("schema_version", 1)),
                "resolved_at": _now_iso(),
                "project_id": None,
            }
            _CACHE.set(cache_key, payload)
            return payload

    env_name = ENV_MAP.get(key)
    if env_name:
        env_value = os.getenv(env_name)
        if env_value is not None:
            schema_info = default_value_for_key(key)
            schema_version = schema_info[1] if schema_info else 1
            payload = {
                "key": key,
                "value": env_value,
                "source": "env",
                "schema_version": schema_version,
                "resolved_at": _now_iso(),
            }
            _CACHE.set(cache_key, payload)
            return payload

    schema_info = default_value_for_key(key)
    if schema_info is None:
        payload = {
            "key": key,
            "value": None,
            "source": "default",
            "schema_version": 1,
            "resolved_at": _now_iso(),
        }
        _CACHE.set(cache_key, payload)
        return payload

    default_value, schema_version = schema_info
    payload = {
        "key": key,
        "value": default_value,
        "source": "default",
        "schema_version": schema_version,
        "resolved_at": _now_iso(),
    }
    _CACHE.set(cache_key, payload)
    return payload
