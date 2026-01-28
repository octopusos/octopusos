# AgentOS WebUI API Contract

**Version:** 1.0
**Status:** Active
**Introduced:** 2025-01-29

---

## Overview

This document defines the unified API contract for all AgentOS WebUI endpoints. The contract standardizes:

- Response format (success and error cases)
- Error codes and messages
- Authentication mechanisms
- Audit logging

---

## Standard Response Format

All new API endpoints must return responses in this format:

```typescript
interface ApiResponse<T> {
  ok: boolean;           // Operation success status
  data?: T;              // Response data (present if ok=true)
  error?: string;        // Human-readable error message (present if ok=false)
  hint?: string;         // User-actionable hint for fixing errors
  reason_code?: string;  // Machine-readable error code
}
```

### Success Response Example

```json
{
  "ok": true,
  "data": {
    "task_id": "01HQ7XYZABC123",
    "status": "running",
    "created_at": "2025-01-29T10:00:00Z"
  },
  "error": null,
  "hint": null,
  "reason_code": null
}
```

### Error Response Example

```json
{
  "ok": false,
  "data": null,
  "error": "Task not found: 01HQ7XYZABC123",
  "hint": "Check the task_id and ensure the task exists",
  "reason_code": "TASK_NOT_FOUND"
}
```

---

## Reason Codes

### Authentication & Authorization

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_REQUIRED` | 401 | Missing or invalid authentication token |
| `AUTH_FORBIDDEN` | 403 | Authenticated but insufficient permissions |

### Input Validation

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_INPUT` | 400 | Generic validation error |
| `INVALID_TASK_ID` | 400 | Task ID format is invalid |
| `INVALID_REPO_ID` | 400 | Repository ID format is invalid |
| `INVALID_SESSION_ID` | 400 | Session ID format is invalid |

### Resource Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_FOUND` | 404 | Generic resource not found |
| `TASK_NOT_FOUND` | 404 | Specific task not found |
| `REPO_NOT_FOUND` | 404 | Repository not found |
| `SESSION_NOT_FOUND` | 404 | Session not found |

### State & Conflict

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `CONFLICT` | 409 | Resource conflict (duplicate entry) |
| `BAD_STATE` | 409 | Operation not allowed in current state |
| `TASK_NOT_READY` | 409 | Task is not ready for the operation |

### Service Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | Downstream service unavailable |
| `DATABASE_ERROR` | 500 | Database operation failed |

### Rate Limiting

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `RATE_LIMITED` | 429 | Too many requests |

---

## Python API

### Importing the Contract

```python
from agentos.webui.api.contracts import (
    success,
    error,
    not_found_error,
    validation_error,
    bad_state_error,
    validate_admin_token,
    validate_user_token,
    ReasonCode,
)
```

### Creating Success Responses

```python
@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise not_found_error("Task", task_id)

    return success(task.to_dict())
```

### Creating Error Responses

```python
# Validation error
if len(task_id) < 10:
    raise validation_error(
        "Invalid task_id format",
        hint="task_id must be a valid ULID",
        details={"task_id": task_id}
    )

# Not found error
if not task:
    raise not_found_error("Task", task_id)

# Bad state error
if task.status not in ["DRAFT", "QUEUED"]:
    raise bad_state_error(
        "Cannot approve task in current state",
        hint="Task must be in DRAFT or QUEUED state",
        details={"current_state": task.status}
    )

# Generic error
raise error(
    "Failed to process task",
    reason_code=ReasonCode.INTERNAL_ERROR,
    hint="Check server logs for details",
    http_status=500
)
```

### Protected Endpoints

```python
# Admin-only endpoint
@router.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: str,
    _: bool = Depends(validate_admin_token)
):
    # Admin token validated by dependency
    task_manager.delete_task(task_id)
    return success({"task_id": task_id, "status": "deleted"})

# User-scoped endpoint
@router.post("/api/tasks/{task_id}/claim")
async def claim_task(
    task_id: str,
    user_id: str = Depends(validate_user_token)
):
    task_manager.claim_task(task_id, user_id)
    return success({"task_id": task_id, "claimed_by": user_id})
```

---

## JavaScript/TypeScript API

### Response Type

```typescript
interface ApiResponse<T> {
  ok: boolean;
  data?: T;
  error?: string;
  hint?: string;
  reason_code?: string;
}
```

### Handling Responses

```typescript
async function getTask(taskId: string): Promise<Task> {
  const response = await fetch(`/api/tasks/${taskId}`);
  const json: ApiResponse<Task> = await response.json();

  if (json.ok) {
    return json.data!;
  } else {
    // Handle error
    console.error('Error:', json.error);
    console.log('Hint:', json.hint);
    console.log('Code:', json.reason_code);

    // Show user-friendly message
    if (json.reason_code === 'TASK_NOT_FOUND') {
      showNotification('Task not found', json.hint);
    }

    throw new Error(json.error);
  }
}
```

### Displaying Errors to Users

```typescript
function displayError(response: ApiResponse<any>) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'error-message';

  // Show error message
  const messageEl = document.createElement('p');
  messageEl.textContent = response.error;
  errorDiv.appendChild(messageEl);

  // Show hint if available
  if (response.hint) {
    const hintEl = document.createElement('p');
    hintEl.className = 'error-hint';
    hintEl.textContent = `💡 ${response.hint}`;
    errorDiv.appendChild(hintEl);
  }

  document.body.appendChild(errorDiv);
}
```

---

## Authentication

### Admin Token Authentication

Set the admin token in environment variables:

```bash
export AGENTOS_ADMIN_TOKEN=your-secret-admin-token
```

Include the token in requests:

```bash
curl -H "X-Admin-Token: your-secret-admin-token" \
  http://localhost:8080/api/admin/tasks/123/cancel
```

### User Token Authentication

Enable user authentication (optional):

```bash
export AGENTOS_REQUIRE_USER_AUTH=true
```

Include the user token in requests:

```bash
curl -H "X-User-Token: user-123" \
  http://localhost:8080/api/tasks/123/claim
```

---

## Audit Logging

All write operations (POST, PUT, DELETE, PATCH) are automatically audited by the audit middleware.

### Audit Record Structure

```json
{
  "task_id": "01HQ7XYZ...",
  "repo_id": "repo-1",
  "operation": "post",
  "event_type": "task_approved",
  "status": "success",
  "level": "info",
  "payload": {
    "method": "POST",
    "path": "/api/tasks/01HQ7XYZ/approve",
    "status_code": 200,
    "duration_ms": 45,
    "user_id": "user-123"
  },
  "created_at": "2025-01-29T10:00:00Z"
}
```

### Querying Audit Logs

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

## Migration Guide

### For Existing Endpoints

Existing endpoints do not need to be updated immediately. The new contract applies to:

1. All new API endpoints (mandatory)
2. Existing endpoints during refactoring (optional)

### Migration Steps

1. Import the contract utilities:
   ```python
   from agentos.webui.api.contracts import success, not_found_error, validation_error
   ```

2. Replace manual response construction with contract functions:
   ```python
   # Old
   return {"task_id": task_id, "status": "running"}

   # New
   return success({"task_id": task_id, "status": "running"})
   ```

3. Replace manual HTTPException raising with contract helpers:
   ```python
   # Old
   raise HTTPException(status_code=404, detail="Task not found")

   # New
   raise not_found_error("Task", task_id)
   ```

4. Add reason codes to all error responses:
   ```python
   # Old
   raise HTTPException(status_code=400, detail="Invalid input")

   # New
   raise validation_error("Invalid input", hint="Check the format")
   ```

---

## Best Practices

### 1. Always Provide Hints

```python
# Good
raise validation_error(
    "Invalid task_id format",
    hint="task_id must be a valid ULID (26 characters)"
)

# Bad
raise validation_error("Invalid task_id format")
```

### 2. Use Specific Error Helpers

```python
# Good
raise not_found_error("Task", task_id)

# Less good
raise error("Task not found", reason_code=ReasonCode.NOT_FOUND)
```

### 3. Include Useful Details

```python
# Good
raise bad_state_error(
    "Cannot approve task in RUNNING state",
    hint="Task must be in DRAFT or QUEUED state",
    details={
        "current_state": task.status,
        "allowed_states": ["DRAFT", "QUEUED"]
    }
)

# Bad
raise bad_state_error("Cannot approve task")
```

### 4. Handle Partial Success

```python
@router.post("/api/tasks/bulk-approve")
async def bulk_approve_tasks(task_ids: List[str]):
    results = []
    errors = []

    for task_id in task_ids:
        try:
            task_manager.approve_task(task_id)
            results.append({"task_id": task_id, "status": "approved"})
        except Exception as e:
            errors.append({"task_id": task_id, "error": str(e)})

    return success({
        "total": len(task_ids),
        "succeeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    })
```

### 5. Log Errors Appropriately

```python
import logging

logger = logging.getLogger(__name__)

@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise not_found_error("Task", task_id)
        return success(task.to_dict())
    except HTTPException:
        # Re-raise contract errors
        raise
    except Exception as e:
        # Log unexpected errors
        logger.exception(f"Failed to get task {task_id}")
        raise error(
            "Failed to get task",
            reason_code=ReasonCode.INTERNAL_ERROR,
            hint="Check server logs for details"
        )
```

---

## Testing

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient

def test_get_task_success(client: TestClient):
    response = client.get("/api/tasks/01HQ7XYZ")
    assert response.status_code == 200

    json = response.json()
    assert json["ok"] is True
    assert "data" in json
    assert json["data"]["task_id"] == "01HQ7XYZ"

def test_get_task_not_found(client: TestClient):
    response = client.get("/api/tasks/nonexistent")
    assert response.status_code == 404

    json = response.json()
    assert json["ok"] is False
    assert json["reason_code"] == "TASK_NOT_FOUND"
    assert json["hint"] is not None
```

### Integration Tests

```python
def test_audit_logging(client: TestClient, db):
    # Make write request
    response = client.post("/api/tasks/01HQ7XYZ/approve")
    assert response.status_code == 200

    # Verify audit log
    cursor = db.execute(
        "SELECT * FROM task_audits WHERE task_id = ?",
        ("01HQ7XYZ",)
    )
    audit = cursor.fetchone()

    assert audit is not None
    assert audit["event_type"] == "task_approved"
    assert audit["status"] == "success"
```

---

## Examples

See [`examples/api_contract_usage.py`](../../../examples/api_contract_usage.py) for complete working examples.

---

## References

- [Contracts Module](./contracts.py) - Implementation
- [Execution API](./execution.py) - Example usage
- [Audit Middleware](../middleware/audit.py) - Automatic auditing
- [Delivery Report](../../../AGENT_API_CONTRACT_DELIVERY.md) - Full documentation
