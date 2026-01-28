"""
Provider Lifecycle Management API

Manages provider installation and process lifecycle:
- Start/stop provider services (e.g., llama-server)
- Install providers via brew (macOS)
- Open apps (e.g., LM Studio)
- Process status and output logs

Sprint B+ Provider Architecture Refactor
"""

import asyncio
import logging
import shutil
import subprocess
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/providers")


# ============================================================================
# Request/Response Models
# ============================================================================


class StartInstanceRequest(BaseModel):
    """Request to start a provider instance"""
    instance_id: str = Field(..., description="Instance identifier")
    launch_config: Optional[Dict[str, Any]] = Field(None, description="Override launch config")


class StartInstanceResponse(BaseModel):
    """Response for start instance"""
    ok: bool
    instance_key: str
    pid: Optional[int] = None
    message: str


class StopInstanceRequest(BaseModel):
    """Request to stop a provider instance"""
    instance_id: str = Field(..., description="Instance identifier")
    force: bool = Field(False, description="Force kill (SIGKILL)")


class StopInstanceResponse(BaseModel):
    """Response for stop instance"""
    ok: bool
    instance_key: str
    message: str


class ProcessStatusResponse(BaseModel):
    """Process status for a provider instance"""
    instance_key: str
    running: bool
    pid: Optional[int] = None
    command: Optional[str] = None
    started_at: Optional[float] = None
    uptime_seconds: Optional[float] = None
    returncode: Optional[int] = None


class ProcessOutputResponse(BaseModel):
    """Process output logs"""
    instance_key: str
    stdout: List[str]
    stderr: List[str]


class InstallProviderRequest(BaseModel):
    """Request to install a provider via brew"""
    provider_id: str = Field(..., description="Provider ID (ollama, llamacpp)")


class InstallProviderResponse(BaseModel):
    """Response for provider installation"""
    ok: bool
    provider_id: str
    message: str
    command: Optional[str] = None


class CLICheckResponse(BaseModel):
    """CLI binary check response"""
    provider_id: str
    cli_found: bool
    bin_path: Optional[str] = None
    version: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================


def check_cli_installed(bin_name: str) -> tuple[bool, Optional[str]]:
    """
    Check if CLI binary is installed

    Returns: (found, path)
    """
    path = shutil.which(bin_name)
    return (path is not None, path)


async def run_brew_install(package: str) -> tuple[bool, str]:
    """
    Install package via brew

    Returns: (success, message)
    """
    try:
        # Check if brew is installed
        if not shutil.which("brew"):
            return False, "Homebrew not installed. Install from https://brew.sh"

        # Run brew install
        logger.info(f"Installing {package} via brew...")
        process = await asyncio.create_subprocess_exec(
            "brew", "install", package,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return True, f"Successfully installed {package}"
        else:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            return False, f"brew install failed: {error_msg}"

    except Exception as e:
        logger.error(f"Failed to install {package}: {e}")
        return False, f"Installation failed: {e}"


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/{provider_id}/instances/start", response_model=StartInstanceResponse)
async def start_provider_instance(
    provider_id: str,
    request: StartInstanceRequest,
):
    """
    Start a provider instance

    Supports locally-managed providers (e.g., llamacpp)
    """
    from agentos.providers.process_manager import ProcessManager
    from agentos.providers.providers_config import ProvidersConfigManager

    try:
        # Get configuration
        config_mgr = ProvidersConfigManager()
        provider_config = config_mgr.get_provider_config(provider_id)

        if not provider_config:
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

        # Find instance
        instance_config = None
        for inst in provider_config.instances:
            if inst.id == request.instance_id:
                instance_config = inst
                break

        if not instance_config:
            raise HTTPException(
                status_code=404,
                detail=f"Instance {request.instance_id} not found for provider {provider_id}"
            )

        # Check if instance has launch config
        if not instance_config.launch:
            raise HTTPException(
                status_code=400,
                detail=f"Instance {request.instance_id} does not have launch configuration"
            )

        # Use override launch config if provided
        launch_config = request.launch_config or instance_config.launch.args
        bin_name = instance_config.launch.bin

        # Start process
        process_mgr = ProcessManager.get_instance()
        instance_key = f"{provider_id}:{request.instance_id}"

        success, message = await process_mgr.start_process(
            instance_key=instance_key,
            bin_name=bin_name,
            args=launch_config,
        )

        if not success:
            raise HTTPException(status_code=500, detail=message)

        # Get PID
        proc_info = process_mgr.get_process_info(instance_key)
        pid = proc_info.pid if proc_info else None

        return StartInstanceResponse(
            ok=True,
            instance_key=instance_key,
            pid=pid,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start instance {provider_id}:{request.instance_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start instance: {e}")


@router.post("/{provider_id}/instances/stop", response_model=StopInstanceResponse)
async def stop_provider_instance(
    provider_id: str,
    request: StopInstanceRequest,
):
    """Stop a provider instance"""
    from agentos.providers.process_manager import ProcessManager

    try:
        process_mgr = ProcessManager.get_instance()
        instance_key = f"{provider_id}:{request.instance_id}"

        success, message = await process_mgr.stop_process(
            instance_key=instance_key,
            force=request.force,
        )

        if not success:
            raise HTTPException(status_code=500, detail=message)

        return StopInstanceResponse(
            ok=True,
            instance_key=instance_key,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop instance {provider_id}:{request.instance_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop instance: {e}")


@router.get("/{provider_id}/instances/{instance_id}/status", response_model=ProcessStatusResponse)
async def get_instance_status(provider_id: str, instance_id: str):
    """Get status of a provider instance"""
    from agentos.providers.process_manager import ProcessManager

    try:
        process_mgr = ProcessManager.get_instance()
        instance_key = f"{provider_id}:{instance_id}"

        proc_info = process_mgr.get_process_info(instance_key)

        if not proc_info:
            # Not managed by process manager
            return ProcessStatusResponse(
                instance_key=instance_key,
                running=False,
                pid=None,
                command=None,
            )

        running = process_mgr.is_process_running(instance_key)

        return ProcessStatusResponse(
            instance_key=instance_key,
            running=running,
            pid=proc_info.pid,
            command=proc_info.command,
            started_at=proc_info.started_at,
            uptime_seconds=None if not running else (asyncio.get_event_loop().time() - proc_info.started_at),
            returncode=proc_info.returncode,
        )

    except Exception as e:
        logger.error(f"Failed to get instance status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


@router.get("/{provider_id}/instances/{instance_id}/output", response_model=ProcessOutputResponse)
async def get_instance_output(
    provider_id: str,
    instance_id: str,
    lines: int = 100,
):
    """Get process output logs"""
    from agentos.providers.process_manager import ProcessManager

    try:
        process_mgr = ProcessManager.get_instance()
        instance_key = f"{provider_id}:{instance_id}"

        stdout = process_mgr.get_process_output(instance_key, lines=lines, stream="stdout")
        stderr = process_mgr.get_process_output(instance_key, lines=lines, stream="stderr")

        return ProcessOutputResponse(
            instance_key=instance_key,
            stdout=stdout,
            stderr=stderr,
        )

    except Exception as e:
        logger.error(f"Failed to get instance output: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get output: {e}")


@router.post("/{provider_id}/install", response_model=InstallProviderResponse)
async def install_provider(provider_id: str):
    """
    Install provider via brew (macOS only)

    Supported providers:
    - ollama: brew install ollama
    - llamacpp: brew install llama.cpp
    """
    # Map provider IDs to brew packages
    brew_packages = {
        "ollama": "ollama",
        "llamacpp": "llama.cpp",
    }

    package = brew_packages.get(provider_id)
    if not package:
        raise HTTPException(
            status_code=400,
            detail=f"Provider {provider_id} does not support brew installation"
        )

    success, message = await run_brew_install(package)

    if not success:
        raise HTTPException(status_code=500, detail=message)

    return InstallProviderResponse(
        ok=True,
        provider_id=provider_id,
        message=message,
        command=f"brew install {package}",
    )


@router.get("/{provider_id}/cli-check", response_model=CLICheckResponse)
async def check_provider_cli(provider_id: str):
    """
    Check if provider CLI is installed

    Checks for binary in PATH
    """
    # Map provider IDs to CLI binary names
    cli_binaries = {
        "ollama": "ollama",
        "llamacpp": "llama-server",
        "lmstudio": "lms",  # LM Studio CLI (if installed)
    }

    bin_name = cli_binaries.get(provider_id)
    if not bin_name:
        raise HTTPException(
            status_code=400,
            detail=f"Provider {provider_id} does not have a CLI binary"
        )

    found, path = check_cli_installed(bin_name)

    # Try to get version
    version = None
    if found and path:
        try:
            result = subprocess.run(
                [bin_name, "--version"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
        except:
            pass

    return CLICheckResponse(
        provider_id=provider_id,
        cli_found=found,
        bin_path=path,
        version=version,
    )


@router.post("/lmstudio/open-app")
async def open_lmstudio_app():
    """
    Open LM Studio application (macOS only)

    Uses 'open -a "LM Studio"' command
    """
    try:
        # Check if LM Studio is installed
        result = subprocess.run(
            ["open", "-a", "LM Studio"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=404,
                detail="LM Studio application not found. Install from https://lmstudio.ai"
            )

        return {
            "ok": True,
            "message": "LM Studio opened successfully"
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Timeout opening LM Studio")
    except Exception as e:
        logger.error(f"Failed to open LM Studio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to open LM Studio: {e}")
