# Phase 2: Configuration Management - Quick Reference Guide

## Overview

Phase 2 extends the `ProvidersConfigManager` with executable path and models directory management capabilities.

---

## Quick Start

### Import
```python
from agentos.providers.providers_config import ProvidersConfigManager

manager = ProvidersConfigManager()  # Uses default config location
```

---

## Executable Path Management

### Enable Auto-Detection (Default)
```python
manager.set_executable_path("ollama", None)
# Sets: executable_path=None, auto_detect=True
```

### Set Custom Path
```python
manager.set_executable_path("ollama", "/opt/custom/ollama")
# Sets: executable_path="/opt/custom/ollama", auto_detect=False
# Raises ValueError if path is invalid
```

### Get Executable Path
```python
path = manager.get_executable_path("ollama")
# Returns: Path object or None
# Priority: configured path > auto-detected > None
```

### Supported Providers
- `ollama` → searches for `ollama` executable
- `llamacpp` → searches for `llama-server` executable
- `lmstudio` → searches for `lmstudio` or `LM Studio.app`

---

## Models Directory Management

### Set Provider-Specific Directory
```python
manager.set_models_directory("ollama", "/path/to/ollama/models")
# Validates that directory exists
```

### Set Global Directory
```python
manager.set_models_directory("global", "/path/to/shared/models")
# Used as fallback for all providers
```

### Get Models Directory
```python
path = manager.get_models_directory("ollama")
# Returns: Path object or None
# Priority: provider-specific > global > platform default
```

### Supported Providers
- `ollama` - Default: `~/.ollama/models`
- `llamacpp` - Default: `~/Documents/AI Models` (macOS), `~/Documents/AI_Models` (Linux)
- `lmstudio` - Default: `~/.cache/lm-studio/models`
- `global` - Shared fallback for all providers

---

## Configuration Structure

### Full Example
```json
{
  "providers": {
    "ollama": {
      "enabled": true,
      "executable_path": null,
      "auto_detect": true,
      "instances": [
        {
          "id": "default",
          "base_url": "http://127.0.0.1:11434",
          "enabled": true
        }
      ]
    }
  },
  "global": {
    "models_directories": {
      "ollama": "/custom/ollama/models",
      "llamacpp": null,
      "lmstudio": null,
      "global": "/shared/models"
    }
  }
}
```

---

## Common Patterns

### Pattern 1: Auto-Detect Everything
```python
manager = ProvidersConfigManager()

# All providers use auto-detection by default
for provider in ["ollama", "llamacpp", "lmstudio"]:
    exe = manager.get_executable_path(provider)
    models = manager.get_models_directory(provider)
    print(f"{provider}: exe={exe}, models={models}")
```

### Pattern 2: Custom Paths for Development
```python
manager = ProvidersConfigManager()

# Use custom build of llama-server
manager.set_executable_path("llamacpp", "/home/dev/llama.cpp/build/bin/llama-server")

# Use shared models directory
manager.set_models_directory("global", "/mnt/shared/models")
```

### Pattern 3: Validate Before Starting
```python
manager = ProvidersConfigManager()

provider_id = "ollama"
exe_path = manager.get_executable_path(provider_id)

if exe_path is None:
    print(f"❌ {provider_id} not found. Please install or configure path.")
else:
    print(f"✅ {provider_id} found at: {exe_path}")
    # Start the provider...
```

---

## Error Handling

### Invalid Executable Path
```python
try:
    manager.set_executable_path("ollama", "/nonexistent/path")
except ValueError as e:
    print(f"Error: {e}")
    # Error: Invalid executable path for ollama: /nonexistent/path
    # File must exist and be executable.
```

### Invalid Models Directory
```python
try:
    manager.set_models_directory("ollama", "/nonexistent/models")
except ValueError as e:
    print(f"Error: {e}")
    # Error: Models directory does not exist: /nonexistent/models
```

---

## Migration

### Old Config (Pre-Phase 2)
```json
{
  "providers": {
    "ollama": {
      "enabled": true,
      "instances": [...]
    }
  }
}
```

### Auto-Migrated Config (Phase 2+)
```json
{
  "providers": {
    "ollama": {
      "enabled": true,
      "executable_path": null,
      "auto_detect": true,
      "instances": [...]
    }
  },
  "global": {
    "models_directories": {
      "ollama": null,
      "llamacpp": null,
      "lmstudio": null,
      "global": null
    }
  }
}
```

**Migration is automatic** - no user action required!

---

## Platform-Specific Behavior

### Executable Detection

#### macOS
```python
# Searches in order:
# 1. /usr/local/bin/ollama
# 2. /opt/homebrew/bin/ollama
# 3. ~/Applications/Ollama.app/Contents/MacOS/ollama
# 4. PATH environment variable
```

#### Windows
```python
# Searches in order:
# 1. %LOCALAPPDATA%\Programs\Ollama\ollama.exe
# 2. C:\Program Files\Ollama\ollama.exe
# 3. PATH environment variable
# Note: Requires .exe extension
```

#### Linux
```python
# Searches in order:
# 1. /usr/local/bin/ollama
# 2. /usr/bin/ollama
# 3. ~/.local/bin/ollama
# 4. PATH environment variable
```

### Models Directories

| Provider | Windows | macOS/Linux |
|----------|---------|-------------|
| Ollama | `C:\Users\{user}\.ollama\models` | `~/.ollama/models` |
| LlamaCpp | `C:\Users\{user}\Documents\AI Models` | `~/Documents/AI Models` |
| LM Studio | `C:\Users\{user}\.cache\lm-studio\models` | `~/.cache/lm-studio/models` |

---

## Best Practices

### 1. Use Auto-Detection First
```python
# Let the system find executables automatically
path = manager.get_executable_path("ollama")
if path is None:
    # Only prompt user if auto-detection fails
    prompt_user_for_path()
```

### 2. Validate Paths Before Use
```python
# Always check if path exists before starting provider
exe_path = manager.get_executable_path("ollama")
if exe_path and exe_path.exists():
    start_ollama(exe_path)
else:
    show_error("Ollama not found")
```

### 3. Provide Fallbacks
```python
# Try auto-detection, then manual, then install prompt
exe_path = manager.get_executable_path("ollama")
if exe_path is None:
    # Try manual configuration
    exe_path = prompt_user_for_path()
    if exe_path:
        manager.set_executable_path("ollama", exe_path)
    else:
        # Prompt user to install
        show_install_instructions()
```

### 4. Handle Platform Differences
```python
from agentos.providers import platform_utils

platform = platform_utils.get_platform()
if platform == "windows":
    # Windows-specific logic
    pass
elif platform == "macos":
    # macOS-specific logic
    pass
else:  # linux
    # Linux-specific logic
    pass
```

---

## Testing

### Run Tests
```bash
# Simple test runner (no dependencies)
python3 test_providers_config_phase2_simple.py

# Full pytest suite (requires pytest)
pytest test_providers_config_phase2.py -v
```

### Run Demo
```bash
python3 demo_providers_config_phase2.py
```

---

## API Reference

### ProvidersConfigManager Methods

#### `set_executable_path(provider_id: str, path: Optional[str]) -> None`
Sets the executable path for a provider.
- `provider_id`: `"ollama"`, `"llamacpp"`, or `"lmstudio"`
- `path`: Absolute path to executable or `None` for auto-detection
- **Raises**: `ValueError` if path is invalid

#### `get_executable_path(provider_id: str) -> Optional[Path]`
Gets the executable path for a provider.
- **Returns**: `Path` object or `None`
- **Priority**: configured > auto-detected > None

#### `set_models_directory(provider_id: str, path: str) -> None`
Sets the models directory for a provider.
- `provider_id`: `"ollama"`, `"llamacpp"`, `"lmstudio"`, or `"global"`
- `path`: Absolute path to existing directory
- **Raises**: `ValueError` if path is invalid

#### `get_models_directory(provider_id: str) -> Optional[Path]`
Gets the models directory for a provider.
- **Returns**: `Path` object or `None`
- **Priority**: provider-specific > global > default

---

## Troubleshooting

### Problem: get_executable_path() returns None
**Cause**: Executable not in standard locations or PATH
**Solution**: Use `set_executable_path()` with custom path

### Problem: set_executable_path() raises ValueError
**Cause**: File doesn't exist or isn't executable
**Solution**: Check file permissions and path

### Problem: Old config not migrating
**Cause**: Config file permission issues
**Solution**: Check file write permissions

### Problem: Models directory not found
**Cause**: Default location doesn't exist
**Solution**: Use `set_models_directory()` to specify location

---

## Related Documentation

- **Implementation Report**: `TASK5_PHASE2_CONFIG_ENHANCEMENT_REPORT.md`
- **Phase 2 Checklist**: `PROVIDERS_CROSS_PLATFORM_FIX_CHECKLIST.md` (Section 2)
- **Platform Utils**: `agentos/providers/platform_utils.py`
- **Config Manager**: `agentos/providers/providers_config.py`

---

## Support

For issues or questions:
1. Check the implementation report
2. Run the demo script to see examples
3. Review test cases for usage patterns
4. Refer to the main checklist document

---

**Version**: 1.0
**Date**: 2026-01-29
**Status**: Production Ready ✅
