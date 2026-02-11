"""Config key allowlist and risk policy for editable WebUI configuration."""

from __future__ import annotations

from typing import Dict, List


ALLOWLIST: Dict[str, Dict[str, object]] = {
    "calls": {
        "title": "Calls",
        "keys": [
            "calls.enabled",
            "calls.provider",
            "calls.webhook_base_url",
            "calls.recording.enabled",
            "calls.recording.retention_days",
        ],
        "secrets": [
            "calls.twilio.account_sid_ref",
            "calls.twilio.auth_token_ref",
            "calls.volc.access_key_ref",
            "calls.volc.secret_key_ref",
        ],
        "high_risk_keys": [
            "calls.provider",
        ],
        "key_meta": {
            "calls.provider": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": False,
            },
        },
    },
    "providers": {
        "title": "Providers",
        "keys": [
            "providers.default",
            "providers.routing.policy",
            "providers.openai.enabled",
            "providers.openai.base_url",
            "providers.openai.model",
            "providers.openai.timeout_ms",
            "providers.openai.retry.max_attempts",
            "providers.openai.retry.backoff_ms",
            "providers.openai.concurrency.max",
            "providers.volc.enabled",
            "providers.volc.base_url",
            "providers.volc.model",
            "providers.volc.timeout_ms",
            "providers.volc.retry.max_attempts",
            "providers.volc.retry.backoff_ms",
            "providers.volc.concurrency.max",
            "providers.volc.app_id",
            "providers.volc.resource_id",
            "providers.volc.tts_speaker",
            "providers.volc.keep_alive",
            "providers.ollama.enabled",
            "providers.ollama.base_url",
            "providers.ollama.model",
            "providers.ollama.timeout_ms",
            "providers.ollama.retry.max_attempts",
            "providers.ollama.retry.backoff_ms",
            "providers.ollama.concurrency.max",
            "providers.lmstudio.enabled",
            "providers.lmstudio.base_url",
            "providers.lmstudio.model",
            "providers.lmstudio.timeout_ms",
            "providers.lmstudio.retry.max_attempts",
            "providers.lmstudio.retry.backoff_ms",
            "providers.lmstudio.concurrency.max",
        ],
        "secrets": [
            "providers.openai.api_key_ref",
            "providers.volc.access_key_ref",
            "providers.volc.app_key_ref",
            "providers.volc.api_secret_ref",
        ],
        "high_risk_keys": [
            "providers.openai.model",
            "providers.volc.model",
        ],
        "key_meta": {
            "providers.openai.model": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": True,
            },
            "providers.volc.model": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": True,
            },
        },
    },
    "comm": {
        "title": "Communication",
        "keys": [
            "comm.sms.enabled",
            "comm.email.enabled",
            "comm.social.enabled",
        ],
        "secrets": [],
    },
    "runtime": {
        "title": "Runtime",
        "keys": [
            "runtime.base_url",
            "runtime.public_url",
            "runtime.timezone",
            "runtime.web_search_extension_entrypoint",
        ],
        "secrets": [],
    },
    "logging": {
        "title": "Logging",
        "keys": [
            "logging.level",
            "logging.format",
        ],
        "secrets": [],
    },
    "governance": {
        "title": "Governance",
        "keys": [
            "governance.policy.strictness",
            "governance.audit.retention_days",
        ],
        "secrets": [],
    },
    "budget": {
        "title": "Budget",
        "keys": [
            "budget.enabled",
            "budget.daily_token_limit",
            "budget.per_minute_token_limit",
            "providers.openai.max_tokens_per_min",
            "providers.openai.daily_cap_tokens",
            "providers.volc.max_tokens_per_min",
            "providers.volc.daily_cap_tokens",
            "providers.ollama.max_tokens_per_min",
            "providers.ollama.daily_cap_tokens",
            "providers.lmstudio.max_tokens_per_min",
            "providers.lmstudio.daily_cap_tokens",
        ],
        "secrets": [],
        "high_risk_keys": [
            "budget.daily_token_limit",
            "budget.per_minute_token_limit",
            "providers.openai.max_tokens_per_min",
            "providers.openai.daily_cap_tokens",
            "providers.volc.max_tokens_per_min",
            "providers.volc.daily_cap_tokens",
        ],
        "key_meta": {
            "budget.daily_token_limit": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": True,
            },
            "budget.per_minute_token_limit": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": True,
            },
        },
    },
    "chat": {
        "title": "Chat",
        "keys": [
            "chat.writer.mode",
            "chat.writer.failpoint",
            "chat.ledger.enabled",
        ],
        "secrets": [],
        "high_risk_keys": [
            "chat.writer.mode",
            "chat.writer.failpoint",
        ],
        "key_meta": {
            "chat.writer.mode": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": False,
            },
            "chat.writer.failpoint": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": False,
            },
        },
    },
    "attention": {
        "title": "Attention",
        "keys": [
            "attention.mode.global",
            "attention.quiet_hours.enabled",
            "attention.quiet_hours.start",
            "attention.quiet_hours.end",
            "attention.rate_limit.per_minute",
            "attention.card.cooldown_ms",
            "attention.chat_injection.enabled",
            "attention.chat_injection.mode",
            "attention.chat_injection.max_per_session_per_minute",
            "attention.chat_injection.max_per_global_per_minute",
            "attention.chat_injection.require_user_idle_ms",
            "attention.chat_injection.only_when_session_active",
            "attention.chat_injection.severity_threshold",
        ],
        "secrets": [],
        "high_risk_keys": [
            "attention.chat_injection.enabled",
            "attention.chat_injection.mode",
        ],
        "key_meta": {
            "attention.chat_injection.enabled": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": False,
            },
            "attention.chat_injection.mode": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": False,
            },
        },
    },
    "work": {
        "title": "Work",
        "keys": [
            "work.mode.global",
            "work.auto_execute.enabled",
            "work.auto_execute.max_concurrent",
            "work.auto_execute.safe_only",
            "work.auto_execute.quiet_hours_respect",
            "work.auto_execute.fail_open",
        ],
        "secrets": [],
        "high_risk_keys": [
            "work.mode.global",
            "work.auto_execute.enabled",
        ],
        "key_meta": {
            "work.mode.global": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": False,
            },
            "work.auto_execute.enabled": {
                "risk_level": "high",
                "requires_confirmation": True,
                "requires_dry_run": False,
            },
        },
    },
}


def iter_allowed_keys() -> set[str]:
    allowed: set[str] = set()
    for module in ALLOWLIST.values():
        for key in module.get("keys", []):  # type: ignore[union-attr]
            if isinstance(key, str):
                allowed.add(key)
        for key in module.get("secrets", []):  # type: ignore[union-attr]
            if isinstance(key, str):
                allowed.add(key)
    return allowed


def is_allowed_key(key: str) -> bool:
    return key in iter_allowed_keys()


def is_high_risk_key(key: str) -> bool:
    policy = get_key_policy(key)
    return policy["risk_level"] == "high"


def get_key_policy(key: str) -> Dict[str, object]:
    default_policy: Dict[str, object] = {
        "risk_level": "low",
        "requires_confirmation": False,
        "requires_dry_run": False,
    }
    for module in ALLOWLIST.values():
        key_meta = module.get("key_meta", {})
        if isinstance(key_meta, dict) and key in key_meta:
            policy = key_meta[key]
            if isinstance(policy, dict):
                merged = dict(default_policy)
                merged.update(policy)
                return merged
        high = module.get("high_risk_keys", [])
        if isinstance(high, list) and key in high:
            merged = dict(default_policy)
            merged.update({"risk_level": "high", "requires_confirmation": True})
            return merged
    return default_policy
