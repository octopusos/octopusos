# Task #4: External Info Declaration Capture Implementation

**Status**: Completed
**Date**: 2026-01-31
**Related**: Task #2 (ExternalInfoDeclaration data structure), ADR-EXTERNAL-INFO-DECLARATION-001

## Overview

Implemented declaration capture mechanism in `ChatEngine` that detects when LLMs declare the need for external information, logs these declarations to the audit trail, and marks session metadata accordingly—WITHOUT triggering any external execution.

## Implementation Summary

### Key Files Modified

1. **`agentos/core/chat/engine.py`**
   - Added imports for external info models and audit logging
   - Integrated declaration capture into `_invoke_model()` method
   - Implemented three new methods for capturing and parsing declarations

2. **`agentos/core/audit.py`**
   - Added new audit event type: `EXTERNAL_INFO_DECLARED`
   - Registered in `VALID_EVENT_TYPES` set

3. **`tests/unit/core/chat/test_external_info_capture.py`**
   - Comprehensive test suite with 11 test cases
   - All tests passing

## Implementation Details

### 1. New Imports in `engine.py`

```python
import json
import re

from agentos.core.chat.models.external_info import (
    ExternalInfoDeclaration,
    ExternalInfoAction
)
from agentos.core.audit import log_audit_event
```

### 2. Integration Point in `_invoke_model()`

After model generates response, capture declarations:

```python
# Generate response
response, metadata = adapter.generate(
    messages=messages,
    temperature=0.7,
    max_tokens=2000,
    stream=False
)

# Task #4: Capture external info declarations from LLM response
if session_id:
    self._capture_external_info_declarations(response, session_id, metadata)

return response, metadata
```

**Key Characteristic**: Response is returned AS-IS to the UI. No external execution is triggered.

### 3. Core Capture Method

```python
def _capture_external_info_declarations(
    self,
    response_content: str,
    session_id: str,
    response_metadata: Dict[str, Any]
) -> None:
    """Capture external information declarations from LLM response

    Task #4: Detects external_info declarations in LLM responses and:
    1. Logs them to audit trail
    2. Marks session metadata if external info is required
    3. Returns response as-is (NO external execution)

    CRITICAL CONSTRAINT: This method MUST NOT trigger /comm commands or
    call comm_adapter. It only captures declarations for later user review.
    """
```

**Flow**:
1. Parse response for external_info declarations
2. Filter for `required: true` declarations
3. Log each declaration to audit trail
4. Update session metadata with `external_info_required: true`
5. Handle errors gracefully (don't break response flow)

### 4. Declaration Parsing

The `_parse_external_info_declarations()` method supports this format:

```json
{
  "external_info": {
    "required": true,
    "declarations": [
      {
        "action": "web_search",
        "reason": "Need to find latest Python release notes",
        "target": "Python 3.12 release notes",
        "priority": 1,
        "estimated_cost": "LOW"
      }
    ]
  }
}
```

**Features**:
- Extracts JSON blocks from LLM responses using regex
- Validates against `ExternalInfoDeclaration` schema
- Handles multiple declarations in single response
- Gracefully handles invalid JSON
- Only captures when `required: true`

### 5. Audit Logging

Each declaration is logged with:

```python
audit_metadata = {
    "session_id": session_id,
    "action": "web_search",
    "reason": "Need to find...",
    "target": "Python 3.12 release notes",
    "priority": 1,
    "estimated_cost": "LOW",
    "params": {...},
    "alternatives": [...]
}

audit_id = log_audit_event(
    event_type=EXTERNAL_INFO_DECLARED,
    task_id=None,
    level="info",
    metadata=audit_metadata
)
```

### 6. Session Metadata Marking

When required declarations are detected:

```python
session_metadata["external_info_required"] = True
session_metadata["external_info_count"] = len(required_declarations)

self.chat_service.update_session_metadata(
    session_id=session_id,
    metadata=session_metadata
)
```

This flag can be used by:
- **WebUI** (Task #5) to display pending external info requests
- **Phase Gate** to enforce approval before execution phase
- **Governance** to apply additional scrutiny

## Critical Constraints (Red Lines)

### ✅ MUST DO:

1. **Capture declarations** from LLM responses
2. **Log to audit trail** with full metadata
3. **Mark session metadata** when external info required
4. **Return response AS-IS** to UI (no modification)
5. **Handle errors gracefully** (don't break chat flow)

### ❌ MUST NOT DO:

1. **Trigger /comm commands** from capture mechanism
2. **Call comm_adapter** or any external execution
3. **Modify LLM response** content
4. **Block or delay response** delivery
5. **Raise exceptions** that break chat flow

## Audit Trail Integration

### Audit Event Type

```python
# In agentos/core/audit.py
EXTERNAL_INFO_DECLARED = "EXTERNAL_INFO_DECLARED"
```

Added to `VALID_EVENT_TYPES` set.

### Audit Record Format

```python
{
  "audit_id": 123,
  "task_id": "ORPHAN",  # Not tied to specific task
  "level": "info",
  "event_type": "EXTERNAL_INFO_DECLARED",
  "payload": {
    "session_id": "session-abc123",
    "action": "web_search",
    "reason": "Need to find latest Python release notes",
    "target": "Python 3.12 release notes",
    "priority": 1,
    "estimated_cost": "LOW",
    "params": {...},
    "alternatives": [...]
  },
  "created_at": 1738307200
}
```

### Querying Audit Events

```python
from agentos.core.audit import get_audit_events, EXTERNAL_INFO_DECLARED

# Get all external info declarations for a session
events = get_audit_events(
    event_type=EXTERNAL_INFO_DECLARED,
    limit=100
)

# Filter by session
session_events = [
    e for e in events
    if e["payload"].get("session_id") == "session-abc123"
]
```

## Test Coverage

### Test Suite: `tests/unit/core/chat/test_external_info_capture.py`

**11 tests, all passing:**

1. ✅ `test_parse_external_info_declaration_with_required_true`
   - Verifies parsing of external_info blocks with required=true

2. ✅ `test_parse_external_info_declaration_with_required_false`
   - Verifies that required=false is NOT captured

3. ✅ `test_parse_direct_declaration_object`
   - Verifies parsing of declarations in external_info wrapper

4. ✅ `test_parse_no_declarations`
   - Verifies handling of responses without declarations

5. ✅ `test_parse_invalid_json`
   - Verifies graceful handling of malformed JSON

6. ✅ `test_log_external_info_declaration`
   - Verifies audit logging with correct event type and metadata

7. ✅ `test_capture_external_info_declarations_updates_session_metadata`
   - Verifies session metadata is marked correctly

8. ✅ `test_capture_does_not_trigger_comm_commands`
   - **CRITICAL**: Verifies no external execution is triggered

9. ✅ `test_capture_handles_errors_gracefully`
   - Verifies errors don't break response flow

10. ✅ `test_multiple_declarations_in_response`
    - Verifies handling of multiple declarations

11. ✅ `test_integration_with_invoke_model`
    - Verifies end-to-end integration with model invocation

### Run Tests

```bash
python3 -m pytest tests/unit/core/chat/test_external_info_capture.py -v
```

**Result**: 11 passed, 2 warnings (unrelated Pydantic deprecations)

## Usage Example

### LLM Response with Declaration

```python
# LLM generates response with external info declaration
response = """
I understand you want to know about Python 3.12 features.

To provide accurate information, I need to access external resources:

```json
{
  "external_info": {
    "required": true,
    "declarations": [
      {
        "action": "web_search",
        "reason": "Need to find the latest Python 3.12 release notes to answer version-specific questions accurately",
        "target": "Python 3.12 release notes site:python.org",
        "priority": 1,
        "estimated_cost": "LOW",
        "alternatives": [
          "Use cached documentation if available",
          "Provide answer based on Python 3.11 as approximation"
        ]
      }
    ]
  }
}
```

Once I have this information, I can provide a comprehensive answer.
"""
```

### ChatEngine Processing

```python
# In ChatEngine._invoke_model():
response, metadata = adapter.generate(messages=..., ...)

# Capture declarations (automatic)
if session_id:
    self._capture_external_info_declarations(response, session_id, metadata)

# Response returned as-is to UI
return response, metadata
```

### Result

1. **Audit Log Entry Created**:
   - Event type: `EXTERNAL_INFO_DECLARED`
   - Session ID: recorded
   - Action: `web_search`
   - Reason: recorded
   - Priority: `1` (critical)

2. **Session Metadata Updated**:
   ```python
   {
       "external_info_required": True,
       "external_info_count": 1
   }
   ```

3. **Response Delivered to UI**:
   - Full response including JSON declaration
   - UI can parse and display pending request
   - User can review and approve

## Integration with Other Components

### Phase Gate (Guards)

Phase Gate can check session metadata:

```python
def check_external_info_approval(session_id):
    session = chat_service.get_session(session_id)

    if session.metadata.get("external_info_required"):
        # Block execution phase until approved
        if not session.metadata.get("external_info_approved"):
            raise PhaseGateViolation(
                "External info required but not approved. "
                "Review pending declarations before execution."
            )
```

### WebUI Display (Task #5)

WebUI can query audit events to display pending requests:

```python
from agentos.core.audit import get_audit_events, EXTERNAL_INFO_DECLARED

# Get pending external info declarations
pending = get_audit_events(
    event_type=EXTERNAL_INFO_DECLARED,
    limit=50
)

# Filter by session
session_pending = [
    e for e in pending
    if e["payload"].get("session_id") == current_session_id
]

# Display to user for approval
for event in session_pending:
    display_external_info_request(event["payload"])
```

### Governance Integration

Governance policies can evaluate declarations:

```python
def evaluate_external_info_request(declaration):
    # Check trust tier
    if declaration["action"] in ["command_exec", "file_write"]:
        if user_trust_tier < TRUST_TIER_HIGH:
            return "DENY"

    # Check quotas
    if has_exceeded_external_io_quota(session_id):
        return "DENY"

    # Check estimated cost
    if declaration["estimated_cost"] == "HIGH":
        return "REQUIRE_APPROVAL"

    return "ALLOW"
```

## Error Handling

All errors are caught and logged, but do NOT propagate:

```python
try:
    # Parse declarations
    declarations = self._parse_external_info_declarations(response_content)
    # ... log and update metadata ...
except Exception as e:
    # Don't propagate - declaration capture should not break response flow
    logger.error(
        f"Failed to capture external info declarations: {e}",
        exc_info=True
    )
```

**Rationale**: Chat responses should always be delivered to users, even if declaration capture fails. Capture is a monitoring/governance feature, not a critical path.

## Security Considerations

### ✅ Safe by Design

1. **No Auto-Execution**: Capture mechanism NEVER triggers external I/O
2. **Audit Trail**: All declarations logged for compliance
3. **Session Marking**: Enables governance and approval flows
4. **Error Isolation**: Capture failures don't break chat

### ✅ Defense in Depth

Multiple layers prevent unauthorized external I/O:

1. **Phase Gate**: Blocks execution in planning phase
2. **Declaration Capture**: Logs intent before execution
3. **Governance**: Evaluates declarations against policy
4. **User Approval**: Required for high-risk operations
5. **Attribution Guard**: Marks external content when executed

## Future Enhancements

### Short-term (Task #5)

- WebUI display of pending external info requests
- User approval flow integration
- Session metadata API for governance

### Medium-term

- Automatic policy evaluation on declarations
- Smart approval (auto-approve low-risk, common patterns)
- Declaration templates for common operations

### Long-term

- ML-based risk scoring for declarations
- Historical analysis of approved/denied requests
- Quota management based on declaration patterns

## Acceptance Criteria

- [x] Detects external_info declarations in LLM responses
- [x] Logs to audit trail with EXTERNAL_INFO_DECLARED event type
- [x] Marks session metadata with external_info_required flag
- [x] Returns response as-is (no modification)
- [x] Does NOT trigger /comm commands or comm_adapter
- [x] Handles errors gracefully (no exceptions break chat)
- [x] Comprehensive test coverage (11 tests, all passing)
- [x] Integration with existing audit system
- [x] Clear documentation

## Verification Commands

### Run Tests

```bash
# All tests
python3 -m pytest tests/unit/core/chat/test_external_info_capture.py -v

# Specific test
python3 -m pytest tests/unit/core/chat/test_external_info_capture.py::TestExternalInfoCapture::test_capture_does_not_trigger_comm_commands -v
```

### Check Audit Events

```python
from agentos.core.audit import get_audit_events, EXTERNAL_INFO_DECLARED

# List all external info declarations
events = get_audit_events(event_type=EXTERNAL_INFO_DECLARED, limit=100)

for event in events:
    print(f"Session: {event['payload'].get('session_id')}")
    print(f"Action: {event['payload'].get('action')}")
    print(f"Reason: {event['payload'].get('reason')}")
    print("---")
```

### Check Session Metadata

```python
from agentos.core.chat.service import ChatService

chat_service = ChatService()
session = chat_service.get_session("session-abc123")

if session.metadata.get("external_info_required"):
    print(f"External info required: {session.metadata['external_info_count']} declarations")
else:
    print("No external info required")
```

## Related Tasks

- **Task #1**: ✅ ADR-EXTERNAL-INFO-DECLARATION-001 written
- **Task #2**: ✅ ExternalInfoDeclaration data structure implemented
- **Task #3**: 🔄 System Prompt modifications (in progress)
- **Task #4**: ✅ **Declaration capture in ChatEngine (THIS TASK)**
- **Task #5**: 🔄 WebUI external info prompt (in progress)
- **Task #6**: ✅ Phase Gate verification
- **Task #7**: 📋 Integration tests (pending)
- **Task #8**: ✅ Gate enforcement scripts
- **Task #9**: 📋 System acceptance testing (pending)

## Conclusion

Task #4 is **COMPLETE**. The declaration capture mechanism is fully implemented, tested, and integrated with the audit system. It provides the foundation for Task #5 (WebUI display) and enforces the core architectural principle that **LLMs can only declare the need for external information, not execute it**.

**Next Steps**: Implement WebUI external info request display (Task #5) to visualize pending declarations and enable user approval workflow.
