from __future__ import annotations

from typing import Literal, cast

from octopusos.core.work.work_mode import get_work_mode_global


InjectionMode = Literal["off", "inbox_only", "chat_allowed"]
Severity = Literal["info", "warn", "high", "critical"]


def _resolve_value(key: str) -> object | None:
    try:
        from octopusos.webui.config_resolver import resolve_config

        payload = resolve_config(key=key, project_id=None)
        return payload.get("value")
    except Exception:
        return None


def _resolve_payload(key: str) -> dict | None:
    try:
        from octopusos.webui.config_resolver import resolve_config

        return resolve_config(key=key, project_id=None)
    except Exception:
        return None


def injection_enabled() -> bool:
    # Work-mode matrix is the user-facing switch. Injection is only ever possible in proactive.
    if get_work_mode_global() != "proactive":
        return False
    payload = _resolve_payload("attention.chat_injection.enabled") or {}
    raw = payload.get("value")
    src = str(payload.get("source") or "")

    # In Phase 4, switching work.mode.global to proactive is the user-facing
    # action that enables injection by default. We still allow an explicit
    # DB override to disable it.
    if src == "db":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "on"}
        return False

    # Not explicitly configured: enabled by default under proactive.
    return True


def injection_mode() -> InjectionMode:
    # Work-mode matrix is the user-facing switch. Non-proactive modes must never inject.
    if get_work_mode_global() != "proactive":
        return "inbox_only"

    payload = _resolve_payload("attention.chat_injection.mode") or {}
    raw = payload.get("value")
    src = str(payload.get("source") or "")

    if isinstance(raw, str):
        value = raw.strip()
        if value in ("off", "inbox_only", "chat_allowed"):
            # Respect explicit rollback to inbox_only/off.
            return cast(InjectionMode, value)

    # If not explicitly configured, default to allowing injection under proactive.
    return "chat_allowed" if src == "default" else "chat_allowed"


def max_per_session_per_minute() -> int:
    raw = _resolve_value("attention.chat_injection.max_per_session_per_minute")
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except Exception:
        return 2


def max_per_global_per_minute() -> int:
    raw = _resolve_value("attention.chat_injection.max_per_global_per_minute")
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except Exception:
        return 6


def require_user_idle_ms() -> int:
    raw = _resolve_value("attention.chat_injection.require_user_idle_ms")
    try:
        return max(0, int(raw))  # type: ignore[arg-type]
    except Exception:
        return 5000


def only_when_session_active() -> bool:
    raw = _resolve_value("attention.chat_injection.only_when_session_active")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return True


def severity_threshold() -> Severity:
    raw = _resolve_value("attention.chat_injection.severity_threshold")
    if isinstance(raw, str):
        value = raw.strip()
        if value in ("info", "warn", "high", "critical"):
            return cast(Severity, value)
    return "high"
