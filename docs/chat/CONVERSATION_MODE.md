# Conversation Mode & Execution Phase

## Overview

AgentOS chat sessions now support two independent metadata fields:

1. **`conversation_mode`**: UI/UX context for the conversation
2. **`execution_phase`**: Security context for external operations

These fields are **completely independent** and serve different purposes.

## Conversation Mode

### Purpose

`conversation_mode` defines the UI/UX context and conversation style. It affects:
- UI presentation and layout
- Conversation prompts and suggestions
- Available shortcuts and commands
- Session organization and filtering

It does **NOT** affect security controls or what operations are allowed.

### Valid Values

```python
from agentos.core.chat.models import ConversationMode

ConversationMode.CHAT         # "chat" - Free-form conversation (default)
ConversationMode.DISCUSSION   # "discussion" - Structured discussion
ConversationMode.PLAN         # "plan" - Planning and design work
ConversationMode.DEVELOPMENT  # "development" - Active development
ConversationMode.TASK         # "task" - Task-focused conversation
```

### Usage

```python
from agentos.core.chat.service import ChatService

service = ChatService()

# Create session with default mode (chat)
session = service.create_session(title="My Chat")
print(session.metadata["conversation_mode"])  # "chat"

# Create session with specific mode
session = service.create_session(
    title="Planning Session",
    metadata={"conversation_mode": "plan"}
)

# Get current mode
mode = service.get_conversation_mode(session.session_id)

# Update mode
service.update_conversation_mode(session.session_id, "development")
```

## Execution Phase

### Purpose

`execution_phase` defines the security context for external operations. It controls:
- Whether external communication (comm.*) operations are allowed
- Security boundaries and restrictions
- What actions the agent can perform

This is a **security-critical** field with audit logging.

### Valid Values

- `"planning"`: No external communication allowed (safe default)
- `"execution"`: All operations allowed (including comm.*)

See [Phase Gate Guard](../chat/guards/phase_gate.py) for security policy details.

### Usage

```python
from agentos.core.chat.service import ChatService

service = ChatService()

# Create session with default phase (planning - safe)
session = service.create_session(title="My Chat")
print(session.metadata["execution_phase"])  # "planning"

# Create session with specific phase
session = service.create_session(
    title="Execution Session",
    metadata={"execution_phase": "execution"}
)

# Get current phase
phase = service.get_execution_phase(session.session_id)

# Update phase (with audit logging)
service.update_execution_phase(
    session.session_id,
    phase="execution",
    actor="user",
    reason="User requested web search capability"
)
```

### Audit Logging

All execution phase changes are logged with:
- Old phase and new phase
- Actor who made the change
- Reason for the change
- Timestamp

This provides a complete audit trail for security and compliance.

## Independence

**Important**: `conversation_mode` and `execution_phase` are completely independent.

### Why Separate?

1. **Different Concerns**:
   - Mode: UI/UX and workflow context
   - Phase: Security and external operation control

2. **Different Change Patterns**:
   - Mode: Changes frequently as conversation evolves
   - Phase: Changes rarely, requires explicit user action

3. **Different Audit Requirements**:
   - Mode: No audit logging needed
   - Phase: Full audit logging required

### Examples

```python
service = ChatService()

# Example 1: Planning conversation in development mode
session = service.create_session(
    title="Design Discussion",
    metadata={
        "conversation_mode": "development",  # UI context
        "execution_phase": "planning"        # No external ops
    }
)

# Example 2: Chat-style interaction with execution allowed
session = service.create_session(
    title="Research Session",
    metadata={
        "conversation_mode": "chat",        # UI context
        "execution_phase": "execution"      # External ops allowed
    }
)

# Changing mode does NOT affect phase
service.update_conversation_mode(session.session_id, "task")
assert service.get_execution_phase(session.session_id) == "execution"

# Changing phase does NOT affect mode
service.update_execution_phase(session.session_id, "planning", actor="user")
assert service.get_conversation_mode(session.session_id) == "task"
```

## Best Practices

### Default Values

- Always use **safe defaults**:
  - `conversation_mode`: "chat" (neutral)
  - `execution_phase`: "planning" (safe)

- Only enable execution phase when explicitly needed

### Mode Selection

Choose conversation mode based on UI/workflow needs:

| Mode | Use Case |
|------|----------|
| `chat` | General conversation, Q&A |
| `discussion` | Brainstorming, structured discussion |
| `plan` | Planning, design, architecture |
| `development` | Active coding, debugging |
| `task` | Task execution, focused work |

### Phase Management

- Start in `planning` phase by default
- Switch to `execution` phase only when:
  - User explicitly requests external operations (search, fetch, etc.)
  - System needs to perform external communication
- Document reason for phase changes
- Switch back to `planning` when external ops complete

### Security Considerations

1. **Never auto-switch phases** based on conversation mode
2. **Always audit** execution phase changes
3. **Use PhaseGate** to enforce restrictions
4. **Validate inputs** before updating either field

## Migration Guide

### For Existing Code

If your code uses session metadata:

```python
# Old code (still works)
session = service.create_session(title="Test")
# session.metadata is empty except defaults

# New code (explicit)
session = service.create_session(
    title="Test",
    metadata={
        "conversation_mode": "chat",
        "execution_phase": "planning"
    }
)
```

### For Database Schema

No database migration required. The fields are stored in the existing `metadata` JSON column:

```sql
-- Existing schema (no changes needed)
CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,
    title TEXT,
    task_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT  -- JSON: {conversation_mode, execution_phase, ...}
);
```

## API Reference

### ConversationMode Enum

```python
class ConversationMode(str, Enum):
    """Conversation mode for chat sessions."""
    CHAT = "chat"
    DISCUSSION = "discussion"
    PLAN = "plan"
    DEVELOPMENT = "development"
    TASK = "task"
```

### ChatService Methods

#### `get_conversation_mode(session_id: str) -> str`
Get conversation mode for a session.

**Returns**: Conversation mode (default: "chat")

#### `update_conversation_mode(session_id: str, mode: str) -> None`
Update conversation mode for a session.

**Args**:
- `session_id`: Session ID
- `mode`: New mode (chat/discussion/plan/development/task)

**Raises**: `ValueError` if mode is invalid

#### `get_execution_phase(session_id: str) -> str`
Get execution phase for a session.

**Returns**: Execution phase (default: "planning")

#### `update_execution_phase(session_id: str, phase: str, actor: str = "system", reason: Optional[str] = None) -> None`
Update execution phase for a session with audit logging.

**Args**:
- `session_id`: Session ID
- `phase`: New phase (planning/execution)
- `actor`: Who initiated the change (default: "system")
- `reason`: Optional reason for the change

**Raises**: `ValueError` if phase is invalid

## Testing

Run comprehensive tests:

```bash
python3 -m pytest tests/unit/core/chat/test_conversation_mode.py -v
```

Test coverage includes:
- Enum definition
- Default values
- Helper methods
- Validation
- Independence verification
- Audit logging
- All valid combinations

## Related Documentation

- [Phase Gate Guard](../chat/guards/phase_gate.py) - Security policy enforcement
- [Chat Service](../../agentos/core/chat/service.py) - Implementation
- [Chat Models](../../agentos/core/chat/models.py) - Data models
- [Audit Logging](../../agentos/core/capabilities/audit.py) - Audit system
