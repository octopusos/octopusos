"""
Provider Lifecycle Management API

Manages provider installation and process lifecycle:
- Start/stop provider services (e.g., llama-server)
- Install providers via brew (macOS)
- Open apps (e.g., LM Studio)
- Process status and output logs

Sprint B+ Provider Architecture Refactor
Phase 3.3: Unified Error Handling
"""

import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from agentos.webui.api import providers_errors
from agentos.providers.logging_utils import get_provider_logger, OperationTimer

logger = logging.getLogger(__name__)
provider_logger = get_provider_logger()

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
    old_pid: Optional[int] = None


class RestartInstanceRequest(BaseModel):
    """Request to restart a provider instance"""
    instance_id: str = Field(..., description="Instance identifier")
    force: bool = Field(False, description="Force kill before restart")
    launch_config: Optional[Dict[str, Any]] = Field(None, description="Override launch config")


class RestartInstanceResponse(BaseModel):
    """Response for restart instance"""
    ok: bool
    instance_key: str
    message: str
    old_pid: Optional[int] = None
    new_pid: Optional[int] = None


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


class ProviderCapabilitiesResponse(BaseModel):
    """Provider capabilities and supported actions"""
    provider_id: str
    manual_lifecycle: bool
    supported_actions: List[str]
    enabled: bool


class DetectExecutableResponse(BaseModel):
    """Response for executable detection with enhanced path information"""
    detected: bool
    path: Optional[str] = None  # Auto-detected path (standard paths or PATH)
    custom_path: Optional[str] = None  # User-configured path from config
    resolved_path: Optional[str] = None  # Final resolved path (considering priority)
    version: Optional[str] = None
    platform: str
    search_paths: List[str]
    is_valid: bool
    detection_source: Optional[str] = None  # 'config', 'standard', or 'path'


class ValidateExecutableRequest(BaseModel):
    """Request to validate an executable path"""
    path: str = Field(..., description="Path to the executable file")


class ValidateExecutableResponse(BaseModel):
    """Response for executable validation with detailed results"""
    is_valid: bool
    path: str
    exists: bool
    is_executable: bool
    version: Optional[str] = None
    error: Optional[str] = None


class SetExecutableRequest(BaseModel):
    """Request to set executable path"""
    path: Optional[str] = Field(None, description="Path to executable, or None for auto-detect")
    auto_detect: bool = Field(True, description="Enable automatic detection")


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


def get_executable_version(executable_path: Path) -> Optional[str]:
    """
    Get version of an executable by running --version command.

    Args:
        executable_path: Path to the executable

    Returns:
        Optional[str]: Version string if successful, None otherwise

    Note:
        Executes '{executable} --version' and captures output.
        Handles timeout and errors gracefully.
    """
    try:
        result = subprocess.run(
            [str(executable_path), "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Return the stdout stripped of whitespace
            return result.stdout.strip()
        else:
            # Some executables might return version on stderr
            stderr_output = result.stderr.strip()
            if stderr_output:
                return stderr_output
            return None
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout getting version for {executable_path}")
        return None
    except Exception as e:
        logger.debug(f"Failed to get version for {executable_path}: {e}")
        return None


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
    timeout: float = 30.0,
):
    """
    Start a provider instance with timeout control.

    Supports locally-managed providers (e.g., llamacpp)

    Args:
        provider_id: Provider identifier
        request: Start instance request with instance_id and optional launch_config
        timeout: Startup timeout in seconds (default: 30s)

    Returns:
        StartInstanceResponse with process info

    Raises:
        HTTPException: With standardized error format for various failure scenarios
    """
    from agentos.providers.process_manager import ProcessManager
    from agentos.providers.providers_config import ProvidersConfigManager

    instance_key = f"{provider_id}:{request.instance_id}"

    # Start operation timer
    with OperationTimer() as timer:
        try:
            # Log start of operation
            provider_logger.log_start(
                provider=provider_id,
                instance_key=instance_key
            )

            # Get configuration
            config_mgr = ProvidersConfigManager()
            provider_config = config_mgr.get_provider_config(provider_id)

            if not provider_config:
                providers_errors.raise_provider_error(
                    code=providers_errors.CONFIG_ERROR,
                    message=f"Provider '{provider_id}' not found in configuration",
                    details={"provider_id": provider_id},
                    suggestion="Check provider ID or configure the provider first",
                    status_code=404
                )

            # Find instance
            instance_config = None
            for inst in provider_config.instances:
                if inst.id == request.instance_id:
                    instance_config = inst
                    break

            if not instance_config:
                providers_errors.raise_provider_error(
                    code=providers_errors.CONFIG_ERROR,
                    message=f"Instance '{request.instance_id}' not found for provider '{provider_id}'",
                    details={
                        "provider_id": provider_id,
                        "instance_id": request.instance_id,
                        "available_instances": [inst.id for inst in provider_config.instances]
                    },
                    suggestion="Check instance ID or create the instance first",
                    status_code=404
                )

            # Check if instance has launch config
            if not instance_config.launch:
                providers_errors.raise_provider_error(
                    code=providers_errors.CONFIG_ERROR,
                    message=f"Instance '{request.instance_id}' does not have launch configuration",
                    details={
                        "instance_key": instance_key,
                        "provider_id": provider_id,
                        "instance_id": request.instance_id
                    },
                    suggestion="Add launch configuration to the instance before starting",
                    status_code=400
                )

            # Use override launch config if provided
            launch_config = request.launch_config or instance_config.launch.args
            bin_name = instance_config.launch.bin

            # Check if process is already running
            process_mgr = ProcessManager.get_instance()
            if process_mgr.is_process_running(instance_key):
                existing_info = process_mgr.get_process_info(instance_key)
                providers_errors.raise_provider_error(
                    code=providers_errors.PROCESS_ALREADY_RUNNING,
                    message=f"Instance '{instance_key}' is already running",
                    details={
                        "instance_key": instance_key,
                        "pid": existing_info.pid if existing_info else None
                    },
                    suggestion="Stop the instance first, or use restart endpoint",
                    status_code=409  # Conflict
                )

            # Start process with timeout
            try:
                success, message = await asyncio.wait_for(
                    process_mgr.start_process(
                        instance_key=instance_key,
                        bin_name=bin_name,
                        args=launch_config,
                    ),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Log timeout with structured logging
                provider_logger.log_start_failure(
                    provider=provider_id,
                    error_code=providers_errors.STARTUP_TIMEOUT,
                    elapsed_ms=timer.elapsed_ms(),
                    message=f"Startup timeout for {instance_key}",
                    instance_key=instance_key,
                    timeout_seconds=timeout
                )

                providers_errors.log_provider_error(
                    error_code=providers_errors.STARTUP_TIMEOUT,
                    message=f"Startup timeout for {instance_key}",
                    details={"timeout_seconds": timeout}
                )
                error_info = providers_errors.build_timeout_error(
                    operation="startup",
                    timeout_seconds=timeout,
                    instance_key=instance_key
                )
                providers_errors.raise_provider_error(**error_info)

            if not success:
                # Log failure with structured logging
                provider_logger.log_start_failure(
                    provider=provider_id,
                    error_code=providers_errors.PROCESS_START_FAILED,
                    resolved_exe=bin_name,
                    elapsed_ms=timer.elapsed_ms(),
                    message=message,
                    instance_key=instance_key
                )

                # Parse the error message to provide better context
                providers_errors.log_provider_error(
                    error_code=providers_errors.PROCESS_START_FAILED,
                    message=message,
                    details={"instance_key": instance_key}
                )

                # Check for common error patterns
                if "not found" in message.lower() or "no such file" in message.lower():
                    # Use detailed error builder with searched paths
                    from agentos.providers import platform_utils
                    exe_name = bin_name
                    searched_paths = [str(p) for p in platform_utils.get_standard_paths(exe_name)]
                    error_info = providers_errors.build_exe_not_found_error(
                        provider=provider_id.capitalize(),
                        searched_paths=searched_paths
                    )
                    providers_errors.raise_provider_error(**error_info)
                elif "permission denied" in message.lower():
                    error_info = providers_errors.build_permission_denied_error_detailed(
                        exe_path=bin_name
                    )
                    providers_errors.raise_provider_error(**error_info)
                elif "port" in message.lower() and ("in use" in message.lower() or "already" in message.lower()):
                    # Extract port if possible (basic extraction)
                    import re
                    port_match = re.search(r':(\d+)', instance_config.base_url)
                    port = int(port_match.group(1)) if port_match else None
                    if port:
                        error_info = providers_errors.build_port_in_use_error_detailed(
                            port=port,
                            provider=provider_id.capitalize()
                        )
                        providers_errors.raise_provider_error(**error_info)

                # Generic process start failure - get stderr from process manager
                proc_info = process_mgr.get_process_info(instance_key)
                stderr_output = ""
                if proc_info and proc_info.stderr_buffer:
                    stderr_output = '\n'.join(list(proc_info.stderr_buffer))

                # Get log file path
                log_file = str(process_mgr.log_dir / f"{instance_key.replace(':', '__')}.log")

                error_info = providers_errors.build_start_failed_error(
                    provider=provider_id.capitalize(),
                    exit_code=proc_info.returncode if proc_info else None,
                    stderr=stderr_output or message,
                    log_file=log_file,
                    instance_key=instance_key
                )
                providers_errors.raise_provider_error(**error_info)

            # Get PID
            proc_info = process_mgr.get_process_info(instance_key)
            pid = proc_info.pid if proc_info else None

            logger.info(f"Successfully started {instance_key} (PID: {pid})")

            # Log successful start with timing
            provider_logger.log_start_success(
                provider=provider_id,
                pid=pid,
                resolved_exe=bin_name,
                elapsed_ms=timer.elapsed_ms(),
                instance_key=instance_key
            )

            return StartInstanceResponse(
                ok=True,
                instance_key=instance_key,
                pid=pid,
                message=message,
            )

        except HTTPException:
            raise
        except Exception as e:
            providers_errors.log_provider_error(
                error_code=providers_errors.INTERNAL_ERROR,
                message=f"Unexpected error starting {instance_key}",
                exc=e,
                details={"instance_key": instance_key}
            )
            providers_errors.raise_provider_error(
                code=providers_errors.INTERNAL_ERROR,
                message=f"Unexpected error while starting instance: {str(e)}",
                details={"instance_key": instance_key},
                suggestion="Check server logs for more details",
                status_code=500
            )


@router.post("/{provider_id}/instances/stop", response_model=StopInstanceResponse)
async def stop_provider_instance(
    provider_id: str,
    request: StopInstanceRequest,
    timeout: float = 10.0,
):
    """
    Stop a provider instance with timeout control.

    Args:
        provider_id: Provider identifier
        request: Stop instance request with instance_id and force flag
        timeout: Shutdown timeout in seconds (default: 10s)

    Returns:
        StopInstanceResponse with status

    Raises:
        HTTPException: With standardized error format for various failure scenarios
    """
    from agentos.providers.process_manager import ProcessManager

    instance_key = f"{provider_id}:{request.instance_id}"

    # Check if this is LM Studio - it doesn't support CLI stop/restart
    if provider_id.lower() == 'lmstudio':
        error_info = providers_errors.build_unsupported_action_error(
            provider="LM Studio",
            action="stop"
        )
        providers_errors.raise_provider_error(**error_info)

    # Start operation timer
    with OperationTimer() as timer:
        try:
            # Log stop operation
            provider_logger.log_stop(
                provider=provider_id,
                instance_key=instance_key,
                force=request.force
            )

            process_mgr = ProcessManager.get_instance()

            # Check if process exists
            if not process_mgr.is_process_running(instance_key):
                proc_info = process_mgr.get_process_info(instance_key)

                # If we have info but it's not running, it was stopped cleanly
                if proc_info:
                    logger.info(f"Process {instance_key} already stopped")
                    return StopInstanceResponse(
                        ok=True,
                        instance_key=instance_key,
                        message="Process already stopped",
                    )
                else:
                    # No record of this process
                    providers_errors.raise_provider_error(
                        code=providers_errors.PROCESS_NOT_RUNNING,
                        message=f"No process found for instance '{instance_key}'",
                        details={
                            "instance_key": instance_key,
                            "provider_id": provider_id,
                            "instance_id": request.instance_id
                        },
                        suggestion="Process may not have been started or already stopped",
                        status_code=404
                    )

            # Get PID before stopping
            proc_info = process_mgr.get_process_info(instance_key)
            pid = proc_info.pid if proc_info else None

            # Stop process with timeout
            try:
                success, message, old_pid = await asyncio.wait_for(
                    process_mgr.stop_process(
                        instance_key=instance_key,
                        force=request.force,
                    ),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Log timeout with structured logging
                provider_logger.log_stop_failure(
                    provider=provider_id,
                    error_code=providers_errors.SHUTDOWN_TIMEOUT,
                    pid=pid,
                    elapsed_ms=timer.elapsed_ms(),
                    message=f"Shutdown timeout for {instance_key}",
                    instance_key=instance_key,
                    timeout_seconds=timeout,
                    force=request.force
                )

                providers_errors.log_provider_error(
                    error_code=providers_errors.SHUTDOWN_TIMEOUT,
                    message=f"Shutdown timeout for {instance_key}",
                    details={
                        "timeout_seconds": timeout,
                        "force": request.force
                    }
                )
                error_info = providers_errors.build_timeout_error(
                    operation="shutdown",
                    timeout_seconds=timeout,
                    instance_key=instance_key
                )
                error_info["suggestion"] = "Try force stop (force=true) or check if process is hung"
                providers_errors.raise_provider_error(**error_info)

            if not success:
                # Log stop failure
                provider_logger.log_stop_failure(
                    provider=provider_id,
                    error_code=providers_errors.PROCESS_STOP_FAILED,
                    pid=pid,
                    elapsed_ms=timer.elapsed_ms(),
                    message=message,
                    instance_key=instance_key,
                    force=request.force
                )

                providers_errors.log_provider_error(
                    error_code=providers_errors.PROCESS_STOP_FAILED,
                    message=message,
                    details={"instance_key": instance_key, "force": request.force}
                )

                # Check for common error patterns
                if "permission denied" in message.lower():
                    error_info = providers_errors.build_permission_denied_error_detailed(
                        exe_path=f"进程 {instance_key}"
                    )
                    providers_errors.raise_provider_error(**error_info)

                # Generic process stop failure
                error_info = providers_errors.build_process_stop_failed_error(
                    instance_key=instance_key,
                    reason=message,
                    details={"force": request.force}
                )
                providers_errors.raise_provider_error(**error_info)

            logger.info(f"Successfully stopped {instance_key}")

            # Log successful stop
            provider_logger.log_stop_success(
                provider=provider_id,
                pid=pid,
                elapsed_ms=timer.elapsed_ms(),
                instance_key=instance_key
            )

            return StopInstanceResponse(
                ok=True,
                instance_key=instance_key,
                message=message,
                old_pid=old_pid or pid,
            )

        except HTTPException:
            raise
        except Exception as e:
            providers_errors.log_provider_error(
                error_code=providers_errors.INTERNAL_ERROR,
                message=f"Unexpected error stopping {instance_key}",
                exc=e,
                details={"instance_key": instance_key}
            )
            providers_errors.raise_provider_error(
                code=providers_errors.INTERNAL_ERROR,
                message=f"Unexpected error while stopping instance: {str(e)}",
                details={"instance_key": instance_key},
                suggestion="Check server logs for more details",
                status_code=500
            )


@router.post("/{provider_id}/instances/restart", response_model=RestartInstanceResponse)
async def restart_provider_instance(
    provider_id: str,
    request: RestartInstanceRequest,
    timeout: float = 45.0,
):
    """
    Restart a provider instance.

    Task #16: P0.3 - Restart logic implementation

    Restart sequence:
    1. Stop the instance (if running)
    2. Wait for port to be released (max 5s)
    3. Check for and clean up any process remnants
    4. Start the instance
    5. Return old and new PIDs

    Args:
        provider_id: Provider identifier
        request: Restart instance request with instance_id, force flag, and optional launch_config
        timeout: Total timeout for restart operation (default: 45s)

    Returns:
        RestartInstanceResponse with old and new PID

    Raises:
        HTTPException: With standardized error format for various failure scenarios
    """
    from agentos.providers.process_manager import ProcessManager
    from agentos.providers.providers_config import ProvidersConfigManager
    import socket

    instance_key = f"{provider_id}:{request.instance_id}"

    # Check if this is LM Studio - it doesn't support CLI stop/restart
    if provider_id.lower() == 'lmstudio':
        error_info = providers_errors.build_unsupported_action_error(
            provider="LM Studio",
            action="restart"
        )
        providers_errors.raise_provider_error(**error_info)

    with OperationTimer() as timer:
        try:
            provider_logger.log_info(
                f"Restarting {instance_key}",
                provider=provider_id,
                instance_key=instance_key
            )

            process_mgr = ProcessManager.get_instance()
            config_mgr = ProvidersConfigManager()

            # Get configuration for restart
            provider_config = config_mgr.get_provider_config(provider_id)
            if not provider_config:
                providers_errors.raise_provider_error(
                    code=providers_errors.CONFIG_ERROR,
                    message=f"Provider '{provider_id}' not found",
                    details={"provider_id": provider_id},
                    status_code=404
                )

            # Find instance config
            instance_config = None
            for inst in provider_config.instances:
                if inst.id == request.instance_id:
                    instance_config = inst
                    break

            if not instance_config:
                providers_errors.raise_provider_error(
                    code=providers_errors.CONFIG_ERROR,
                    message=f"Instance '{request.instance_id}' not found",
                    details={"provider_id": provider_id, "instance_id": request.instance_id},
                    status_code=404
                )

            old_pid = None

            # Step 1: Stop if running
            if process_mgr.is_process_running(instance_key):
                logger.info(f"Stopping {instance_key} for restart...")
                try:
                    success, message, old_pid = await asyncio.wait_for(
                        process_mgr.stop_process(
                            instance_key=instance_key,
                            force=request.force,
                        ),
                        timeout=10.0
                    )
                    if not success:
                        providers_errors.raise_provider_error(
                            code=providers_errors.PROCESS_STOP_FAILED,
                            message=f"Failed to stop instance for restart: {message}",
                            details={"instance_key": instance_key, "old_pid": old_pid},
                            status_code=500
                        )
                except asyncio.TimeoutError:
                    providers_errors.raise_provider_error(
                        code=providers_errors.SHUTDOWN_TIMEOUT,
                        message=f"Timeout stopping instance for restart",
                        details={"instance_key": instance_key, "timeout": 10.0},
                        suggestion="Try force restart or manually kill the process",
                        status_code=504
                    )

            # Step 2: Wait for port to be released
            if instance_config.base_url:
                import re
                port_match = re.search(r':(\d+)', instance_config.base_url)
                if port_match:
                    port = int(port_match.group(1))
                    host = "127.0.0.1"
                    logger.info(f"Waiting for port {port} to be released...")

                    # Wait up to 5 seconds for port to be released
                    port_released = False
                    for i in range(10):  # 10 attempts * 0.5s = 5s
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.5)
                        try:
                            result = sock.connect_ex((host, port))
                            if result != 0:
                                # Port is free
                                port_released = True
                                sock.close()
                                break
                        except:
                            pass
                        finally:
                            sock.close()

                        await asyncio.sleep(0.5)

                    if not port_released:
                        logger.warning(f"Port {port} still in use after 5s, continuing anyway...")

            # Step 3: Check for process remnants
            if old_pid and process_mgr._is_process_alive(old_pid):
                logger.warning(f"Old process {old_pid} still alive, force killing...")
                try:
                    from agentos.core.utils.process import kill_process
                    kill_process(old_pid)
                    await asyncio.sleep(1)
                except:
                    pass

            # Step 4: Start the instance
            if not instance_config.launch:
                providers_errors.raise_provider_error(
                    code=providers_errors.CONFIG_ERROR,
                    message=f"Instance '{request.instance_id}' does not have launch configuration",
                    details={"instance_key": instance_key},
                    status_code=400
                )

            launch_config = request.launch_config or instance_config.launch.args
            bin_name = instance_config.launch.bin

            logger.info(f"Starting {instance_key} after restart...")
            try:
                success, message = await asyncio.wait_for(
                    process_mgr.start_process(
                        instance_key=instance_key,
                        bin_name=bin_name,
                        args=launch_config,
                    ),
                    timeout=max(30.0, timeout - timer.elapsed_ms() / 1000)
                )
            except asyncio.TimeoutError:
                providers_errors.raise_provider_error(
                    code=providers_errors.STARTUP_TIMEOUT,
                    message=f"Timeout starting instance after restart",
                    details={"instance_key": instance_key},
                    status_code=504
                )

            if not success:
                providers_errors.raise_provider_error(
                    code=providers_errors.PROCESS_START_FAILED,
                    message=f"Failed to start instance after restart: {message}",
                    details={"instance_key": instance_key, "old_pid": old_pid},
                    status_code=500
                )

            # Get new PID
            proc_info = process_mgr.get_process_info(instance_key)
            new_pid = proc_info.pid if proc_info else None

            logger.info(f"Successfully restarted {instance_key}: old_pid={old_pid}, new_pid={new_pid}")

            return RestartInstanceResponse(
                ok=True,
                instance_key=instance_key,
                message=f"Instance restarted successfully (old PID: {old_pid}, new PID: {new_pid})",
                old_pid=old_pid,
                new_pid=new_pid,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error restarting {instance_key}: {e}", exc_info=True)
            providers_errors.raise_provider_error(
                code=providers_errors.INTERNAL_ERROR,
                message=f"Unexpected error during restart: {str(e)}",
                details={"instance_key": instance_key},
                status_code=500
            )


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
async def install_provider(provider_id: str, timeout: float = 300.0):
    """
    Install provider via brew (macOS only).

    Supported providers:
    - ollama: brew install ollama
    - llamacpp: brew install llama.cpp

    Args:
        provider_id: Provider identifier (ollama, llamacpp)
        timeout: Installation timeout in seconds (default: 300s = 5 minutes)

    Returns:
        InstallProviderResponse with installation status

    Raises:
        HTTPException: With standardized error format for various failure scenarios
    """
    from agentos.providers import platform_utils

    # Check platform
    platform = platform_utils.get_platform()
    if platform != "macos":
        providers_errors.raise_provider_error(
            code=providers_errors.UNSUPPORTED_PLATFORM,
            message=f"Brew installation is only supported on macOS, not {platform}",
            details={
                "provider_id": provider_id,
                "platform": platform
            },
            suggestion=providers_errors.get_install_suggestion(provider_id, platform),
            status_code=400
        )

    # Map provider IDs to brew packages
    brew_packages = {
        "ollama": "ollama",
        "llamacpp": "llama.cpp",
    }

    package = brew_packages.get(provider_id)
    if not package:
        providers_errors.raise_provider_error(
            code=providers_errors.CONFIG_ERROR,
            message=f"Provider '{provider_id}' does not support brew installation",
            details={
                "provider_id": provider_id,
                "supported_providers": list(brew_packages.keys())
            },
            suggestion=f"Manual installation required for {provider_id}",
            status_code=400
        )

    try:
        # Run brew install with timeout
        success, message = await asyncio.wait_for(
            run_brew_install(package),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        providers_errors.log_provider_error(
            error_code=providers_errors.TIMEOUT_ERROR,
            message=f"Installation timeout for {provider_id}",
            details={"timeout_seconds": timeout}
        )
        error_info = providers_errors.build_timeout_error(
            operation=f"brew install {package}",
            timeout_seconds=timeout
        )
        error_info["suggestion"] = "Try again with a longer timeout or install manually"
        providers_errors.raise_provider_error(**error_info)

    if not success:
        providers_errors.log_provider_error(
            error_code=providers_errors.LAUNCH_FAILED,
            message=f"Brew installation failed for {provider_id}: {message}",
            details={"package": package}
        )

        # Check for common error patterns
        if "homebrew not installed" in message.lower():
            providers_errors.raise_provider_error(
                code=providers_errors.EXECUTABLE_NOT_FOUND,
                message="Homebrew is not installed on this system",
                details={"platform": platform},
                suggestion="Install Homebrew from https://brew.sh first",
                status_code=404
            )

        # Generic installation failure
        providers_errors.raise_provider_error(
            code=providers_errors.LAUNCH_FAILED,
            message=f"Failed to install {provider_id} via brew: {message}",
            details={
                "provider_id": provider_id,
                "package": package,
                "command": f"brew install {package}"
            },
            suggestion="Check brew logs or try manual installation",
            status_code=500
        )

    logger.info(f"Successfully installed {provider_id} via brew")

    return InstallProviderResponse(
        ok=True,
        provider_id=provider_id,
        message=message,
        command=f"brew install {package}",
    )


@router.get("/{provider_id}/capabilities", response_model=ProviderCapabilitiesResponse)
async def get_provider_capabilities(provider_id: str):
    """
    Get provider capabilities and supported actions.

    Task #16: P0.3 - Provider capabilities API

    Returns information about what actions a provider supports:
    - manual_lifecycle: Whether provider requires manual app management (e.g., LM Studio)
    - supported_actions: List of supported actions (start, stop, restart, open_app, detect)
    - enabled: Whether provider is enabled in configuration

    Args:
        provider_id: Provider identifier (ollama, llamacpp, lmstudio)

    Returns:
        ProviderCapabilitiesResponse: Provider capabilities

    Example:
        LM Studio returns:
        {
            "manual_lifecycle": true,
            "supported_actions": ["open_app", "detect"],
            "enabled": true
        }
    """
    from agentos.providers.providers_config import ProvidersConfigManager

    try:
        config_mgr = ProvidersConfigManager()
        provider_config = config_mgr.get_provider_config(provider_id)

        if not provider_config:
            raise HTTPException(
                status_code=404,
                detail=f"Provider {provider_id} not found in configuration"
            )

        return ProviderCapabilitiesResponse(
            provider_id=provider_id,
            manual_lifecycle=provider_config.manual_lifecycle,
            supported_actions=provider_config.supported_actions,
            enabled=provider_config.enabled,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get capabilities for {provider_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get provider capabilities: {str(e)}"
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


@router.get("/{provider_id}/executable/detect", response_model=DetectExecutableResponse)
async def detect_executable(provider_id: str):
    """
    Auto-detect executable for a provider with enhanced path information.

    This endpoint searches for provider executables using the following priority:
    1. User-configured path (from providers.json config file)
    2. Platform-specific standard installation paths (including brew --prefix on macOS)
    3. System PATH environment variable

    Supported providers: ollama, llamacpp, lmstudio

    Returns:
        DetectExecutableResponse: Detection results including:
            - detected: Whether executable was found
            - path: Auto-detected path (standard paths or PATH)
            - custom_path: User-configured path from config
            - resolved_path: Final resolved path (considering priority)
            - version: Executable version if available
            - platform: Current platform
            - search_paths: Paths that were searched
            - is_valid: Whether the resolved path is valid
            - detection_source: Where the executable was found ('config', 'standard', or 'path')
    """
    from agentos.providers import platform_utils
    from agentos.providers.providers_config import ProvidersConfigManager

    try:
        # Map provider_id to executable name
        executable_name_map = {
            "ollama": "ollama",
            "llamacpp": "llama-server",
            "lmstudio": "lmstudio",
        }

        executable_name = executable_name_map.get(provider_id)
        if not executable_name:
            raise HTTPException(
                status_code=400,
                detail=f"Provider {provider_id} does not support executable detection"
            )

        # Get config manager to check for user-configured path
        config_mgr = ProvidersConfigManager()
        provider_config = config_mgr._config.get("providers", {}).get(provider_id, {})
        custom_path_str = provider_config.get("executable_path")

        # Get search paths for documentation
        search_paths = [str(p) for p in platform_utils.get_standard_paths(executable_name)]
        current_platform = platform_utils.get_platform()

        # Detect paths with priority:
        # 1. Custom configured path
        # 2. Standard installation paths
        # 3. PATH environment variable

        resolved_path = None
        detection_source = None
        auto_detected_path = None

        # Priority 1: Check custom configured path
        if custom_path_str:
            custom_path = Path(custom_path_str)
            if platform_utils.validate_executable(custom_path):
                resolved_path = custom_path
                detection_source = 'config'

        # Priority 2 & 3: Auto-detect (standard paths + PATH)
        if not resolved_path:
            # First try standard paths
            standard_paths = platform_utils.get_standard_paths(executable_name)
            for std_path in standard_paths:
                if platform_utils.validate_executable(std_path):
                    auto_detected_path = std_path
                    resolved_path = std_path
                    detection_source = 'standard'
                    break

            # Then try PATH if not found in standard paths
            if not resolved_path:
                path_result = platform_utils.find_in_path(executable_name)
                if path_result:
                    auto_detected_path = path_result
                    resolved_path = path_result
                    detection_source = 'path'

        # Log detection result
        provider_logger.log_detect(
            provider=provider_id,
            resolved_exe=str(resolved_path) if resolved_path else None,
            searched_paths=search_paths,
            detected=resolved_path is not None
        )

        if resolved_path:
            # Get version information
            version = platform_utils.get_executable_version(resolved_path)

            return DetectExecutableResponse(
                detected=True,
                path=str(auto_detected_path) if auto_detected_path else None,
                custom_path=custom_path_str if custom_path_str else None,
                resolved_path=str(resolved_path),
                version=version,
                platform=current_platform,
                search_paths=search_paths,
                is_valid=True,
                detection_source=detection_source,
            )
        else:
            # Not found
            return DetectExecutableResponse(
                detected=False,
                path=None,
                custom_path=custom_path_str if custom_path_str else None,
                resolved_path=None,
                version=None,
                platform=current_platform,
                search_paths=search_paths,
                is_valid=False,
                detection_source=None,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to detect executable for {provider_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect executable: {str(e)}"
        )


@router.post("/{provider_id}/executable/validate", response_model=ValidateExecutableResponse)
async def validate_executable_path(
    provider_id: str,
    request: ValidateExecutableRequest,
):
    """
    Validate a user-provided executable path with detailed results.

    This endpoint performs comprehensive validation:
    - Checks file existence
    - Validates executable permissions (Unix) or extension (Windows)
    - Attempts to retrieve version information
    - Returns detailed validation status

    Args:
        provider_id: Provider identifier (ollama, llamacpp, lmstudio)
        request: Validation request with path to check

    Returns:
        ValidateExecutableResponse: Detailed validation result including:
            - is_valid: Overall validation status
            - path: The path that was validated
            - exists: Whether the file exists
            - is_executable: Whether the file is executable
            - version: Version information if available
            - error: Detailed error message if validation failed
    """
    from agentos.providers import platform_utils

    try:
        path_obj = Path(request.path)

        # Use the new detailed validation function
        validation_result = platform_utils.validate_executable_detailed(path_obj)

        # Log validation result
        provider_logger.log_validate(
            provider=provider_id,
            path=str(path_obj),
            is_valid=validation_result['is_valid'],
            version=validation_result.get('version'),
            error_message=validation_result.get('error')
        )

        return ValidateExecutableResponse(
            is_valid=validation_result['is_valid'],
            path=str(path_obj),
            exists=validation_result['exists'],
            is_executable=validation_result['is_executable'],
            version=validation_result.get('version'),
            error=validation_result.get('error'),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate executable path for {provider_id}: {e}")
        return ValidateExecutableResponse(
            is_valid=False,
            path=request.path,
            exists=False,
            is_executable=False,
            version=None,
            error=f"Validation error: {str(e)}",
        )


@router.put("/{provider_id}/executable", response_model=Dict[str, Any])
async def set_executable_path(
    provider_id: str,
    request: SetExecutableRequest,
):
    """
    Set or update the executable path for a provider.

    This endpoint allows users to:
    1. Set a custom executable path (after validation)
    2. Enable auto-detection (by setting path=None and auto_detect=True)

    The configuration is persisted to ~/.agentos/config/providers.json

    Args:
        provider_id: Provider identifier (ollama, llamacpp, lmstudio)
        request: Configuration with path and auto_detect flag

    Returns:
        dict: Success status with configured path and auto_detect setting

    Raises:
        HTTPException: If path validation fails or configuration cannot be saved
    """
    from agentos.providers.providers_config import ProvidersConfigManager
    from agentos.providers import platform_utils

    try:
        config_mgr = ProvidersConfigManager()

        # If path is provided, validate it first
        if request.path is not None:
            path_obj = Path(request.path)

            # Validate the executable
            if not platform_utils.validate_executable(path_obj):
                # Determine specific error message
                if not path_obj.exists():
                    error_detail = {
                        "error": {
                            "code": "FILE_NOT_FOUND",
                            "message": f"Executable file does not exist: {request.path}",
                            "path": request.path,
                        }
                    }
                elif not path_obj.is_file():
                    error_detail = {
                        "error": {
                            "code": "NOT_A_FILE",
                            "message": f"Path is not a file: {request.path}",
                            "path": request.path,
                        }
                    }
                else:
                    error_detail = {
                        "error": {
                            "code": "NOT_EXECUTABLE",
                            "message": "File is not executable or has incorrect extension",
                            "path": request.path,
                            "platform": platform_utils.get_platform(),
                        }
                    }
                raise HTTPException(status_code=400, detail=error_detail)

            # Path is valid, save it
            config_mgr.set_executable_path(provider_id, str(path_obj))

            # Get version for confirmation
            version = get_executable_version(path_obj)

            return {
                "success": True,
                "path": str(path_obj),
                "auto_detect": False,
                "version": version,
            }

        else:
            # path is None - enable auto-detection
            if request.auto_detect:
                config_mgr.set_executable_path(provider_id, None)

                # Try to detect immediately to confirm
                detected_path = config_mgr.get_executable_path(provider_id)
                version = None
                if detected_path:
                    version = get_executable_version(detected_path)

                return {
                    "success": True,
                    "path": str(detected_path) if detected_path else None,
                    "auto_detect": True,
                    "version": version,
                }
            else:
                # Both path=None and auto_detect=False doesn't make sense
                raise HTTPException(
                    status_code=400,
                    detail="Cannot disable auto_detect without providing a path"
                )

    except HTTPException:
        raise
    except ValueError as e:
        # Configuration validation error
        logger.error(f"Configuration error for {provider_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "CONFIG_ERROR",
                    "message": str(e),
                }
            }
        )
    except Exception as e:
        logger.error(f"Failed to set executable path for {provider_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to save configuration: {str(e)}",
                }
            }
        )


class ProviderDiagnosticsResponse(BaseModel):
    """
    Provider diagnostics response

    Task #19: P1.6 - Providers diagnostics panel
    """
    provider_id: str
    platform: str
    detected_executable: Optional[str] = None
    configured_executable: Optional[str] = None
    resolved_executable: Optional[str] = None
    detection_source: Optional[str] = None
    version: Optional[str] = None
    supported_actions: List[str]
    current_status: Optional[str] = None
    pid: Optional[int] = None
    port: Optional[int] = None
    port_listening: Optional[bool] = None
    models_directory: Optional[str] = None
    models_count: Optional[int] = None
    last_error: Optional[str] = None


@router.get("/{provider_id}/diagnostics", response_model=ProviderDiagnosticsResponse)
async def get_provider_diagnostics(provider_id: str):
    """
    Get complete diagnostics information for a provider.

    Task #19: P1.6 - Providers self-check diagnostics panel

    Returns comprehensive diagnostic information including:
    - Platform and system info
    - Executable detection paths (detected, configured, resolved)
    - Version information
    - Supported actions
    - Current status (RUNNING/STOPPED/ERROR)
    - Process info (PID, port, listening status)
    - Models directory and count
    - Last error if any

    Args:
        provider_id: Provider identifier (ollama, llamacpp, lmstudio)

    Returns:
        ProviderDiagnosticsResponse: Complete diagnostics information
    """
    from agentos.providers import platform_utils
    from agentos.providers.providers_config import ProvidersConfigManager
    from agentos.providers.process_manager import ProcessManager
    import socket

    try:
        # Get platform info
        current_platform = platform_utils.get_platform()
        system_info = f"{current_platform} ({os.uname().sysname} {os.uname().release})"

        # Get configuration
        config_mgr = ProvidersConfigManager()
        provider_config = config_mgr.get_provider_config(provider_id)

        if not provider_config:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider_id}' not found in configuration"
            )

        # Map provider_id to executable name
        executable_name_map = {
            "ollama": "ollama",
            "llamacpp": "llama-server",
            "lmstudio": "lmstudio",
        }

        executable_name = executable_name_map.get(provider_id)

        # Detect executable paths
        detected_path = None
        configured_path = None
        resolved_path = None
        detection_source = None
        version = None

        if executable_name:
            # Get configured path from config
            provider_config_raw = config_mgr._config.get("providers", {}).get(provider_id, {})
            configured_path_str = provider_config_raw.get("executable_path")

            if configured_path_str:
                configured_path = configured_path_str
                # Check if configured path is valid
                if platform_utils.validate_executable(Path(configured_path_str)):
                    resolved_path = configured_path_str
                    detection_source = 'config'
                    version = platform_utils.get_executable_version(Path(configured_path_str))

            # Auto-detect if not configured or configured path is invalid
            if not resolved_path:
                # Try standard paths first
                standard_paths = platform_utils.get_standard_paths(executable_name)
                for std_path in standard_paths:
                    if platform_utils.validate_executable(std_path):
                        detected_path = str(std_path)
                        resolved_path = detected_path
                        detection_source = 'standard'
                        version = platform_utils.get_executable_version(std_path)
                        break

                # Try PATH if not found in standard paths
                if not resolved_path:
                    path_result = platform_utils.find_in_path(executable_name)
                    if path_result:
                        detected_path = str(path_result)
                        resolved_path = detected_path
                        detection_source = 'path'
                        version = platform_utils.get_executable_version(path_result)

        # Get supported actions
        supported_actions = provider_config.supported_actions

        # Get current status and process info
        current_status = None
        pid = None
        port = None
        port_listening = None

        # Check if we have any instances for this provider
        if provider_config.instances:
            instance = provider_config.instances[0]  # Use first instance for diagnostics
            instance_key = f"{provider_id}:{instance.id}"

            # Check process status
            process_mgr = ProcessManager.get_instance()
            if process_mgr.is_process_running(instance_key):
                current_status = "RUNNING"
                proc_info = process_mgr.get_process_info(instance_key)
                if proc_info:
                    pid = proc_info.pid
            else:
                # Check if there's a PID file but process is dead
                pid_data = process_mgr.load_pid(provider_id, instance.id)
                if pid_data:
                    current_status = "ERROR"  # PID file exists but process not running
                else:
                    current_status = "STOPPED"

            # Extract port from base_url
            if instance.base_url:
                import re
                port_match = re.search(r':(\d+)', instance.base_url)
                if port_match:
                    port = int(port_match.group(1))

                    # Check if port is listening
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    try:
                        result = sock.connect_ex(("127.0.0.1", port))
                        port_listening = (result == 0)
                    except:
                        port_listening = False
                    finally:
                        sock.close()

        # Get models directory and count
        models_directory = None
        models_count = None

        try:
            models_dir = config_mgr.get_models_dir(provider_id)
            if models_dir and models_dir.exists():
                models_directory = str(models_dir)
                # Count model files (basic implementation - count files)
                model_files = list(models_dir.rglob("*"))
                models_count = len([f for f in model_files if f.is_file()])
        except Exception as e:
            logger.warning(f"Failed to get models directory for {provider_id}: {e}")

        # Get last error (if any)
        last_error = None
        # TODO: Could fetch from logs or status store if available

        return ProviderDiagnosticsResponse(
            provider_id=provider_id,
            platform=system_info,
            detected_executable=detected_path,
            configured_executable=configured_path,
            resolved_executable=resolved_path,
            detection_source=detection_source,
            version=version,
            supported_actions=supported_actions,
            current_status=current_status,
            pid=pid,
            port=port,
            port_listening=port_listening,
            models_directory=models_directory,
            models_count=models_count,
            last_error=last_error,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get diagnostics for {provider_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve diagnostics: {str(e)}"
        )


@router.post("/lmstudio/open-app")
async def open_lmstudio_app():
    """
    Open LM Studio application (cross-platform)

    Supports:
    - macOS: Uses 'open -a "LM Studio"'
    - Windows: Launches LM Studio.exe with 'start' command
    - Linux: Executes AppImage or executable directly
    """
    from agentos.providers import platform_utils

    try:
        system = platform_utils.get_platform()

        if system == 'macos':
            # macOS: Use 'open -a' to launch application
            logger.info("Opening LM Studio on macOS")
            result = subprocess.run(
                ["open", "-a", "LM Studio"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                error_detail = {
                    "error": {
                        "code": "EXECUTABLE_NOT_FOUND",
                        "message": "LM Studio is not installed or not found",
                        "platform": "macos",
                        "suggestion": "Please install LM Studio from https://lmstudio.ai",
                        "searched_paths": [
                            "/Applications/LM Studio.app",
                            "~/Applications/LM Studio.app"
                        ]
                    }
                }
                raise HTTPException(status_code=404, detail=error_detail)

            return {
                "success": True,
                "message": "LM Studio is opening..."
            }

        elif system == 'windows':
            # Windows: Find executable and launch with 'start' command
            logger.info("Opening LM Studio on Windows")
            lmstudio_path = platform_utils.find_executable('lmstudio')

            if not lmstudio_path:
                # Search common Windows installation paths
                searched_paths = [str(p) for p in platform_utils.get_standard_paths('lmstudio')]
                error_detail = {
                    "error": {
                        "code": "EXECUTABLE_NOT_FOUND",
                        "message": "LM Studio is not installed or not found",
                        "platform": "windows",
                        "suggestion": "Please install LM Studio from https://lmstudio.ai",
                        "searched_paths": searched_paths
                    }
                }
                raise HTTPException(status_code=404, detail=error_detail)

            # Use 'start' command to launch without blocking
            # The empty string '' is required as the window title parameter
            subprocess.Popen(
                ['cmd', '/c', 'start', '', str(lmstudio_path)],
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            return {
                "success": True,
                "message": "LM Studio is opening..."
            }

        elif system == 'linux':
            # Linux: Find and execute AppImage or executable
            logger.info("Opening LM Studio on Linux")
            lmstudio_path = platform_utils.find_executable('lmstudio')

            if not lmstudio_path:
                # Search common Linux installation paths
                searched_paths = [str(p) for p in platform_utils.get_standard_paths('lmstudio')]
                error_detail = {
                    "error": {
                        "code": "EXECUTABLE_NOT_FOUND",
                        "message": "LM Studio is not installed or not found",
                        "platform": "linux",
                        "suggestion": "Please install LM Studio from https://lmstudio.ai",
                        "searched_paths": searched_paths
                    }
                }
                raise HTTPException(status_code=404, detail=error_detail)

            # Launch in a new session to avoid blocking
            subprocess.Popen(
                [str(lmstudio_path)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            return {
                "success": True,
                "message": "LM Studio is opening..."
            }

        else:
            # Unknown platform
            raise HTTPException(
                status_code=500,
                detail=f"Unsupported platform: {system}"
            )

    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        logger.error("Timeout opening LM Studio")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "TIMEOUT",
                    "message": "Timeout while trying to open LM Studio",
                    "platform": platform_utils.get_platform()
                }
            }
        )
    except Exception as e:
        logger.error(f"Failed to open LM Studio: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "LAUNCH_FAILED",
                    "message": f"Failed to open LM Studio: {str(e)}",
                    "platform": platform_utils.get_platform()
                }
            }
        )
