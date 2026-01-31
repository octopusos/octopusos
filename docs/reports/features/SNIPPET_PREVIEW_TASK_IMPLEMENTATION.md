# Snippet → Preview → Task Capability Chain Implementation

## Overview

This document describes the implementation of the Snippet → Preview → Task capability chain, which connects three core modules in AgentOS:

1. **Snippets API** - Code snippet asset library
2. **Preview API** - HTML preview with runtime dependency injection
3. **Task API** - Task draft creation for materialization

## Architecture

```
┌─────────────┐
│  Snippet    │
│  (code)     │
└──────┬──────┘
       │
       ├─────────────► POST /api/snippets/{id}/preview
       │                     │
       │                     ▼
       │               ┌─────────────────┐
       │               │  Preview API    │
       │               │  - Detect deps  │
       │               │  - Inject CDN   │
       │               │  - Create HTML  │
       │               └─────────────────┘
       │
       └─────────────► POST /api/snippets/{id}/materialize
                             │
                             ▼
                       ┌─────────────────┐
                       │  Task Draft     │
                       │  - Write file   │
                       │  - Require auth │
                       └─────────────────┘
```

## Implementation Details

### 1. Extended Audit System

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/audit.py`

Added new event constants:
- `SNIPPET_USED_IN_PREVIEW` - Tracks snippet usage in preview
- `TASK_MATERIALIZED_FROM_SNIPPET` - Tracks task draft creation

All preview events now use the centralized audit system:
- `PREVIEW_SESSION_CREATED`
- `PREVIEW_SESSION_OPENED`
- `PREVIEW_SESSION_EXPIRED`
- `PREVIEW_RUNTIME_SELECTED`
- `PREVIEW_DEP_INJECTED`

### 2. Snippets API Extensions

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/snippets.py`

#### 2.1 POST /api/snippets/{id}/preview

Creates a preview session from a snippet with intelligent HTML wrapping:

**Request**:
```json
{
  "preset": "three-webgl-umd"  // or "html-basic"
}
```

**Response**:
```json
{
  "snippet_id": "uuid",
  "preview_session_id": "uuid",
  "url": "/api/preview/{session_id}",
  "preset": "three-webgl-umd",
  "deps_injected": ["three-core", "three-fontloader", "three-text-geometry"],
  "expires_at": 1643234567
}
```

**HTML Wrapping Logic**:
- `language: "html"` → Use code directly
- `language: "javascript"` → Wrap in HTML with `<script>` tag
- Other languages → Wrap in `<pre><code>` for display

**Audit Trail**:
- Updates snippet `updated_at` timestamp
- Logs `SNIPPET_USED_IN_PREVIEW` event with metadata

#### 2.2 POST /api/snippets/{id}/materialize

Creates a task draft for writing snippet to file (P0.5 simplified version).

**Request**:
```json
{
  "target_path": "examples/demo.html",
  "description": "Write demo to examples directory"  // optional
}
```

**Response**:
```json
{
  "task_draft": {
    "source": "snippet",
    "snippet_id": "uuid",
    "title": "Materialize: Three.js Font Test",
    "description": "Write snippet to examples/demo.html",
    "target_path": "examples/demo.html",
    "language": "javascript",
    "tags": ["three.js", "webgl"],
    "plan": {
      "action": "write_file",
      "path": "examples/demo.html",
      "content": "...",
      "create_dirs": true
    },
    "files_affected": ["examples/demo.html"],
    "risk_level": "MEDIUM",
    "requires_admin_token": true
  },
  "message": "Task draft created. Execute in TasksView to write file."
}
```

**Security**:
- Validates `target_path` is relative (not absolute)
- Marks as `risk_level: MEDIUM` (file write operation)
- Requires admin token for actual execution (not enforced in P0.5)

**Audit Trail**:
- Logs `TASK_MATERIALIZED_FROM_SNIPPET` event to ORPHAN task

### 3. Preview API Integration

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/preview.py`

Updated to use centralized audit system from `agentos.core.audit`:

- Removed local audit event definitions
- Import audit functions from `agentos.core.audit`
- All audit events now stored in `task_audits` table

**Key Features**:
- Automatic dependency detection for Three.js
- CDN script injection (jsDelivr)
- Session TTL management (1 hour)
- Metadata endpoint: `GET /api/preview/{id}/meta`

### 4. Integration Test Suite

**File**: `/Users/pangge/PycharmProjects/AgentOS/test_api_integration.py`

Comprehensive test suite covering:

**Test 1: Snippet → Preview**
- Create Three.js snippet with FontLoader
- Create preview with `three-webgl-umd` preset
- Verify dependencies detected and injected
- Load preview HTML and verify CDN scripts

**Test 2: Snippet → Task Draft**
- Create HTML snippet
- Materialize to task draft
- Verify task draft structure and security settings

**Test 3: Error Handling**
- 404 for non-existent snippets
- 422 for invalid target paths (absolute paths)

**Run Tests**:
```bash
# Start WebUI server
python -m agentos.webui.app

# Run integration tests (in another terminal)
python3 test_api_integration.py
```

## API Documentation

### Snippets API

#### POST /api/snippets/{snippet_id}/preview

Create preview session from snippet.

**Parameters**:
- `snippet_id` (path): Snippet UUID

**Request Body**:
```json
{
  "preset": "html-basic" | "three-webgl-umd"
}
```

**Response**: `200 OK`
```json
{
  "snippet_id": "string",
  "preview_session_id": "string",
  "url": "string",
  "preset": "string",
  "deps_injected": ["string"],
  "expires_at": 123456789
}
```

**Errors**:
- `404`: Snippet not found
- `500`: Preview API call failed

---

#### POST /api/snippets/{snippet_id}/materialize

Create task draft from snippet.

**Parameters**:
- `snippet_id` (path): Snippet UUID

**Request Body**:
```json
{
  "target_path": "string",  // Relative path (required)
  "description": "string"   // Optional description
}
```

**Response**: `200 OK`
```json
{
  "task_draft": {
    "source": "snippet",
    "snippet_id": "string",
    "title": "string",
    "description": "string",
    "target_path": "string",
    "language": "string",
    "tags": ["string"],
    "plan": {
      "action": "write_file",
      "path": "string",
      "content": "string",
      "create_dirs": true
    },
    "files_affected": ["string"],
    "risk_level": "MEDIUM" | "HIGH",
    "requires_admin_token": true
  },
  "message": "string"
}
```

**Errors**:
- `404`: Snippet not found
- `422`: Invalid target path (absolute path)
- `500`: Internal server error

---

### Preview API

#### GET /api/preview/{session_id}/meta

Get metadata for preview session.

**Parameters**:
- `session_id` (path): Preview session UUID

**Response**: `200 OK`
```json
{
  "session_id": "string",
  "preset": "string",
  "deps_injected": ["string"],
  "snippet_id": "string | null",
  "created_at": 123456789,
  "expires_at": 123456789,
  "ttl_remaining": 3600
}
```

**Errors**:
- `404`: Session not found
- `410`: Session expired

## Database Schema

### Audit Events in task_audits

All capability chain events are stored in the `task_audits` table:

```sql
CREATE TABLE task_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,              -- "ORPHAN" for non-task events
    level TEXT DEFAULT 'info',          -- info|warn|error
    event_type TEXT NOT NULL,           -- Event type constant
    payload TEXT,                       -- JSON with snippet_id, preview_id, metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
```

**Payload Structure**:
```json
{
  "snippet_id": "uuid",       // For snippet-related events
  "preview_id": "uuid",       // For preview-related events
  ...metadata                 // Event-specific metadata
}
```

## Usage Examples

### Example 1: Preview Three.js Snippet

```bash
# 1. Create snippet
curl -X POST http://localhost:8000/api/snippets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Three.js Font Demo",
    "language": "javascript",
    "code": "const loader = new THREE.FontLoader(); ...",
    "tags": ["three.js", "webgl"]
  }'

# Response: {"id": "abc-123", ...}

# 2. Create preview
curl -X POST http://localhost:8000/api/snippets/abc-123/preview \
  -H "Content-Type: application/json" \
  -d '{"preset": "three-webgl-umd"}'

# Response: {"preview_session_id": "xyz-789", "url": "/api/preview/xyz-789", ...}

# 3. Open preview in browser
open http://localhost:8000/api/preview/xyz-789
```

### Example 2: Materialize Snippet to File

```bash
# Create task draft
curl -X POST http://localhost:8000/api/snippets/abc-123/materialize \
  -H "Content-Type: application/json" \
  -d '{
    "target_path": "examples/font_demo.html",
    "description": "Save Three.js font demo"
  }'

# Response: {"task_draft": {...}, "message": "Task draft created..."}
```

## Security Considerations

### Preview API
- Session TTL: 1 hour (configurable)
- Same-origin framing only (`X-Frame-Options: SAMEORIGIN`)
- In-memory session storage (no persistence)

### Materialize API
- Only relative paths allowed (validates `target_path`)
- Marked as `risk_level: MEDIUM` for file writes
- Requires admin token for execution (P1+ feature)
- Creates audit trail before execution

## P0 Acceptance Criteria

- [x] POST /api/snippets/{id}/preview creates preview from snippet
- [x] three-webgl-umd preset auto-injects dependencies
- [x] POST /api/snippets/{id}/materialize generates task draft
- [x] Materialize marks need for admin token (risk_level: MEDIUM/HIGH)
- [x] Audit events correctly recorded (SNIPPET_USED_IN_PREVIEW, TASK_MATERIALIZED_FROM_SNIPPET)
- [x] Integration test suite created and documented

## Future Enhancements (P1+)

### P1: Task Execution
- Implement actual task execution from draft
- Admin token validation
- File system permission checks
- Real-time execution status

### P2: Advanced Features
- Preview session persistence (Redis)
- Custom dependency injection rules
- Multi-file materialization
- Git commit integration

### P3: UI Integration
- SnippetsView with preview button
- TasksView integration
- Drag-and-drop materialization
- Preview iframe in UI

## Testing

### Manual Testing Checklist

1. **Snippet → Preview (JavaScript)**
   - [ ] Create JavaScript snippet
   - [ ] Create preview with html-basic preset
   - [ ] Create preview with three-webgl-umd preset
   - [ ] Verify dependencies injected
   - [ ] Check preview loads in browser

2. **Snippet → Preview (HTML)**
   - [ ] Create HTML snippet
   - [ ] Create preview (should use HTML directly)
   - [ ] Verify preview renders correctly

3. **Snippet → Task Draft**
   - [ ] Create snippet
   - [ ] Materialize to relative path
   - [ ] Verify task draft structure
   - [ ] Try absolute path (should fail with 422)

4. **Error Handling**
   - [ ] Preview non-existent snippet (404)
   - [ ] Materialize non-existent snippet (404)
   - [ ] Materialize with absolute path (422)

5. **Audit Trail**
   - [ ] Check task_audits table for events
   - [ ] Verify payload contains snippet_id, preview_id
   - [ ] Verify ORPHAN task created

### Automated Testing

```bash
# Run integration test suite
python3 test_api_integration.py

# Expected output:
# ✅ Test 1 PASSED: Snippet → Preview
# ✅ Test 2 PASSED: Snippet → Task Draft
# ✅ Test 3 PASSED: Error Handling
# ✅ ALL TESTS PASSED!
```

## Troubleshooting

### Issue: Preview returns 500 error
**Solution**: Check if preview API is registered in app.py:
```python
app.include_router(preview.router, prefix="/api", tags=["preview"])
```

### Issue: Dependencies not injected
**Solution**: Verify preset is set to `three-webgl-umd` and code contains Three.js API calls (e.g., `THREE.FontLoader`)

### Issue: Audit events not recorded
**Solution**: Check ORPHAN task exists in tasks table:
```sql
SELECT * FROM tasks WHERE task_id = 'ORPHAN';
```

### Issue: httpx module not found
**Solution**: Install httpx:
```bash
pip install httpx
```

## References

- Audit System: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/audit.py`
- Snippets API: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/snippets.py`
- Preview API: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/preview.py`
- Integration Tests: `/Users/pangge/PycharmProjects/AgentOS/test_api_integration.py`
- Database Schema: `/Users/pangge/PycharmProjects/AgentOS/agentos/store/schema_v06.sql`
