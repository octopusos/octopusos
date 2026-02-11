from __future__ import annotations

from typing import Literal, cast


AttentionMode = Literal["silent", "reactive", "proactive"]


def _resolve_value(key: str) -> object | None:
    try:
        from octopusos.webui.config_resolver import resolve_config

        payload = resolve_config(key=key, project_id=None)
        return payload.get("value")
    except Exception:
        return None


def get_attention_mode_global() -> AttentionMode:
    raw = _resolve_value("attention.mode.global")
    if isinstance(raw, str):
        value = raw.strip()
        if value in ("silent", "reactive", "proactive"):
            return cast(AttentionMode, value)
    return "reactive"


def quiet_hours_enabled() -> bool:
    raw = _resolve_value("attention.quiet_hours.enabled")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return False


def quiet_hours_start() -> str:
    raw = _resolve_value("attention.quiet_hours.start")
    return raw.strip() if isinstance(raw, str) and raw.strip() else "22:00"


def quiet_hours_end() -> str:
    raw = _resolve_value("attention.quiet_hours.end")
    return raw.strip() if isinstance(raw, str) and raw.strip() else "08:00"


def rate_limit_per_minute() -> int:
    raw = _resolve_value("attention.rate_limit.per_minute")
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except Exception:
        return 6


def card_cooldown_ms() -> int:
    raw = _resolve_value("attention.card.cooldown_ms")
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except Exception:
        return 600_000
