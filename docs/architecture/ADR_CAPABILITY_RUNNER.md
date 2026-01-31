# ADR-CAP-001: Capability Runner Architecture

## Status

**ACCEPTED** — 2026-01-30

## Context

AgentOS extensions provide capabilities that need to be executed in a controlled, secure, and auditable manner. Before this ADR, we had:

1. **Extension System (PR-A)**: Extensions can declare capabilities in manifest.json
2. **Slash Command Router (PR-D)**: Routes user commands to extensions
3. **Gap**: No execution layer to actually run extension capabilities

The challenge was to design an execution system that:
- Executes different types of capabilities (CLI tools, LLM analysis, browser automation)
- Enforces security boundaries and permissions
- Provides auditability and traceability
- Supports extensibility for new runner types
- Handles errors gracefully

### Key Requirements

1. **Isolation**: Extension code must not execute directly in the main process
2. **Type Safety**: Different capability types need different execution strategies
3. **Auditability**: All executions must be logged with sufficient detail
4. **Security**: Enforce work directory boundaries, timeouts, and permission checks
5. **Usability**: Provide clear error messages to users
6. **Performance**: Execute capabilities efficiently without blocking the system

### Previous Approaches Considered

#### Approach 1: Direct Execution
Execute extension code directly in the ChatEngine process.

**Pros:**
- Simple implementation
- Low overhead

**Cons:**
- Security risk (malicious extensions could compromise system)
- No isolation between extensions
- Hard to enforce timeouts and resource limits
- Difficult to audit execution

**Verdict:** ❌ Rejected — Too risky

#### Approach 2: Subprocess per Extension
Spawn a new subprocess for each extension execution.

**Pros:**
- Process isolation
- Can enforce timeouts
- Can limit resources

**Cons:**
- High overhead (process creation for every command)
- Complex inter-process communication
- Hard to share state between commands
- Platform-dependent behavior

**Verdict:** ⚠️ Partially viable — Good for long-running extensions but overkill for simple commands

#### Approach 3: Runner Architecture (Selected)
Use a runner-based architecture where different runner types handle different capability classes.

**Pros:**
- Flexible execution strategies per capability type
- Can optimize for each runner type
- Easy to add new runner types
- Clear separation of concerns
- Audit trail at runner level

**Cons:**
- More complex architecture
- Requires defining runner types upfront

**Verdict:** ✅ Selected — Best balance of flexibility, security, and performance

## Decision

We implement a **Capability Runner Architecture** with the following design:

### Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                       Chat Interface                         │
│                    (WebUI / CLI / API)                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                      Slash Command Router                    │
│                          (PR-D)                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  CommandRoute:                                     │    │
│  │  - command_name: "/postman"                        │    │
│  │  - extension_id: "tools.postman"                   │    │
│  │  - action_id: "get"                                │    │
│  │  - runner: "exec.postman_cli"                      │    │
│  │  - args: ["https://api.example.com"]               │    │
│  │  - usage_doc: "..."                                │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    Capability Runner                         │
│                         (PR-E)                               │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  CapabilityRunner.execute(route, context)        │      │
│  │    1. Validate inputs                            │      │
│  │    2. Select executor based on runner type       │      │
│  │    3. Execute capability                         │      │
│  │    4. Log execution for audit                    │      │
│  │    5. Return formatted result                    │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
│  Executor Selection:                                        │
│  ┌─────────────┬────────────────────────────┐              │
│  │ Runner Type │ Executor                   │              │
│  ├─────────────┼────────────────────────────┤              │
│  │ exec.*      │ ExecToolExecutor           │              │
│  │ analyze.*   │ AnalyzeResponseExecutor    │              │
│  │ browser.*   │ BrowserExecutor (future)   │              │
│  │ api.*       │ APICallExecutor (future)   │              │
│  └─────────────┴────────────────────────────┘              │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ↓                    ↓                    ↓
┌──────────────┐    ┌─────────────────┐   ┌─────────────┐
│ExecToolExec  │    │AnalyzeResponse  │   │   Future    │
│              │    │    Executor     │   │  Executors  │
│              │    │                 │   │             │
│ ToolExecutor │    │   LLM Client    │   │             │
│ RunStore     │    │   RunStore      │   │             │
└──────────────┘    └─────────────────┘   └─────────────┘
```

### Core Classes

#### 1. CapabilityRunner (Main Orchestrator)

```python
class CapabilityRunner:
    """
    Main capability execution orchestrator

    Responsibilities:
    - Route commands to appropriate executors
    - Manage execution context
    - Handle errors gracefully
    - Format results for user display
    - Log execution for audit
    """

    def __init__(self, base_dir: Path, llm_client=None):
        self.base_dir = base_dir
        self.executors = {
            "exec": ExecToolExecutor(),
            "analyze.response": AnalyzeResponseExecutor(llm_client),
            "analyze.schema": AnalyzeSchemaExecutor(),
        }

    def execute(
        self,
        route: CommandRoute,
        context: ExecutionContext
    ) -> CapabilityResult:
        """
        Execute an extension capability

        Process:
        1. Validate inputs
        2. Get appropriate executor
        3. Execute capability
        4. Format result for display
        5. Log execution
        """
```

#### 2. BaseExecutor (Abstract Base Class)

```python
class BaseExecutor(ABC):
    """Base class for capability executors"""

    @abstractmethod
    def execute(
        self,
        route: CommandRoute,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute a capability"""
        pass

    @abstractmethod
    def supports_runner(self, runner: str) -> bool:
        """Check if this executor supports a runner type"""
        pass
```

#### 3. ExecToolExecutor (Command-Line Tools)

```python
class ExecToolExecutor(BaseExecutor):
    """
    Execute command-line tools (exec.* runner type)

    Handles: exec.postman_cli, exec.curl, exec.ffmpeg
    """

    def execute(self, route, context) -> ExecutionResult:
        """
        Process:
        1. Extract tool name from runner (exec.postman_cli -> postman)
        2. Build command arguments from route
        3. Execute tool in controlled environment
        4. Store response for potential follow-up commands
        5. Return formatted result
        """
```

#### 4. AnalyzeResponseExecutor (LLM Analysis)

```python
class AnalyzeResponseExecutor(BaseExecutor):
    """
    Analyze output using LLM (analyze.response runner type)
    """

    def execute(self, route, context) -> ExecutionResult:
        """
        Process:
        1. Get content to analyze (last_response or provided)
        2. Build analysis prompt with usage documentation
        3. Call LLM for analysis
        4. Return formatted result
        """
```

### Data Models

#### CommandRoute (from Slash Router)

```python
@dataclass
class CommandRoute:
    command_name: str       # e.g., "/postman"
    extension_id: str       # e.g., "tools.postman"
    action_id: str          # e.g., "get"
    runner: str             # e.g., "exec.postman_cli"
    args: List[str]         # Command arguments
    flags: Dict[str, Any]   # Named flags
    description: str        # Action description
    metadata: Dict          # Additional metadata
```

#### ExecutionContext

```python
@dataclass
class ExecutionContext:
    session_id: str          # Chat session ID
    user_id: str             # User identifier
    extension_id: str        # Extension ID
    work_dir: Path           # Working directory
    usage_doc: str           # Content from docs/USAGE.md
    last_response: str       # For analyze.response
    timeout: int = 300       # Timeout in seconds
    env_whitelist: List[str] # Allowed env vars
```

#### CapabilityResult (Returned to User)

```python
@dataclass
class CapabilityResult:
    success: bool            # Execution success
    output: str              # Formatted output for display
    error: str               # User-friendly error message
    metadata: Dict           # Execution metadata
    artifacts: List[Path]    # Generated files
    started_at: datetime     # Start timestamp
    completed_at: datetime   # End timestamp
```

### Execution Flow

```
1. User Input
   └─> "/postman get https://api.example.com"

2. Slash Router (PR-D)
   └─> Parse command
   └─> Look up extension
   └─> Build CommandRoute

3. Chat Engine
   └─> Create ExecutionContext (session_id, work_dir, etc.)
   └─> Call runner.execute(route, context)

4. Capability Runner
   └─> Get executor for runner type "exec.postman_cli"
   └─> ExecToolExecutor selected

5. ExecToolExecutor
   └─> Extract tool name: "postman"
   └─> Build command: ["postman", "get", "https://api.example.com"]
   └─> ToolExecutor.execute_tool()

6. ToolExecutor
   └─> Verify tool exists
   └─> Check security boundaries
   └─> Run subprocess with timeout
   └─> Capture stdout/stderr
   └─> Return ToolExecutionResult

7. ExecToolExecutor (continued)
   └─> Store response in ResponseStore
   └─> Build ExecutionResult

8. Capability Runner (continued)
   └─> Convert to CapabilityResult
   └─> Log execution to audit trail
   └─> Return to Chat Engine

9. Chat Engine
   └─> Add assistant message to history
   └─> Return to user
```

### Security Enforcement

#### Work Directory Boundaries

```python
class ToolExecutor:
    def _validate_work_directory(self, work_dir: Path) -> None:
        """
        Ensure work directory is within allowed boundaries

        Rules:
        - Must be under ~/.agentos/extensions/{ext_id}/work/
        - Cannot use .. to escape
        - Must be an absolute path
        """
        allowed_base = Path.home() / ".agentos" / "extensions"
        if not work_dir.resolve().is_relative_to(allowed_base):
            raise SecurityError(
                f"Work directory {work_dir} is outside allowed boundary"
            )
```

#### Environment Variable Filtering

```python
def _build_clean_env(self, whitelist: List[str]) -> Dict[str, str]:
    """
    Build a clean environment with only whitelisted vars

    Default whitelist:
    - PATH, HOME, USER, LANG, LC_ALL, TMPDIR
    """
    return {k: v for k, v in os.environ.items() if k in whitelist}
```

#### Timeout Enforcement

```python
result = subprocess.run(
    command,
    cwd=work_dir,
    timeout=timeout_seconds,
    env=clean_env,
    capture_output=True,
    text=True
)
```

### Audit Trail

Every capability execution is logged:

```python
log_entry = {
    "event": "capability_executed",
    "timestamp": datetime.now().isoformat(),
    "extension_id": "tools.postman",
    "command": "/postman",
    "action": "get",
    "runner": "exec.postman_cli",
    "session_id": "sess_123",
    "user_id": "user_456",
    "success": True,
    "duration_seconds": 1.234,
    "exit_code": 0,
    "error": None
}
```

### Runner Types

| Runner Type | Purpose | Executor | Example |
|------------|---------|----------|---------|
| `exec.*` | Execute CLI tools | ExecToolExecutor | `exec.postman_cli` |
| `analyze.response` | Analyze text with LLM | AnalyzeResponseExecutor | `analyze.response` |
| `analyze.schema` | Analyze JSON schema | AnalyzeSchemaExecutor | `analyze.schema` |
| `browser.navigate` | Browser automation | BrowserExecutor (future) | `browser.navigate` |
| `api.call` | Make API calls | APICallExecutor (future) | `api.call` |

### Response Storage

For commands that support follow-up analysis:

```python
class ResponseStore:
    """
    Store last response per session for follow-up commands

    Example:
      1. /postman get https://api.example.com  # Stores response
      2. /postman explain last_response         # Analyzes stored response
    """

    def save(self, session_id: str, response: str, metadata: dict):
        """Save response for session"""

    def get(self, session_id: str) -> Optional[str]:
        """Get last response for session"""

    def clear(self, session_id: str):
        """Clear response for session"""
```

## Rationale

### Why Runner-Based Architecture?

1. **Separation of Concerns**: Each executor handles one type of capability
2. **Extensibility**: Easy to add new runner types without modifying core
3. **Type Safety**: Different runners enforce different constraints
4. **Testability**: Can test each executor in isolation
5. **Performance**: Can optimize each executor for its specific task

### Why Not Direct Code Execution?

1. **Security**: Extensions might be malicious or buggy
2. **Isolation**: One extension shouldn't affect others
3. **Control**: Need to enforce timeouts, resource limits
4. **Auditability**: Need to log all executions

### Why Response Store?

1. **User Experience**: Users expect to reference previous outputs
2. **Workflow**: Common pattern: execute → analyze → refine
3. **Efficiency**: Don't re-execute expensive commands
4. **Context**: LLM analyzers need the actual response text

## Consequences

### Positive

1. **Security**: Strong isolation between extensions and main system
2. **Auditability**: Complete execution trail in logs
3. **Extensibility**: Easy to add new capability types
4. **Error Handling**: Graceful degradation with clear user messages
5. **Performance**: Efficient execution with caching where appropriate
6. **Testability**: Each component can be tested independently

### Negative

1. **Complexity**: More moving parts than direct execution
2. **Overhead**: Additional abstraction layers add latency
3. **Learning Curve**: Extension developers need to understand runner types
4. **Maintenance**: Need to maintain multiple executor implementations

### Neutral

1. **Runner Type Declaration**: Extensions must specify runner type in commands.yaml
2. **Context Management**: ExecutionContext carries more information than simple args
3. **Result Formatting**: Need to convert between internal and user-facing formats

## Implementation Notes

### Phase 1: Core Runner (Completed)
- ✅ CapabilityRunner class
- ✅ BaseExecutor interface
- ✅ ExecToolExecutor for CLI tools
- ✅ AnalyzeResponseExecutor for LLM analysis
- ✅ Response storage system
- ✅ Audit logging

### Phase 2: Security Enhancements (Completed)
- ✅ Work directory validation
- ✅ Environment variable filtering
- ✅ Timeout enforcement
- ✅ Tool existence checking

### Phase 3: Integration (Completed)
- ✅ Integration with ChatEngine
- ✅ Integration with Slash Command Router
- ✅ Error message formatting
- ✅ Result serialization

### Future Phases
- ⏳ Browser automation executor (browser.*)
- ⏳ API call executor (api.*)
- ⏳ File operation executor (file.*)
- ⏳ Database query executor (db.*)

## Testing Strategy

### Unit Tests
```python
# Test executor selection
def test_get_executor_for_exec_runner():
    runner = CapabilityRunner()
    executor = runner.get_executor("exec.postman_cli")
    assert isinstance(executor, ExecToolExecutor)

# Test tool extraction
def test_extract_tool_name():
    executor = ExecToolExecutor()
    assert executor._extract_tool_name("exec.postman_cli") == "postman"
    assert executor._extract_tool_name("exec.curl") == "curl"

# Test security validation
def test_work_directory_validation():
    tool_exec = ToolExecutor()
    # Should pass
    tool_exec._validate_work_directory(
        Path.home() / ".agentos/extensions/tools.test/work"
    )
    # Should fail
    with pytest.raises(SecurityError):
        tool_exec._validate_work_directory(Path("/etc"))
```

### Integration Tests
```python
# Test full execution flow
def test_execute_echo_command():
    runner = CapabilityRunner()
    route = CommandRoute(
        command_name="/test",
        extension_id="tools.test",
        action_id="hello",
        runner="exec.echo",
        args=["Hello, World!"]
    )
    context = ExecutionContext(
        session_id="test_session",
        user_id="test_user",
        extension_id="tools.test",
        work_dir=Path("/tmp/.agentos/test/work")
    )

    result = runner.execute(route, context)

    assert result.success is True
    assert "Hello, World!" in result.output
```

### End-to-End Tests
```python
# Test through chat interface
def test_chat_slash_command():
    engine = ChatEngine()
    session_id = engine.create_session()

    response = engine.send_message(
        session_id=session_id,
        user_input="/test hello"
    )

    assert response['metadata']['extension_command'] == "/test"
    assert "hello" in response['text'].lower()
```

## Related Documents

- **PR-A Summary**: Extension system and registry
- **PR-D Summary**: Slash command routing
- **Slash Command Routing Guide**: `/docs/extensions/SLASH_COMMAND_ROUTING.md`
- **Extension Development Guide**: `/docs/extensions/CAPABILITY_RUNNER_GUIDE.md`
- **Runner Architecture**: `/docs/extensions/RUNNER_ARCHITECTURE.md`

## Alternatives Considered

### Alternative 1: WebAssembly Sandboxing

Execute extension code in WebAssembly sandbox.

**Pros:**
- True sandboxing
- Platform-independent

**Cons:**
- Complex tooling required
- Limited access to system resources
- Performance overhead
- Requires recompiling extensions

**Why rejected:** Too restrictive for tools that need system access (CLI, browser)

### Alternative 2: Docker Containers

Execute each capability in a Docker container.

**Pros:**
- Strong isolation
- Resource limits
- Reproducible environment

**Cons:**
- Heavy overhead (containers per command)
- Requires Docker installation
- Complex networking and volume management
- Slow startup time

**Why rejected:** Overhead too high for simple commands, better suited for long-running services

### Alternative 3: Virtual Environments per Extension

Each extension runs in its own Python venv.

**Pros:**
- Dependency isolation
- Python-native

**Cons:**
- Only works for Python extensions
- Doesn't help with CLI tool execution
- venv management overhead
- Doesn't address security concerns

**Why rejected:** Too narrow, only solves Python dependency conflicts

## References

- Python `subprocess` module documentation
- OWASP guidelines for subprocess execution
- Postman CLI (`newman`) documentation
- Similar systems: VS Code extensions, Slack bots, GitHub Actions

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-30 | 1.0 | Initial ADR created |
