"""Schema registry for app_config validation and defaults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class _SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(default=1)


class CallsConfigSchema(_SchemaBase):
    enabled: bool = True
    provider: Literal["twilio", "volc", "mock"] = "mock"
    webhook_base_url: str = ""
    recording_enabled: bool = False
    recording_retention_days: int = 30
    twilio_account_sid_ref: str = ""
    twilio_auth_token_ref: str = ""
    volc_access_key_ref: str = ""
    volc_secret_key_ref: str = ""


class ProvidersConfigSchema(_SchemaBase):
    default: str = "ollama"
    routing_policy: str = "balanced"
    openai_enabled: bool = True
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_timeout_ms: int = 30000
    openai_retry_max_attempts: int = 2
    openai_retry_backoff_ms: int = 800
    openai_concurrency_max: int = 4
    openai_api_key_ref: str = ""
    openai_max_tokens_per_min: int = 120000
    openai_daily_cap_tokens: int = 2000000
    volc_enabled: bool = True
    volc_base_url: str = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"
    volc_model: str = "O"
    volc_timeout_ms: int = 30000
    volc_retry_max_attempts: int = 2
    volc_retry_backoff_ms: int = 800
    volc_concurrency_max: int = 4
    volc_app_id: str = ""
    volc_resource_id: str = "volc.speech.dialog"
    volc_tts_speaker: str = "zh_female_vv_jupiter_bigtts"
    volc_keep_alive: bool = True
    volc_access_key_ref: str = ""
    volc_app_key_ref: str = ""
    volc_api_secret_ref: str = ""
    volc_max_tokens_per_min: int = 120000
    volc_daily_cap_tokens: int = 2000000
    ollama_enabled: bool = True
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_ms: int = 30000
    ollama_retry_max_attempts: int = 2
    ollama_retry_backoff_ms: int = 800
    ollama_concurrency_max: int = 2
    ollama_max_tokens_per_min: int = 200000
    ollama_daily_cap_tokens: int = 5000000
    lmstudio_enabled: bool = True
    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    lmstudio_model: str = "default"
    lmstudio_timeout_ms: int = 30000
    lmstudio_retry_max_attempts: int = 2
    lmstudio_retry_backoff_ms: int = 800
    lmstudio_concurrency_max: int = 2
    lmstudio_max_tokens_per_min: int = 200000
    lmstudio_daily_cap_tokens: int = 5000000


class CommConfigSchema(_SchemaBase):
    sms_enabled: bool = False
    email_enabled: bool = False
    social_enabled: bool = False


class RuntimeConfigSchema(_SchemaBase):
    base_url: str = ""
    public_url: str = ""
    timezone: str = "UTC"
    web_search_extension_entrypoint: str = ""


class LoggingConfigSchema(_SchemaBase):
    level: str = "INFO"
    format: str = "text"


class GovernanceConfigSchema(_SchemaBase):
    policy_strictness: str = "standard"
    audit_retention_days: int = 30


class BudgetConfigSchema(_SchemaBase):
    enabled: bool = True
    daily_token_limit: int = 2000000
    per_minute_token_limit: int = 120000


class ChatConfigSchema(_SchemaBase):
    writer_mode: Literal["legacy", "dual_write", "ledger_primary"] = "legacy"
    writer_failpoint: str = ""
    ledger_enabled: bool = True


class AttentionConfigSchema(_SchemaBase):
    mode_global: Literal["silent", "reactive", "proactive"] = "reactive"
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    rate_limit_per_minute: int = 6
    card_cooldown_ms: int = 600_000
    chat_injection_enabled: bool = False
    chat_injection_mode: Literal["off", "inbox_only", "chat_allowed"] = "inbox_only"
    chat_injection_max_per_session_per_minute: int = 2
    chat_injection_max_per_global_per_minute: int = 6
    chat_injection_require_user_idle_ms: int = 5000
    chat_injection_only_when_session_active: bool = True
    chat_injection_severity_threshold: Literal["info", "warn", "high", "critical"] = "high"


class WorkConfigSchema(_SchemaBase):
    # User-facing global mode matrix (Phase 4).
    # Mapping is enforced in code (see octopusos.core.work.work_mode and attention.chat_injection_config).
    mode_global: Literal["reactive", "proactive", "silent_proactive"] = "reactive"
    auto_execute_enabled: bool = False
    auto_execute_max_concurrent: int = 2
    auto_execute_safe_only: bool = True
    auto_execute_quiet_hours_respect: bool = True
    auto_execute_fail_open: bool = False


SCHEMA_REGISTRY: Dict[str, Type[_SchemaBase]] = {
    "calls": CallsConfigSchema,
    "providers": ProvidersConfigSchema,
    "comm": CommConfigSchema,
    "runtime": RuntimeConfigSchema,
    "logging": LoggingConfigSchema,
    "governance": GovernanceConfigSchema,
    "budget": BudgetConfigSchema,
    "chat": ChatConfigSchema,
    "attention": AttentionConfigSchema,
    "work": WorkConfigSchema,
}

KEY_TO_FIELD: Dict[str, Tuple[str, str]] = {
    "calls.enabled": ("calls", "enabled"),
    "calls.provider": ("calls", "provider"),
    "calls.webhook_base_url": ("calls", "webhook_base_url"),
    "calls.recording.enabled": ("calls", "recording_enabled"),
    "calls.recording.retention_days": ("calls", "recording_retention_days"),
    "calls.twilio.account_sid_ref": ("calls", "twilio_account_sid_ref"),
    "calls.twilio.auth_token_ref": ("calls", "twilio_auth_token_ref"),
    "calls.volc.access_key_ref": ("calls", "volc_access_key_ref"),
    "calls.volc.secret_key_ref": ("calls", "volc_secret_key_ref"),
    "providers.default": ("providers", "default"),
    "providers.routing.policy": ("providers", "routing_policy"),
    "providers.openai.enabled": ("providers", "openai_enabled"),
    "providers.openai.base_url": ("providers", "openai_base_url"),
    "providers.openai.model": ("providers", "openai_model"),
    "providers.openai.timeout_ms": ("providers", "openai_timeout_ms"),
    "providers.openai.retry.max_attempts": ("providers", "openai_retry_max_attempts"),
    "providers.openai.retry.backoff_ms": ("providers", "openai_retry_backoff_ms"),
    "providers.openai.concurrency.max": ("providers", "openai_concurrency_max"),
    "providers.openai.api_key_ref": ("providers", "openai_api_key_ref"),
    "providers.openai.max_tokens_per_min": ("providers", "openai_max_tokens_per_min"),
    "providers.openai.daily_cap_tokens": ("providers", "openai_daily_cap_tokens"),
    "providers.volc.enabled": ("providers", "volc_enabled"),
    "providers.volc.base_url": ("providers", "volc_base_url"),
    "providers.volc.model": ("providers", "volc_model"),
    "providers.volc.timeout_ms": ("providers", "volc_timeout_ms"),
    "providers.volc.retry.max_attempts": ("providers", "volc_retry_max_attempts"),
    "providers.volc.retry.backoff_ms": ("providers", "volc_retry_backoff_ms"),
    "providers.volc.concurrency.max": ("providers", "volc_concurrency_max"),
    "providers.volc.app_id": ("providers", "volc_app_id"),
    "providers.volc.resource_id": ("providers", "volc_resource_id"),
    "providers.volc.tts_speaker": ("providers", "volc_tts_speaker"),
    "providers.volc.keep_alive": ("providers", "volc_keep_alive"),
    "providers.volc.access_key_ref": ("providers", "volc_access_key_ref"),
    "providers.volc.app_key_ref": ("providers", "volc_app_key_ref"),
    "providers.volc.api_secret_ref": ("providers", "volc_api_secret_ref"),
    "providers.volc.max_tokens_per_min": ("providers", "volc_max_tokens_per_min"),
    "providers.volc.daily_cap_tokens": ("providers", "volc_daily_cap_tokens"),
    "providers.ollama.enabled": ("providers", "ollama_enabled"),
    "providers.ollama.base_url": ("providers", "ollama_base_url"),
    "providers.ollama.model": ("providers", "ollama_model"),
    "providers.ollama.timeout_ms": ("providers", "ollama_timeout_ms"),
    "providers.ollama.retry.max_attempts": ("providers", "ollama_retry_max_attempts"),
    "providers.ollama.retry.backoff_ms": ("providers", "ollama_retry_backoff_ms"),
    "providers.ollama.concurrency.max": ("providers", "ollama_concurrency_max"),
    "providers.ollama.max_tokens_per_min": ("providers", "ollama_max_tokens_per_min"),
    "providers.ollama.daily_cap_tokens": ("providers", "ollama_daily_cap_tokens"),
    "providers.lmstudio.enabled": ("providers", "lmstudio_enabled"),
    "providers.lmstudio.base_url": ("providers", "lmstudio_base_url"),
    "providers.lmstudio.model": ("providers", "lmstudio_model"),
    "providers.lmstudio.timeout_ms": ("providers", "lmstudio_timeout_ms"),
    "providers.lmstudio.retry.max_attempts": ("providers", "lmstudio_retry_max_attempts"),
    "providers.lmstudio.retry.backoff_ms": ("providers", "lmstudio_retry_backoff_ms"),
    "providers.lmstudio.concurrency.max": ("providers", "lmstudio_concurrency_max"),
    "providers.lmstudio.max_tokens_per_min": ("providers", "lmstudio_max_tokens_per_min"),
    "providers.lmstudio.daily_cap_tokens": ("providers", "lmstudio_daily_cap_tokens"),
    "comm.sms.enabled": ("comm", "sms_enabled"),
    "comm.email.enabled": ("comm", "email_enabled"),
    "comm.social.enabled": ("comm", "social_enabled"),
    "runtime.base_url": ("runtime", "base_url"),
    "runtime.public_url": ("runtime", "public_url"),
    "runtime.timezone": ("runtime", "timezone"),
    "runtime.web_search_extension_entrypoint": ("runtime", "web_search_extension_entrypoint"),
    "logging.level": ("logging", "level"),
    "logging.format": ("logging", "format"),
    "governance.policy.strictness": ("governance", "policy_strictness"),
    "governance.audit.retention_days": ("governance", "audit_retention_days"),
    "budget.enabled": ("budget", "enabled"),
    "budget.daily_token_limit": ("budget", "daily_token_limit"),
    "budget.per_minute_token_limit": ("budget", "per_minute_token_limit"),
    "chat.writer.mode": ("chat", "writer_mode"),
    "chat.writer.failpoint": ("chat", "writer_failpoint"),
    "chat.ledger.enabled": ("chat", "ledger_enabled"),
    "attention.mode.global": ("attention", "mode_global"),
    "attention.quiet_hours.enabled": ("attention", "quiet_hours_enabled"),
    "attention.quiet_hours.start": ("attention", "quiet_hours_start"),
    "attention.quiet_hours.end": ("attention", "quiet_hours_end"),
    "attention.rate_limit.per_minute": ("attention", "rate_limit_per_minute"),
    "attention.card.cooldown_ms": ("attention", "card_cooldown_ms"),
    "attention.chat_injection.enabled": ("attention", "chat_injection_enabled"),
    "attention.chat_injection.mode": ("attention", "chat_injection_mode"),
    "attention.chat_injection.max_per_session_per_minute": ("attention", "chat_injection_max_per_session_per_minute"),
    "attention.chat_injection.max_per_global_per_minute": ("attention", "chat_injection_max_per_global_per_minute"),
    "attention.chat_injection.require_user_idle_ms": ("attention", "chat_injection_require_user_idle_ms"),
    "attention.chat_injection.only_when_session_active": ("attention", "chat_injection_only_when_session_active"),
    "attention.chat_injection.severity_threshold": ("attention", "chat_injection_severity_threshold"),
    "work.mode.global": ("work", "mode_global"),
    "work.auto_execute.enabled": ("work", "auto_execute_enabled"),
    "work.auto_execute.max_concurrent": ("work", "auto_execute_max_concurrent"),
    "work.auto_execute.safe_only": ("work", "auto_execute_safe_only"),
    "work.auto_execute.quiet_hours_respect": ("work", "auto_execute_quiet_hours_respect"),
    "work.auto_execute.fail_open": ("work", "auto_execute_fail_open"),
}


@dataclass
class ValidationFailure:
    error: str
    module: str
    schema_version_expected: int
    errors: list[dict[str, Any]]


def module_for_key(key: str) -> Optional[str]:
    if key in KEY_TO_FIELD:
        return KEY_TO_FIELD[key][0]
    for module in SCHEMA_REGISTRY:
        prefix = f"{module}."
        if key.startswith(prefix):
            return module
    return None


def expected_schema_version(module: str) -> int:
    model_cls = SCHEMA_REGISTRY[module]
    return int(model_cls.model_fields["schema_version"].default or 1)


def default_value_for_key(key: str) -> tuple[Any, int] | None:
    mapping = KEY_TO_FIELD.get(key)
    if not mapping:
        return None
    module, field_name = mapping
    model_cls = SCHEMA_REGISTRY[module]
    instance = model_cls()
    return getattr(instance, field_name), expected_schema_version(module)


def validate_config_entry(
    *,
    key: str,
    value: Any,
    schema_version: int,
) -> ValidationFailure | None:
    mapping = KEY_TO_FIELD.get(key)
    if mapping is None:
        module = module_for_key(key)
        if not module:
            return ValidationFailure(
                error="CONFIG_SCHEMA_VALIDATION_FAILED",
                module="unknown",
                schema_version_expected=1,
                errors=[{"path": "key", "message": f"Unsupported config key: {key}"}],
            )
        expected = expected_schema_version(module)
        return ValidationFailure(
            error="CONFIG_SCHEMA_VALIDATION_FAILED",
            module=module,
            schema_version_expected=expected,
            errors=[{"path": "key", "message": f"Unsupported config key in module {module}: {key}"}],
        )

    module, field_name = mapping
    expected = expected_schema_version(module)
    if schema_version != expected:
        return ValidationFailure(
            error="CONFIG_SCHEMA_VALIDATION_FAILED",
            module=module,
            schema_version_expected=expected,
            errors=[{"path": "schema_version", "message": f"Expected {expected}, got {schema_version}"}],
        )

    model_cls = SCHEMA_REGISTRY[module]
    try:
        model_cls.model_validate({"schema_version": schema_version, field_name: value}, strict=True)
    except ValidationError as exc:
        errors = []
        for issue in exc.errors():
            path = ".".join(str(p) for p in issue.get("loc", []))
            errors.append({"path": path, "message": issue.get("msg", "Invalid value")})
        return ValidationFailure(
            error="CONFIG_SCHEMA_VALIDATION_FAILED",
            module=module,
            schema_version_expected=expected,
            errors=errors,
        )
    return None
