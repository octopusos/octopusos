# Agent-API-Contract Delivery Report

**Date:** 2025-01-29
**Objective:** Establish unified API response contracts and execution snapshot aggregation endpoint
**Status:** ✅ Complete

---

## Overview

This delivery establishes a unified API contract for AgentOS WebUI and implements the execution snapshot aggregation endpoint. All new API endpoints follow this standard contract for consistent error handling, authentication, and response formatting.

---

## Deliverables

### 1. API Response Contracts (Wave1-A1) ✅

**File:** `agentos/webui/api/contracts.py`

#### Features Implemented

1. **Standard Response Format**
   ```python
   {
       "ok": bool,           # Operation success status
       "data": Any,          # Actual response data
       "error": str | None,  # Human-readable error message
       "hint": str | None,   # User-actionable hint
       "reason_code": str | None  # Machine-readable error code
   }
   ```

2. **Reason Code Enumeration**
   - `AUTH_REQUIRED` - Missing or invalid authentication token
   - `AUTH_FORBIDDEN` - Authenticated but insufficient permissions
   - `INVALID_INPUT` - Validation error in request parameters
   - `NOT_FOUND` - Requested resource does not exist
   - `TASK_NOT_FOUND` - Specific task not found
   - `REPO_NOT_FOUND` - Repository not found
   - `CONFLICT` - Resource conflict (duplicate entry)
   - `BAD_STATE` - Operation not allowed in current state
   - `INTERNAL_ERROR` - Unexpected server error
   - `SERVICE_UNAVAILABLE` - Downstream service unavailable
   - `DATABASE_ERROR` - Database operation failed
   - `RATE_LIMITED` - Too many requests

3. **Pydantic Models**
   - `ApiResponse[T]` - Generic success/error response wrapper
   - `ApiError` - Detailed error response with hint and details

4. **Utility Functions**
   - `success(data)` - Create success response
   - `error(message, reason_code, hint, details, http_status)` - Create HTTPException with standard format
   - `error_response(message, reason_code, hint, details)` - Create error dict without raising exception
   - `not_found_error(resource_type, resource_id, hint)` - Helper for NOT_FOUND errors
   - `validation_error(message, hint, details)` - Helper for INVALID_INPUT errors
   - `bad_state_error(message, hint, details)` - Helper for BAD_STATE errors

5. **Authentication Functions**
   - `validate_admin_token(x_admin_token)` - Validate admin token for protected endpoints
   - `validate_user_token(x_user_token)` - Validate user token and extract user ID

#### Usage Example

```python
from agentos.webui.api.contracts import success, not_found_error, validation_error

@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    # Validate input
    if len(task_id) < 10:
        raise validation_error(
            "Invalid task_id format",
            hint="task_id must be a valid ULID",
        )

    # Get task
    task = task_manager.get_task(task_id)
    if not task:
        raise not_found_error("Task", task_id)

    # Return success
    return success(task.to_dict())
```

---

### 2. Execution Snapshot API (Wave1-A2) ✅

**File:** `agentos/webui/api/execution.py`

#### Endpoint

```
GET /api/execution/{task_id}/snapshot
```

#### Query Parameters

- `include` - Comma-separated list of fields to include (default: "plan,steps,logs,artifacts,diffs")
  - `plan` - Execution plan structure
  - `steps` - Individual execution steps
  - `logs` - Audit log entries
  - `artifacts` - Git artifacts (commits, PRs, branches)
  - `diffs` - File change summary
- `log_limit` - Maximum number of log entries (default: 100, max: 1000)
- `artifact_limit` - Maximum number of artifacts (default: 50, max: 500)

#### Response Structure

```json
{
  "ok": true,
  "data": {
    "task_id": "01HQ7XYZ...",
    "title": "Implement feature X",
    "status": "running",
    "created_at": "2025-01-29T10:00:00Z",
    "updated_at": "2025-01-29T10:15:00Z",

    "plan": {
      "plan_id": "plan-1",
      "title": "Feature implementation plan",
      "created_at": "2025-01-29T10:00:00Z",
      "steps": [...]
    },

    "logs": [
      {
        "log_id": 1,
        "level": "info",
        "event_type": "task_started",
        "message": "Task execution started",
        "timestamp": "2025-01-29T10:00:00Z",
        "repo_id": null
      }
    ],

    "artifacts": [
      {
        "artifact_id": 1,
        "repo_id": "repo-1",
        "ref_type": "commit",
        "ref_value": "abc123...",
        "summary": "Initial implementation",
        "created_at": "2025-01-29T10:15:00Z"
      }
    ],

    "diffs": [
      {
        "file_path": "src/api.py",
        "lines_added": 50,
        "lines_deleted": 10,
        "status": "modified"
      }
    ]
  },
  "error": null,
  "hint": null,
  "reason_code": null
}
```

#### Data Sources

The snapshot endpoint aggregates data from:

1. **TaskManager** - Task basic info (title, status, timestamps)
2. **TaskAuditService** - Execution logs and file change summaries
3. **TaskArtifactService** - Git artifacts (commits, PRs, branches)
4. **Route Plan** - Execution plan from router or task metadata

#### Performance Optimization

- Single database connection per request
- Selective field inclusion via `include` parameter (avoid fetching unused data)
- Query limits to prevent excessive data transfer
- No N+1 queries (all data fetched in batch)

#### Usage Examples

```bash
# Get full snapshot
curl http://localhost:8080/api/execution/01HQ7XYZ.../snapshot

# Get only plan and logs
curl http://localhost:8080/api/execution/01HQ7XYZ.../snapshot?include=plan,logs

# Get with custom limits
curl http://localhost:8080/api/execution/01HQ7XYZ.../snapshot?log_limit=50&artifact_limit=20
```

---

### 3. Audit Middleware (Wave1-A3) ✅

**File:** `agentos/webui/middleware/audit.py`

#### Features

1. **Automatic Audit Recording**
   - Intercepts all write operations (POST, PUT, DELETE, PATCH)
   - Records to `task_audits` table via `TaskAuditService`
   - Captures: user_id, action, target, timestamp, result, duration

2. **Metadata Extraction**
   - `task_id` - Extracted from path segments (`/api/tasks/{task_id}/...`)
   - `repo_id` - Extracted from path or query parameters
   - `user_id` - Extracted from `X-User-Token` or `Authorization` headers
   - `operation` - HTTP method (post, put, delete)
   - `event_type` - Determined from path and method (task_approved, repo_write, etc.)

3. **Status Tracking**
   - `success` - HTTP status 200-399
   - `failed` - HTTP status 400+
   - Includes error messages for failures

4. **Performance Metrics**
   - Request duration in milliseconds
   - Recorded in audit payload

5. **Error Handling**
   - Graceful degradation (audit failures don't block requests)
   - Logs errors but allows request to proceed

#### Path Exclusions

The following paths are excluded from auditing:
- `/health`
- `/api/health`
- `/static/*`
- `/favicon.ico`

#### Event Type Mapping

| Path Pattern | Method | Event Type |
|-------------|--------|-----------|
| `/api/tasks/*/approve` | POST | `task_approved` |
| `/api/tasks/*/queue` | POST | `task_queued` |
| `/api/tasks/*/start` | POST | `task_started` |
| `/api/tasks/*/complete` | POST | `task_completed` |
| `/api/tasks/*/cancel` | POST | `task_canceled` |
| `/api/tasks/*` | POST | `task_created` |
| `/api/tasks/*` | PUT | `task_updated` |
| `/api/tasks/*` | DELETE | `task_deleted` |
| `/api/execution/*` | * | `execution_action` |
| `/api/repos/*` | POST | `repo_write` |
| `/api/repos/*` | PUT | `repo_update` |
| `/api/repos/*` | DELETE | `repo_delete` |

#### Registration

```python
# In agentos/webui/app.py
from agentos.webui.middleware.audit import add_audit_middleware

app = FastAPI()
add_audit_middleware(app)
```

#### Audit Record Structure

```python
{
    "task_id": "01HQ7XYZ...",  # or "system" if not task-scoped
    "repo_id": "repo-1",  # optional
    "operation": "post",
    "event_type": "task_approved",
    "status": "success",  # or "failed"
    "level": "info",  # or "warn"
    "payload": {
        "method": "POST",
        "path": "/api/tasks/01HQ7XYZ/approve",
        "status_code": 200,
        "duration_ms": 45,
        "user_id": "user-123",
        # ... additional context
    },
    "created_at": "2025-01-29T10:00:00Z"
}
```

---

## Integration

### 1. WebUI App Registration

The execution API and audit middleware are registered in `agentos/webui/app.py`:

```python
# Import execution API
from agentos.webui.api import execution

# Register audit middleware (before routes)
from agentos.webui.middleware.audit import add_audit_middleware
add_audit_middleware(app)

# Register execution API router
app.include_router(execution.router, tags=["execution"])
```

### 2. Database Schema

The implementation uses existing database tables:

- `tasks` - Task basic info
- `task_audits` - Audit logs and operations
- `task_artifact_ref` - Git artifacts
- `task_lineage` - Task execution timeline

No schema changes required.

---

## Testing

### Test Coverage

1. **Contracts Module** - `tests/unit/webui/test_contracts.py`
   - Response model validation
   - Utility function behavior
   - Error helpers
   - Authentication functions
   - Reason code constants

2. **Execution API** - `tests/unit/webui/test_execution_api.py`
   - Snapshot endpoint success/failure cases
   - Field inclusion parameter
   - Limit parameters
   - Helper function extraction logic
   - Integration with services

3. **Audit Middleware** - `tests/unit/webui/test_audit_middleware.py`
   - Request filtering (GET vs POST/PUT/DELETE)
   - Path exclusions
   - Metadata extraction
   - Event type determination
   - Error handling and graceful degradation

### Running Tests

```bash
# Run all contract tests
pytest tests/unit/webui/test_contracts.py -v

# Run execution API tests
pytest tests/unit/webui/test_execution_api.py -v

# Run audit middleware tests
pytest tests/unit/webui/test_audit_middleware.py -v

# Run all WebUI tests
pytest tests/unit/webui/ -v
```

---

## Usage Guide

### For API Developers

When creating new API endpoints, use the standard contract:

```python
from fastapi import APIRouter
from agentos.webui.api.contracts import success, not_found_error, validation_error

router = APIRouter(prefix="/api/myapi", tags=["myapi"])

@router.get("/{resource_id}")
async def get_resource(resource_id: str):
    # Validate input
    if not resource_id:
        raise validation_error("resource_id is required")

    # Get resource
    resource = my_service.get(resource_id)
    if not resource:
        raise not_found_error("Resource", resource_id)

    # Return success
    return success(resource)
```

### For Frontend Developers

All new API endpoints return responses in this format:

```typescript
interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
  hint?: string;
  reason_code?: string;
}

// Usage
const response = await fetch('/api/execution/task-123/snapshot');
const json = await response.json();

if (json.ok) {
  console.log('Success:', json.data);
} else {
  console.error('Error:', json.error);
  console.log('Hint:', json.hint);
  console.log('Code:', json.reason_code);
}
```

### For Administrators

#### Authentication

Set environment variables to enable authentication:

```bash
# Admin token (for protected endpoints)
export AGENTOS_ADMIN_TOKEN=your-secret-admin-token

# User authentication (optional)
export AGENTOS_REQUIRE_USER_AUTH=true
```

#### Audit Logs

Query audit logs from the database:

```sql
-- Get recent audits for a task
SELECT * FROM task_audits
WHERE task_id = '01HQ7XYZ...'
ORDER BY created_at DESC
LIMIT 50;

-- Get failed operations
SELECT * FROM task_audits
WHERE json_extract(payload, '$.status') = 'failed'
ORDER BY created_at DESC;

-- Get operations by user
SELECT * FROM task_audits
WHERE json_extract(payload, '$.user_id') = 'user-123'
ORDER BY created_at DESC;
```

---

## Constraints & Design Decisions

### 1. Backward Compatibility

- Existing API endpoints are not modified
- New contract applies only to new endpoints
- Gradual migration path available

### 2. Read-Only Implementation

- Execution snapshot is read-only
- No task execution control (run, pause, cancel)
- Focused on observability, not control

### 3. Database Compatibility

- Uses existing `store/registry.sqlite`
- No schema migrations required
- Compatible with v18+ database schema

### 4. Error Handling

- Audit failures are logged but don't block requests
- Missing data returns empty arrays (not errors)
- Graceful degradation for missing services

### 5. Performance

- Selective field inclusion prevents over-fetching
- Query limits prevent excessive data transfer
- Single DB connection per request
- No N+1 query patterns

---

## Future Enhancements

### Potential Improvements

1. **Streaming Logs**
   - WebSocket endpoint for real-time log streaming
   - Server-sent events for audit trail updates

2. **Advanced Filtering**
   - Log level filtering (info/warn/error)
   - Time range filtering for logs and artifacts
   - Regex search in log messages

3. **Aggregation Statistics**
   - File change statistics (total lines added/deleted)
   - Operation counts by type
   - Duration percentiles

4. **Caching**
   - Redis cache for frequently accessed snapshots
   - ETags for conditional requests
   - Cache invalidation on state changes

5. **GraphQL Support**
   - GraphQL schema for flexible queries
   - Nested field selection
   - Batch loading with DataLoader

---

## Acceptance Checklist

- [x] contracts.py defined with complete type annotations
- [x] Execution snapshot API returns aggregated data
- [x] Audit middleware intercepts write operations
- [x] All errors include reason_code and hint
- [x] Code follows existing style (governance.py reference)
- [x] Pytest tests for all modules
- [x] No modifications to existing API return formats
- [x] Read-only implementation (no exec run)
- [x] Compatible with store/registry.sqlite
- [x] Documentation complete

---

## Files Created

1. `agentos/webui/api/contracts.py` - API response contracts (398 lines)
2. `agentos/webui/api/execution.py` - Execution snapshot API (453 lines)
3. `agentos/webui/middleware/audit.py` - Audit middleware (356 lines)
4. `tests/unit/webui/test_contracts.py` - Contracts tests (397 lines)
5. `tests/unit/webui/test_execution_api.py` - Execution API tests (613 lines)
6. `tests/unit/webui/test_audit_middleware.py` - Middleware tests (484 lines)
7. `AGENT_API_CONTRACT_DELIVERY.md` - This document

**Total:** 2,701 lines of implementation + tests + documentation

---

## Next Steps

### For Integration (Wave 2)

1. Migrate existing endpoints to use new contracts (optional)
2. Add execution control endpoints (run, pause, cancel)
3. Implement WebSocket streaming for real-time logs
4. Add dashboard UI components for execution visualization

### For Production

1. Configure authentication tokens (`AGENTOS_ADMIN_TOKEN`)
2. Enable audit logging in production environment
3. Set up monitoring for audit log volume
4. Document API contracts in OpenAPI/Swagger docs

---

**Delivery Date:** 2025-01-29
**Implemented By:** Claude (Sonnet 4.5)
**Review Status:** Ready for review
