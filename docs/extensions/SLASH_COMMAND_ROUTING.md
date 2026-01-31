# Slash Command Routing (PR-D)

## Overview

The Slash Command Router enables users to invoke extension capabilities through chat using slash commands like `/postman`, `/hello`, etc. When a user types a slash command, the system:

1. Identifies it as a slash command
2. Routes it to the appropriate extension
3. Parses the action and arguments
4. Executes the capability via the runner (PR-E)

## Architecture

```
User Input: "/postman get https://api.example.com"
     ↓
ChatEngine.send_message()
     ↓
SlashCommandRouter.is_slash_command() → True
     ↓
SlashCommandRouter.route()
     ↓
CommandParser.parse() → {command: "/postman", action: "get", args: [...]}
     ↓
Lookup in command cache (from commands.yaml)
     ↓
CommandRoute (extension_id, action_id, runner, args, usage_doc)
     ↓
Check if extension is enabled
     ↓
Execute via Capability Runner (PR-E)
```

## Components

### 1. SlashCommandRouter

Main router class that discovers and routes commands.

```python
from agentos.core.extensions.registry import ExtensionRegistry
from agentos.core.chat.slash_command_router import SlashCommandRouter

# Initialize
registry = ExtensionRegistry()
router = SlashCommandRouter(registry)

# Check if message is a slash command
if router.is_slash_command("/postman get https://api.example.com"):
    # Route to extension
    route = router.route("/postman get https://api.example.com")

    if route:
        print(f"Extension: {route.extension_name}")
        print(f"Action: {route.action_id}")
        print(f"Args: {route.args}")
        print(f"Enabled: {route.extension_enabled}")
```

### 2. CommandParser

Parses command strings into structured data.

```python
from agentos.core.chat.slash_command_router import CommandParser

parser = CommandParser()

# Simple command
result = parser.parse("/postman get https://api.example.com")
# → {command: "/postman", action: "get", args: ["https://api.example.com"]}

# Complex command with flags
result = parser.parse('/postman test "./collection.json" --env dev')
# → {command: "/postman", action: "test", args: ["./collection.json", "--env", "dev"]}
```

### 3. CommandRoute

Data class representing a routed command.

```python
@dataclass
class CommandRoute:
    command_name: str          # "/postman"
    extension_id: str          # "tools.postman"
    extension_name: str        # "Postman Toolkit"
    extension_enabled: bool    # True/False
    capability_name: str       # "tools.postman"
    action_id: str            # "get"
    runner: str               # "exec.postman_cli"
    args: List[str]           # ["https://api.example.com"]
    raw_args: str             # "https://api.example.com"
    description: str          # "Send a GET request"
    usage_doc: Optional[str]  # Content from docs/USAGE.md
    examples: List[str]       # Example commands
```

## Extension Configuration

### commands.yaml Format

Extensions define their slash commands in `commands.yaml`:

```yaml
slash_commands:
  - name: "/postman"
    summary: "Run API tests via Postman CLI and explain responses."
    description: "Execute Postman collections and analyze API responses using Newman."
    examples:
      - "/postman get https://httpbin.org/get"
      - "/postman test collection.json --env dev.json"
      - "/postman explain last_response"
    maps_to:
      capability: "tools.postman"
      actions:
        - id: "get"
          description: "Send a GET request and summarize response."
          runner: "exec.postman_cli"
        - id: "test"
          description: "Run a collection test."
          runner: "exec.postman_cli"
        - id: "explain"
          description: "Explain the last response format and fields."
          runner: "analyze.response"
```

### Usage Documentation

Extensions should provide usage documentation in `docs/USAGE.md`:

```markdown
# Postman Extension Usage

## Commands

### GET Request
Send a GET request to an API endpoint:
```
/postman get <url>
```

Example:
```
/postman get https://httpbin.org/get
```

### Run Tests
Run a Postman collection test:
```
/postman test <collection.json> [--env <env.json>]
```

Example:
```
/postman test ./collections/demo.json --env ./env/dev.json
```
```

## Integration with Chat

### In ChatEngine

The router is integrated into `ChatEngine.send_message()`:

```python
def send_message(self, session_id: str, user_input: str, stream: bool = False):
    # 1. Save user message
    self.chat_service.add_message(session_id, "user", user_input)

    # 2. Check if it's an extension slash command
    if self.slash_command_router.is_slash_command(user_input):
        route = self.slash_command_router.route(user_input)

        if route is None:
            # Unknown command
            return build_command_not_found_response(user_input.split()[0])

        if not route.extension_enabled:
            # Extension disabled
            return build_extension_disabled_response(route)

        # Execute via capability runner (PR-E)
        return self._execute_extension_command(session_id, route, stream)

    # 3. Normal chat flow
    ...
```

### Error Handling

#### Unknown Command

When a command is not found:

```json
{
  "type": "extension_prompt",
  "command": "/unknown",
  "message": "Command '/unknown' is not available. This command may require an extension to be installed.",
  "suggestion": {
    "action": "search_extensions",
    "query": "unknown"
  }
}
```

#### Disabled Extension

When an extension is disabled:

```json
{
  "type": "extension_prompt",
  "command": "/postman",
  "message": "Command '/postman' is available but the 'Postman Toolkit' extension is currently disabled.",
  "extension_info": {
    "id": "tools.postman",
    "name": "Postman Toolkit",
    "status": "disabled"
  },
  "action": {
    "type": "enable_extension",
    "extension_id": "tools.postman",
    "label": "Enable Postman Toolkit"
  }
}
```

## API Endpoints

### GET /api/chat/slash-commands

Get available slash commands (for autocomplete).

**Query Parameters:**
- `enabled_only` (bool): Only return commands from enabled extensions (default: true)

**Response:**
```json
{
  "commands": [
    {
      "name": "/postman",
      "source": "extension",
      "extension_id": "tools.postman",
      "extension_name": "Postman Toolkit",
      "summary": "Run API tests via Postman CLI",
      "description": "Execute Postman collections and analyze responses",
      "examples": [
        "/postman get https://httpbin.org/get",
        "/postman test collection.json"
      ],
      "enabled": true
    },
    {
      "name": "/hello",
      "source": "extension",
      "extension_id": "examples.hello",
      "extension_name": "Hello World",
      "summary": "Hello world example",
      "description": "Simple hello world extension",
      "examples": ["/hello"],
      "enabled": true
    }
  ],
  "total": 2
}
```

### POST /api/chat/refresh-commands

Refresh slash command cache (call after installing/enabling extensions).

**Response:**
```json
{
  "success": true,
  "message": "Slash command cache refreshed",
  "total_commands": 2
}
```

## Command Discovery Flow

1. **Initialization**: When `SlashCommandRouter` is created, it scans all installed extensions
2. **Load commands.yaml**: For each extension with `slash_command` capability, load its `commands.yaml`
3. **Build cache**: Store mapping of command name → (extension_id, capability_config)
4. **Refresh on changes**: Call `refresh_cache()` when extensions are installed/enabled/disabled

## Command Execution Flow

1. **User types command**: `/postman get https://api.example.com`
2. **Parse**: Extract command `/postman`, action `get`, args `["https://api.example.com"]`
3. **Route**: Look up in cache → find `tools.postman` extension
4. **Check status**: Verify extension is enabled
5. **Load usage doc**: Read `docs/USAGE.md` for context
6. **Build CommandRoute**: Package all info for runner
7. **Execute**: Pass to Capability Runner (PR-E)

## Performance

- **Caching**: Commands are cached in memory for fast lookup
- **Lazy loading**: Usage docs are loaded on-demand, not during cache build
- **Efficient parsing**: Uses `shlex` for proper quote handling

## Security

- **No eval**: Command parsing is safe, no code execution
- **Validation**: All commands must be from registered extensions
- **Permission check**: Extensions declare required permissions in manifest
- **Logging**: Command execution is logged (but sensitive args are filtered)

## Testing

### Unit Tests

```python
# Test command parsing
def test_parse_command():
    parser = CommandParser()
    result = parser.parse("/postman get https://api.example.com")
    assert result['command'] == "/postman"
    assert result['action'] == "get"

# Test routing
def test_route_command(mock_registry):
    router = SlashCommandRouter(mock_registry)
    route = router.route("/postman get https://api.example.com")
    assert route.extension_id == "tools.postman"
    assert route.action_id == "get"
```

### Integration Tests

```python
# Test full flow
def test_extension_command_execution():
    engine = ChatEngine()
    session_id = engine.create_session()

    response = engine.send_message(
        session_id=session_id,
        user_input="/postman get https://api.example.com"
    )

    assert response['metadata']['extension_command'] == "/postman"
```

## Future Enhancements

1. **Command aliases**: Allow extensions to define multiple names for the same command
2. **Parameter validation**: Validate command arguments before execution
3. **Autocomplete in UI**: Frontend integration with command suggestions
4. **Command help**: `/help postman` to show command usage
5. **Command history**: Track most-used commands per user
6. **Command permissions**: Require user confirmation for sensitive commands

## Related PRs

- **PR-A**: Extension Registry and capability declaration
- **PR-E**: Capability Runner (executes routed commands)
- **PR-C**: WebUI Extensions management (enable/disable)
- **PR-F**: Example extensions (postman, hello)

## Example Usage

### For Extension Developers

1. Define commands in `commands.yaml`
2. Implement runners in `runners/` directory
3. Provide usage docs in `docs/USAGE.md`
4. Test with sample commands

### For Users

1. Install extension: `/extensions install postman`
2. Use command: `/postman get https://api.example.com`
3. View available commands: `/help` or autocomplete in UI
4. Disable if needed: `/extensions disable postman`
