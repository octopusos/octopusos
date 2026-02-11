from __future__ import annotations

from typing import Literal, cast


WorkMode = Literal["reactive", "proactive", "silent_proactive"]


def _resolve_payload(key: str) -> dict | None:
    try:
        from octopusos.webui.config_resolver import resolve_config

        return resolve_config(key=key, project_id=None)
    except Exception:
        return None


def get_work_mode_global() -> WorkMode:
    payload = _resolve_payload("work.mode.global") or {}
    raw = payload.get("value")
    if isinstance(raw, str):
        v = raw.strip()
        if v in {"reactive", "proactive", "silent_proactive"}:
            return cast(WorkMode, v)
    return "reactive"


def auto_execute_enabled() -> bool:
    # Reactive must never auto-execute.
    if get_work_mode_global() == "reactive":
        return False
    payload = _resolve_payload("work.auto_execute.enabled") or {}
    raw = payload.get("value")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return False


def auto_execute_max_concurrent() -> int:
    payload = _resolve_payload("work.auto_execute.max_concurrent") or {}
    raw = payload.get("value")
    try:
        return max(1, min(8, int(raw)))  # type: ignore[arg-type]
    except Exception:
        return 2


def auto_execute_safe_only() -> bool:
    payload = _resolve_payload("work.auto_execute.safe_only") or {}
    raw = payload.get("value")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return True


def auto_execute_quiet_hours_respect() -> bool:
    payload = _resolve_payload("work.auto_execute.quiet_hours_respect") or {}
    raw = payload.get("value")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return True


def auto_execute_fail_open() -> bool:
    payload = _resolve_payload("work.auto_execute.fail_open") or {}
    raw = payload.get("value")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return False

