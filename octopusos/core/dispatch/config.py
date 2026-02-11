"""Dispatch configuration for auto-execution policies."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from octopusos.core.capabilities.permissions import PermissionChecker, DeploymentMode


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DispatchConfig:
    auto_execute_enabled: bool
    auto_execute_max_risk: str
    max_attempts: int
    deployment_mode: DeploymentMode


def load_dispatch_config() -> DispatchConfig:
    checker = PermissionChecker()
    mode = checker.mode

    # Default: disabled in LOCAL_LOCKED, enabled in LOCAL_OPEN unless overridden.
    default_enabled = False if mode == DeploymentMode.LOCAL_LOCKED else True
    auto_execute_enabled = _env_bool("DISPATCH_AUTO_EXECUTE_ENABLED", default_enabled)
    max_risk = os.getenv("DISPATCH_AUTO_EXECUTE_MAX_RISK", "medium").lower()

    try:
        max_attempts = int(os.getenv("DISPATCH_EXECUTION_MAX_ATTEMPTS", "3"))
    except ValueError:
        max_attempts = 3

    return DispatchConfig(
        auto_execute_enabled=auto_execute_enabled,
        auto_execute_max_risk=max_risk,
        max_attempts=max_attempts,
        deployment_mode=mode,
    )
