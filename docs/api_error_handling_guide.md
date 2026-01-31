# Providers API Error Handling Guide

## Quick Reference for Developers

This guide explains how to use the unified error handling system for providers-related APIs.

---

## Table of Contents

1. [Overview](#overview)
2. [Error Response Format](#error-response-format)
3. [Error Codes](#error-codes)
4. [Usage Examples](#usage-examples)
5. [Best Practices](#best-practices)
6. [Platform-Specific Features](#platform-specific-features)

---

## Overview

The `providers_errors` module provides:
- **Standardized error codes** for consistent error handling
- **Unified error response format** across all APIs
- **Platform-specific suggestions** for users
- **Timeout control** for async operations
- **Structured logging** for debugging

**Module**: `agentos.webui.api.providers_errors`

---

## Error Response Format

All provider API errors follow this JSON structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "key": "value",
      "context": "additional context"
    },
    "suggestion": "What the user should do to fix this"
  }
}
```

### Fields

- **code** (required): Error code constant
- **message** (required): Clear description of what went wrong
- **details** (optional): Additional context (paths, PIDs, ports, etc.)
- **suggestion** (optional): Actionable advice for the user

---

## Error Codes

### Executable/Binary Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `EXECUTABLE_NOT_FOUND` | 404 | Binary not found in search paths |
| `INVALID_PATH` | 400 | Path is invalid or malformed |
| `NOT_EXECUTABLE` | 400 | File lacks execute permissions |
| `FILE_NOT_FOUND` | 404 | File does not exist |
| `NOT_A_FILE` | 400 | Path points to directory, not file |

### Directory Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `DIRECTORY_NOT_FOUND` | 404 | Directory does not exist |
| `NOT_A_DIRECTORY` | 400 | Path is not a directory |
| `DIRECTORY_NOT_READABLE` | 403 | Cannot read directory contents |

### Permission Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `PERMISSION_DENIED` | 403 | Insufficient permissions for operation |

### Process Management Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `PROCESS_START_FAILED` | 500 | Failed to start process |
| `PROCESS_STOP_FAILED` | 500 | Failed to stop process |
| `PROCESS_NOT_RUNNING` | 404 | Process is not running |
| `PROCESS_ALREADY_RUNNING` | 409 | Process is already running (conflict) |

### Network Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `PORT_IN_USE` | 409 | Port is already in use |
| `PORT_NOT_AVAILABLE` | 500 | Port cannot be bound |

### Timeout Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `TIMEOUT_ERROR` | 504 | Operation timed out |
| `STARTUP_TIMEOUT` | 504 | Process startup timed out |
| `SHUTDOWN_TIMEOUT` | 504 | Process shutdown timed out |

### Model Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `MODEL_FILE_NOT_FOUND` | 404 | Model file does not exist |
| `INVALID_MODEL_FILE` | 400 | Model file format is invalid |

### Configuration Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `CONFIG_ERROR` | 404/400 | Configuration is missing or invalid |
| `INVALID_CONFIG` | 400 | Configuration validation failed |

### Platform Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNSUPPORTED_PLATFORM` | 400 | Operation not supported on this platform |
| `PLATFORM_SPECIFIC_ERROR` | 500 | Platform-specific failure |

### General Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INTERNAL_ERROR` | 500 | Unexpected internal server error |
| `LAUNCH_FAILED` | 500 | Failed to launch application/service |
| `VALIDATION_ERROR` | 400 | Input validation failed |

---

## Usage Examples

### 1. Raising an Error

```python
from agentos.webui.api import providers_errors

@router.post("/my-endpoint")
async def my_endpoint():
    if not executable_found:
        providers_errors.raise_provider_error(
            code=providers_errors.EXECUTABLE_NOT_FOUND,
            message="Ollama executable not found",
            details={"searched_paths": ["/usr/local/bin/ollama"]},
            suggestion="Install Ollama or configure the path",
            status_code=404
        )
```

### 2. Using Error Builders

```python
from agentos.webui.api import providers_errors

# Executable not found
error_info = providers_errors.build_executable_not_found_error(
    provider_id="ollama",
    searched_paths=["/usr/local/bin/ollama", "/opt/homebrew/bin/ollama"]
)
providers_errors.raise_provider_error(**error_info)

# Port in use
error_info = providers_errors.build_port_in_use_error(
    port=11434,
    occupant="ollama"
)
providers_errors.raise_provider_error(**error_info)

# Timeout
error_info = providers_errors.build_timeout_error(
    operation="startup",
    timeout_seconds=30.0,
    instance_key="ollama:default"
)
providers_errors.raise_provider_error(**error_info)
```

### 3. Adding Timeout Control

```python
import asyncio
from agentos.webui.api import providers_errors

@router.post("/start")
async def start_service(timeout: float = 30.0):
    try:
        result = await asyncio.wait_for(
            start_process(...),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        error_info = providers_errors.build_timeout_error(
            operation="startup",
            timeout_seconds=timeout,
            instance_key="ollama:default"
        )
        providers_errors.raise_provider_error(**error_info)
```

### 4. Structured Logging

```python
from agentos.webui.api import providers_errors

try:
    # Some operation
    pass
except Exception as e:
    providers_errors.log_provider_error(
        error_code=providers_errors.INTERNAL_ERROR,
        message="Failed to start provider",
        exc=e,
        details={"provider_id": "ollama"}
    )
    # Then raise the error
    providers_errors.raise_provider_error(...)
```

### 5. Platform-Specific Suggestions

```python
from agentos.webui.api import providers_errors

# Get install suggestion for current platform
suggestion = providers_errors.get_install_suggestion("ollama")
# macOS: "Install via Homebrew: brew install ollama, or download from https://ollama.ai"
# Windows: "Download installer from https://ollama.ai and run the setup"
# Linux: "Install via curl: curl -fsSL https://ollama.ai/install.sh | sh"

# Get permission fix suggestion
suggestion = providers_errors.get_path_permission_suggestion()
# Unix: "Run 'chmod +x <path>' to make the file executable, or check file permissions"
# Windows: "Ensure the file has a valid executable extension (.exe, .bat, .cmd) and you have permission to execute it"
```

---

## Best Practices

### 1. Use Specific Error Codes

❌ **Don't**:
```python
raise HTTPException(status_code=500, detail="Something went wrong")
```

✅ **Do**:
```python
providers_errors.raise_provider_error(
    code=providers_errors.EXECUTABLE_NOT_FOUND,
    message="Ollama executable not found",
    details={"searched_paths": paths},
    suggestion="Install Ollama or configure the path",
    status_code=404
)
```

### 2. Always Provide Context in Details

❌ **Don't**:
```python
providers_errors.raise_provider_error(
    code=providers_errors.PORT_IN_USE,
    message="Port in use",
    status_code=409
)
```

✅ **Do**:
```python
providers_errors.raise_provider_error(
    code=providers_errors.PORT_IN_USE,
    message=f"Port {port} is already in use",
    details={
        "port": port,
        "host": host,
        "occupant": "ollama"
    },
    suggestion="Stop the existing service or use a different port",
    status_code=409
)
```

### 3. Include Actionable Suggestions

❌ **Don't**:
```python
suggestion="There was an error"
```

✅ **Do**:
```python
suggestion="Install Ollama via Homebrew: brew install ollama"
# or
suggestion="Stop the instance first, or use the restart endpoint"
# or
suggestion="Configure models directory for llamacpp first"
```

### 4. Use Error Builders for Common Scenarios

❌ **Don't**:
```python
providers_errors.raise_provider_error(
    code=providers_errors.TIMEOUT_ERROR,
    message=f"Timeout after {timeout}s",
    details={"timeout": timeout},
    status_code=504
)
```

✅ **Do**:
```python
error_info = providers_errors.build_timeout_error(
    operation="startup",
    timeout_seconds=timeout,
    instance_key="ollama:default"
)
providers_errors.raise_provider_error(**error_info)
```

### 5. Log Before Raising

```python
# Log the error with context
providers_errors.log_provider_error(
    error_code=providers_errors.PROCESS_START_FAILED,
    message="Failed to start ollama",
    exc=exception,
    details={"instance_key": "ollama:default"}
)

# Then raise for client
providers_errors.raise_provider_error(...)
```

### 6. Preserve HTTPExceptions

```python
try:
    # Your code
    pass
except HTTPException:
    # Don't wrap HTTPExceptions - re-raise them
    raise
except Exception as e:
    # Handle unexpected errors
    providers_errors.raise_provider_error(...)
```

---

## Platform-Specific Features

### Install Suggestions

The `get_install_suggestion()` function returns platform-specific installation instructions:

```python
from agentos.webui.api import providers_errors

# Auto-detect platform
suggestion = providers_errors.get_install_suggestion("ollama")

# Explicit platform
suggestion = providers_errors.get_install_suggestion("ollama", "macos")
```

**Supported Providers**:
- `ollama`
- `llamacpp` (llama-server)
- `lmstudio`

**Platforms**:
- `windows`
- `macos`
- `linux`

### Permission Fix Suggestions

The `get_path_permission_suggestion()` function returns platform-specific permission fix instructions:

```python
from agentos.webui.api import providers_errors

# Auto-detect platform
suggestion = providers_errors.get_path_permission_suggestion()

# Explicit platform
suggestion = providers_errors.get_path_permission_suggestion("linux")
```

---

## Complete Endpoint Example

```python
from fastapi import APIRouter
from agentos.webui.api import providers_errors
import asyncio

router = APIRouter()

@router.post("/providers/{provider_id}/start")
async def start_provider(
    provider_id: str,
    timeout: float = 30.0
):
    """
    Start a provider with comprehensive error handling.
    """
    try:
        # Validate configuration
        if not config_exists(provider_id):
            providers_errors.raise_provider_error(
                code=providers_errors.CONFIG_ERROR,
                message=f"Provider '{provider_id}' not configured",
                details={"provider_id": provider_id},
                suggestion="Configure the provider first",
                status_code=404
            )

        # Check if already running
        if is_running(provider_id):
            providers_errors.raise_provider_error(
                code=providers_errors.PROCESS_ALREADY_RUNNING,
                message=f"Provider '{provider_id}' is already running",
                details={"provider_id": provider_id},
                suggestion="Stop the provider first or use restart",
                status_code=409
            )

        # Start with timeout
        try:
            result = await asyncio.wait_for(
                start_process(provider_id),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            error_info = providers_errors.build_timeout_error(
                operation="startup",
                timeout_seconds=timeout,
                instance_key=provider_id
            )
            providers_errors.raise_provider_error(**error_info)

        return {"status": "success", "pid": result.pid}

    except HTTPException:
        # Re-raise HTTPExceptions unchanged
        raise

    except Exception as e:
        # Log unexpected errors
        providers_errors.log_provider_error(
            error_code=providers_errors.INTERNAL_ERROR,
            message=f"Unexpected error starting {provider_id}",
            exc=e,
            details={"provider_id": provider_id}
        )

        # Raise with context
        providers_errors.raise_provider_error(
            code=providers_errors.INTERNAL_ERROR,
            message=f"Unexpected error: {str(e)}",
            details={"provider_id": provider_id},
            suggestion="Check server logs for more details",
            status_code=500
        )
```

---

## Testing Error Responses

### Validation Script

Run the validation script to verify implementation:

```bash
python3 tests/unit/test_error_codes_simple.py
```

### Expected Error Response

```bash
curl -X POST http://localhost:8000/api/providers/ollama/instances/start \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "nonexistent"}'
```

**Response** (404):
```json
{
  "error": {
    "code": "CONFIG_ERROR",
    "message": "Instance 'nonexistent' not found for provider 'ollama'",
    "details": {
      "provider_id": "ollama",
      "instance_id": "nonexistent",
      "available_instances": ["default"]
    },
    "suggestion": "Check instance ID or create the instance first"
  }
}
```

---

## Migration Guide

### Before (Old Style)

```python
@router.post("/start")
async def start():
    if not found:
        raise HTTPException(status_code=404, detail="Not found")

    if error:
        raise HTTPException(status_code=500, detail=str(error))
```

### After (New Style)

```python
from agentos.webui.api import providers_errors

@router.post("/start")
async def start():
    if not found:
        providers_errors.raise_provider_error(
            code=providers_errors.EXECUTABLE_NOT_FOUND,
            message="Ollama executable not found",
            details={"searched_paths": paths},
            suggestion=providers_errors.get_install_suggestion("ollama"),
            status_code=404
        )

    if error:
        providers_errors.log_provider_error(
            error_code=providers_errors.PROCESS_START_FAILED,
            message="Start failed",
            exc=error
        )
        providers_errors.raise_provider_error(
            code=providers_errors.PROCESS_START_FAILED,
            message=f"Failed to start: {str(error)}",
            details={"reason": str(error)},
            suggestion="Check logs and permissions",
            status_code=500
        )
```

---

## Summary

### Key Takeaways

1. **Always use error codes** - Never use plain strings
2. **Provide context in details** - Help debugging with specific information
3. **Include suggestions** - Guide users to solutions
4. **Use error builders** - Leverage pre-built error contexts
5. **Log before raising** - Maintain audit trail
6. **Add timeouts** - Protect against hanging operations

### Benefits

- ✅ Consistent error format across all APIs
- ✅ Better client-side error handling
- ✅ Platform-specific user guidance
- ✅ Easier debugging with structured logs
- ✅ Type-safe error codes
- ✅ Built-in timeout protection

---

**Document Version**: 1.0
**Last Updated**: 2026-01-29
**Module**: `agentos.webui.api.providers_errors`
