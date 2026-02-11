from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Intent:
    intent_type: str
    cloud: str = "unknown"
    service: str = "unknown"
    slots: Dict[str, Any] = field(default_factory=dict)
    lang: str = "en"
    confidence: float = 0.5
    raw_text: str = ""


def _is_zh(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in (text or ""))


def parse_intent(text: str) -> Intent:
    src = (text or "").strip()
    low = src.lower()
    lang = "zh" if _is_zh(src) else "en"

    continue_tokens = (
        "继续",
        "继续修复",
        "我已经修复",
        "我已修复",
        "已修复",
        "再试",
        "再试试",
        "done",
        "fixed",
        "continue",
        "retry",
        "recheck",
    )
    cancel_tokens = ("取消", "不用", "stop", "cancel")
    install_tokens = ("安装并启用", "安装", "启用", "install", "enable")
    create_min_tokens = ("创建最小权限并绑定", "create minimal", "new role", "recommended role")

    if any(t in low for t in cancel_tokens):
        return Intent("control.cancel", cloud="aws", service="monitoring", lang=lang, confidence=0.9, raw_text=src)
    if any(t in low for t in continue_tokens):
        return Intent("control.continue", cloud="aws", service="monitoring", lang=lang, confidence=0.9, raw_text=src)
    if any(t in low for t in create_min_tokens):
        return Intent("input.create_minimal_role_profile", cloud="aws", service="compute", lang=lang, confidence=0.95, raw_text=src)
    if any(t in low for t in install_tokens):
        return Intent("monitor.ensure_agent", cloud="aws", service="monitoring", lang=lang, confidence=0.8, raw_text=src)
    return Intent("unknown", cloud="unknown", service="unknown", lang=lang, confidence=0.1, raw_text=src)
