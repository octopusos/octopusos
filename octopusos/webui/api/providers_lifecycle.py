"""Provider lifecycle helpers for executable detection and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel, Field

from octopusos.providers import platform_utils
from octopusos.providers.providers_config import ProvidersConfigManager


class DetectExecutableResponse(BaseModel):
    executable_path: Optional[str] = Field(None, description="Detected executable path")
    version: Optional[str] = Field(None, description="Detected version string")


class ValidateExecutableResponse(BaseModel):
    is_valid: bool = Field(..., description="Whether the executable path is valid")
    version: Optional[str] = Field(None, description="Detected version string")
    error: Optional[str] = Field(None, description="Validation error details")


def get_executable_version(executable_path: str | Path) -> Optional[str]:
    return platform_utils.get_executable_version(Path(executable_path))


class ProviderDiagnosticsResponse(BaseModel):
    provider_id: str
    platform: str
    detected_executable: Optional[str] = None
    configured_executable: Optional[str] = None
    resolved_executable: Optional[str] = None
    detection_source: Optional[str] = None
    version: Optional[str] = None
    supported_actions: List[str] = []
    current_status: Optional[str] = None
    pid: Optional[int] = None
    port: Optional[int] = None
    port_listening: Optional[bool] = None
    models_directory: Optional[str] = None
    models_count: Optional[int] = None
    last_error: Optional[str] = None


async def get_provider_diagnostics(provider_id: str) -> ProviderDiagnosticsResponse:
    """
    Minimal diagnostics implementation used by tests.

    Returns stable schema without requiring live providers.
    """
    config_mgr = ProvidersConfigManager()
    raw_provider = config_mgr._config.get("providers", {}).get(provider_id)
    provider_config = config_mgr.get_provider_config(provider_id)

    supported_actions: List[str] = []
    if provider_config is not None:
        supported_actions = list(provider_config.supported_actions)

    configured_executable = None
    auto_detect = True
    if raw_provider:
        configured_executable = raw_provider.get("executable_path")
        auto_detect = raw_provider.get("auto_detect", True)

    detected_executable = None
    detection_source = None
    resolved_executable = None
    version = None

    if configured_executable:
        detection_source = "configured"
        resolved_executable = configured_executable
    elif auto_detect:
        exe_map = {
            "ollama": "ollama",
            "llamacpp": "llama-server",
            "lmstudio": "lmstudio",
        }
        exe_name = exe_map.get(provider_id, provider_id)
        detected_path = platform_utils.find_executable(exe_name)
        if detected_path:
            detected_executable = str(detected_path)
            detection_source = "auto_detect"
            resolved_executable = detected_executable
            version = platform_utils.get_executable_version(detected_path)

    models_directory = None
    try:
        models_dir = platform_utils.get_models_dir(provider_id)
        if models_dir is not None:
            models_directory = str(models_dir)
    except Exception:
        models_directory = None

    last_error = None
    if raw_provider is None:
        last_error = f"Provider '{provider_id}' not configured"

    return ProviderDiagnosticsResponse(
        provider_id=provider_id,
        platform=platform_utils.get_platform(),
        detected_executable=detected_executable,
        configured_executable=configured_executable,
        resolved_executable=resolved_executable,
        detection_source=detection_source,
        version=version,
        supported_actions=supported_actions,
        current_status=None,
        pid=None,
        port=None,
        port_listening=None,
        models_directory=models_directory,
        models_count=None,
        last_error=last_error,
    )
