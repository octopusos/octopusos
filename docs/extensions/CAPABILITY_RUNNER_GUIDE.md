# Capability Runner Developer Guide

## Overview

The Capability Runner is the execution engine for AgentOS extensions. When users invoke slash commands like `/postman get https://api.example.com`, the Capability Runner:

1. Receives a parsed command route from the Slash Command Router
2. Selects the appropriate executor based on runner type
3. Executes the capability in a controlled environment
4. Returns formatted results to the user
5. Logs execution for audit and debugging

This guide teaches you how to develop extensions that leverage the Capability Runner system.

## Table of Contents

- [Quick Start](#quick-start)
- [Runner Types](#runner-types)
- [Declaring Capabilities](#declaring-capabilities)
- [Implementing Handlers](#implementing-handlers)
- [Permissions](#permissions)
- [Execution Context](#execution-context)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Debugging](#debugging)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Quick Start

### 1. Create Extension Structure

```
my-extension/
├── manifest.json           # Extension metadata
├── commands/
│   └── commands.yaml      # Slash command definitions
├── handlers.py            # Python handlers (optional)
├── tools/                 # CLI tools (optional)
│   └── my-tool
├── docs/
│   └── USAGE.md          # Usage documentation
└── install/
    └── plan.yaml         # Installation plan
```

### 2. Define Capabilities in manifest.json

```json
{
  "id": "tools.example",
  "name": "Example Extension",
  "version": "1.0.0",
  "description": "Example extension for learning",

  "capabilities": [
    {
      "type": "slash_command",
      "name": "/example",
      "description": "Example command"
    }
  ],

  "permissions_required": [
    "exec",
    "network"
  ]
}
```

### 3. Define Actions in commands.yaml

```yaml
slash_commands:
  - name: "/example"
    summary: "Example command"
    examples:
      - "/example hello"
      - "/example status"

    actions:
      - id: hello
        description: "Say hello"
        runner: exec.python_handler

      - id: status
        description: "Show status"
        runner: exec.python_handler
```

### 4. Implement Handlers in handlers.py

```python
"""Handlers for example extension"""

def hello_fn(args, context):
    """Say hello"""
    name = args[0] if args else "World"
    return f"Hello, {name}! 🎉"

def status_fn(args, context):
    """Show system status"""
    import platform
    import sys
    from datetime import datetime

    return f"""System Status:
- Platform: {platform.system()} {platform.release()}
- Python: {sys.version.split()[0]}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

# Export handlers
HANDLERS = {
    "hello": hello_fn,
    "status": status_fn,
}
```

### 5. Test Your Extension

```python
# Install extension
agentos extensions install ./my-extension

# Test commands
/example hello Alice
/example status
```

---

## Runner Types

The runner type determines how your capability is executed. Choose the runner type that best matches your capability's needs.

### exec.* — Execute Command-Line Tools

For capabilities that invoke CLI tools (external programs).

**Format:** `exec.{tool_name}[_cli|_tool]`

**Examples:**
- `exec.postman_cli` → runs `postman` command
- `exec.curl` → runs `curl` command
- `exec.python_handler` → runs Python handler function

**Use when:**
- You need to invoke an external CLI tool
- You want to run shell commands
- You have a standalone executable

**Example:**

```yaml
actions:
  - id: get
    description: "Send GET request"
    runner: exec.curl
```

When user runs `/http get https://api.example.com`:
1. Runner extracts tool name: `curl`
2. Builds command: `curl get https://api.example.com`
3. Executes in controlled environment
4. Returns output to user

### analyze.response — Analyze with LLM

For capabilities that analyze previous command outputs or provided data using an LLM.

**Format:** `analyze.response`

**Use when:**
- You want to explain API responses
- You need to summarize command output
- You want to extract insights from data

**Example:**

```yaml
actions:
  - id: explain
    description: "Explain the last response"
    runner: analyze.response
```

When user runs `/postman explain last_response`:
1. Runner retrieves last response from ResponseStore
2. Builds analysis prompt with your USAGE.md context
3. Calls LLM for analysis
4. Returns formatted explanation

### analyze.schema — Analyze JSON Schema

For validating and explaining JSON schemas.

**Format:** `analyze.schema`

**Status:** Not yet implemented (future)

### browser.* — Browser Automation

For capabilities that control a browser.

**Format:** `browser.{action}`

**Examples:**
- `browser.navigate`
- `browser.screenshot`
- `browser.fill_form`

**Status:** Planned for future release

### api.* — API Calls

For capabilities that make HTTP API calls.

**Format:** `api.{method}`

**Examples:**
- `api.get`
- `api.post`
- `api.graphql`

**Status:** Planned for future release

---

## Declaring Capabilities

### In manifest.json

Declare what your extension can do:

```json
{
  "capabilities": [
    {
      "type": "slash_command",
      "name": "/mycommand",
      "description": "What this command does"
    }
  ]
}
```

### In commands.yaml

Define the slash command and its actions:

```yaml
slash_commands:
  - name: "/mycommand"
    summary: "Brief one-line summary"
    description: "Detailed description of what this command does"
    examples:
      - "/mycommand action1 arg"
      - "/mycommand action2 --flag value"

    maps_to:
      capability: "my.extension.id"
      actions:
        - id: action1
          description: "What action1 does"
          runner: exec.my_tool

        - id: action2
          description: "What action2 does"
          runner: analyze.response
```

**Field Descriptions:**

- `name`: The slash command (must start with `/`)
- `summary`: One-line description for autocomplete
- `description`: Detailed description shown in help
- `examples`: Example commands for users
- `maps_to.capability`: Your extension ID
- `actions[].id`: Action identifier (first argument after command)
- `actions[].description`: What the action does
- `actions[].runner`: Runner type to use

---

## Implementing Handlers

If your runner is `exec.python_handler` or you want custom Python logic, implement handlers.

### Handler Function Signature

```python
def handler_fn(args: List[str], context: dict) -> str:
    """
    Handler function

    Args:
        args: Command arguments (after action name)
        context: Execution context with session info

    Returns:
        String output to display to user

    Raises:
        Exception: On error (will be caught and formatted)
    """
    pass
```

### Context Object

The context dictionary contains:

```python
{
    "session_id": "sess_abc123",
    "user_id": "user_xyz",
    "extension_id": "tools.example",
    "work_dir": Path("/home/user/.agentos/extensions/tools.example/work"),
    "usage_doc": "Content from docs/USAGE.md",
    "timeout": 300
}
```

### Example Handlers

#### Simple Handler

```python
def hello_fn(args, context):
    """Say hello to user"""
    name = args[0] if args else "World"
    return f"Hello, {name}!"

HANDLERS = {"hello": hello_fn}
```

#### Handler with Arguments

```python
def greet_fn(args, context):
    """Greet user with custom message"""
    if not args:
        return "Error: Please provide a name"

    name = args[0]
    greeting = args[1] if len(args) > 1 else "Hello"

    return f"{greeting}, {name}!"

HANDLERS = {"greet": greet_fn}
```

Usage: `/example greet Alice "Good morning"`
Output: `Good morning, Alice!`

#### Handler with Context

```python
def whoami_fn(args, context):
    """Show current user and session info"""
    return f"""Current Context:
- User ID: {context['user_id']}
- Session ID: {context['session_id']}
- Extension ID: {context['extension_id']}
- Work Directory: {context['work_dir']}
"""

HANDLERS = {"whoami": whoami_fn}
```

#### Handler that Reads Files

```python
def read_config_fn(args, context):
    """Read extension configuration"""
    from pathlib import Path

    work_dir = Path(context['work_dir'])
    config_file = work_dir / "config.json"

    if not config_file.exists():
        return "Error: config.json not found"

    import json
    with open(config_file) as f:
        config = json.load(f)

    return f"Configuration:\n{json.dumps(config, indent=2)}"

HANDLERS = {"config": read_config_fn}
```

#### Handler that Makes API Calls

```python
def fetch_data_fn(args, context):
    """Fetch data from an API"""
    import requests

    if not args:
        return "Error: Please provide a URL"

    url = args[0]

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return f"Response ({response.status_code}):\n{response.text[:500]}"
    except Exception as e:
        return f"Error: {str(e)}"

HANDLERS = {"fetch": fetch_data_fn}
```

#### Handler with Error Handling

```python
def safe_divide_fn(args, context):
    """Safely divide two numbers"""
    if len(args) < 2:
        return "Error: Please provide two numbers"

    try:
        a = float(args[0])
        b = float(args[1])

        if b == 0:
            return "Error: Cannot divide by zero"

        result = a / b
        return f"{a} / {b} = {result}"

    except ValueError:
        return "Error: Invalid numbers provided"
    except Exception as e:
        return f"Error: {str(e)}"

HANDLERS = {"divide": safe_divide_fn}
```

### Exporting Handlers

Always export your handlers in a `HANDLERS` dictionary:

```python
HANDLERS = {
    "action1": action1_fn,
    "action2": action2_fn,
    "action3": action3_fn,
}
```

The keys must match the `action.id` values in your `commands.yaml`.

---

## Permissions

Extensions must declare required permissions in `manifest.json`.

### Available Permissions

| Permission | Description | Required For |
|-----------|-------------|--------------|
| `exec` | Execute commands | CLI tools, handlers |
| `network` | Make network requests | API calls, downloads |
| `filesystem.read` | Read files | Reading config, data files |
| `filesystem.write` | Write files | Saving output, cache |
| `browser` | Control browser | Browser automation |

### Declaring Permissions

```json
{
  "permissions_required": [
    "exec",
    "network",
    "filesystem.read"
  ]
}
```

### Permission Enforcement

The Capability Runner enforces permissions:

1. **exec**: Can only execute if declared
2. **network**: Network calls blocked if not declared
3. **filesystem**: Read/write operations validated against work directory

**Security Note:** Extensions are sandboxed to their work directory:
- ✅ `~/.agentos/extensions/{ext_id}/work/`
- ❌ Outside this directory

---

## Execution Context

When your capability executes, it receives an `ExecutionContext`:

```python
@dataclass
class ExecutionContext:
    session_id: str          # Chat session ID
    user_id: str             # User identifier
    extension_id: str        # Your extension ID
    work_dir: Path           # Your work directory
    usage_doc: Optional[str] # Content from docs/USAGE.md
    last_response: Optional[str]  # For analyze.response
    timeout: int = 300       # Timeout in seconds
    env_whitelist: List[str] # Allowed environment variables
```

### Work Directory

Each extension gets an isolated work directory:

```
~/.agentos/extensions/{extension_id}/work/
```

**Use it for:**
- Temporary files
- Cache
- Downloaded data
- Generated artifacts

**Example:**

```python
def cache_data_fn(args, context):
    """Cache data to work directory"""
    from pathlib import Path

    work_dir = Path(context['work_dir'])
    cache_file = work_dir / "cache.json"

    # Write data
    import json
    with open(cache_file, 'w') as f:
        json.dump({"data": args}, f)

    return f"Data cached to {cache_file}"
```

### Usage Documentation

Your `docs/USAGE.md` is automatically loaded and provided in context.

**Use it for:**
- LLM analysis prompts
- User help messages
- Context for AI assistants

**Example:**

```python
def help_fn(args, context):
    """Show usage help"""
    usage_doc = context.get('usage_doc', 'No documentation available')
    return f"Usage:\n\n{usage_doc}"
```

### Last Response

For `analyze.response` runners, the last command output is available:

```python
def explain_last_fn(args, context):
    """Explain the last response"""
    last_response = context.get('last_response')

    if not last_response:
        return "No previous response to explain"

    # Analyze the response
    return f"Analysis of last response:\n{analyze(last_response)}"
```

---

## Error Handling

### In Handlers

Raise exceptions for errors:

```python
def risky_operation_fn(args, context):
    """Perform risky operation"""
    if not args:
        raise ValueError("Missing required argument")

    try:
        result = perform_operation(args[0])
        return f"Success: {result}"
    except Exception as e:
        raise RuntimeError(f"Operation failed: {str(e)}")

HANDLERS = {"risky": risky_operation_fn}
```

The Capability Runner will catch exceptions and format them nicely for users.

### Error Types

| Error Type | When to Use |
|-----------|-------------|
| `ValueError` | Invalid arguments |
| `FileNotFoundError` | Missing required files |
| `RuntimeError` | Operation failed |
| `TimeoutError` | Operation took too long |
| `PermissionError` | Access denied |

### User-Friendly Errors

The runner formats errors for users:

```python
# Your handler raises:
raise ValueError("API key is required")

# User sees:
Error: API key is required

Hint: Set your API key in the extension settings.
```

---

## Testing

### Unit Testing Handlers

```python
# test_handlers.py
import pytest
from my_extension.handlers import hello_fn, status_fn

def test_hello_with_name():
    """Test hello with name argument"""
    args = ["Alice"]
    context = {"session_id": "test"}

    result = hello_fn(args, context)

    assert "Alice" in result

def test_hello_without_name():
    """Test hello with no arguments"""
    args = []
    context = {"session_id": "test"}

    result = hello_fn(args, context)

    assert "World" in result

def test_status():
    """Test status command"""
    args = []
    context = {"session_id": "test"}

    result = status_fn(args, context)

    assert "Platform" in result
    assert "Python" in result
```

### Integration Testing

```python
# test_integration.py
from agentos.core.capabilities import CapabilityRunner
from agentos.core.capabilities.models import CommandRoute, ExecutionContext

def test_execute_hello_command():
    """Test full execution through runner"""
    runner = CapabilityRunner()

    route = CommandRoute(
        command_name="/test",
        extension_id="tools.test",
        action_id="hello",
        runner="exec.python_handler",
        args=["Alice"]
    )

    context = ExecutionContext(
        session_id="test_session",
        user_id="test_user",
        extension_id="tools.test",
        work_dir=Path("/tmp/.agentos/test/work")
    )

    result = runner.execute(route, context)

    assert result.success is True
    assert "Alice" in result.output
```

### End-to-End Testing

```python
# test_e2e.py
from agentos.core.chat.engine import ChatEngine

def test_chat_command():
    """Test through chat interface"""
    engine = ChatEngine()
    session_id = engine.create_session()

    response = engine.send_message(
        session_id=session_id,
        user_input="/test hello Alice"
    )

    assert "Alice" in response['text']
```

---

## Debugging

### Enable Debug Logging

```python
import logging

# In your handlers.py
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def my_handler_fn(args, context):
    """My handler with debug logging"""
    logger.debug(f"Handler called with args: {args}")
    logger.debug(f"Context: {context}")

    result = do_something(args)

    logger.debug(f"Result: {result}")
    return result
```

### Check Execution Logs

AgentOS logs all capability executions:

```bash
# View logs
tail -f ~/.agentos/logs/agentos.log | grep capability_executed
```

Log format:

```json
{
  "event": "capability_executed",
  "timestamp": "2026-01-30T10:30:45Z",
  "extension_id": "tools.test",
  "command": "/test",
  "action": "hello",
  "runner": "exec.python_handler",
  "session_id": "sess_123",
  "user_id": "user_456",
  "success": true,
  "duration_seconds": 0.123,
  "error": null
}
```

### Debugging with Print

```python
def debug_handler_fn(args, context):
    """Handler with debug prints"""
    print(f"DEBUG: Args = {args}")
    print(f"DEBUG: Context = {context}")
    print(f"DEBUG: Work dir exists = {context['work_dir'].exists()}")

    return "Debug info printed to console"
```

### Test in Isolation

```python
# Run handler directly
from my_extension.handlers import HANDLERS

handler = HANDLERS['hello']
result = handler(['Alice'], {'session_id': 'test'})
print(result)
```

---

## Best Practices

### 1. Use Descriptive Action Names

```yaml
# Good
actions:
  - id: get_user
    description: "Get user by ID"

  - id: list_users
    description: "List all users"

# Bad
actions:
  - id: action1
  - id: do_stuff
```

### 2. Provide Usage Examples

```yaml
examples:
  - "/users get 123"
  - "/users list --limit 10"
  - "/users create name=Alice email=alice@example.com"
```

### 3. Handle All Error Cases

```python
def robust_handler_fn(args, context):
    """Robust handler with error handling"""
    # Validate arguments
    if not args:
        return "Error: Missing required arguments"

    # Validate format
    if not is_valid_format(args[0]):
        return "Error: Invalid format. Expected: ..."

    # Try operation
    try:
        result = perform_operation(args)
        return f"Success: {result}"
    except SpecificError as e:
        return f"Error: {str(e)}\n\nHint: Try ..."
    except Exception as e:
        return f"Unexpected error: {str(e)}"
```

### 4. Provide Help Messages

```python
def command_fn(args, context):
    """Command with help"""
    if not args or args[0] == "help":
        return """Usage: /command <action> [args]

Actions:
  action1    - Do something
  action2    - Do something else

Examples:
  /command action1 arg
  /command action2 --flag value
"""

    # ... rest of handler
```

### 5. Use Type Hints

```python
from typing import List, Dict
from pathlib import Path

def typed_handler_fn(args: List[str], context: Dict) -> str:
    """Handler with type hints"""
    work_dir: Path = Path(context['work_dir'])
    session_id: str = context['session_id']

    # ...
```

### 6. Document Your Handlers

```python
def documented_handler_fn(args, context):
    """
    Fetch user data by ID

    Args:
        args[0]: User ID (integer)
        args[1]: Format (json/yaml/text) [optional]

    Returns:
        Formatted user data

    Raises:
        ValueError: If user ID is invalid
        RuntimeError: If API call fails

    Examples:
        /users get 123
        /users get 123 json
    """
    # ...
```

### 7. Cache Expensive Operations

```python
def cached_handler_fn(args, context):
    """Handler with caching"""
    from pathlib import Path
    import json
    import time

    work_dir = Path(context['work_dir'])
    cache_file = work_dir / "cache.json"

    # Check cache
    if cache_file.exists():
        cache_age = time.time() - cache_file.stat().st_mtime
        if cache_age < 300:  # 5 minutes
            with open(cache_file) as f:
                cached_data = json.load(f)
            return f"Cached result: {cached_data}"

    # Fetch fresh data
    fresh_data = fetch_expensive_data(args)

    # Save to cache
    with open(cache_file, 'w') as f:
        json.dump(fresh_data, f)

    return f"Fresh result: {fresh_data}"
```

### 8. Use Timeouts for Network Calls

```python
def network_handler_fn(args, context):
    """Handler with network timeout"""
    import requests

    timeout = min(context.get('timeout', 300), 30)  # Max 30 seconds

    try:
        response = requests.get(args[0], timeout=timeout)
        return response.text
    except requests.Timeout:
        return "Error: Request timed out"
```

---

## Examples

### Example 1: Weather Extension

```yaml
# commands.yaml
slash_commands:
  - name: "/weather"
    summary: "Get weather information"
    examples:
      - "/weather current London"
      - "/weather forecast Tokyo 5"

    actions:
      - id: current
        description: "Get current weather"
        runner: exec.python_handler

      - id: forecast
        description: "Get weather forecast"
        runner: exec.python_handler
```

```python
# handlers.py
import requests

def current_fn(args, context):
    """Get current weather"""
    if not args:
        return "Error: Please provide a city name"

    city = " ".join(args)

    try:
        # Call weather API
        response = requests.get(
            f"https://api.weather.com/current?city={city}",
            timeout=10
        )
        data = response.json()

        return f"""Weather in {city}:
- Temperature: {data['temp']}°C
- Condition: {data['condition']}
- Humidity: {data['humidity']}%
"""
    except Exception as e:
        return f"Error fetching weather: {str(e)}"

def forecast_fn(args, context):
    """Get weather forecast"""
    if not args:
        return "Error: Please provide a city name"

    city = args[0]
    days = int(args[1]) if len(args) > 1 else 3

    # ... similar implementation

HANDLERS = {
    "current": current_fn,
    "forecast": forecast_fn,
}
```

### Example 2: Database Query Extension

```yaml
# commands.yaml
slash_commands:
  - name: "/db"
    summary: "Query database"
    examples:
      - "/db query SELECT * FROM users"
      - "/db schema users"

    actions:
      - id: query
        description: "Execute SQL query"
        runner: exec.python_handler

      - id: schema
        description: "Show table schema"
        runner: exec.python_handler
```

```python
# handlers.py
import sqlite3
from pathlib import Path

def query_fn(args, context):
    """Execute SQL query"""
    if not args:
        return "Error: Please provide a SQL query"

    query = " ".join(args)
    work_dir = Path(context['work_dir'])
    db_path = work_dir / "database.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()

        # Format results
        output = "\n".join(str(row) for row in results)
        return f"Query results:\n{output}"

    except Exception as e:
        return f"Error: {str(e)}"

def schema_fn(args, context):
    """Show table schema"""
    # ... implementation

HANDLERS = {
    "query": query_fn,
    "schema": schema_fn,
}
```

### Example 3: File Processing Extension

```yaml
# commands.yaml
slash_commands:
  - name: "/files"
    summary: "Process files"
    examples:
      - "/files convert image.png jpeg"
      - "/files resize image.png 800x600"

    actions:
      - id: convert
        description: "Convert file format"
        runner: exec.imagemagick

      - id: resize
        description: "Resize image"
        runner: exec.imagemagick
```

---

## Next Steps

1. **Read the ADR**: Understand the design decisions in `/docs/architecture/ADR_CAPABILITY_RUNNER.md`
2. **Check Runner Architecture**: Review `/docs/extensions/RUNNER_ARCHITECTURE.md` for execution flow
3. **Study Examples**: Look at the Postman extension and Test extension
4. **Build Your Extension**: Start with a simple handler and expand from there
5. **Test Thoroughly**: Write unit, integration, and end-to-end tests
6. **Share**: Submit your extension to the AgentOS extension registry

## Support

- **Issues**: Report bugs on GitHub
- **Discussions**: Ask questions in GitHub Discussions
- **Docs**: Read more at https://docs.agentos.dev
- **Examples**: Browse community extensions

---

**Happy building!** 🚀
