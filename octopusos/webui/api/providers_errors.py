"""Unified provider error helpers for WebUI APIs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi.responses import JSONResponse

EXECUTABLE_NOT_FOUND = "EXECUTABLE_NOT_FOUND"
PORT_IN_USE = "PORT_IN_USE"
PROCESS_START_FAILED = "PROCESS_START_FAILED"
TIMEOUT_ERROR = "TIMEOUT_ERROR"
PERMISSION_DENIED = "PERMISSION_DENIED"
DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"
UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"


def provider_error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    suggestion: Optional[str] = None,
    status_code: int = 400,
) -> JSONResponse:
    payload = {
        "code": code,
        "message": message,
        "details": details or {},
        "suggestion": suggestion or "",
    }
    return JSONResponse(status_code=status_code, content=payload)


def get_install_suggestion(provider: str, platform: str) -> str:
    provider = provider.lower()
    platform = platform.lower()

    if provider in ("ollama", "ollama-server"):
        if platform == "macos":
            return "Install Ollama via Homebrew: `brew install ollama` and run `ollama serve`."
        if platform == "windows":
            return "Install Ollama from the official Windows installer and add it to PATH."
        return "Install Ollama using your package manager and ensure it is on PATH."

    if provider in ("llamacpp", "llama.cpp", "llama-server"):
        if platform == "windows":
            return "Build llama.cpp from source or download prebuilt binaries; add to PATH."
        return "Build llama.cpp and ensure the executable is on PATH."

    if provider in ("lmstudio", "lm-studio"):
        if platform == "windows":
            return "Install LM Studio and enable the local server from the UI."
        return "Install LM Studio and enable the local server from the UI."

    return "Install the provider and ensure the executable is available on PATH."


def get_path_permission_suggestion(platform: str) -> str:
    platform = platform.lower()
    if platform == "windows":
        return "Check file permissions and run the terminal as Administrator."
    if platform == "macos":
        return "Check permissions: `chmod +x <path>` and allow terminal in Security & Privacy."
    return "Check permissions: `chmod +x <path>` and ensure the file is executable."


def build_executable_not_found_error(provider_id: str, searched_paths: List[str]) -> Dict[str, Any]:
    suggestion = get_install_suggestion(provider_id, _infer_platform())
    return {
        "code": EXECUTABLE_NOT_FOUND,
        "message": f"Executable for provider '{provider_id}' not found.",
        "status_code": 404,
        "details": {"searched_paths": searched_paths, "provider": provider_id},
        "suggestion": suggestion,
    }


def build_exe_not_found_error(provider: str, searched_paths: List[str], platform: str) -> Dict[str, Any]:
    suggestion = get_install_suggestion(provider, platform)
    return {
        "code": EXECUTABLE_NOT_FOUND,
        "message": f"{provider} executable not found.",
        "status_code": 404,
        "details": {"searched_paths": searched_paths, "provider": provider, "platform": platform},
        "suggestion": suggestion,
    }


def build_port_in_use_error(port: int, occupant: str) -> Dict[str, Any]:
    return {
        "code": PORT_IN_USE,
        "message": f"Port {port} is already in use by {occupant}.",
        "status_code": 409,
        "details": {"port": port, "occupant": occupant},
        "suggestion": "Stop the occupying process or choose a different port.",
    }


def build_port_in_use_error_detailed(port: int, provider: str, platform: str) -> Dict[str, Any]:
    return {
        "code": PORT_IN_USE,
        "message": f"Port {port} is already in use.",
        "status_code": 409,
        "details": {"port": port, "provider": provider, "platform": platform},
        "suggestion": "Stop the process using the port or reconfigure the provider.",
    }


def build_process_start_failed_error(instance_key: str, reason: str) -> Dict[str, Any]:
    return {
        "code": PROCESS_START_FAILED,
        "message": f"Failed to start provider instance {instance_key}.",
        "status_code": 500,
        "details": {"instance_key": instance_key, "reason": reason},
        "suggestion": "Check logs and verify executable path/configuration.",
    }


def build_start_failed_error(
    provider: str,
    exit_code: int,
    stderr: str,
    log_file: Optional[str] = None,
    instance_key: Optional[str] = None,
) -> Dict[str, Any]:
    stderr_lines = stderr.splitlines()
    tail = "\n".join(stderr_lines[-30:]) if stderr_lines else ""
    details = {"provider": provider, "exit_code": exit_code, "stderr_tail": tail}
    if log_file:
        details["log_file"] = log_file
    if instance_key:
        details["instance_key"] = instance_key
    return {
        "code": PROCESS_START_FAILED,
        "message": f"{provider} failed to start (exit code {exit_code}).",
        "status_code": 500,
        "details": details,
        "suggestion": "Review the log output and verify model files and configuration.",
    }


def build_timeout_error(operation: str, timeout_seconds: float, instance_key: str) -> Dict[str, Any]:
    return {
        "code": TIMEOUT_ERROR,
        "message": f"Timeout during {operation}.",
        "status_code": 504,
        "details": {"operation": operation, "timeout_seconds": timeout_seconds, "instance_key": instance_key},
        "suggestion": "Retry the operation or increase the timeout.",
    }


def build_permission_denied_error(path: str, operation: str) -> Dict[str, Any]:
    return {
        "code": PERMISSION_DENIED,
        "message": f"Permission denied for {operation} on {path}.",
        "status_code": 403,
        "details": {"path": path, "operation": operation},
        "suggestion": get_path_permission_suggestion(_infer_platform()),
    }


def build_permission_denied_error_detailed(exe_path: str, platform: str) -> Dict[str, Any]:
    return {
        "code": PERMISSION_DENIED,
        "message": f"Permission denied: {exe_path}",
        "status_code": 403,
        "details": {"path": exe_path, "platform": platform},
        "suggestion": get_path_permission_suggestion(platform),
    }


def build_directory_not_found_error(path: str) -> Dict[str, Any]:
    return {
        "code": DIRECTORY_NOT_FOUND,
        "message": f"Directory not found: {path}",
        "status_code": 404,
        "details": {"path": path},
        "suggestion": "Create the directory or update the configuration path.",
    }


def build_unsupported_action_error(provider: str, action: str) -> Dict[str, Any]:
    return {
        "code": UNSUPPORTED_ACTION,
        "message": f"Action '{action}' is not supported by {provider}.",
        "status_code": 400,
        "details": {"provider": provider, "action": action},
        "suggestion": "Check provider documentation for supported actions.",
    }


def _infer_platform() -> str:
    import sys
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("darwin"):
        return "macos"
    return "linux"
