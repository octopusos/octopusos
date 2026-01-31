# WebUI Degradation Strategy

**Version**: v0.3.2 (P1 Sprint W-P1-02)
**Status**: ✅ Implemented in Phase 4

## Overview

AgentOS WebUI implements multi-layer degradation to ensure availability even when components fail. This document describes the error handling and fallback strategies across all subsystems.

---

## 1. Storage Layer Degradation (W-P1-01)

### SQLite → Memory Fallback

**Trigger**: SQLite database unavailable (file locked, permissions, corruption)

**Behavior**:
```python
# In app.py startup_event()
try:
    store = SQLiteSessionStore(db_path)
except Exception:
    logger.warning("Falling back to MemorySessionStore")
    store = MemorySessionStore()
```

**Impact**:
- ✅ WebUI remains operational
- ⚠️ Data persists only for current session (lost on restart)
- ✅ All API endpoints continue to work

**User Experience**:
- No visible error to user
- Logged warning in server logs
- Sessions/messages are functional but ephemeral

**Recovery**:
- Restart server after fixing database issue
- Data from degraded mode is NOT recovered

---

## 2. Runtime Config Degradation (W-P1-02 Phase 3)

### Invalid Config → Default Config

**Trigger**: User sends invalid runtime config in WebSocket metadata

**Validation Failures**:
- `model_type` not in `["local", "cloud"]`
- `temperature` not in `[0.0, 2.0]`
- `top_p` not in `[0.0, 1.0]`
- `max_tokens <= 0`
- Non-numeric values for numeric fields

**Behavior**:
```python
# In handle_user_message()
runtime_config, config_error = extract_runtime_config(metadata)

if config_error:
    await manager.send_message(session_id, {
        "type": "message.error",
        "content": f"⚠️ Configuration error: {config_error}",
        "metadata": {
            "error_type": "invalid_config",
            "error_detail": config_error,
        },
    })
    return  # Early return, message NOT processed
```

**Impact**:
- ❌ Message is NOT processed (fail-fast)
- ✅ User receives structured error immediately
- ✅ No partial state changes (atomicity)

**User Experience**:
- Error message shown in chat UI
- Can retry with corrected config
- Previous messages unaffected

**Example Error Response**:
```json
{
  "type": "message.error",
  "content": "⚠️ Configuration error: Invalid temperature: 3.0 (must be 0.0-2.0)",
  "metadata": {
    "error_type": "invalid_config",
    "error_detail": "Invalid temperature: 3.0 (must be 0.0-2.0)"
  }
}
```

---

## 3. ChatEngine Degradation (W-P1-02 Phase 2)

### ChatEngine Unavailable → Error Message

**Trigger**: ChatEngine fails to initialize or respond

**Behavior**:
```python
try:
    chat_engine = get_chat_engine()
except Exception as e:
    await manager.send_message(session_id, {
        "type": "error",
        "content": "Chat engine unavailable. Please check configuration.",
    })
    return
```

**Impact**:
- ✅ User message is stored in WebUI (not lost)
- ❌ No assistant response generated
- ✅ Session remains intact for future messages

**User Experience**:
- Error message shown in chat
- User can retry after fixing engine config
- Message history preserved

### Streaming Error → Fallback to Error Message

**Trigger**: Exception during streaming generation

**Behavior**:
```python
except Exception as e:
    error_message = f"⚠️ Chat engine error: {str(e)}"
    response_buffer = [error_message]

    await manager.send_message(session_id, {
        "type": "message.error",
        "message_id": message_id,
        "content": error_message,
    })
```

**Impact**:
- ✅ Partial stream is NOT shown to user (all-or-nothing)
- ✅ Error message clearly indicates failure
- ⚠️ Error message is NOT stored in database (flagged with `⚠️`)

**User Experience**:
- Error message appears in chat
- Can retry immediately
- No corrupted partial responses

---

## 4. WebSocket Connection Degradation

### Client Disconnect During Streaming

**Trigger**: User closes tab/browser during response generation

**Behavior**:
```python
try:
    while True:
        msg_type, data = await chunk_queue.get()
        # ... streaming logic
except asyncio.CancelledError:
    producer_task.cancel()
    logger.warning(f"Streaming cancelled for session {session_id}")
    raise
```

**Impact**:
- ✅ Producer task is cancelled (no wasted compute)
- ✅ Resources are cleaned up
- ✅ Partial response is NOT stored (consistency)

**User Experience**:
- On reconnect: sees last complete message
- No corrupted/partial messages in history
- Can continue conversation normally

---

## 5. Core Session Creation Degradation

### Core Chat Session Creation Fails

**Trigger**: ChatService unavailable or database write fails

**Behavior**:
```python
try:
    chat_service = ChatService()
    # Create Core session with runtime config
except Exception as e:
    logger.warning(f"Failed to ensure Core chat session: {e}")
    # Not fatal, continue (ChatEngine will use defaults)
```

**Impact**:
- ⚠️ Warning logged but NOT user-visible
- ✅ Message processing continues
- ⚠️ ChatEngine uses default config (no runtime config applied)

**User Experience**:
- No visible error
- Message processing completes
- May not use requested model/provider (degraded experience)

---

## 6. Whitelist Strategy (Unknown Fields)

### Unknown Metadata Fields

**Trigger**: Frontend sends extra/unknown fields in metadata

**Behavior**:
```python
# Only extract known fields, ignore everything else
config = ChatRuntimeConfig(
    model_type=metadata.get("model_type"),
    provider=metadata.get("provider"),
    # ... known fields only
)
# Unknown fields like "ui_theme", "user_preference" are ignored
```

**Impact**:
- ✅ No crashes from unexpected data
- ✅ Forward-compatible (old backend ignores new fields)
- ✅ Backward-compatible (missing fields default to None)

**User Experience**:
- Transparent (no visible impact)
- UI can safely add new fields without backend changes

---

## 7. Validation Order and Early Returns

### Fail-Fast Philosophy

**Validation Order**:
1. ✅ Extract runtime config (Phase 3)
2. ✅ Validate config (return on error)
3. ✅ Store user message (return on error)
4. ✅ Get ChatEngine (return on error)
5. ✅ Ensure Core session (log warning, continue)
6. ✅ Stream response (return on error)
7. ✅ Store assistant message (log warning if error)

**Benefits**:
- No partial state changes on early failures
- Clear error messages at each stage
- Resources not allocated for doomed requests

---

## 8. Error Response Taxonomy

### Error Types

| Type | Protocol | Storage | Impact |
|------|----------|---------|--------|
| `message.error` | Structured | NOT stored | Config validation, streaming errors |
| `error` | Legacy | NOT stored | Generic errors (JSON parse, unknown type) |
| `event` | Info | NOT stored | Non-fatal notifications (storage warning) |

### Structured Error Format

```json
{
  "type": "message.error",
  "message_id": "uuid",
  "content": "⚠️ Human-readable error message",
  "metadata": {
    "error_type": "invalid_config" | "engine_error" | "storage_error",
    "error_detail": "Technical details for debugging"
  }
}
```

---

## 9. Testing Coverage (Phase 4)

### Unit Tests

**File**: `tests/webui/test_runtime_config.py`

**Coverage**:
- ✅ 18 tests covering all validation scenarios
- ✅ Boundary value testing (0.0, 2.0, -0.1, 2.1)
- ✅ Type mismatch testing (string instead of number)
- ✅ camelCase/snake_case compatibility
- ✅ Whitelist behavior (unknown fields ignored)
- ✅ None value handling (degradation)

**All 18 tests passing** ✅

### Integration Tests

**File**: `tests/webui/test_chat_websocket.py`

**Coverage** (requires FastAPI TestClient):
- ConnectionManager lifecycle
- WebSocket message flow
- Streaming cancellation
- Error propagation

---

## 10. Observability

### Logging Strategy

**Levels**:
- `ERROR`: User-impacting failures (config validation, ChatEngine crash)
- `WARNING`: Degraded mode (MemoryStore fallback, Core session creation failed)
- `INFO`: Normal operation (config extracted, message stored, streaming complete)

**Key Log Points**:
```python
# Config validation failure
logger.error(f"Invalid runtime config: {config_error}")

# Storage fallback
logger.warning("Falling back to MemorySessionStore (degraded mode)")

# Config applied
logger.info(f"Runtime config: {config_dict}")

# Streaming cancelled
logger.warning(f"Streaming cancelled for session {session_id}")
```

### Metrics to Monitor

1. **Storage fallback rate**: MemoryStore vs SQLiteStore usage
2. **Config validation errors**: Track invalid config submissions
3. **ChatEngine errors**: Streaming failures per session
4. **WebSocket cancellations**: Client disconnect frequency

---

## 11. Recovery Procedures

### From SQLite Failure

1. Check database file permissions
2. Verify disk space
3. Check for file locks (other processes)
4. Restart server (automatic SQLite retry)

### From ChatEngine Failure

1. Check provider connectivity (ollama, OpenAI)
2. Verify API keys/credentials
3. Check model availability
4. Review ChatEngine logs

### From Config Validation Errors

1. No action needed (user-side error)
2. Frontend should validate before sending (optional)
3. Error message guides user to fix

---

## 12. Design Principles

### Fail-Fast

- Invalid config → immediate error, no processing
- ChatEngine unavailable → immediate error, no retry

### Graceful Degradation

- SQLite fails → MemoryStore (data loss acceptable for availability)
- Core session creation fails → continue with defaults (UX degradation acceptable)

### Atomicity

- Streaming cancelled → no partial message stored
- Config validation failed → no user message stored

### Clear Error Messages

- Human-readable error text (`⚠️ Configuration error: ...`)
- Structured metadata for debugging (`error_type`, `error_detail`)

### No Silent Failures

- All errors logged at appropriate level
- User-facing errors shown in UI
- Internal errors logged for debugging

---

## Summary

**Degradation Layers**:
1. ✅ Storage: SQLite → Memory
2. ✅ Config: Invalid → Error (fail-fast)
3. ✅ Engine: Unavailable → Error
4. ✅ Streaming: Error → Error message
5. ✅ Connection: Disconnect → Cancel + cleanup
6. ✅ Core Session: Failed → Continue with defaults

**Test Coverage**: 18/18 unit tests passing ✅

**Production Ready**: All critical paths have error handling ✅
