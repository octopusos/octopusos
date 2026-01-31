# PR-E2: BuiltinRunner Quick Start Guide

## What is PR-E2?

PR-E2 implements the **BuiltinRunner** - a Python handler executor that enables real extension command execution. Now `/test hello` and `/test status` work with actual Python code execution!

## Quick Test (5 minutes)

### Step 1: Install Handler Files

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python3 scripts/install_test_handlers.py
```

Expected output:
```
✅ Installed handlers.py to ~/.agentos/extensions/tools.test/handlers.py
✅ Installed commands/commands.yaml to ~/.agentos/extensions/tools.test/commands/commands.yaml
```

### Step 2: Run Tests

```bash
# Unit tests (16 tests)
python3 -m pytest tests/unit/core/capabilities/test_builtin_runner.py -v

# Integration tests (4 tests)
python3 -m pytest tests/integration/extensions/test_builtin_runner_e2e.py -v

# Manual test suite (all scenarios)
python3 scripts/test_builtin_runner_manual.py
```

### Step 3: Test in WebUI

```bash
# Start WebUI
python3 -m agentos.webui.app
```

Open http://localhost:8888 and try:
- `/test hello` → "Hello from Test Extension! 🎉"
- `/test hello Alice` → "Hello, Alice! 🎉"
- `/test status` → System status report

## What's New?

### Before PR-E2
```
User: /test hello
Bot: Extension command '/test' routed successfully!
     Note: Capability runner is not yet implemented.
```

### After PR-E2
```
User: /test hello
Bot: Hello from Test Extension! 🎉
```

**Real execution with progress tracking!**

## Architecture

```
User types: /test hello world
         ↓
SlashCommandRouter routes to tools.test
         ↓
ChatEngine calls Execute API
         ↓
BuiltinRunner loads handlers.py
         ↓
Executes hello_fn(["world"], context)
         ↓
Returns: "Hello, world! 🎉"
```

## Key Files

### Implementation
- `agentos/core/capabilities/runner_base/builtin.py` - BuiltinRunner
- `agentos/core/capabilities/runner_base/__init__.py` - Factory
- `agentos/webui/api/extensions_execute.py` - Execute API
- `agentos/core/chat/engine.py` - ChatEngine integration

### Extension
- `store/extensions/tools.test/handlers.py` - Handler functions
- `store/extensions/tools.test/commands/commands.yaml` - Command routes

### Tests
- `tests/unit/core/capabilities/test_builtin_runner.py` - Unit tests
- `tests/integration/extensions/test_builtin_runner_e2e.py` - E2E tests
- `scripts/test_builtin_runner_manual.py` - Manual tests

## Testing Commands

### Direct Python Test
```python
from agentos.core.capabilities.runner_base import BuiltinRunner, Invocation

runner = BuiltinRunner()
invocation = Invocation(
    extension_id="tools.test",
    action_id="hello",
    session_id="test",
    args=["Alice"]
)

def progress(stage, pct, msg):
    print(f"[{pct}%] {stage}: {msg}")

result = runner.run(invocation, progress_cb=progress)
print(f"Output: {result.output}")
```

### API Test
```bash
# Execute command
curl -X POST http://localhost:8888/api/extensions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_123",
    "command": "/test hello world",
    "dry_run": false
  }'

# Check status (replace run_id)
curl http://localhost:8888/api/runs/run_abc123def456
```

## Progress Stages

When executing, you'll see 5 progress stages:

1. **VALIDATING (5%)** - Check extension and handler exist
2. **LOADING (15%)** - Load handlers.py module
3. **EXECUTING (60%)** - Run handler function
4. **FINALIZING (90%)** - Process results
5. **DONE (100%)** - Complete

## Available Commands

### /test hello [name]
Says hello from the test extension.

**Examples:**
- `/test hello` → "Hello from Test Extension! 🎉"
- `/test hello Alice` → "Hello, Alice! 🎉"
- `/test hello Alice Bob` → "Hello, Alice Bob! 🎉"

### /test status
Shows system status information.

**Output:**
```
System Status Report:

Environment:
- Platform: Darwin 25.2.0
- Architecture: arm64
- Python Version: 3.14.2
- Current Time: 2026-01-30 14:05:07

Execution Context:
- Session ID: sess_123
- Extension ID: tools.test
- Work Directory: ~/.agentos/extensions/tools.test

Status: ✅ All systems operational
```

## Error Handling

### Extension Not Found
```
User: /nonexistent hello
Bot: Command not found: /nonexistent
```

### Handler Not Found
```
User: /test nonexistent
Bot: Handler not found for action 'nonexistent' in extension tools.test.
     Available actions: hello, status
```

### Extension Disabled
```
User: /test hello
Bot: Extension 'Test Extension' is disabled.
     Enable the extension to use /test
```

## Performance

- **Execution time**: 100-150ms per handler
- **Module loading**: ~10ms (cached after first load)
- **Progress updates**: Real-time via polling (0.5s intervals)

## Troubleshooting

### handlers.py not found?
```bash
# Run installation script
python3 scripts/install_test_handlers.py
```

### Tests failing?
```bash
# Check if tools.test is installed
ls ~/.agentos/extensions/tools.test/handlers.py

# Reinstall if missing
python3 scripts/install_test_handlers.py
```

### WebUI not working?
```bash
# Check if server is running
curl http://localhost:8888/api/runs

# Check logs for errors
python3 -m agentos.webui.app
```

## Next Steps

After testing PR-E2:

1. **PR-E3**: ShellRunner for PostmanCLI
2. **PR-E4**: WebUI run progress display
3. **PR-E5**: Enhanced security (timeout, resource limits)

## Support

If you encounter issues:

1. Check test results: `python3 scripts/test_builtin_runner_manual.py`
2. Review logs: WebUI console output
3. Verify installation: `ls ~/.agentos/extensions/tools.test/`
4. Check documentation: `PR_E2_IMPLEMENTATION_REPORT.md`

## Summary

✅ BuiltinRunner implemented
✅ Test extension working
✅ All tests passing
✅ Ready for WebUI testing

**Try it now**: `/test hello world`
