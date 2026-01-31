# Session Mode and Phase Management API

**Implemented in**: Task #4
**API Version**: v0.3.2+

## Overview

The Session API provides independent management of two orthogonal session attributes:

- **conversation_mode**: UI/UX context (what the user is doing)
- **execution_phase**: Security context (what external operations are allowed)

Both attributes can be managed independently, but certain combinations have special rules (e.g., `plan` mode blocks `execution` phase).

---

## Endpoints

### 1. GET /api/sessions/{session_id}

Get session details including mode and phase.

**Response**:
```json
{
  "id": "01JFGH12345678",
  "title": "My Session",
  "created_at": "2025-01-31T10:00:00Z",
  "updated_at": "2025-01-31T10:30:00Z",
  "tags": ["development"],
  "metadata": {
    "conversation_mode": "development",
    "execution_phase": "planning",
    ...
  },
  "conversation_mode": "development",
  "execution_phase": "planning"
}
```

---

### 2. PATCH /api/sessions/{session_id}/mode

Update conversation mode for a session.

**Request Body**:
```json
{
  "mode": "development"
}
```

**Valid modes**:
- `chat` - Free-form conversation (default)
- `discussion` - Structured discussion or brainstorming
- `plan` - Planning and design work
- `development` - Active development work
- `task` - Task-focused conversation

**Response (200 OK)**:
```json
{
  "ok": true,
  "session": {
    "session_id": "01JFGH12345678",
    "conversation_mode": "development",
    "execution_phase": "planning",
    "title": "My Session",
    "metadata": {...}
  }
}
```

**Error Responses**:

- **400 Bad Request** - Invalid mode value:
  ```json
  {
    "error": "Invalid conversation mode",
    "mode": "invalid_mode",
    "valid_modes": ["chat", "discussion", "plan", "development", "task"]
  }
  ```

- **404 Not Found** - Session not found:
  ```json
  {
    "detail": "Session not found: 01JFGH12345678"
  }
  ```

---

### 3. PATCH /api/sessions/{session_id}/phase

Update execution phase for a session with audit logging.

**Request Body**:
```json
{
  "phase": "execution",
  "confirmed": true,
  "actor": "user_john",
  "reason": "Starting deployment process"
}
```

**Fields**:
- `phase` (required): `"planning"` or `"execution"`
- `confirmed` (optional, default: false): Required=true for `execution` phase
- `actor` (optional, default: "user"): Who initiated the change
- `reason` (optional): Reason for the change

**Response (200 OK)**:
```json
{
  "ok": true,
  "session": {
    "session_id": "01JFGH12345678",
    "conversation_mode": "development",
    "execution_phase": "execution",
    "title": "My Session",
    "metadata": {...}
  },
  "audit_id": "audit_abc123def456"
}
```

**Error Responses**:

- **400 Bad Request** - Invalid phase:
  ```json
  {
    "error": "Invalid execution phase",
    "phase": "invalid",
    "valid_phases": ["planning", "execution"]
  }
  ```

- **400 Bad Request** - Missing confirmation:
  ```json
  {
    "error": "Confirmation required for execution phase",
    "phase": "execution",
    "confirmed": false,
    "hint": "Set confirmed=true to proceed with execution phase"
  }
  ```

- **403 Forbidden** - Plan mode blocks execution:
  ```json
  {
    "error": "Mode 'plan' blocks execution phase",
    "current_mode": "plan",
    "requested_phase": "execution",
    "hint": "Change conversation_mode first, then update execution_phase"
  }
  ```

- **404 Not Found** - Session not found:
  ```json
  {
    "detail": "Session not found: 01JFGH12345678"
  }
  ```

---

## Usage Examples

### Example 1: Update Mode

```bash
curl -X PATCH http://localhost:8000/api/sessions/01JFGH12345678/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "development"}'
```

### Example 2: Update Phase to Execution (with confirmation)

```bash
curl -X PATCH http://localhost:8000/api/sessions/01JFGH12345678/phase \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "execution",
    "confirmed": true,
    "actor": "user_john",
    "reason": "Starting deployment"
  }'
```

### Example 3: Update Phase to Planning (no confirmation needed)

```bash
curl -X PATCH http://localhost:8000/api/sessions/01JFGH12345678/phase \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "planning",
    "actor": "user_john",
    "reason": "Returning to planning"
  }'
```

### Example 4: Get Session with Mode/Phase

```bash
curl -X GET http://localhost:8000/api/sessions/01JFGH12345678
```

---

## Workflow Examples

### Workflow 1: Development Session

```bash
# 1. Create session (defaults: mode=chat, phase=planning)
curl -X POST http://localhost:8000/api/sessions \
  -d '{"title": "Feature Development"}'

# 2. Switch to development mode
curl -X PATCH http://localhost:8000/api/sessions/{id}/mode \
  -d '{"mode": "development"}'

# 3. Enter execution phase (requires confirmation)
curl -X PATCH http://localhost:8000/api/sessions/{id}/phase \
  -d '{"phase": "execution", "confirmed": true}'

# 4. Return to planning phase
curl -X PATCH http://localhost:8000/api/sessions/{id}/phase \
  -d '{"phase": "planning"}'
```

### Workflow 2: Plan Mode Restriction

```bash
# 1. Switch to plan mode
curl -X PATCH http://localhost:8000/api/sessions/{id}/mode \
  -d '{"mode": "plan"}'

# 2. Try to enter execution phase (will fail with 403)
curl -X PATCH http://localhost:8000/api/sessions/{id}/phase \
  -d '{"phase": "execution", "confirmed": true}'
# Error: "Mode 'plan' blocks execution phase"

# 3. Switch out of plan mode first
curl -X PATCH http://localhost:8000/api/sessions/{id}/mode \
  -d '{"mode": "development"}'

# 4. Now execution phase is allowed
curl -X PATCH http://localhost:8000/api/sessions/{id}/phase \
  -d '{"phase": "execution", "confirmed": true}'
```

---

## Security Features

### 1. Confirmation Requirement
Changing to `execution` phase requires `confirmed=true` to prevent accidental transitions.

### 2. Audit Logging
All phase changes are audited with:
- Session ID
- Old and new phase
- Actor (who made the change)
- Reason (why the change was made)
- Timestamp
- Audit ID (for tracking)

### 3. Mode-Based Restrictions
The `plan` conversation mode blocks transitions to `execution` phase, enforcing a planning-first workflow.

### 4. Independent Management
Mode and phase are independent, allowing flexible workflows while maintaining security boundaries.

---

## Design Principles

1. **Orthogonal Attributes**: Mode (UI/UX) and phase (security) are independent
2. **Safe Defaults**: New sessions start in `chat` mode and `planning` phase
3. **Explicit Confirmation**: Execution phase requires explicit confirmation
4. **Audit Trail**: All phase changes are logged for compliance
5. **Clear Errors**: Error messages include hints for resolution

---

## Testing

Unit tests are available at:
- `tests/webui/api/test_sessions_mode_phase.py` (15 tests)

Test coverage includes:
- ✅ All valid modes and phases
- ✅ Invalid value handling
- ✅ Confirmation requirements
- ✅ Plan mode restrictions
- ✅ Audit logging
- ✅ Error messages and hints
- ✅ Mode/phase independence
- ✅ Response format compliance

Run tests:
```bash
pytest tests/webui/api/test_sessions_mode_phase.py -v
```

---

## Implementation Details

**Backend Components**:
- API Layer: `agentos/webui/api/sessions.py`
- Service Layer: `agentos/core/chat/service.py`
- Models: `agentos/core/chat/models.py` (ConversationMode enum)
- Audit: `agentos/core/capabilities/audit.py` (emit_audit_event)

**Database Storage**:
- Stored in `chat_sessions.metadata` as JSON
- Fields: `conversation_mode`, `execution_phase`

**Audit Table**:
- Phase changes logged to `task_audits` table
- Event type: `execution_phase_changed`
- Includes audit_id for tracking

---

## Future Enhancements

Potential improvements:
1. Add `GET /api/sessions/{id}/audit` to view phase change history
2. Add WebSocket events for real-time mode/phase changes
3. Add role-based access control for phase changes
4. Add bulk operations (update multiple sessions)
5. Add session templates with predefined mode/phase combinations
