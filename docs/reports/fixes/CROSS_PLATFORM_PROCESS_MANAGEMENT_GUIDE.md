# Cross-Platform Process Management - Developer Guide

**Last Updated**: 2026-01-29
**Status**: Phase 1.2 Complete

---

## Quick Start

AgentOS now provides cross-platform process management utilities that work seamlessly on Windows, macOS, and Linux.

### Import the Utilities

```python
from agentos.providers.process_manager import (
    start_process_cross_platform,
    stop_process_cross_platform,
    is_process_running_cross_platform,
    ProcessManager  # For advanced features
)
```

---

## Simple Process Management

For basic process operations without PID tracking or monitoring:

### Start a Process

```python
import subprocess
from agentos.providers.process_manager import start_process_cross_platform

# Start a process with automatic cross-platform compatibility
proc = start_process_cross_platform(
    command=['ollama', 'serve'],
    cwd=None,  # Optional: working directory
    env=None,  # Optional: environment variables
    capture_output=True  # Capture stdout/stderr
)

print(f"Process started with PID: {proc.pid}")
```

**What it does**:
- Windows: Uses `CREATE_NO_WINDOW` flag (no CMD popup)
- Unix: Standard subprocess.Popen
- Returns a subprocess.Popen object

---

### Check if Process is Running

```python
from agentos.providers.process_manager import is_process_running_cross_platform

pid = 12345

if is_process_running_cross_platform(pid):
    print(f"Process {pid} is running")
else:
    print(f"Process {pid} is not running")
```

**What it does**:
- Uses `psutil.pid_exists()` internally
- Works on Windows, macOS, Linux
- Replaces `os.kill(pid, 0)` on Unix and `tasklist` on Windows

---

### Stop a Process

```python
from agentos.providers.process_manager import stop_process_cross_platform

pid = 12345

# Graceful termination (5 second timeout)
success = stop_process_cross_platform(pid, timeout=5.0)

# Force kill (immediate)
success = stop_process_cross_platform(pid, force=True)
```

**What it does**:
- Graceful: SIGTERM on Unix, taskkill on Windows
- Force: SIGKILL on Unix, taskkill /F on Windows
- Returns True if process stopped, False if not found
- Raises ProcessError if termination fails

---

## Advanced Process Management

For full process lifecycle management with PID tracking, monitoring, and recovery:

### Using ProcessManager

```python
from agentos.providers.process_manager import ProcessManager

# Get singleton instance
pm = ProcessManager.get_instance()

# Start a managed process
success, message = await pm.start_process(
    instance_key="ollama:main",  # Unique identifier
    bin_name="ollama",
    args={
        "host": "127.0.0.1",
        "port": 11434,
        "extra_args": ["--verbose"]
    },
    check_port=True  # Check port availability before starting
)

if success:
    print(f"Started: {message}")
else:
    print(f"Failed: {message}")
```

**Features**:
- PID file tracking (survives reboots)
- Port conflict detection
- stdout/stderr capture
- Process recovery from PID files
- Background monitoring

---

### Check Process Status

```python
# Simple check
if pm.is_process_running("ollama:main"):
    print("Ollama is running")

# Get detailed info
proc_info = pm.get_process_info("ollama:main")
if proc_info:
    print(f"PID: {proc_info.pid}")
    print(f"Command: {proc_info.command}")
    print(f"Started: {proc_info.started_at}")
    print(f"Return code: {proc_info.returncode}")
```

---

### Get Process Output

```python
# Get last 100 lines of stdout
stdout_lines = pm.get_process_output(
    instance_key="ollama:main",
    lines=100,
    stream="stdout"
)

for line in stdout_lines:
    print(line)

# Get stderr
stderr_lines = pm.get_process_output(
    instance_key="ollama:main",
    lines=50,
    stream="stderr"
)
```

**Note**: ProcessManager buffers up to 1000 lines of output per stream.

---

### Stop a Managed Process

```python
# Graceful stop (5 second timeout)
success, message = await pm.stop_process("ollama:main")

# Force stop (immediate)
success, message = await pm.stop_process("ollama:main", force=True)

if success:
    print(f"Stopped: {message}")
```

---

### List All Managed Processes

```python
all_processes = pm.list_all_processes()

for instance_key, info in all_processes.items():
    print(f"{instance_key}:")
    print(f"  PID: {info['pid']}")
    print(f"  Running: {info['running']}")
    print(f"  Uptime: {info['uptime_seconds']}s")
    print(f"  Command: {info['command']}")
```

---

## Platform-Specific Paths

Use `platform_utils` for cross-platform directory paths:

```python
from agentos.providers.platform_utils import (
    get_run_dir,
    get_log_dir,
    get_config_dir,
    get_platform
)

# Get platform name
platform = get_platform()  # 'windows', 'macos', or 'linux'

# Get directories (automatically uses correct path for platform)
run_dir = get_run_dir()      # PID files
log_dir = get_log_dir()      # Log files
config_dir = get_config_dir()  # Configuration files

# Example on Windows:
# run_dir = C:\Users\User\AppData\Roaming\agentos\run
# Example on macOS/Linux:
# run_dir = /Users/user/.agentos/run
```

---

## Migration Guide

### Replacing Direct os.kill() Calls

**Before (Unix-only)**:
```python
import os
import signal

# Check process
try:
    os.kill(pid, 0)
    print("Process exists")
except ProcessLookupError:
    print("Process not found")

# Stop process
os.kill(pid, signal.SIGTERM)
```

**After (Cross-platform)**:
```python
from agentos.providers.process_manager import (
    is_process_running_cross_platform,
    stop_process_cross_platform
)

# Check process
if is_process_running_cross_platform(pid):
    print("Process exists")
else:
    print("Process not found")

# Stop process
stop_process_cross_platform(pid)
```

---

### Replacing subprocess.Popen Calls

**Before (No Windows handling)**:
```python
import subprocess

proc = subprocess.Popen(
    ['ollama', 'serve'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
# On Windows, this creates a visible CMD window!
```

**After (Cross-platform)**:
```python
from agentos.providers.process_manager import start_process_cross_platform

proc = start_process_cross_platform(['ollama', 'serve'])
# Windows: No CMD window (uses CREATE_NO_WINDOW)
# Unix: Standard behavior
```

---

### Replacing Hard-Coded Paths

**Before (Unix-only)**:
```python
from pathlib import Path

run_dir = Path.home() / ".agentos" / "run"
# Doesn't follow Windows conventions!
```

**After (Cross-platform)**:
```python
from agentos.providers.platform_utils import get_run_dir

run_dir = get_run_dir()
# Windows: %APPDATA%\agentos\run
# Unix: ~/.agentos/run
```

---

## Best Practices

### 1. Always Use Cross-Platform Utilities

❌ **Don't**:
```python
import os
os.kill(pid, 0)  # Unix only
```

✅ **Do**:
```python
from agentos.providers.process_manager import is_process_running_cross_platform
is_process_running_cross_platform(pid)
```

---

### 2. Use ProcessManager for Long-Running Services

❌ **Don't** (for services):
```python
proc = subprocess.Popen(['llama-server', ...])
# No PID tracking, no recovery, no monitoring
```

✅ **Do**:
```python
pm = ProcessManager.get_instance()
await pm.start_process("llamacpp:model1", "llama-server", args)
# Automatic PID tracking, recovery, monitoring
```

---

### 3. Handle Process Termination Gracefully

❌ **Don't**:
```python
stop_process_cross_platform(pid, force=True)  # Always force kill
```

✅ **Do**:
```python
# Try graceful first, force only if needed
success = stop_process_cross_platform(pid, timeout=5.0)
if not success:
    stop_process_cross_platform(pid, force=True)
```

---

### 4. Use Platform-Aware Paths

❌ **Don't**:
```python
pid_file = f"~/.agentos/run/{name}.pid"
```

✅ **Do**:
```python
from agentos.providers.platform_utils import get_run_dir
pid_file = get_run_dir() / f"{name}.pid"
```

---

## Testing Your Code

### Test on Multiple Platforms

```python
from agentos.providers.platform_utils import get_platform

platform = get_platform()

if platform == 'windows':
    # Test Windows-specific behavior
    pass
elif platform == 'macos':
    # Test macOS-specific behavior
    pass
elif platform == 'linux':
    # Test Linux-specific behavior
    pass
```

---

### Mock Process Operations

```python
from unittest.mock import patch

# Mock process start
with patch('agentos.providers.process_manager.start_process_cross_platform') as mock_start:
    mock_start.return_value = Mock(pid=12345)
    # Your test code here

# Mock process check
with patch('psutil.pid_exists') as mock_exists:
    mock_exists.return_value = True
    # Your test code here
```

---

## Troubleshooting

### Problem: Process doesn't start on Windows

**Symptom**: Process starts but no output, or CMD window flashes

**Solution**: Use `start_process_cross_platform()` which adds `CREATE_NO_WINDOW` flag

---

### Problem: Can't find process by PID

**Symptom**: `is_process_running_cross_platform()` returns False for valid PID

**Possible Causes**:
1. Process has already exited
2. Access denied (check permissions)
3. PID doesn't exist

**Debug**:
```python
import psutil

try:
    proc = psutil.Process(pid)
    print(f"Status: {proc.status()}")
    print(f"Name: {proc.name()}")
except psutil.NoSuchProcess:
    print("Process doesn't exist")
except psutil.AccessDenied:
    print("Access denied - check permissions")
```

---

### Problem: PID files in wrong location on Windows

**Symptom**: PID files created in `C:\Users\User\.agentos\run` instead of AppData

**Solution**: Ensure you're using `get_run_dir()` from `platform_utils`, not hard-coded paths

---

## Dependencies

- **psutil >= 5.9.0**: Cross-platform process management (required)
- **platform_utils**: Cross-platform path utilities (internal)

---

## API Reference

### Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `start_process_cross_platform()` | Start a process | subprocess.Popen |
| `stop_process_cross_platform()` | Stop a process | bool |
| `is_process_running_cross_platform()` | Check if process exists | bool |

### ProcessManager Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_instance()` | Get singleton instance | ProcessManager |
| `start_process()` | Start managed process | tuple[bool, str] |
| `stop_process()` | Stop managed process | tuple[bool, str] |
| `is_process_running()` | Check process status | bool |
| `get_process_info()` | Get process details | ProcessInfo or None |
| `get_process_output()` | Get stdout/stderr | list[str] |
| `list_all_processes()` | List all processes | dict |

---

## Further Reading

- **Task #1 Report**: `TASK1_PLATFORM_UTILS_REPORT.md` - Platform detection and paths
- **Task #2 Report**: `TASK2_PROCESS_MANAGER_REFACTOR_REPORT.md` - Process manager details
- **Checklist**: `PROVIDERS_CROSS_PLATFORM_FIX_CHECKLIST.md` - Complete implementation plan
- **psutil Documentation**: https://psutil.readthedocs.io/

---

## Support

For questions or issues:
1. Check this guide for common patterns
2. Review the implementation reports
3. Check the PROVIDERS_CROSS_PLATFORM_FIX_CHECKLIST.md
4. Test on multiple platforms before committing

---

**Version**: 1.0
**Maintained by**: AgentOS Development Team
