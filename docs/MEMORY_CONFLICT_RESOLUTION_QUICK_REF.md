# Memory Conflict Resolution - Quick Reference

**Task #12: 实现Memory冲突解决策略**

## Quick Start

### Check if Migration is Applied

```bash
sqlite3 ~/.agentos/store.db "SELECT version FROM schema_version WHERE version = '0.45.0';"
```

### Apply Migration (if needed)

```bash
sqlite3 ~/.agentos/store.db < agentos/store/migrations/schema_v45_memory_conflict_resolution.sql
```

## API Usage

### Basic Upsert (with Conflict Resolution)

```python
from agentos.core.memory.service import MemoryService

memory_service = MemoryService()

# First preference
memory_service.upsert({
    "scope": "global",
    "type": "preference",
    "content": {
        "key": "preferred_name",
        "value": "张三"
    },
    "confidence": 0.9
})

# Updated preference (conflicts with above)
memory_service.upsert({
    "scope": "global",
    "type": "preference",
    "content": {
        "key": "preferred_name",
        "value": "李四"  # New value supersedes old
    },
    "confidence": 0.9
})
# Result: "张三" marked as superseded, "李四" is now active
```

### Retrieve Active Memories Only

```python
# Default behavior: only active memories
active_memories = memory_service.list(scope="global")

# Build context (only active)
context = memory_service.build_context(
    project_id="proj-123",
    agent_type="planner"
)
```

### Retrieve All Memories (Including Superseded)

```python
# For audit/timeline views
all_memories = memory_service.list(
    scope="global",
    include_inactive=True
)
```

### Get Version History

```python
# Get full version chain
history = memory_service.get_version_history("mem-abc123")

for version in history:
    print(f"v{version['version']}: {version['content']['value']} "
          f"(active={version['is_active']})")
```

## Conflict Resolution Logic

### Decision Tree

```
New memory conflicts with existing?
├─ No → Insert normally
└─ Yes → Check confidence difference
    ├─ diff < 0.1 → Latest wins (temporal precedence)
    │   ├─ Mark old as superseded
    │   ├─ Insert new with version = old.version + 1
    │   └─ Link chain (new.supersedes = old.id)
    └─ diff >= 0.1 → Higher confidence wins
        ├─ New higher → Insert new (supersede old)
        └─ Old higher → Keep old (return old.id)
```

### Examples

| Old Conf | New Conf | Diff  | Winner | Reason              |
|----------|----------|-------|--------|---------------------|
| 0.9      | 0.85     | 0.05  | New    | Similar, latest wins |
| 0.95     | 0.6      | 0.35  | Old    | Old much higher     |
| 0.6      | 0.95     | 0.35  | New    | New much higher     |
| 0.8      | 0.8      | 0.0   | New    | Equal, latest wins  |

## Database Schema

### New Fields in `memory_items`

```sql
ALTER TABLE memory_items ADD COLUMN superseded_by TEXT DEFAULT NULL;
ALTER TABLE memory_items ADD COLUMN supersedes TEXT DEFAULT NULL;
ALTER TABLE memory_items ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE memory_items ADD COLUMN is_active INTEGER DEFAULT 1;
ALTER TABLE memory_items ADD COLUMN superseded_at TEXT DEFAULT NULL;
```

### Key Indexes

```sql
-- Fast active-only queries
CREATE INDEX idx_memory_is_active
    ON memory_items(is_active, scope, type);

-- Fast conflict detection
CREATE INDEX idx_memory_conflict_detection
    ON memory_items(scope, type, is_active, json_extract(content, '$.key'));
```

## REST API

### GET /api/memory/{id}/history

```bash
curl http://localhost:8000/api/memory/mem-abc123/history
```

**Response:**
```json
[
  {
    "id": "mem-001",
    "value": "张三",
    "version": 1,
    "is_active": false,
    "superseded_by": "mem-002",
    "superseded_at": "2025-01-31T10:05:00Z"
  },
  {
    "id": "mem-002",
    "value": "李四",
    "version": 2,
    "is_active": true,
    "supersedes": "mem-001"
  }
]
```

## UI Features

### Memory List View
- Shows "Last Updated" with relative time
- Version badge (v2, v3, etc.) for updated memories
- Filters superseded memories by default

### Memory Detail View
- Displays version number
- Shows "Superseded" status if inactive
- "View History" button for versioned memories

### Version History View
- Timeline of all versions
- Visual indicators for active/superseded
- Confidence scores for each version

## Testing

### Run Tests

```bash
python3 -m pytest tests/unit/core/memory/test_conflict_resolution.py -v
```

### Test Coverage

- ✓ No conflict when different key/scope/type
- ✓ Latest wins with similar confidence
- ✓ Higher confidence wins
- ✓ Version chain tracking
- ✓ Active-only queries
- ✓ Version history retrieval

## Troubleshooting

### Issue: Migration not applied

**Symptom:** Column 'version' not found

**Solution:**
```bash
sqlite3 ~/.agentos/store.db < agentos/store/migrations/schema_v45_memory_conflict_resolution.sql
```

### Issue: Old memories still showing up

**Check:** Make sure you're not using `include_inactive=True`

```python
# Wrong (includes superseded)
memories = service.list(scope="global", include_inactive=True)

# Correct (active only)
memories = service.list(scope="global")
```

### Issue: Version history empty

**Check:** Memory must have conflict resolution fields

```python
memory = service.get("mem-123")
print(memory.get("version"))  # Should be >= 1
print(memory.get("supersedes"))  # Check for version chain
```

## Best Practices

### 1. Always Use Keys for Conflictable Data

```python
# Good: Uses key for conflict detection
{
    "content": {
        "key": "preferred_name",
        "value": "张三"
    }
}

# Bad: No key, won't trigger conflict resolution
{
    "content": {
        "summary": "User prefers 张三"
    }
}
```

### 2. Set Appropriate Confidence

```python
# User explicit input: high confidence
memory_service.upsert({
    "content": {"key": "name", "value": "李四"},
    "confidence": 0.95
})

# Inferred from behavior: medium confidence
memory_service.upsert({
    "content": {"key": "name", "value": "王五"},
    "confidence": 0.7
})
```

### 3. Use Scopes Appropriately

```python
# Global preference (across all projects)
{"scope": "global", "content": {"key": "language", "value": "中文"}}

# Project-specific (won't conflict with global)
{"scope": "project", "project_id": "proj-123",
 "content": {"key": "language", "value": "English"}}
```

## See Also

- [Full Documentation](./MEMORY_CONFLICT_RESOLUTION.md)
- [Memory Service API](../agentos/core/memory/service.py)
- [Test Suite](../tests/unit/core/memory/test_conflict_resolution.py)
- [Migration SQL](../agentos/store/migrations/schema_v45_memory_conflict_resolution.sql)
