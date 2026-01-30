"""
Unified Error Handling for Providers API

This module provides standardized error codes, error response structures,
and helper functions for all provider-related API endpoints.

Sprint B+ Provider Architecture Refactor
Phase 3.3: API Error Handling Unification
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from agentos.providers import platform_utils

logger = logging.getLogger(__name__)


# ============================================================================
# Error Code Constants
# ============================================================================

# Executable/Binary Errors
EXECUTABLE_NOT_FOUND = "EXECUTABLE_NOT_FOUND"
INVALID_PATH = "INVALID_PATH"
NOT_EXECUTABLE = "NOT_EXECUTABLE"
FILE_NOT_FOUND = "FILE_NOT_FOUND"
NOT_A_FILE = "NOT_A_FILE"

# Directory Errors
DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"
NOT_A_DIRECTORY = "NOT_A_DIRECTORY"
DIRECTORY_NOT_READABLE = "DIRECTORY_NOT_READABLE"

# Permission Errors
PERMISSION_DENIED = "PERMISSION_DENIED"

# Process Management Errors
PROCESS_START_FAILED = "PROCESS_START_FAILED"
PROCESS_STOP_FAILED = "PROCESS_STOP_FAILED"
PROCESS_NOT_RUNNING = "PROCESS_NOT_RUNNING"
PROCESS_ALREADY_RUNNING = "PROCESS_ALREADY_RUNNING"

# Port/Network Errors
PORT_IN_USE = "PORT_IN_USE"
PORT_NOT_AVAILABLE = "PORT_NOT_AVAILABLE"

# Timeout Errors
TIMEOUT_ERROR = "TIMEOUT_ERROR"
STARTUP_TIMEOUT = "STARTUP_TIMEOUT"
SHUTDOWN_TIMEOUT = "SHUTDOWN_TIMEOUT"

# Model Errors
MODEL_FILE_NOT_FOUND = "MODEL_FILE_NOT_FOUND"
INVALID_MODEL_FILE = "INVALID_MODEL_FILE"

# Configuration Errors
CONFIG_ERROR = "CONFIG_ERROR"
INVALID_CONFIG = "INVALID_CONFIG"

# Platform Errors
UNSUPPORTED_PLATFORM = "UNSUPPORTED_PLATFORM"
PLATFORM_SPECIFIC_ERROR = "PLATFORM_SPECIFIC_ERROR"

# Action Errors
UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"

# General Errors
INTERNAL_ERROR = "INTERNAL_ERROR"
LAUNCH_FAILED = "LAUNCH_FAILED"
VALIDATION_ERROR = "VALIDATION_ERROR"


# ============================================================================
# Error Response Builder
# ============================================================================


def provider_error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    suggestion: Optional[str] = None,
    status_code: int = 500
) -> JSONResponse:
    """
    Build a standardized error response for provider APIs.

    Args:
        code: Error code constant (e.g., EXECUTABLE_NOT_FOUND)
        message: Human-readable error message
        details: Additional error details (optional)
        suggestion: Action suggestion for the user (optional)
        status_code: HTTP status code (default: 500)

    Returns:
        JSONResponse: Standardized error response

    Example:
        ```python
        return provider_error_response(
            code=EXECUTABLE_NOT_FOUND,
            message="Ollama executable not found",
            details={
                "searched_paths": ["/usr/local/bin/ollama"],
                "platform": "macos"
            },
            suggestion="Install Ollama or specify custom path in settings",
            status_code=404
        )
        ```
    """
    error_body = {
        "error": {
            "code": code,
            "message": message,
        }
    }

    if details:
        error_body["error"]["details"] = details

    if suggestion:
        error_body["error"]["suggestion"] = suggestion

    return JSONResponse(
        status_code=status_code,
        content=error_body
    )


def raise_provider_error(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    suggestion: Optional[str] = None,
    status_code: int = 500
) -> None:
    """
    Raise an HTTPException with standardized provider error format.

    This is a convenience wrapper around HTTPException that uses
    the same error structure as provider_error_response.

    Args:
        code: Error code constant
        message: Human-readable error message
        details: Additional error details (optional)
        suggestion: Action suggestion for the user (optional)
        status_code: HTTP status code (default: 500)

    Raises:
        HTTPException: With standardized error detail structure

    Example:
        ```python
        raise_provider_error(
            code=PORT_IN_USE,
            message=f"Port {port} is already in use",
            details={"port": port, "occupant": "ollama"},
            suggestion="Stop the existing service or use a different port",
            status_code=409
        )
        ```
    """
    error_detail = {
        "error": {
            "code": code,
            "message": message,
        }
    }

    if details:
        error_detail["error"]["details"] = details

    if suggestion:
        error_detail["error"]["suggestion"] = suggestion

    raise HTTPException(status_code=status_code, detail=error_detail)


# ============================================================================
# Platform-Specific Installation Suggestions
# ============================================================================


def get_install_suggestion(provider_id: str, platform: Optional[str] = None) -> str:
    """
    Get platform-specific installation suggestion for a provider.

    Args:
        provider_id: Provider identifier (ollama, llamacpp, lmstudio)
        platform: Platform name (windows, macos, linux). Auto-detected if None.

    Returns:
        str: Installation suggestion text

    Example:
        >>> get_install_suggestion("ollama", "macos")
        "Install via Homebrew: brew install ollama, or download from https://ollama.ai"
    """
    if platform is None:
        platform = platform_utils.get_platform()

    suggestions = {
        "ollama": {
            "windows": "Download installer from https://ollama.ai and run the setup",
            "macos": "Install via Homebrew: brew install ollama, or download from https://ollama.ai",
            "linux": "Install via curl: curl -fsSL https://ollama.ai/install.sh | sh"
        },
        "llamacpp": {
            "windows": "Download pre-built binaries from https://github.com/ggerganov/llama.cpp/releases or build from source",
            "macos": "Install via Homebrew: brew install llama.cpp, or build from source",
            "linux": "Install via package manager or build from source: https://github.com/ggerganov/llama.cpp"
        },
        "lmstudio": {
            "windows": "Download installer from https://lmstudio.ai and run the setup",
            "macos": "Download .dmg from https://lmstudio.ai and drag to Applications folder",
            "linux": "Download AppImage from https://lmstudio.ai and make it executable"
        }
    }

    provider_suggestions = suggestions.get(provider_id, {})
    suggestion = provider_suggestions.get(platform, f"Install {provider_id} from the official website")

    return suggestion


def get_path_permission_suggestion(platform: Optional[str] = None) -> str:
    """
    Get platform-specific permission fix suggestion.

    Args:
        platform: Platform name. Auto-detected if None.

    Returns:
        str: Permission fix suggestion

    Example:
        >>> get_path_permission_suggestion("linux")
        "Run 'chmod +x <path>' to make the file executable"
    """
    if platform is None:
        platform = platform_utils.get_platform()

    if platform == "windows":
        return "Ensure the file has a valid executable extension (.exe, .bat, .cmd) and you have permission to execute it"
    else:
        return "Run 'chmod +x <path>' to make the file executable, or check file permissions"


# ============================================================================
# Error Context Builders
# ============================================================================


def build_executable_not_found_error(
    provider_id: str,
    searched_paths: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Build error details for executable not found scenario.

    Args:
        provider_id: Provider identifier
        searched_paths: List of paths that were searched

    Returns:
        dict: Error detail dictionary ready for provider_error_response
    """
    platform = platform_utils.get_platform()

    if searched_paths is None:
        # Get standard search paths
        executable_names = {
            "ollama": "ollama",
            "llamacpp": "llama-server",
            "lmstudio": "lmstudio"
        }
        exe_name = executable_names.get(provider_id, provider_id)
        standard_paths = platform_utils.get_standard_paths(exe_name)
        searched_paths = [str(p) for p in standard_paths]

    return {
        "code": EXECUTABLE_NOT_FOUND,
        "message": f"{provider_id.capitalize()} executable not found. Please install or configure the path.",
        "details": {
            "provider_id": provider_id,
            "searched_paths": searched_paths,
            "platform": platform
        },
        "suggestion": get_install_suggestion(provider_id, platform),
        "status_code": 404
    }


def build_port_in_use_error(
    port: int,
    host: str = "localhost",
    occupant: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build error details for port already in use scenario.

    Args:
        port: Port number that is in use
        host: Host address (default: localhost)
        occupant: Process/service using the port (optional)

    Returns:
        dict: Error detail dictionary ready for provider_error_response
    """
    message = f"Port {port} is already in use"
    if occupant:
        message += f" by {occupant}"

    suggestion = f"Stop the service using port {port}, or configure a different port"
    if occupant:
        suggestion = f"Stop {occupant} first, or configure a different port"

    return {
        "code": PORT_IN_USE,
        "message": message,
        "details": {
            "port": port,
            "host": host,
            "occupant": occupant
        },
        "suggestion": suggestion,
        "status_code": 409  # Conflict
    }


def build_process_start_failed_error(
    instance_key: str,
    reason: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build error details for process start failure.

    Args:
        instance_key: Instance identifier (e.g., "ollama:default")
        reason: Reason for failure
        details: Additional context (optional)

    Returns:
        dict: Error detail dictionary ready for provider_error_response
    """
    error_details = {
        "instance_key": instance_key,
        "reason": reason
    }

    if details:
        error_details.update(details)

    return {
        "code": PROCESS_START_FAILED,
        "message": f"Failed to start process for {instance_key}: {reason}",
        "details": error_details,
        "suggestion": "Check logs for more details, verify executable path and permissions",
        "status_code": 500
    }


def build_process_stop_failed_error(
    instance_key: str,
    reason: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build error details for process stop failure.

    Args:
        instance_key: Instance identifier
        reason: Reason for failure
        details: Additional context (optional)

    Returns:
        dict: Error detail dictionary ready for provider_error_response
    """
    error_details = {
        "instance_key": instance_key,
        "reason": reason
    }

    if details:
        error_details.update(details)

    return {
        "code": PROCESS_STOP_FAILED,
        "message": f"Failed to stop process for {instance_key}: {reason}",
        "details": error_details,
        "suggestion": "Try force stop, or check process status and permissions",
        "status_code": 500
    }


def build_timeout_error(
    operation: str,
    timeout_seconds: float,
    instance_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build error details for timeout scenario.

    Args:
        operation: Operation that timed out (e.g., "startup", "shutdown", "probe")
        timeout_seconds: Timeout duration in seconds
        instance_key: Instance identifier (optional)

    Returns:
        dict: Error detail dictionary ready for provider_error_response
    """
    message = f"Operation '{operation}' timed out after {timeout_seconds}s"
    if instance_key:
        message += f" for {instance_key}"

    error_details = {
        "operation": operation,
        "timeout_seconds": timeout_seconds
    }

    if instance_key:
        error_details["instance_key"] = instance_key

    return {
        "code": TIMEOUT_ERROR,
        "message": message,
        "details": error_details,
        "suggestion": "Check system resources, logs, and consider increasing timeout",
        "status_code": 504  # Gateway Timeout
    }


def build_permission_denied_error(
    path: str,
    operation: str = "access"
) -> Dict[str, Any]:
    """
    Build error details for permission denied scenario.

    Args:
        path: Path that was denied access
        operation: Operation that was denied (e.g., "access", "read", "write", "execute")

    Returns:
        dict: Error detail dictionary ready for provider_error_response
    """
    platform = platform_utils.get_platform()

    suggestion = "Check file/directory permissions and ownership"
    if platform == "windows":
        suggestion += ", or try running as administrator"
    else:
        suggestion += f", or run 'chmod' to fix permissions"

    return {
        "code": PERMISSION_DENIED,
        "message": f"Permission denied: Cannot {operation} {path}",
        "details": {
            "path": path,
            "operation": operation,
            "platform": platform
        },
        "suggestion": suggestion,
        "status_code": 403  # Forbidden
    }


def build_directory_not_found_error(
    path: str,
    provider_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build error details for directory not found scenario.

    Args:
        path: Directory path that was not found
        provider_id: Provider identifier (optional)

    Returns:
        dict: Error detail dictionary ready for provider_error_response
    """
    message = f"Directory does not exist: {path}"

    error_details = {
        "path": path
    }

    if provider_id:
        error_details["provider_id"] = provider_id

    return {
        "code": DIRECTORY_NOT_FOUND,
        "message": message,
        "details": error_details,
        "suggestion": "Create the directory or configure a different path",
        "status_code": 404
    }


def build_model_file_not_found_error(
    path: str,
    provider_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build error details for model file not found scenario.

    Args:
        path: Model file path
        provider_id: Provider identifier (optional)

    Returns:
        dict: Error detail dictionary ready for provider_error_response
    """
    message = f"Model file does not exist: {path}"

    error_details = {
        "path": path
    }

    if provider_id:
        error_details["provider_id"] = provider_id

    return {
        "code": MODEL_FILE_NOT_FOUND,
        "message": message,
        "details": error_details,
        "suggestion": "Check the model file path, or download/install the model",
        "status_code": 404
    }


# ============================================================================
# Advanced Error Builders with Actionable Solutions (Task #20 - P1.7)
# ============================================================================


def build_exe_not_found_error(
    provider: str,
    searched_paths: List[str],
    platform: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build detailed error for executable not found scenario with actionable solutions.

    Args:
        provider: Provider name (e.g., "Ollama", "llama.cpp", "LM Studio")
        searched_paths: List of paths that were searched
        platform: Platform name (auto-detected if None)

    Returns:
        dict: Error detail dictionary with comprehensive solution steps

    Example:
        >>> build_exe_not_found_error("Ollama", ["/usr/local/bin/ollama"], "macos")
    """
    if platform is None:
        platform = platform_utils.get_platform()

    provider_lower = provider.lower()

    # Build installation instructions based on platform
    suggestion = f"""{provider} 未安装或路径未配置。

解决方案：
1. 安装 {provider}：
"""

    if platform == 'macos':
        if provider_lower == 'ollama':
            suggestion += "   • brew install ollama\n"
            suggestion += "   • 或访问 https://ollama.ai 下载\n"
        elif provider_lower in ['llamacpp', 'llama.cpp']:
            suggestion += "   • brew install llama.cpp\n"
            suggestion += "   • 或访问 https://github.com/ggerganov/llama.cpp/releases\n"
        elif provider_lower == 'lmstudio' or 'lm studio' in provider_lower:
            suggestion += "   • 下载 .dmg：https://lmstudio.ai\n"
            suggestion += "   • 拖拽到 Applications 文件夹\n"
        else:
            suggestion += f"   • brew install {provider_lower}\n"

    elif platform == 'linux':
        if provider_lower == 'ollama':
            suggestion += "   • curl -fsSL https://ollama.ai/install.sh | sh\n"
        elif provider_lower in ['llamacpp', 'llama.cpp']:
            suggestion += "   • 从源码构建：https://github.com/ggerganov/llama.cpp\n"
            suggestion += "   • 或下载预编译版本\n"
        elif provider_lower == 'lmstudio' or 'lm studio' in provider_lower:
            suggestion += "   • 下载 AppImage：https://lmstudio.ai\n"
            suggestion += "   • chmod +x LMStudio*.AppImage\n"
        else:
            suggestion += f"   • 使用包管理器安装或从官网下载\n"

    elif platform == 'windows':
        if provider_lower == 'ollama':
            suggestion += "   • 下载安装程序：https://ollama.ai/download/windows\n"
        elif provider_lower in ['llamacpp', 'llama.cpp']:
            suggestion += "   • 下载预编译版本：https://github.com/ggerganov/llama.cpp/releases\n"
        elif provider_lower == 'lmstudio' or 'lm studio' in provider_lower:
            suggestion += "   • 下载安装程序：https://lmstudio.ai/download/windows\n"
        else:
            suggestion += f"   • 从官网下载 Windows 安装程序\n"

    suggestion += "\n2. 或手动指定路径：点击 [配置路径] 按钮\n"
    suggestion += "\n搜索路径："

    for path in searched_paths:
        suggestion += f"\n   • {path}"

    return {
        "code": EXECUTABLE_NOT_FOUND,
        "message": f"{provider} 可执行文件未找到",
        "details": {
            "provider": provider,
            "searched_paths": searched_paths,
            "platform": platform
        },
        "suggestion": suggestion.strip(),
        "status_code": 404
    }


def build_permission_denied_error_detailed(
    exe_path: str,
    platform: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build detailed error for permission denied scenario with platform-specific solutions.

    Args:
        exe_path: Path to the executable that was denied
        platform: Platform name (auto-detected if None)

    Returns:
        dict: Error detail dictionary with permission fix instructions

    Example:
        >>> build_permission_denied_error_detailed("/usr/local/bin/ollama", "macos")
    """
    if platform is None:
        platform = platform_utils.get_platform()

    if platform in ['macos', 'linux']:
        suggestion = f"""无法执行 {exe_path}（权限不足）

解决方案：
• 添加可执行权限：chmod +x {exe_path}
• 或使用 sudo 运行 AgentOS（不推荐）
• 检查文件所有者：ls -l {exe_path}"""

    else:  # windows
        suggestion = f"""无法执行 {exe_path}（权限不足）

解决方案：
• 以管理员权限运行 AgentOS
  - 右键点击应用图标
  - 选择 "以管理员身份运行"
• 或检查文件属性中的"安全"选项卡
• 确保当前用户有执行权限"""

    return {
        "code": PERMISSION_DENIED,
        "message": f"权限不足：无法执行 {exe_path}",
        "details": {
            "path": exe_path,
            "platform": platform,
            "operation": "execute"
        },
        "suggestion": suggestion.strip(),
        "status_code": 403
    }


def build_port_in_use_error_detailed(
    port: int,
    provider: str,
    platform: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build detailed error for port already in use with platform-specific commands.

    Args:
        port: Port number that is in use
        provider: Provider name (e.g., "Ollama", "llama-server")
        platform: Platform name (auto-detected if None)

    Returns:
        dict: Error detail dictionary with port conflict resolution steps

    Example:
        >>> build_port_in_use_error_detailed(11434, "Ollama", "macos")
    """
    if platform is None:
        platform = platform_utils.get_platform()

    suggestion = f"""端口 {port} 已被占用（可能是另一个 {provider} 实例）

解决方案：
1. 停止占用该端口的进程：
"""

    if platform in ['macos', 'linux']:
        suggestion += f"   • 查看占用进程：lsof -i:{port}\n"
        suggestion += f"   • 终止进程：lsof -ti:{port} | xargs kill\n"
        suggestion += f"   • 或强制终止：lsof -ti:{port} | xargs kill -9\n"
    else:  # windows
        suggestion += f"   • 查看占用进程：netstat -ano | findstr :{port}\n"
        suggestion += f"   • 找到 PID 后终止：taskkill /PID <pid> /F\n"
        suggestion += f"   • 示例：taskkill /PID 12345 /F\n"

    suggestion += f"   \n2. 或修改此实例的端口号（在实例配置中更改）"

    return {
        "code": PORT_IN_USE,
        "message": f"端口 {port} 已被占用",
        "details": {
            "port": port,
            "provider": provider,
            "platform": platform
        },
        "suggestion": suggestion.strip(),
        "status_code": 409
    }


def build_start_failed_error(
    provider: str,
    exit_code: Optional[int],
    stderr: str,
    log_file: Optional[str] = None,
    instance_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build detailed error for process start failure with log excerpts.

    Args:
        provider: Provider name
        exit_code: Process exit code (None if process didn't start)
        stderr: Standard error output from the process
        log_file: Path to full log file (optional)
        instance_key: Instance identifier (optional)

    Returns:
        dict: Error detail dictionary with log preview and troubleshooting steps

    Example:
        >>> build_start_failed_error("Ollama", 1, "Error: failed to load model...", "~/.agentos/logs/ollama.log")
    """
    # Extract last 30 lines of stderr
    stderr_lines = stderr.split('\n') if stderr else []
    stderr_preview = '\n'.join(stderr_lines[-30:]) if stderr_lines else "(无输出)"

    # Truncate if still too long
    if len(stderr_preview) > 2000:
        stderr_preview = stderr_preview[-2000:] + "\n... (截断)"

    exit_code_text = exit_code if exit_code is not None else "未知"

    suggestion = f"""{provider} 启动失败（退出码：{exit_code_text}）

最后 30 行错误日志：
{stderr_preview}

解决方案：
"""

    if log_file:
        suggestion += f"1. 检查完整日志文件：{log_file}\n"
    else:
        suggestion += f"1. 检查系统日志获取更多信息\n"

    provider_lower = provider.lower()
    if 'ollama' in provider_lower:
        suggestion += """2. 验证模型文件完整性：ollama list
3. 尝试重新拉取模型：ollama pull <model-name>
4. 查看官方文档：https://ollama.ai/docs
5. 提交 Issue：https://github.com/ollama/ollama/issues"""

    elif 'llamacpp' in provider_lower or 'llama.cpp' in provider_lower:
        suggestion += """2. 验证模型文件路径和格式（需要 GGUF 格式）
3. 检查系统资源（内存、磁盘空间）
4. 查看官方文档：https://github.com/ggerganov/llama.cpp
5. 提交 Issue：https://github.com/ggerganov/llama.cpp/issues"""

    elif 'lmstudio' in provider_lower or 'lm studio' in provider_lower:
        suggestion += """2. 打开 LM Studio 应用手动检查错误
3. 验证模型已正确加载
4. 查看官方文档：https://lmstudio.ai/docs
5. 联系 LM Studio 支持"""

    else:
        suggestion += """2. 验证配置文件和启动参数
3. 检查系统资源和依赖
4. 查看相关文档和 Issue
5. 尝试使用默认配置启动"""

    details = {
        "provider": provider,
        "exit_code": exit_code,
        "stderr_preview": stderr_preview[:500],  # Truncated for details
        "platform": platform_utils.get_platform()
    }

    if log_file:
        details["log_file"] = log_file
    if instance_key:
        details["instance_key"] = instance_key

    return {
        "code": PROCESS_START_FAILED,
        "message": f"{provider} 启动失败",
        "details": details,
        "suggestion": suggestion.strip(),
        "status_code": 500
    }


def build_unsupported_action_error(
    provider: str,
    action: str
) -> Dict[str, Any]:
    """
    Build detailed error for unsupported provider action with alternative guidance.

    Args:
        provider: Provider name (e.g., "LM Studio")
        action: Action that is not supported (e.g., "stop", "restart")

    Returns:
        dict: Error detail dictionary with alternative action guidance

    Example:
        >>> build_unsupported_action_error("LM Studio", "stop")
    """
    provider_lower = provider.lower()

    # Special handling for LM Studio
    if 'lmstudio' in provider_lower or 'lm studio' in provider_lower:
        if action.lower() in ['stop', 'restart', 'shutdown']:
            suggestion = f"""LM Studio 不支持通过 CLI {action}。

说明：
LM Studio 是独立的 GUI 应用，需要在应用内手动管理。

操作方法：
1. 打开 LM Studio 应用（点击 [Open App] 按钮）
2. 在应用内点击 "Stop Server" 停止服务
3. 关闭应用窗口以完全退出

提示：
• 如果需要命令行控制，建议使用 Ollama 或 llama.cpp
• LM Studio 主要设计用于图形界面交互
• 可以通过 API 检测 LM Studio 服务是否运行"""

            return {
                "code": "UNSUPPORTED_ACTION",
                "message": f"LM Studio 不支持 {action} 操作",
                "details": {
                    "provider": provider,
                    "action": action,
                    "reason": "GUI应用，不支持CLI生命周期管理"
                },
                "suggestion": suggestion.strip(),
                "status_code": 400
            }

    # Generic unsupported action
    suggestion = f"""{provider} 不支持 {action} 操作。

说明：
此 provider 可能不支持该操作，或需要特殊的管理方式。

建议：
• 查看该 provider 的文档了解支持的操作
• 尝试使用 provider 自带的管理工具
• 考虑使用其他支持该操作的 provider"""

    return {
        "code": "UNSUPPORTED_ACTION",
        "message": f"{provider} 不支持 {action} 操作",
        "details": {
            "provider": provider,
            "action": action
        },
        "suggestion": suggestion.strip(),
        "status_code": 400
    }


# ============================================================================
# Logging Helpers
# ============================================================================


def log_provider_error(
    error_code: str,
    message: str,
    exc: Optional[Exception] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Log provider error with structured information.

    Args:
        error_code: Error code constant
        message: Error message
        exc: Exception object (optional)
        details: Additional context (optional)
    """
    log_msg = f"[{error_code}] {message}"

    if details:
        log_msg += f" | Details: {details}"

    if exc:
        logger.error(log_msg, exc_info=exc)
    else:
        logger.error(log_msg)
