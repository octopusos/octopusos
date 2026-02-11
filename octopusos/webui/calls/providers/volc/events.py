"""Event helpers for Volc Realtime Dialogue API payloads."""

from __future__ import annotations

from typing import Any, Dict, Optional


def extract_text(payload: Dict[str, Any]) -> str:
    for key in ("text", "transcript", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    result = payload.get("result")
    if isinstance(result, dict):
        for key in ("text", "transcript", "content"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def is_final_asr(payload: Dict[str, Any]) -> bool:
    for key in ("is_final", "final"):
        value = payload.get(key)
        if isinstance(value, bool):
            return value
    result = payload.get("result")
    if isinstance(result, dict):
        for key in ("is_final", "final"):
            value = result.get(key)
            if isinstance(value, bool):
                return value
    return False


def extract_error(payload: Optional[Dict[str, Any]], fallback: str = "Volc realtime error") -> str:
    if not isinstance(payload, dict):
        return fallback
    for key in ("message", "error", "detail"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    code = payload.get("code")
    if code is not None:
        return f"{fallback} (code={code})"
    return fallback
