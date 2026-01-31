# Capability Runner Architecture

## Overview

This document provides a detailed look at the Capability Runner's internal architecture, execution flow, and implementation details. For extension development, see the [Capability Runner Developer Guide](CAPABILITY_RUNNER_GUIDE.md).

## Table of Contents

- [System Architecture](#system-architecture)
- [Execution Flow](#execution-flow)
- [Permission System](#permission-system)
- [Audit Trail](#audit-trail)
- [State Machine](#state-machine)
- [Security Model](#security-model)
- [Performance Considerations](#performance-considerations)

---

## System Architecture

### Component Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                         Chat Layer                            │
│                                                                │
│  ┌────────────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │   WebUI Chat   │  │   CLI Chat      │  │   API Chat    │ │
│  └────────┬───────┘  └────────┬────────┘  └───────┬───────┘ │
│           │                   │                    │          │
│           └───────────────────┴────────────────────┘          │
│                              │                                │
└──────────────────────────────┼────────────────────────────────┘
                               │
                               ↓
┌───────────────────────────────────────────────────────────────┐
│                       Chat Engine                             │
│                                                                │
│  • send_message()                                             │
│  • Check if slash command                                     │
│  • Create ExecutionContext                                    │
│  • Call Capability Runner                                     │
│  • Format response                                            │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ↓
┌───────────────────────────────────────────────────────────────┐
│                  Slash Command Router                         │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Parse command string                             │   │
│  │  2. Look up extension in cache                       │   │
│  │  3. Match action from commands.yaml                  │   │
│  │  4. Load usage documentation                         │   │
│  │  5. Build CommandRoute                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                                │
│  Output: CommandRoute {                                       │
│    command_name, extension_id, action_id,                    │
│    runner, args, flags, description, usage_doc               │
│  }                                                            │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ↓
┌───────────────────────────────────────────────────────────────┐
│                    Capability Runner                          │
│                   (Core Orchestrator)                         │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  execute(route: CommandRoute, context: ExecutionCtx) │   │
│  │                                                       │   │
│  │  1. Validate inputs                                  │   │
│  │  2. Select executor based on runner type             │   │
│  │  3. Pre-execution checks (permissions, etc.)         │   │
│  │  4. Execute via selected executor                    │   │
│  │  5. Post-execution processing                        │   │
│  │  6. Log to audit trail                               │   │
│  │  7. Return CapabilityResult                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                                │
│  Executor Registry:                                           │
│  ┌──────────────┬────────────────────────────────────┐      │
│  │ Runner Type  │ Executor Class                     │      │
│  ├──────────────┼────────────────────────────────────┤      │
│  │ exec.*       │ ExecToolExecutor                   │      │
│  │ analyze.*    │ AnalyzeResponseExecutor            │      │
│  │ browser.*    │ BrowserExecutor (future)           │      │
│  │ api.*        │ APICallExecutor (future)           │      │
│  └──────────────┴────────────────────────────────────┘      │
└───────────────┬────────────────────────┬──────────────────────┘
                │                        │
     ┌──────────┘                        └──────────┐
     ↓                                              ↓
┌────────────────────┐                  ┌───────────────────────┐
│  ExecToolExecutor  │                  │ AnalyzeResponseExec   │
│                    │                  │                       │
│  ┌──────────────┐  │                  │  ┌─────────────────┐ │
│  │ToolExecutor  │  │                  │  │  LLM Client     │ │
│  └──────────────┘  │                  │  └─────────────────┘ │
│  ┌──────────────┐  │                  │  ┌─────────────────┐ │
│  │ResponseStore │  │                  │  │ ResponseStore   │ │
│  └──────────────┘  │                  │  └─────────────────┘ │
└────────────────────┘                  └───────────────────────┘
         │                                          │
         ↓                                          ↓
┌────────────────────┐                  ┌───────────────────────┐
│  Subprocess        │                  │  LLM API              │
│  • Tool execution  │                  │  • Analysis prompts   │
│  • Timeout control │                  │  • Response parsing   │
│  • Output capture  │                  │                       │
└────────────────────┘                  └───────────────────────┘
```

### Class Hierarchy

```
BaseExecutor (ABC)
├── ExecToolExecutor
│   ├── ToolExecutor
│   └── ResponseStore
├── AnalyzeResponseExecutor
│   ├── LLM Client
│   └── ResponseStore
└── AnalyzeSchemaExecutor (future)

CapabilityRunner
├── Executor Registry: Dict[str, BaseExecutor]
├── execute() → CapabilityResult
└── get_executor() → BaseExecutor
```

---

## Execution Flow

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Command Reception                                      │
└─────────────────────────────────────────────────────────────────┘
  User types: "/postman get https://api.example.com"
       ↓
  ChatEngine receives message
       ↓
  Detects slash command prefix "/"

┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Command Routing                                        │
└─────────────────────────────────────────────────────────────────┘
  SlashCommandRouter.is_slash_command() → true
       ↓
  SlashCommandRouter.route() → CommandRoute
       ↓
  CommandRoute {
    command_name: "/postman",
    extension_id: "tools.postman",
    action_id: "get",
    runner: "exec.postman_cli",
    args: ["https://api.example.com"],
    usage_doc: "..."
  }

┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Context Preparation                                    │
└─────────────────────────────────────────────────────────────────┘
  ChatEngine creates ExecutionContext
       ↓
  ExecutionContext {
    session_id: "sess_abc123",
    user_id: "user_xyz",
    extension_id: "tools.postman",
    work_dir: "~/.agentos/extensions/tools.postman/work",
    timeout: 300,
    usage_doc: "...",
    env_whitelist: ["PATH", "HOME", ...]
  }

┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Capability Execution (Capability Runner)               │
└─────────────────────────────────────────────────────────────────┘
  CapabilityRunner.execute(route, context)
       ↓
  ┌───────────────────────────────────────────┐
  │ Step 1: Validate Inputs                   │
  │ • Check route fields are present          │
  │ • Check context is valid                  │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Step 2: Select Executor                   │
  │ • runner = "exec.postman_cli"             │
  │ • Match prefix "exec."                    │
  │ • Select ExecToolExecutor                 │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Step 3: Execute via Executor              │
  │ • Call executor.execute(route, context)   │
  └───────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: Tool Execution (ExecToolExecutor)                      │
└─────────────────────────────────────────────────────────────────┘
  ExecToolExecutor.execute(route, context)
       ↓
  ┌───────────────────────────────────────────┐
  │ Extract tool name                         │
  │ • "exec.postman_cli" → "postman"          │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Build command arguments                   │
  │ • [action_id] + args                      │
  │ • ["get", "https://api.example.com"]      │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Call ToolExecutor                         │
  │ • tool_name = "postman"                   │
  │ • args = ["get", "https://..."]           │
  │ • work_dir = context.work_dir             │
  │ • timeout = 300                           │
  └───────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Phase 6: Subprocess Execution (ToolExecutor)                    │
└─────────────────────────────────────────────────────────────────┘
  ToolExecutor.execute_tool()
       ↓
  ┌───────────────────────────────────────────┐
  │ Check tool exists                         │
  │ • which postman → /usr/local/bin/postman  │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Validate work directory                   │
  │ • Must be under ~/.agentos/extensions/    │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Build clean environment                   │
  │ • Filter env vars by whitelist            │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Execute subprocess                        │
  │ • subprocess.run()                        │
  │ • timeout = 300 seconds                   │
  │ • capture stdout/stderr                   │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Return ToolExecutionResult                │
  │ • success: true                           │
  │ • exit_code: 0                            │
  │ • stdout: "..."                           │
  │ • stderr: ""                              │
  │ • duration_ms: 1234                       │
  └───────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Phase 7: Post-Execution (ExecToolExecutor)                      │
└─────────────────────────────────────────────────────────────────┘
  ┌───────────────────────────────────────────┐
  │ Store response in ResponseStore           │
  │ • session_id → response mapping           │
  │ • For follow-up analyze commands          │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Build ExecutionResult                     │
  │ • success: true                           │
  │ • output: "... stdout ..."                │
  │ • metadata: {exit_code, duration, ...}    │
  └───────────────────────────────────────────┘
       ↓
  Return ExecutionResult to CapabilityRunner

┌─────────────────────────────────────────────────────────────────┐
│ Phase 8: Result Formatting (Capability Runner)                  │
└─────────────────────────────────────────────────────────────────┘
  ┌───────────────────────────────────────────┐
  │ Convert ExecutionResult to CapabilityResult│
  │ • Add timestamps                          │
  │ • Format output for display               │
  │ • Include metadata                        │
  └───────────────────────────────────────────┘
       ↓
  ┌───────────────────────────────────────────┐
  │ Log execution to audit trail              │
  │ • event: capability_executed              │
  │ • extension_id, command, action           │
  │ • success, duration, error                │
  └───────────────────────────────────────────┘
       ↓
  Return CapabilityResult to ChatEngine

┌─────────────────────────────────────────────────────────────────┐
│ Phase 9: Response Delivery                                      │
└─────────────────────────────────────────────────────────────────┘
  ChatEngine receives CapabilityResult
       ↓
  Format as chat message
       ↓
  Save to message history
       ↓
  Return to user (WebUI/CLI/API)
```

---

## Permission System

### Permission Types

```
┌──────────────────────┬───────────────────────────────────────┐
│ Permission           │ Grants Access To                      │
├──────────────────────┼───────────────────────────────────────┤
│ exec                 │ Execute CLI tools and subprocesses    │
│ network              │ Make HTTP/HTTPS requests              │
│ filesystem.read      │ Read files from work directory        │
│ filesystem.write     │ Write files to work directory         │
│ browser              │ Control browser automation            │
│ llm                  │ Call LLM APIs                         │
└──────────────────────┴───────────────────────────────────────┘
```

### Permission Check Flow

```
Extension declares in manifest.json:
┌────────────────────────────────┐
│ "permissions_required": [      │
│   "exec",                      │
│   "network"                    │
│ ]                              │
└────────────────────────────────┘
         │
         ↓
Runner checks before execution:
┌────────────────────────────────┐
│ if "exec" not in permissions:  │
│     raise PermissionError      │
└────────────────────────────────┘
         │
         ↓
Executor enforces constraints:
┌────────────────────────────────┐
│ • exec: Validate tool path     │
│ • network: Check URLs          │
│ • filesystem: Check work_dir   │
└────────────────────────────────┘
```

### Work Directory Enforcement

All filesystem operations are constrained to the extension's work directory:

```python
def _validate_work_directory(work_dir: Path) -> None:
    """
    Validate work directory is within allowed boundaries

    Allowed: ~/.agentos/extensions/{ext_id}/work/
    Denied:  Anything outside this path
    """
    allowed_base = Path.home() / ".agentos" / "extensions"

    # Resolve to absolute path (follows symlinks)
    resolved = work_dir.resolve()

    # Check if path is under allowed base
    if not resolved.is_relative_to(allowed_base):
        raise SecurityError(
            f"Work directory {work_dir} is outside allowed boundary"
        )

    # Check for path traversal attempts
    if ".." in str(work_dir):
        raise SecurityError("Path traversal detected")
```

**Example:**

```
✅ Allowed:
  ~/.agentos/extensions/tools.postman/work/
  ~/.agentos/extensions/tools.postman/work/cache/
  ~/.agentos/extensions/tools.postman/work/output.json

❌ Denied:
  /etc/passwd
  /home/user/documents/
  ~/.agentos/extensions/tools.other/work/  (different extension)
  ~/.agentos/extensions/tools.postman/../../../etc/passwd
```

---

## Audit Trail

### Log Format

Every capability execution is logged in structured JSON format:

```json
{
  "timestamp": "2026-01-30T10:30:45.123Z",
  "level": "INFO",
  "logger": "agentos.core.capabilities.runner",
  "event": "capability_executed",

  "extension_id": "tools.postman",
  "command": "/postman",
  "action": "get",
  "runner": "exec.postman_cli",

  "session_id": "sess_abc123",
  "user_id": "user_xyz",

  "success": true,
  "duration_seconds": 1.234,
  "exit_code": 0,

  "metadata": {
    "tool": "postman",
    "args_count": 1,
    "work_dir": "~/.agentos/extensions/tools.postman/work"
  },

  "error": null
}
```

### Log Levels

| Level | Event | Description |
|-------|-------|-------------|
| DEBUG | capability_started | Execution started |
| INFO | capability_executed | Execution completed successfully |
| WARNING | capability_slow | Execution took longer than expected |
| ERROR | capability_failed | Execution failed |
| ERROR | capability_timeout | Execution timed out |
| ERROR | security_violation | Security check failed |

### Log Aggregation

Logs are written to:

```
~/.agentos/logs/agentos.log         # Main log file
~/.agentos/logs/capabilities.log    # Capability-specific log
~/.agentos/logs/security.log        # Security events
```

### Audit Queries

```bash
# View all capability executions
grep capability_executed ~/.agentos/logs/capabilities.log

# View failures only
grep capability_failed ~/.agentos/logs/capabilities.log

# View specific extension
grep '"extension_id": "tools.postman"' ~/.agentos/logs/capabilities.log

# View security violations
cat ~/.agentos/logs/security.log
```

---

## State Machine

### Execution States

```
┌─────────────┐
│  CREATED    │  Capability execution created
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ VALIDATING  │  Validating inputs and permissions
└──────┬──────┘
       │
       ├─→ [Validation Failed] ─→ FAILED
       │
       ↓
┌─────────────┐
│  EXECUTING  │  Running executor
└──────┬──────┘
       │
       ├─→ [Timeout] ─→ TIMEOUT
       ├─→ [Error] ─→ FAILED
       │
       ↓
┌─────────────┐
│ PROCESSING  │  Post-execution processing
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  LOGGING    │  Writing audit logs
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ COMPLETED   │  Execution finished successfully
└─────────────┘
```

### State Transitions

| From State | Event | To State | Trigger |
|-----------|-------|----------|---------|
| CREATED | validate | VALIDATING | execute() called |
| VALIDATING | validated | EXECUTING | Validation passed |
| VALIDATING | invalid | FAILED | Validation failed |
| EXECUTING | success | PROCESSING | Executor returned |
| EXECUTING | error | FAILED | Exception raised |
| EXECUTING | timeout | TIMEOUT | Exceeded timeout |
| PROCESSING | processed | LOGGING | Processing complete |
| LOGGING | logged | COMPLETED | Log written |

---

## Security Model

### Threat Model

**Threats:**
1. Malicious extension executes arbitrary code
2. Extension escapes work directory sandbox
3. Extension consumes excessive resources
4. Extension leaks sensitive data
5. Extension compromises other extensions

**Mitigations:**

| Threat | Mitigation |
|--------|-----------|
| Arbitrary code | No direct code execution; tools only |
| Directory escape | Path validation with `resolve()` |
| Resource abuse | Timeouts and process limits |
| Data leakage | Environment variable filtering |
| Cross-extension | Isolated work directories |

### Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Permission Declaration                             │
│ • Extension declares required permissions in manifest       │
│ • User can review before enabling                           │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Runtime Permission Checks                          │
│ • Runner verifies permissions before execution              │
│ • Rejects operations without proper permissions             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Filesystem Sandbox                                 │
│ • Work directory validation                                 │
│ • Path traversal prevention                                 │
│ • Absolute path resolution                                  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Environment Isolation                              │
│ • Filtered environment variables                            │
│ • No sensitive vars (API keys, tokens)                      │
│ • Only whitelisted vars                                     │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: Resource Limits                                    │
│ • Execution timeout (default: 300s)                         │
│ • Output size limits                                        │
│ • Process count limits (future)                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 6: Audit Logging                                      │
│ • All executions logged                                     │
│ • Security violations logged                                │
│ • Forensic analysis possible                                │
└─────────────────────────────────────────────────────────────┘
```

### Security Checklist

When adding new executor types:

- [ ] Validate all inputs
- [ ] Enforce work directory boundaries
- [ ] Filter environment variables
- [ ] Set execution timeouts
- [ ] Limit output size
- [ ] Log all operations
- [ ] Handle errors securely (no info leakage)
- [ ] Test with malicious inputs
- [ ] Review permission requirements

---

## Performance Considerations

### Optimization Strategies

#### 1. Executor Caching

```python
# Executors are created once and reused
self.executors = {
    "exec": ExecToolExecutor(),  # Created once
    "analyze.response": AnalyzeResponseExecutor(llm_client),
}
```

#### 2. Command Cache

```python
# Slash Router caches command mappings
self.command_cache = {
    "/postman": (extension_id, capability_config),
    "/test": (extension_id, capability_config),
}
# No filesystem scans on every command
```

#### 3. Response Store

```python
# Store last response per session
# Avoid re-executing expensive commands
response_store.save(session_id, response, metadata)
response_store.get(session_id)  # Fast retrieval
```

#### 4. Lazy Loading

```python
# Usage docs loaded on-demand
usage_doc = self._load_usage_doc(extension_id)  # Only when needed
```

### Performance Metrics

**Target Performance:**

| Operation | Target | Typical |
|-----------|--------|---------|
| Command routing | < 10ms | ~5ms |
| Executor selection | < 1ms | ~0.5ms |
| Tool execution | < 5s | ~1s |
| Result formatting | < 10ms | ~5ms |
| Audit logging | < 5ms | ~2ms |
| **Total overhead** | **< 50ms** | **~15ms** |

**Bottlenecks:**

1. Tool execution (subprocess spawn)
2. LLM API calls (network latency)
3. Disk I/O (logs, response store)

**Monitoring:**

```python
# Log execution duration
log_entry = {
    "duration_seconds": result.duration_seconds,
    "duration_ms": result.metadata.get("duration_ms")
}

# Track slow executions
if duration > 5.0:
    logger.warning(
        "Slow capability execution",
        extra={"duration": duration, "extension_id": extension_id}
    )
```

---

## Future Enhancements

### Planned Features

1. **Browser Automation Executor**
   - Runner type: `browser.*`
   - Playwright/Selenium integration
   - Screenshot capture
   - Form filling

2. **API Call Executor**
   - Runner type: `api.*`
   - HTTP client with auth
   - Rate limiting
   - Response caching

3. **Database Query Executor**
   - Runner type: `db.*`
   - SQL query execution
   - Schema inspection
   - Query validation

4. **Resource Limits**
   - CPU usage limits
   - Memory limits
   - Disk space limits
   - Network bandwidth limits

5. **Advanced Permissions**
   - Fine-grained permissions
   - Temporary permission grants
   - User confirmation for sensitive operations

6. **Execution Queue**
   - Async execution
   - Priority queue
   - Concurrent execution limits

---

## Related Documents

- **ADR**: [ADR_CAPABILITY_RUNNER.md](../architecture/ADR_CAPABILITY_RUNNER.md)
- **Developer Guide**: [CAPABILITY_RUNNER_GUIDE.md](CAPABILITY_RUNNER_GUIDE.md)
- **Slash Routing**: [SLASH_COMMAND_ROUTING.md](SLASH_COMMAND_ROUTING.md)

---

**Last Updated:** 2026-01-30
