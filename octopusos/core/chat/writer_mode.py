"""Runtime configuration accessors for chat writer/ledger.

Phase 1 requirement:
- Centralize config reads (do not scatter env/db lookups across core modules).
- Fail safe: exceptions must not break chat (fallback to defaults).
"""

from __future__ import annotations

from typing import Literal, cast


WriterMode = Literal["legacy", "dual_write", "ledger_primary"]


def _resolve_value(key: str) -> object | None:
    try:
        # WebUI config resolver handles DB/env/default + caching.
        from octopusos.webui.config_resolver import resolve_config

        payload = resolve_config(key=key, project_id=None)
        return payload.get("value")
    except Exception:
        return None


def get_chat_writer_mode() -> WriterMode:
    raw = _resolve_value("chat.writer.mode")
    if isinstance(raw, str):
        value = raw.strip()
        if value in ("legacy", "dual_write", "ledger_primary"):
            return cast(WriterMode, value)
    return "legacy"


def get_chat_writer_failpoint() -> str:
    raw = _resolve_value("chat.writer.failpoint")
    return raw.strip() if isinstance(raw, str) else ""


def is_ledger_enabled() -> bool:
    raw = _resolve_value("chat.ledger.enabled")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return True

