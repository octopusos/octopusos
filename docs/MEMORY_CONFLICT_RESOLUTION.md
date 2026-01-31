# Memory Conflict Resolution Strategy

**Task #12: 实现Memory冲突解决策略**

This document describes the intelligent memory conflict resolution system implemented in AgentOS.

## Overview

The Memory Conflict Resolution system handles scenarios where users change their mind, ensuring the system maintains a professional audit trail while always using the most current value.

### Example Scenario

```
First time:  "以后请叫我张三" (Call me Zhang San)
Second time: "其实还是叫我李四吧" (Actually, call me Li Si instead)

System behavior:
→ Keeps historical record of "张三"
→ Marks old value as superseded
→ Uses new value "李四" going forward
→ Maintains version chain for audit
```

## Data Model

### New Fields Added to `memory_items` Table

The following fields have been added via migration `schema_v45_memory_conflict_resolution.sql`:

- **`superseded_by`** (TEXT): Points to the memory_id that replaces this one
- **`supersedes`** (TEXT): Points to the memory_id that this one replaces
- **`version`** (INTEGER): Version number for same-key memories (starts at 1)
- **`is_active`** (INTEGER): Whether this memory is currently active (1=true, 0=false)
- **`superseded_at`** (TEXT): ISO 8601 timestamp when this memory was superseded

### Example Memory Item with Conflict Fields

```json
{
    "id": "mem-abc123",
    "scope": "global",
    "type": "preference",
    "content": {
        "key": "preferred_name",
        "value": "李四"
    },
    "confidence": 0.9,
    "superseded_by": null,
    "supersedes": "mem-xyz789",
    "version": 2,
    "is_active": true,
    "created_at": "2025-01-31T10:00:00Z",
    "updated_at": "2025-01-31T10:05:00Z",
    "superseded_at": null
}
```

## Conflict Detection

### When Does a Conflict Occur?

A conflict is detected when a new memory is inserted with:
- Same **scope** (e.g., "global")
- Same **type** (e.g., "preference")
- Same **key** in content (e.g., "preferred_name")
- Same **project_id** (or both null)

### Conflict Detection Query

```python
def _find_conflicting_memory(
    self,
    scope: str,
    mem_type: str,
    key: str,
    project_id: Optional[str],
    cursor
) -> Optional[dict]:
    """Find existing active memory with same (scope, type, key)."""

    query = """
        SELECT *
        FROM memory_items
        WHERE scope = ?
          AND type = ?
          AND json_extract(content, '$.key') = ?
          AND is_active = 1
    """
    params = [scope, mem_type, key]

    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    else:
        query += " AND project_id IS NULL"

    query += " ORDER BY created_at DESC LIMIT 1"

    cursor.execute(query, params)
    row = cursor.fetchone()

    return self._row_to_dict(row) if row else None
```

## Conflict Resolution Strategy

### Decision Algorithm

When a conflict is detected, the system uses the following strategy:

1. **Compare Confidence Scores**
   - Calculate difference: `abs(new_confidence - old_confidence)`

2. **Apply Decision Logic**
   - If confidence difference < 0.1: **Latest wins** (temporal precedence)
   - If confidence difference >= 0.1: **Higher confidence wins** (quality precedence)

### Example Scenarios

#### Scenario 1: Similar Confidence (Latest Wins)

```python
# First memory
mem1 = {
    "content": {"key": "preferred_name", "value": "张三"},
    "confidence": 0.9
}
# id1 = "mem-001", version = 1

# Second memory (similar confidence)
mem2 = {
    "content": {"key": "preferred_name", "value": "李四"},
    "confidence": 0.85  # diff = 0.05 < 0.1
}
# Latest wins!
# id2 = "mem-002", version = 2
# mem1.is_active = False, mem1.superseded_by = "mem-002"
```

#### Scenario 2: Higher Confidence Wins

```python
# First memory (high confidence)
mem1 = {
    "content": {"key": "preferred_name", "value": "张三"},
    "confidence": 0.95
}

# Second memory (low confidence)
mem2 = {
    "content": {"key": "preferred_name", "value": "李四"},
    "confidence": 0.6  # diff = 0.35 > 0.1
}
# Old memory wins!
# Returns id1 (existing memory retained)
```

## Version Chain Tracking

### Version Chain Example

```
v1: "张三" → v2: "李四" → v3: "王五"

mem-001:
  version: 1
  is_active: false
  superseded_by: mem-002
  supersedes: null

mem-002:
  version: 2
  is_active: false
  supersedes: mem-001
  superseded_by: mem-003

mem-003:
  version: 3
  is_active: true
  supersedes: mem-002
  superseded_by: null
```

### Retrieving Version History

```python
memory_service = MemoryService()
history = memory_service.get_version_history("mem-003")

# Returns:
# [
#   { "id": "mem-001", "version": 1, "value": "张三", ... },
#   { "id": "mem-002", "version": 2, "value": "李四", ... },
#   { "id": "mem-003", "version": 3, "value": "王五", ... }
# ]
```

## Query Behavior

### Active-Only Queries

By default, all queries return **only active memories**:

```python
# list() - only active by default
memories = memory_service.list(scope="global")
# Returns only memories where is_active = 1

# build_context() - only active
context = memory_service.build_context(
    project_id="proj-123",
    agent_type="planner"
)
# Context contains only active memories
```

### Including Inactive Memories

For audit/timeline views, use `include_inactive=True`:

```python
# Get all memories (including superseded)
all_memories = memory_service.list(
    scope="global",
    include_inactive=True
)
```

## API Endpoints

### GET /api/memory/{item_id}/history

Retrieve version history for a memory item.

**Request:**
```http
GET /api/memory/mem-abc123/history
```

**Response:**
```json
[
  {
    "id": "mem-001",
    "value": "张三",
    "version": 1,
    "is_active": false,
    "confidence": 0.9,
    "superseded_by": "mem-002",
    "created_at": "2025-01-31T10:00:00Z",
    "updated_at": "2025-01-31T10:00:00Z",
    "superseded_at": "2025-01-31T10:05:00Z"
  },
  {
    "id": "mem-002",
    "value": "李四",
    "version": 2,
    "is_active": true,
    "confidence": 0.9,
    "supersedes": "mem-001",
    "created_at": "2025-01-31T10:05:00Z",
    "updated_at": "2025-01-31T10:05:00Z"
  }
]
```

## UI Display

### Memory List View

The memory list now displays:
- **Last Updated** column (replaces "Created")
- **Version badge** for memories with version > 1
- Relative time format (e.g., "2m ago", "1h ago")

### Memory Detail View

Enhanced metadata section shows:
- **Last Updated**: Absolute and relative time
- **Version**: Badge showing version number (v2, v3, etc.)
- **Status**: "Superseded" badge for inactive memories
- **View History** button for versioned memories

### Version History View

Clicking "View History" shows:
- Chronological list of all versions
- Each version displays:
  - Version number and status (Active/Superseded)
  - Timestamp
  - Value at that version
  - Confidence score
  - When it was superseded (if applicable)

## Migration

### Applying the Migration

```bash
# Migration file: agentos/store/migrations/schema_v45_memory_conflict_resolution.sql

# The migration adds:
# - 5 new columns to memory_items table
# - 4 new indexes for conflict resolution queries
```

### Backward Compatibility

The implementation is backward compatible:
- Existing memories without conflict fields are treated as active (v1)
- Queries handle NULL values gracefully
- `is_active IS NULL OR is_active = 1` ensures existing records are included

## Testing

### Test Coverage

Comprehensive test suite in `tests/unit/core/memory/test_conflict_resolution.py`:

1. **No conflict scenarios**
   - Different keys: no conflict
   - Different scopes: no conflict
   - Different types: no conflict

2. **Conflict resolution**
   - Same key, similar confidence: latest wins
   - Same key, higher old confidence: old wins
   - Same key, higher new confidence: new wins

3. **Version chain tracking**
   - Multiple versions tracked correctly
   - Superseded chain follows correctly
   - History retrieval works from any point in chain

4. **Query filtering**
   - `list()` returns only active by default
   - `build_context()` excludes superseded memories
   - `include_inactive=True` returns all

### Running Tests

```bash
python3 -m pytest tests/unit/core/memory/test_conflict_resolution.py -v
```

All 11 tests pass successfully.

## Benefits

### For Users
- System remembers that they changed their mind
- Always uses the latest preference
- Can view history if needed for audit

### For System
- Clean conflict resolution without data loss
- Audit trail for all changes
- Prevents confusion from stale data

### For Developers
- Clear API for conflict detection
- Versioning metadata for debugging
- Backward compatible implementation

## Future Enhancements

Potential future improvements:

1. **Merge strategies**: Allow different merge strategies (e.g., merge tags, combine sources)
2. **Confidence decay**: Reduce confidence of old memories over time
3. **User confirmation**: Ask user before superseding high-confidence memories
4. **Bulk conflict resolution**: Handle multiple conflicts in one operation
5. **Conflict analytics**: Track how often conflicts occur and resolution patterns

## Conclusion

The Memory Conflict Resolution system transforms AgentOS Memory from a simple key-value store into a **professionally managed system** that:

- Handles real-world scenarios (users changing their mind)
- Maintains audit trails for compliance
- Always uses current values for consistency
- Provides rich version history for debugging

This implementation demonstrates the "认真管理的系统" (seriously managed system) philosophy of AgentOS.
