"""
Provider Instances Configuration API

Manages provider instances configuration (CRUD):
- List all provider instances with detailed status
- Add/update/remove instances
- Get instance configuration
- Update launch configurations

Sprint B+ WebUI Integration
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/providers/instances")


# ============================================================================
# Request/Response Models
# ============================================================================


class InstanceLaunchConfig(BaseModel):
    """Launch configuration for locally-managed providers"""
    bin: str = Field(..., description="Binary name (e.g., llama-server)")
    args: Dict[str, Any] = Field(default_factory=dict, description="Launch arguments")


class InstanceConfigRequest(BaseModel):
    """Request to create/update an instance"""
    instance_id: str = Field(..., description="Instance identifier")
    base_url: str = Field(..., description="Base URL/endpoint")
    enabled: bool = Field(True, description="Whether instance is enabled")
    launch: Optional[InstanceLaunchConfig] = Field(None, description="Launch config for local providers")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class InstanceStatusDetail(BaseModel):
    """Detailed instance status including fingerprint"""
    instance_key: str
    provider_id: str
    instance_id: str
    base_url: str
    enabled: bool

    # Status from probe
    state: str  # READY / ERROR / DISCONNECTED
    reason_code: Optional[str] = None
    last_error: Optional[str] = None
    hint: Optional[str] = None
    latency_ms: Optional[float] = None

    # Fingerprint detection
    detected_fingerprint: Optional[str] = None  # ollama / llamacpp / openai_compatible / unknown
    fingerprint_metadata: Optional[Dict[str, Any]] = None

    # Process status (for locally-managed)
    process_running: Optional[bool] = None
    process_pid: Optional[int] = None

    # Configuration
    has_launch_config: bool = False
    launch_config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InstancesListResponse(BaseModel):
    """Response for listing all instances"""
    instances: List[InstanceStatusDetail]


class InstanceConfigResponse(BaseModel):
    """Response for get/update instance config"""
    ok: bool
    instance_key: str
    config: Dict[str, Any]


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=InstancesListResponse)
async def list_all_instances():
    """
    List all provider instances with detailed status

    Includes:
    - Configuration (base_url, enabled, launch config)
    - Probe status (state, reason_code, error)
    - Fingerprint detection result
    - Process status (for locally-managed)
    """
    from agentos.providers.registry import ProviderRegistry
    from agentos.providers.providers_config import ProvidersConfigManager
    from agentos.providers.process_manager import ProcessManager
    from agentos.providers.fingerprint import detect_service_fingerprint

    try:
        registry = ProviderRegistry.get_instance()
        config_mgr = ProvidersConfigManager()
        process_mgr = ProcessManager.get_instance()

        instances_detail = []

        # Get all providers from registry
        providers = registry.list_all()

        for provider in providers:
            # Skip cloud providers (managed separately)
            if provider.type.value == "cloud":
                continue

            # Get configuration
            provider_config = config_mgr.get_provider_config(provider.provider_id)
            if not provider_config:
                continue

            # Find matching instance config
            instance_config = None
            for inst in provider_config.instances:
                if inst.id == provider.instance_id:
                    instance_config = inst
                    break

            if not instance_config:
                continue

            # Probe provider
            status = await provider.probe()

            # Detect fingerprint
            detected_fp, fp_meta = await detect_service_fingerprint(
                provider.endpoint, timeout=1.0
            )

            # Get process status
            instance_key = f"{provider.provider_id}:{provider.instance_id}"
            process_running = process_mgr.is_process_running(instance_key)
            proc_info = process_mgr.get_process_info(instance_key)
            process_pid = proc_info.pid if proc_info else None

            # Build response
            detail = InstanceStatusDetail(
                instance_key=provider.id,
                provider_id=provider.provider_id,
                instance_id=provider.instance_id,
                base_url=instance_config.base_url,
                enabled=instance_config.enabled,
                state=status.state.value,
                reason_code=status.reason_code,
                last_error=status.last_error,
                hint=status.hint,
                latency_ms=status.latency_ms,
                detected_fingerprint=detected_fp.value,
                fingerprint_metadata=fp_meta,
                process_running=process_running,
                process_pid=process_pid,
                has_launch_config=instance_config.launch is not None,
                launch_config={
                    "bin": instance_config.launch.bin,
                    "args": instance_config.launch.args,
                } if instance_config.launch else None,
                metadata=instance_config.metadata,
            )

            instances_detail.append(detail)

        return InstancesListResponse(instances=instances_detail)

    except Exception as e:
        logger.error(f"Failed to list instances: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list instances: {e}")


@router.get("/{provider_id}/{instance_id}", response_model=InstanceConfigResponse)
async def get_instance_config(provider_id: str, instance_id: str):
    """Get configuration for a specific instance"""
    from agentos.providers.providers_config import ProvidersConfigManager

    try:
        config_mgr = ProvidersConfigManager()
        provider_config = config_mgr.get_provider_config(provider_id)

        if not provider_config:
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

        # Find instance
        for inst in provider_config.instances:
            if inst.id == instance_id:
                config_dict = {
                    "instance_id": inst.id,
                    "base_url": inst.base_url,
                    "enabled": inst.enabled,
                    "metadata": inst.metadata,
                }

                if inst.launch:
                    config_dict["launch"] = {
                        "bin": inst.launch.bin,
                        "args": inst.launch.args,
                    }

                return InstanceConfigResponse(
                    ok=True,
                    instance_key=f"{provider_id}:{instance_id}",
                    config=config_dict,
                )

        raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get instance config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {e}")


@router.post("/{provider_id}", response_model=InstanceConfigResponse)
async def add_instance(provider_id: str, request: InstanceConfigRequest):
    """Add a new instance to a provider"""
    from agentos.providers.providers_config import ProvidersConfigManager, LaunchConfig

    try:
        config_mgr = ProvidersConfigManager()

        # Build launch config if provided
        launch = None
        if request.launch:
            launch = LaunchConfig(
                bin=request.launch.bin,
                args=request.launch.args,
            )

        # Add instance
        config_mgr.add_instance(
            provider_id=provider_id,
            instance_id=request.instance_id,
            base_url=request.base_url,
            enabled=request.enabled,
            launch=launch,
        )

        # Update metadata
        if request.metadata:
            config_mgr.update_instance(
                provider_id=provider_id,
                instance_id=request.instance_id,
                metadata=request.metadata,
            )

        # Get updated config
        provider_config = config_mgr.get_provider_config(provider_id)
        inst = next((i for i in provider_config.instances if i.id == request.instance_id), None)

        config_dict = {
            "instance_id": inst.id,
            "base_url": inst.base_url,
            "enabled": inst.enabled,
            "metadata": inst.metadata,
        }

        if inst.launch:
            config_dict["launch"] = {
                "bin": inst.launch.bin,
                "args": inst.launch.args,
            }

        return InstanceConfigResponse(
            ok=True,
            instance_key=f"{provider_id}:{request.instance_id}",
            config=config_dict,
        )

    except Exception as e:
        logger.error(f"Failed to add instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add instance: {e}")


@router.put("/{provider_id}/{instance_id}", response_model=InstanceConfigResponse)
async def update_instance(provider_id: str, instance_id: str, request: InstanceConfigRequest):
    """Update an existing instance"""
    from agentos.providers.providers_config import ProvidersConfigManager, LaunchConfig

    try:
        config_mgr = ProvidersConfigManager()

        # Build launch config if provided
        launch = None
        if request.launch:
            launch = LaunchConfig(
                bin=request.launch.bin,
                args=request.launch.args,
            )

        # Update instance
        config_mgr.update_instance(
            provider_id=provider_id,
            instance_id=instance_id,
            base_url=request.base_url,
            enabled=request.enabled,
            launch=launch,
            metadata=request.metadata,
        )

        # Get updated config
        provider_config = config_mgr.get_provider_config(provider_id)
        inst = next((i for i in provider_config.instances if i.id == instance_id), None)

        if not inst:
            raise HTTPException(status_code=404, detail="Instance not found after update")

        config_dict = {
            "instance_id": inst.id,
            "base_url": inst.base_url,
            "enabled": inst.enabled,
            "metadata": inst.metadata,
        }

        if inst.launch:
            config_dict["launch"] = {
                "bin": inst.launch.bin,
                "args": inst.launch.args,
            }

        return InstanceConfigResponse(
            ok=True,
            instance_key=f"{provider_id}:{instance_id}",
            config=config_dict,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update instance: {e}")


@router.delete("/{provider_id}/{instance_id}")
async def delete_instance(provider_id: str, instance_id: str):
    """Delete an instance"""
    from agentos.providers.providers_config import ProvidersConfigManager

    try:
        config_mgr = ProvidersConfigManager()

        success = config_mgr.remove_instance(provider_id, instance_id)

        if not success:
            raise HTTPException(status_code=404, detail="Instance not found")

        return {"ok": True, "message": f"Instance {provider_id}:{instance_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete instance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete instance: {e}")
