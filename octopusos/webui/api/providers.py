"""Providers API endpoints (executable detection, instances, models)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from octopusos.providers import platform_utils
from octopusos.core.status_store import StatusStore
from octopusos.providers.process_manager import ProcessManager
from octopusos.providers.providers_config import ProvidersConfigManager
from octopusos.providers.registry import ProviderRegistry
from octopusos.providers.base import ProviderType

router = APIRouter(prefix="/api/providers", tags=["providers"])
logger = logging.getLogger(__name__)


class ValidateExecutableRequest(BaseModel):
    path: Optional[str] = Field(None, description="Executable path to validate")


class SetExecutableRequest(BaseModel):
    path: Optional[str] = Field(None, description="Executable path to set")
    auto_detect: bool = Field(False, description="Auto-detect executable path")


class ModelsDirectoryRequest(BaseModel):
    provider_id: str
    path: str


class InstanceRequest(BaseModel):
    id: str
    base_url: str
    enabled: bool = True


def _get_config_manager() -> ProvidersConfigManager:
    get_instance = getattr(ProvidersConfigManager, "get_instance", None)
    if callable(get_instance):
        return get_instance()
    return ProvidersConfigManager()


def _provider_ids() -> List[str]:
    manager = _get_config_manager()
    return list(manager._config.get("providers", {}).keys())


def _get_instances(provider_id: str) -> List[Dict[str, Any]]:
    manager = _get_config_manager()
    get_instances = getattr(manager, "get_instances", None)
    if callable(get_instances):
        return get_instances(provider_id)
    return manager._config.get("providers", {}).get(provider_id, {}).get("instances", [])


def _instance_exists(provider_id: str, instance_id: str) -> bool:
    return any(inst.get("id") == instance_id for inst in _get_instances(provider_id))


def _provider_label(provider_id: str) -> str:
    label_map = {
        "ollama": "Ollama",
        "lmstudio": "LM Studio",
        "llamacpp": "Llama.cpp",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
    }
    return label_map.get(provider_id, provider_id)


def _provider_executable_name(provider_id: str) -> str:
    name_map = {
        "ollama": "ollama",
        "llamacpp": "llama-server",
        "lmstudio": "lmstudio",
    }
    return name_map.get(provider_id, provider_id)


def _candidate_search_paths(executable_name: str) -> List[str]:
    candidates: List[str] = []

    for standard in platform_utils.get_standard_paths(executable_name):
        candidates.append(str(standard))

    path_env = os.environ.get("PATH", "")
    if path_env:
        for dir_path in path_env.split(os.pathsep):
            if not dir_path:
                continue
            candidates.append(str(Path(dir_path) / executable_name))

    # De-duplicate while preserving order
    return list(dict.fromkeys(candidates))


@router.get("")
def list_providers() -> Dict[str, List[Dict[str, Any]]]:
    registry = ProviderRegistry.get_instance()
    config_manager = _get_config_manager()

    local: List[Dict[str, Any]] = []
    cloud: List[Dict[str, Any]] = []

    for provider in registry.list_all():
        provider_base_id = provider.provider_id
        provider_type = provider.type

        supports_start = False
        if provider_type == ProviderType.LOCAL:
            config = config_manager.get_provider_config(provider_base_id)
            if config is not None:
                supports_start = (
                    not config.manual_lifecycle and
                    "start" in (config.supported_actions or [])
                )
            else:
                supports_start = provider_base_id in {"ollama", "llamacpp"}

        supports_auth: List[str] = ["api_key"] if provider_type == ProviderType.CLOUD else []
        payload = {
            "id": provider.id,
            "label": _provider_label(provider_base_id),
            "type": provider_type.value,
            "supports_models": True,
            "supports_start": supports_start,
            "supports_auth": supports_auth,
        }

        if provider_type == ProviderType.CLOUD:
            cloud.append(payload)
        else:
            local.append(payload)

    return {"local": local, "cloud": cloud}


@router.get("/{provider_id}/executable/detect")
def detect_executable(provider_id: str):
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")

    config_manager = _get_config_manager()
    raw_provider = config_manager._config.get("providers", {}).get(provider_id, {})
    custom_path = raw_provider.get("executable_path")
    auto_detect = raw_provider.get("auto_detect", True)

    executable_name = _provider_executable_name(provider_id)
    search_paths = _candidate_search_paths(executable_name)

    resolved_path: Optional[Path] = None
    detection_source: Optional[str] = None

    if custom_path:
        custom_candidate = Path(custom_path)
        if platform_utils.validate_executable(custom_candidate):
            resolved_path = custom_candidate
            detection_source = "config"

    if resolved_path is None and auto_detect:
        for standard in platform_utils.get_standard_paths(executable_name):
            if platform_utils.validate_executable(standard):
                resolved_path = standard
                detection_source = "standard"
                break

        if resolved_path is None:
            path_hit = platform_utils.find_in_path(executable_name)
            if path_hit:
                resolved_path = path_hit
                detection_source = "path"

    version = platform_utils.get_executable_version(resolved_path) if resolved_path else None

    return {
        "detected": resolved_path is not None,
        "path": str(resolved_path) if resolved_path else None,
        "custom_path": custom_path,
        "resolved_path": str(resolved_path) if resolved_path else None,
        "version": version,
        "platform": platform_utils.get_platform(),
        "search_paths": search_paths,
        "is_valid": resolved_path is not None,
        "detection_source": detection_source,
    }


@router.post("/{provider_id}/executable/validate")
def validate_executable(provider_id: str, payload: ValidateExecutableRequest):
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    if not payload.path:
        raise HTTPException(status_code=400, detail="path is required")

    validation = platform_utils.validate_executable_detailed(Path(payload.path))
    return {
        "is_valid": validation.get("is_valid", False),
        "path": str(payload.path),
        "exists": validation.get("exists", False),
        "is_executable": validation.get("is_executable", False),
        "version": validation.get("version"),
        "error": validation.get("error"),
    }


@router.put("/{provider_id}/executable")
def set_executable(provider_id: str, payload: SetExecutableRequest):
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")

    config_manager = _get_config_manager()

    try:
        if payload.auto_detect:
            config_manager.set_executable_path(provider_id, None)
            return {"ok": True, "path": None, "message": "Auto-detection enabled"}
        if not payload.path:
            raise HTTPException(status_code=400, detail="path or auto_detect required")

        config_manager.set_executable_path(provider_id, payload.path)
        return {"ok": True, "path": payload.path, "message": "Executable path updated"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models/directories")
def get_models_directories() -> Dict[str, Optional[str]]:
    return {pid: str(platform_utils.get_models_dir(pid)) for pid in _provider_ids()}


@router.put("/models/directories")
def set_models_directory(payload: ModelsDirectoryRequest):
    if payload.provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    return {"ok": True, "provider_id": payload.provider_id, "path": payload.path}


@router.get("/models/directories/detect")
def detect_models_directories() -> Dict[str, Optional[str]]:
    return {pid: str(platform_utils.get_models_dir(pid)) for pid in _provider_ids()}


@router.get("/models/files")
def list_models_files(provider_id: Optional[str] = Query(None)):
    if not provider_id:
        raise HTTPException(status_code=400, detail="provider_id is required")
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    models_dir = platform_utils.get_models_dir(provider_id)
    if not models_dir or not models_dir.exists():
        raise HTTPException(status_code=404, detail="Models directory not found")
    if not models_dir.is_dir():
        raise HTTPException(status_code=400, detail="Models directory is not a directory")
    return [path.name for path in models_dir.iterdir()]


@router.get("/{provider_id}/models")
async def list_provider_models(provider_id: str) -> Dict[str, Any]:
    registry = ProviderRegistry.get_instance()
    provider = registry.get(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Unknown provider")

    models = await provider.list_models()
    return {
        "models": [
            {
                "id": m.id,
                "name": m.label or m.id,
                "label": m.label or m.id,
                "metadata": m.metadata or {},
            }
            for m in models
        ],
        "total": len(models),
    }


@router.get("/{provider_id}/instances")
def list_instances(provider_id: str) -> List[Dict[str, Any]]:
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    return _get_instances(provider_id)


@router.post("/{provider_id}/instances")
def add_instance(provider_id: str, payload: InstanceRequest):
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    return {"ok": True, "instance": payload.model_dump()}


@router.delete("/{provider_id}/instances/{instance_id}")
def delete_instance(provider_id: str, instance_id: str):
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    return {"ok": True, "instance_id": instance_id}


@router.post("/{provider_id}/instances/{instance_id}/start")
def start_instance(provider_id: str, instance_id: str):
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    if not _instance_exists(provider_id, instance_id):
        raise HTTPException(status_code=404, detail="Unknown instance")
    manager = ProcessManager.get_instance()
    return {"ok": True, "status": "started", "running": manager.is_process_running(f"{provider_id}:{instance_id}")}


@router.post("/{provider_id}/instances/{instance_id}/stop")
def stop_instance(provider_id: str, instance_id: str):
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    if not _instance_exists(provider_id, instance_id):
        raise HTTPException(status_code=404, detail="Unknown instance")
    manager = ProcessManager.get_instance()
    return {"ok": True, "status": "stopped", "running": manager.is_process_running(f"{provider_id}:{instance_id}")}


@router.post("/{provider_id}/instances/{instance_id}/restart")
def restart_instance(provider_id: str, instance_id: str):
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    if not _instance_exists(provider_id, instance_id):
        raise HTTPException(status_code=404, detail="Unknown instance")
    return {"ok": True, "status": "restarted"}


@router.get("/{provider_id}/instances/{instance_id}/status")
def instance_status(provider_id: str, instance_id: str):
    if provider_id not in _provider_ids():
        raise HTTPException(status_code=404, detail="Unknown provider")
    if not _instance_exists(provider_id, instance_id):
        raise HTTPException(status_code=404, detail="Unknown instance")
    manager = ProcessManager.get_instance()
    running = manager.is_process_running(f"{provider_id}:{instance_id}")
    return {"status": "running" if running else "stopped", "running": running}


@router.post("/refresh")
async def refresh_providers_status(provider_id: str | None = None):
    store = StatusStore.get_instance()
    if provider_id:
        store.invalidate_provider(provider_id)
        logger.info(f"Triggered refresh for provider: {provider_id}")
        return {
            "status": "refresh_triggered",
            "provider_id": provider_id,
            "message": f"Refresh triggered for provider {provider_id}",
        }
    store.invalidate_all_providers()
    logger.info("Triggered refresh for all providers")
    return {
        "status": "refresh_triggered",
        "scope": "all",
        "message": "Refresh triggered for all providers",
    }
