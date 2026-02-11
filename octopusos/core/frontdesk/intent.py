"""Frontdesk intent parsing (MVP)."""

import re
from typing import List, Dict

INTENT_TODO = "TODO"
INTENT_STATUS = "STATUS"
INTENT_REPORT = "REPORT"
INTENT_BLOCKER = "BLOCKER"
INTENT_GLOBAL = "GLOBAL"
INTENT_ASSIGN = "ASSIGN"
INTENT_PRIORITIZE = "PRIORITIZE"
INTENT_PAUSE = "PAUSE"
INTENT_RESUME = "RESUME"
INTENT_RUN = "RUN"
INTENT_GENERAL = "GENERAL"

INTENT_KEYWORDS = {
    INTENT_TODO: ["todo", "to-do", "待办", "任务"],
    INTENT_STATUS: ["status", "进度", "状态", "完成了吗"],
    INTENT_REPORT: ["report", "日报", "周报", "总结"],
    INTENT_BLOCKER: ["blocker", "阻塞", "卡住", "问题"],
    INTENT_GLOBAL: ["overview", "/overview", "整体", "前台", "总览"],
    INTENT_ASSIGN: ["assign", "reassign", "交给", "分配"],
    INTENT_PRIORITIZE: ["priority", "优先级", "提升", "降级"],
    INTENT_PAUSE: ["pause", "暂停", "停用"],
    INTENT_RESUME: ["resume", "恢复", "重启"],
    INTENT_RUN: ["run", "执行", "运行", "pipeline"],
}

KNOWN_AGENT_ALIASES = {
    "james": ["james", "詹姆斯"],
}


def extract_mentions(text: str) -> List[str]:
    mentions = set()

    for match in re.finditer(r"@([a-zA-Z0-9_]+)", text):
        mentions.add(match.group(1).lower())

    lower = text.lower()
    for agent, aliases in KNOWN_AGENT_ALIASES.items():
        if any(alias in lower for alias in aliases):
            mentions.add(agent)

    return sorted(mentions)


def detect_intent(text: str) -> str:
    lower = text.lower()

    # Prefer GLOBAL if overview cues are present
    for keyword in INTENT_KEYWORDS[INTENT_GLOBAL]:
        if keyword in lower:
            return INTENT_GLOBAL

    for intent, keywords in INTENT_KEYWORDS.items():
        if intent == INTENT_GLOBAL:
            continue
        if any(keyword in lower for keyword in keywords):
            return intent

    return INTENT_GENERAL


def parse_frontdesk_request(text: str, explicit_mentions: List[str] | None = None) -> Dict[str, object]:
    mentions = set(extract_mentions(text))
    if explicit_mentions:
        mentions.update(name.lower() for name in explicit_mentions)

    intent = detect_intent(text)

    return {
        "intent": intent,
        "mentions": sorted(mentions),
    }
