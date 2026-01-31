# External Information Declaration Models Implementation

**Task #2 Completion Report**

## Overview

This document describes the implementation of external information declaration data structures for the AgentOS chat system. These models enable the LLM to declaratively specify external information needs before execution, supporting the execution phase gating mechanism.

## Implemented Components

### 1. ExternalInfoAction Enum
**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/models/external_info.py`

Enumeration of external information action types:
- `WEB_SEARCH` - Search the internet for information
- `WEB_FETCH` - Fetch content from a specific URL
- `API_CALL` - Call an external API
- `DATABASE_QUERY` - Query external database
- `FILE_READ` - Read file from filesystem
- `FILE_WRITE` - Write file to filesystem
- `COMMAND_EXEC` - Execute system command
- `TOOL_CALL` - Call an external tool/extension

### 2. ExternalInfoDeclaration Model
**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/models/external_info.py`

Pydantic BaseModel representing a structured declaration of external information needs.

**Fields**:
- `action`: ExternalInfoAction - Type of external action needed
- `reason`: str (10-500 chars) - Human-readable explanation of why this info is needed
- `target`: str (1-1000 chars) - Target of the action (URL, query, file path, etc.)
- `params`: Optional[Dict[str, Any]] - Additional parameters for the action
- `priority`: int (1-3) - Priority level (1=critical, 2=important, 3=nice-to-have)
- `estimated_cost`: str (LOW|MED|HIGH) - Estimated cost/risk level
- `alternatives`: Optional[List[str]] - Alternative approaches if action is denied

**Methods**:
- `to_dict()` - Convert to dictionary for serialization
- `to_user_message()` - Convert to user-friendly message for WebUI display

**Validation**:
- All fields use Pydantic v2 validation
- Priority must be 1-3
- Cost must be LOW, MED, or HIGH
- Reason must be 10-500 characters
- Target must be 1-1000 characters

### 3. ChatResponse Model
**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/models_base.py`

Enhanced response model with external info support.

**Fields**:
- `message_id`: Optional[str] - Unique message identifier
- `content`: str - Response text content
- `role`: Literal["system", "user", "assistant", "tool"] - Message role
- `metadata`: Dict[str, Any] - Additional metadata
- `context`: Dict[str, Any] - Context information
- `external_info`: List[ExternalInfoDeclaration] - External information declarations

**Methods**:
- `to_dict()` - Convert to dictionary with external_info serialized
- `has_external_info_needs()` - Check if response has external info declarations
- `get_critical_external_info()` - Get only critical (priority=1) declarations
- `to_user_summary()` - Generate user-friendly summary of external info needs

## File Structure

```
agentos/core/chat/
├── models/
│   ├── __init__.py              # Package exports
│   └── external_info.py         # External info models (NEW)
├── models_base.py               # Base chat models with ChatResponse (MODIFIED)
└── __init__.py                  # Module exports (unchanged)

tests/unit/core/chat/
└── test_external_info_models.py # Unit tests (NEW)
```

## Modified Files

1. **Created**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/models/external_info.py`
   - New module containing ExternalInfoAction and ExternalInfoDeclaration

2. **Created**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/models/__init__.py`
   - New package initialization with exports

3. **Renamed**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/models.py`
   → `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/models_base.py`
   - Renamed to avoid conflict with models/ package
   - Added ChatResponse dataclass with external_info field
   - Added import for ExternalInfoDeclaration

4. **Created**: `/Users/pangge/PycharmProjects/AgentOS/tests/unit/core/chat/test_external_info_models.py`
   - Comprehensive unit tests (14 test cases, all passing)

5. **Created**: `/Users/pangge/PycharmProjects/AgentOS/docs/EXTERNAL_INFO_MODELS_IMPLEMENTATION.md`
   - This documentation file

## Design Decisions

### 1. Pydantic BaseModel vs Dataclass
Used Pydantic BaseModel for ExternalInfoDeclaration to leverage:
- Automatic validation
- Type coercion
- JSON schema generation
- Field constraints (min_length, max_length, ge, le, pattern)

Used dataclass for ChatResponse to maintain consistency with existing ChatSession and ChatMessage models.

### 2. Enum for Actions
Used string enum for ExternalInfoAction to:
- Provide type safety
- Enable IDE autocomplete
- Allow easy serialization to JSON
- Match project style (see ConversationMode, RiskLevel, etc.)

### 3. Validation Rules
- Priority 1-3: Balances specificity with simplicity
- Cost LOW/MED/HIGH: Aligns with existing RiskLevel enum pattern
- Reason 10-500 chars: Forces meaningful explanations without verbosity
- Target 1-1000 chars: Accommodates URLs, file paths, queries

### 4. Helper Methods
Added convenience methods to support common use cases:
- `to_user_message()`: WebUI display
- `has_external_info_needs()`: Quick boolean check
- `get_critical_external_info()`: Filter by priority
- `to_user_summary()`: Batch display for UI

## Testing

All tests pass with no warnings:
```bash
$ python3 -m pytest tests/unit/core/chat/test_external_info_models.py -v
============================== 14 passed in 0.15s ==============================
```

**Test Coverage**:
- ExternalInfoAction enum validation (1 test)
- ExternalInfoDeclaration creation and validation (7 tests)
- ChatResponse with external_info field (6 tests)

## Python Compatibility

- Uses `from __future__ import annotations` for forward references (Python 3.8+)
- Type hints follow Python 3.8+ standards
- Pydantic v2 ConfigDict (no deprecation warnings)
- Compatible with Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.14

## Integration Points

### Backward Compatibility
- Existing imports of `ChatSession` and `ChatMessage` continue to work
- `from agentos.core.chat.models import ChatSession, ChatMessage` works unchanged
- ChatResponse is a new addition, no breaking changes

### Future Integration
These models are ready to be integrated with:
1. **ChatEngine** (Task #4): Capture declarations from LLM responses
2. **System Prompt** (Task #3): Instruct LLM to generate declarations
3. **WebUI** (Task #5): Display external info needs to users
4. **Phase Gate** (existing): Block execution until declarations are approved

## Example Usage

```python
from agentos.core.chat.models import ChatResponse
from agentos.core.chat.models.external_info import (
    ExternalInfoAction,
    ExternalInfoDeclaration
)

# Create a declaration
decl = ExternalInfoDeclaration(
    action=ExternalInfoAction.WEB_SEARCH,
    reason="Need to find latest Python 3.12 release date to answer the question accurately",
    target="Python 3.12 release date site:python.org",
    params={"max_results": 5},
    priority=1,
    estimated_cost="LOW",
    alternatives=["Use cached release notes", "Provide answer for Python 3.11"]
)

# Create response with external info
response = ChatResponse(
    message_id="msg_123",
    content="To answer your question about Python 3.12, I need to search for release information.",
    role="assistant",
    metadata={"model": "gpt-4"},
    external_info=[decl]
)

# Check for external info needs
if response.has_external_info_needs():
    print(response.to_user_summary())

# Get critical items only
critical = response.get_critical_external_info()

# Serialize for API/WebSocket
response_dict = response.to_dict()
```

## Next Steps

1. **Task #3**: Modify System Prompt to instruct LLM to generate declarations
2. **Task #4**: Implement declaration capture in ChatEngine
3. **Task #5**: Implement WebUI external info prompt interface
4. Integration testing with real LLM responses

## Status

✅ **COMPLETED** - All requirements met:
- ✅ Created `agentos/core/chat/models/external_info.py`
- ✅ Implemented ExternalInfoAction enum
- ✅ Implemented ExternalInfoDeclaration Pydantic model
- ✅ Added external_info field to ChatResponse
- ✅ Type annotations complete (Python 3.8+ compatible)
- ✅ Comprehensive unit tests (14 tests passing)
- ✅ No deprecation warnings
- ✅ Documentation complete
