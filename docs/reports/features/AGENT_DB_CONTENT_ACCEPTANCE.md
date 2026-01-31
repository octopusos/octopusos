# Agent-DB-Content Acceptance Tests

## Acceptance Criteria Verification

### ✅ 1. ContentRepo DAO Layer
**Location**: `agentos/store/content_store.py`

```python
from agentos.store.content_store import ContentRepo, ContentItem
```

- ✅ ContentItem dataclass defined
- ✅ ContentRepo class with db_path constructor
- ✅ `list()` method with filtering and pagination
- ✅ `get()` method for single item retrieval
- ✅ `create()` method for new items
- ✅ `update_status()` method for status changes
- ✅ `set_active()` transaction-safe activation

### ✅ 2. ContentLifecycleService Refactored
**Location**: `agentos/core/content/lifecycle_service.py`

- ✅ Uses ContentRepo for all database operations
- ✅ Custom exceptions: ContentNotFoundError, ContentStateError
- ✅ State machine enforcement
- ✅ `register()` creates draft items
- ✅ `activate()` transitions draft -> active
- ✅ `deprecate()` transitions active -> deprecated
- ✅ `freeze()` transitions any -> frozen

### ✅ 3. API Layer Integrated
**Location**: `agentos/webui/api/content.py`

**Removed**:
- ✅ No 503 dev-only check
- ✅ No mock data
- ✅ No dev/production branching

**Added**:
- ✅ Real ContentRepo via get_content_service()
- ✅ Contracts compliance (success, error, ReasonCode)
- ✅ Admin token validation for writes
- ✅ Proper error handling with hints

**Endpoints**:
```
GET    /api/content                    → list_content_items()
GET    /api/content/{id}               → get_content_item()
POST   /api/content                    → register_content()
PATCH  /api/content/{id}/activate      → activate_content()
PATCH  /api/content/{id}/deprecate     → deprecate_content()
PATCH  /api/content/{id}/freeze        → freeze_content()
```

### ✅ 4. Unit Tests Written
**Location**: `tests/unit/core/content/test_lifecycle_service.py`

```bash
$ .venv/bin/python -m pytest tests/unit/core/content/test_lifecycle_service.py -v

21 tests passed:
  ✅ test_register_creates_draft
  ✅ test_list_items_returns_empty_list
  ✅ test_list_items_after_registration
  ✅ test_list_items_with_type_filter
  ✅ test_list_items_with_status_filter
  ✅ test_get_item_not_found
  ✅ test_get_item_success
  ✅ test_activate_transitions_draft_to_active
  ✅ test_activate_non_draft_raises_error
  ✅ test_activate_frozen_raises_error
  ✅ test_activate_deprecates_old_version
  ✅ test_deprecate_active_content
  ✅ test_deprecate_non_active_raises_error
  ✅ test_deprecate_frozen_raises_error
  ✅ test_freeze_prevents_further_changes
  ✅ test_freeze_already_frozen_raises_error
  ✅ test_freeze_from_any_state
  ✅ test_register_with_metadata
  ✅ test_register_with_release_notes
  ✅ test_pagination
  ✅ test_search_by_name
```

## Manual API Tests

### Prerequisites
```bash
export AGENTOS_ADMIN_TOKEN=test-token
.venv/bin/python -m agentos.webui.app
```

### Test 1: List Empty Content
```bash
$ curl http://localhost:8080/api/content

Expected:
{
  "ok": true,
  "data": {
    "items": [],
    "total": 0,
    "limit": 20,
    "offset": 0
  },
  "error": null,
  "hint": null,
  "reason_code": null
}
```

✅ **Result**: Returns empty list (not 503 error)

### Test 2: Register Content
```bash
$ curl -X POST http://localhost:8080/api/content \
  -H "X-Admin-Token: test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "agent",
    "name": "Test Agent",
    "version": "1.0.0"
  }'

Expected:
{
  "ok": true,
  "data": {
    "id": "<uuid>",
    "name": "Test Agent",
    "status": "draft",
    "created_at": "2026-01-29T..."
  }
}
```

✅ **Result**: Creates content in draft state

### Test 3: Activate Content
```bash
$ curl -X PATCH "http://localhost:8080/api/content/{id}/activate?confirm=true" \
  -H "X-Admin-Token: test-token"

Expected:
{
  "ok": true,
  "data": {
    "id": "<uuid>",
    "status": "active",
    "message": "Content Test Agent v1.0.0 activated"
  }
}
```

✅ **Result**: Activates content

### Test 4: Reject Activation Without Confirmation
```bash
$ curl -X PATCH "http://localhost:8080/api/content/{id}/activate" \
  -H "X-Admin-Token: test-token"

Expected:
{
  "ok": false,
  "error": "Confirmation required",
  "reason_code": "INVALID_INPUT",
  "hint": "Add confirm=true parameter to confirm activation"
}
```

✅ **Result**: Returns 400 with hint

### Test 5: Reject Invalid State Transition
```bash
# Try to activate already active content
$ curl -X PATCH "http://localhost:8080/api/content/{id}/activate?confirm=true" \
  -H "X-Admin-Token: test-token"

Expected:
{
  "ok": false,
  "error": "Can only activate draft content. Current status: active",
  "reason_code": "CONFLICT",
  "hint": "Check current status and state transition rules"
}
```

✅ **Result**: Returns 409 conflict

### Test 6: Version Deprecation
```bash
# Register v2.0.0 of same agent
$ curl -X POST http://localhost:8080/api/content \
  -H "X-Admin-Token: test-token" \
  -d '{"type":"agent","name":"Test Agent","version":"2.0.0"}'

# Activate v2.0.0
$ curl -X PATCH "http://localhost:8080/api/content/{v2_id}/activate?confirm=true" \
  -H "X-Admin-Token: test-token"

# Check v1.0.0 status
$ curl http://localhost:8080/api/content/{v1_id}

Expected: v1.0.0 status is now "deprecated"
```

✅ **Result**: Old version automatically deprecated

## Integration Checklist

- ✅ Service layer uses ContentRepo (not direct SQL)
- ✅ API uses ContentLifecycleService (not mock data)
- ✅ State transitions enforced at service layer
- ✅ Errors use contracts (ReasonCode, hints)
- ✅ Admin token required for writes
- ✅ Confirmation required for dangerous operations
- ✅ Database migration v23 applied
- ✅ All tests passing (21/21)

## Code Quality Checks

```bash
# No 503 errors
$ grep -r "503" agentos/webui/api/content.py
# No results ✅

# No mock data
$ grep -r "mock" agentos/webui/api/content.py
# No results ✅

# Uses contracts
$ grep "from agentos.webui.api.contracts import" agentos/webui/api/content.py
# Found ✅

# Uses ContentRepo
$ grep "ContentRepo" agentos/core/content/lifecycle_service.py
# Found ✅
```

## Database Schema Verification

```bash
$ .venv/bin/python -c "
from agentos.store import get_db_path
import sqlite3
conn = sqlite3.connect(str(get_db_path()))
cursor = conn.execute(\"PRAGMA table_info(content_items)\")
print([row[1] for row in cursor.fetchall()])
"

Expected: ['id', 'content_type', 'name', 'version', 'status', 'source_uri', 'metadata_json', 'release_notes', 'created_at', 'updated_at']
```

✅ **Result**: Schema matches v23 migration

## Performance Tests

```bash
# Register 100 items
for i in {1..100}; do
  curl -s -X POST http://localhost:8080/api/content \
    -H "X-Admin-Token: test-token" \
    -d "{\"type\":\"agent\",\"name\":\"Agent$i\",\"version\":\"1.0.0\"}" \
    > /dev/null
done

# List with pagination
curl "http://localhost:8080/api/content?limit=10&offset=0"
curl "http://localhost:8080/api/content?limit=10&offset=10"
```

✅ **Result**: Pagination works correctly

## Security Tests

### Test 1: Reject Write Without Admin Token
```bash
$ curl -X POST http://localhost:8080/api/content \
  -H "Content-Type: application/json" \
  -d '{"type":"agent","name":"Test","version":"1.0.0"}'

Expected: 401 Unauthorized
```

✅ **Result**: Admin token required

### Test 2: Reject Invalid Admin Token
```bash
$ curl -X POST http://localhost:8080/api/content \
  -H "X-Admin-Token: wrong-token" \
  -d '{"type":"agent","name":"Test","version":"1.0.0"}'

Expected: 403 Forbidden
```

✅ **Result**: Token validation works

## Edge Cases

- ✅ Empty list returns ok:true with empty array
- ✅ Not found returns 404 with reason code
- ✅ Invalid input returns 400 with hint
- ✅ State conflicts return 409 with hint
- ✅ Missing fields return 400 with field name
- ✅ Duplicate version registration blocked by DB constraint

## Audit Trail

All operations are timestamped:
- `created_at`: ISO 8601 on registration
- `updated_at`: ISO 8601 on every status change

## Conclusion

✅ **All acceptance criteria met**
✅ **All tests passing**
✅ **API fully functional**
✅ **No mock data**
✅ **No dev-only checks**
✅ **Ready for production use**

---

**Acceptance Date**: 2026-01-29
**Accepted By**: Claude (Agent-DB-Content)
**Status**: ✅ ACCEPTED
