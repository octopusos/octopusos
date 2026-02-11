from __future__ import annotations

import re
from typing import Any, Dict, Optional

_ENV_PATTERNS = {
    "prod": ("prod", "production", "线上", "生产"),
    "staging": ("staging", "stage", "预发", "测试环境"),
    "dev": ("dev", "development", "开发"),
}


def _extract_environment(text: str) -> Optional[str]:
    lower = text.lower()
    for env, words in _ENV_PATTERNS.items():
        if any(word in lower for word in words):
            return env
    return None


def _extract_target(text: str) -> Optional[str]:
    lower = text.lower()
    # heuristic target words commonly used in DB naming
    candidates = re.findall(r"\b(payments|orders|users|sessions|analytics|inventory|billing|cache)\b", lower)
    if candidates:
        return candidates[0]
    zh_map = {
        "支付": "payments",
        "订单": "orders",
        "用户": "users",
        "会话": "sessions",
        "分析": "analytics",
        "库存": "inventory",
        "账单": "billing",
        "缓存": "cache",
    }
    for zh_key, mapped in zh_map.items():
        if zh_key in text:
            return mapped
    return None


def _extract_engine(text: str) -> Optional[str]:
    lower = text.lower()
    if "postgres" in lower or "postgresql" in lower or re.search(r"\bpg\b", lower):
        return "postgres"
    if "mysql" in lower:
        return "mysql"
    if "sql server" in lower or "sqlserver" in lower or "mssql" in lower:
        return "sqlserver"
    if "sqlite" in lower:
        return "sqlite"
    if "mongo" in lower:
        return "mongodb"
    if "redis" in lower:
        return "redis"
    if "dynamodb" in lower:
        return "dynamodb"
    return None


def _is_confirm_text(text: str) -> bool:
    lower = text.lower().strip()
    return bool(re.search(r"\b(confirm|approve|continue|yes|确认|继续|同意)\b", lower))


def _is_cancel_text(text: str) -> bool:
    lower = text.lower().strip()
    return bool(re.search(r"\b(cancel|abort|stop|no|取消|中止|不要)\b", lower))


def parse_db_intent(text: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Parse NL into db.* action intent only. No execution side effects.

    Returns None when no DB intent is detected.
    """
    ctx = context or {}
    pending = ctx.get("pending_action")

    if pending:
        if _is_cancel_text(text):
            return {"intent": "confirm_control", "confirm": False, "cancel": True}
        if _is_confirm_text(text):
            return {
                "intent": "confirm_control",
                "confirm": True,
                "cancel": False,
                "action_id": pending.get("action_id"),
                "confirm_token": pending.get("confirm_token"),
                "nl_text": pending.get("nl_text"),
                "parameters": pending.get("parameters") or {},
                "reason": pending.get("reason") or "confirmed_by_user",
            }

    lower = text.lower()
    if not any(k in lower for k in ("db", "database", "schema", "table", "migration", "sql", "库", "表", "迁移", "统计", "drop", "truncate")):
        return None

    env = _extract_environment(text)
    target = _extract_target(text)
    engine = _extract_engine(text)

    if any(k in lower for k in ("drop table", "truncate", "删除表", "清空表")):
        return {
            "intent": "db_action",
            "action_id": "db.admin.critical.drop_table",
            "args": {
                "parameters": {
                    "engine": engine,
                    "target": target,
                },
                "reason": "admin_critical_request",
                "dry_run": False,
            },
            "hints": {"environment": env, "target": target, "engine": engine},
        }

    if any(k in lower for k in ("refresh stats", "analyze table", "统计", "刷新统计")):
        return {
            "intent": "db_action",
            "action_id": "db.safe.maintenance.refresh_stats",
            "args": {
                "parameters": {
                    "engine": engine,
                    "target": target,
                    "estimated_rows": 100,
                },
                "reason": "maintenance_refresh_stats",
                "dry_run": True,
            },
            "hints": {"environment": env, "target": target, "engine": engine},
        }

    if any(k in lower for k in ("migration", "migrate", "迁移")):
        migration_path = None
        m = re.search(r"(migrations?/[^\s]+)", text)
        if m:
            migration_path = m.group(1)
        if not migration_path:
            return {
                "intent": "ask_missing_fields",
                "missing": ["migration_path"],
                "message": "需要提供 migration 路径，例如 migrations/20260210_add_index.sql",
            }
        return {
            "intent": "db_action",
            "action_id": "db.migration.apply",
            "args": {
                "parameters": {
                    "engine": engine,
                    "target": target,
                    "migration_path": migration_path,
                    "path": migration_path,
                    "estimated_rows": 0,
                },
                "reason": "migration_request",
                "dry_run": True,
            },
            "hints": {"environment": env, "target": target, "engine": engine},
        }

    if any(k in lower for k in ("sample", "query sample", "抽样", "样本")):
        return {
            "intent": "db_action",
            "action_id": "db.readonly.query_sample",
            "args": {
                "parameters": {
                    "engine": engine,
                    "target": target,
                    "limit": 20,
                    "estimated_rows": 20,
                },
                "reason": "readonly_query_sample",
                "dry_run": True,
            },
            "hints": {"environment": env, "target": target, "engine": engine},
        }

    if any(k in lower for k in ("inspect", "schema", "describe", "结构", "看下", "看看")):
        if not target:
            return {
                "intent": "ask_missing_fields",
                "missing": ["target"],
                "message": "请补充目标库/服务名，例如 payments、orders。",
            }
        return {
            "intent": "db_action",
            "action_id": "db.readonly.inspect",
            "args": {
                "parameters": {
                    "engine": engine,
                    "target": target,
                    "estimated_rows": 0,
                },
                "reason": "readonly_inspect",
                "dry_run": True,
            },
            "hints": {"environment": env, "target": target, "engine": engine},
        }

    return None
