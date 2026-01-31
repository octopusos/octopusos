# Epoch Millisecond Timestamps - Usage Guide

Part of Time & Timestamp Contract (ADR-011)

---

## Quick Start

### Import Utilities

```python
from agentos.store.timestamp_utils import (
    now_ms,
    to_epoch_ms,
    from_epoch_ms,
    format_timestamp,
    time_ago,
)
```

---

## Common Patterns

### 1. Creating New Records

**Always use `now_ms()` for current timestamp**:

```python
from agentos.store.timestamp_utils import now_ms

# Creating a new chat session
conn.execute(
    """
    INSERT INTO chat_sessions (
        session_id,
        title,
        created_at_ms,
        updated_at_ms
    ) VALUES (?, ?, ?, ?)
    """,
    (session_id, title, now_ms(), now_ms())
)
```

### 2. Updating Records

```python
from agentos.store.timestamp_utils import now_ms

# Updating a task
conn.execute(
    "UPDATE tasks SET status = ?, updated_at_ms = ? WHERE task_id = ?",
    (new_status, now_ms(), task_id)
)
```

### 3. Querying Recent Records

```python
from agentos.store.timestamp_utils import now_ms

# Get sessions from last hour
one_hour_ago = now_ms() - 3600 * 1000

cursor.execute(
    """
    SELECT * FROM chat_sessions
    WHERE created_at_ms > ?
    ORDER BY created_at_ms DESC
    """,
    (one_hour_ago,)
)
```

### 4. Date Range Queries

```python
from agentos.store.timestamp_utils import to_epoch_ms

# Query tasks created between two dates
start_date = to_epoch_ms("2024-01-01T00:00:00Z")
end_date = to_epoch_ms("2024-02-01T00:00:00Z")

cursor.execute(
    """
    SELECT * FROM tasks
    WHERE created_at_ms BETWEEN ? AND ?
    ORDER BY created_at_ms ASC
    """,
    (start_date, end_date)
)
```

### 5. Display Formatting

```python
from agentos.store.timestamp_utils import format_timestamp, time_ago

# Format for display
for row in results:
    session_id = row['session_id']
    created_ms = row['created_at_ms']

    # Absolute time
    print(f"Session {session_id}")
    print(f"  Created: {format_timestamp(created_ms)}")

    # Relative time
    print(f"  ({time_ago(created_ms)})")
```

Output:
```
Session session_abc123
  Created: 2024-01-15 12:00:00 UTC
  (2 hours ago)
```

### 6. Custom Formatting

```python
from agentos.store.timestamp_utils import format_timestamp

# Different formats
timestamp = 1705320000000

format_timestamp(timestamp, fmt="%Y-%m-%d")           # "2024-01-15"
format_timestamp(timestamp, fmt="%H:%M:%S")           # "12:00:00"
format_timestamp(timestamp, fmt="%B %d, %Y")          # "January 15, 2024"
format_timestamp(timestamp, fmt="%Y-%m-%d %H:%M:%S")  # "2024-01-15 12:00:00"
```

### 7. Converting User Input

```python
from agentos.store.timestamp_utils import to_epoch_ms

# From ISO string
user_input = "2024-01-15T12:00:00Z"
epoch_ms = to_epoch_ms(user_input)

# From datetime object
from datetime import datetime, timezone
dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
epoch_ms = to_epoch_ms(dt)

# Store in database
conn.execute(
    "INSERT INTO tasks (task_id, created_at_ms) VALUES (?, ?)",
    (task_id, epoch_ms)
)
```

### 8. Checking Recency

```python
from agentos.store.timestamp_utils import is_recent

# Check if session is active (within last 5 minutes)
if is_recent(session['updated_at_ms'], seconds_ago=300):
    print("Session is active")
else:
    print("Session is stale")
```

---

## Migration from Old Code

### Before (using TIMESTAMP)

```python
# OLD: Using SQLite TIMESTAMP
conn.execute(
    """
    INSERT INTO chat_sessions (session_id, created_at)
    VALUES (?, CURRENT_TIMESTAMP)
    """,
    (session_id,)
)

# OLD: Querying with date string
cursor.execute(
    "SELECT * FROM chat_sessions WHERE created_at > '2024-01-01'",
)
```

### After (using epoch_ms)

```python
# NEW: Using epoch_ms
from agentos.store.timestamp_utils import now_ms, to_epoch_ms

conn.execute(
    """
    INSERT INTO chat_sessions (session_id, created_at_ms)
    VALUES (?, ?)
    """,
    (session_id, now_ms())
)

# NEW: Querying with epoch_ms
cursor.execute(
    """
    SELECT * FROM chat_sessions
    WHERE created_at_ms > ?
    """,
    (to_epoch_ms("2024-01-01T00:00:00Z"),)
)
```

---

## Best Practices

### ✅ DO

- Use `now_ms()` for current timestamps
- Store all timestamps as epoch_ms (INTEGER)
- Use `to_epoch_ms()` to convert user input
- Use `format_timestamp()` for display
- Query with epoch_ms fields for performance

### ❌ DON'T

- Don't use `CURRENT_TIMESTAMP` in SQL
- Don't store timestamps as strings
- Don't do arithmetic on TIMESTAMP strings
- Don't compare TIMESTAMP across timezones
- Don't use old `created_at` fields in new code

---

## Performance Tips

### 1. Use Indexes

The migration creates indexes on all `*_at_ms` fields:

```sql
-- These indexes are already created by migration
CREATE INDEX idx_chat_sessions_created_at_ms ON chat_sessions(created_at_ms DESC);
CREATE INDEX idx_tasks_created_at_ms ON tasks(created_at_ms DESC);
```

### 2. Range Queries

```python
# Efficient: Uses index
cursor.execute(
    "SELECT * FROM tasks WHERE created_at_ms > ? ORDER BY created_at_ms DESC",
    (threshold,)
)

# Inefficient: Converts every row
cursor.execute(
    "SELECT * FROM tasks WHERE datetime(created_at) > '2024-01-01'"
)
```

### 3. Pagination

```python
# Efficient pagination using epoch_ms
def get_tasks_page(after_ms=None, limit=50):
    if after_ms:
        cursor.execute(
            """
            SELECT * FROM tasks
            WHERE created_at_ms > ?
            ORDER BY created_at_ms DESC
            LIMIT ?
            """,
            (after_ms, limit)
        )
    else:
        cursor.execute(
            """
            SELECT * FROM tasks
            ORDER BY created_at_ms DESC
            LIMIT ?
            """,
            (limit,)
        )
    return cursor.fetchall()
```

---

## Timezone Handling

### Why Epoch Milliseconds?

Epoch milliseconds are **always UTC** and **timezone-independent**:

```python
# Same epoch_ms value worldwide
epoch_ms = 1705320000000

# Display in different timezones
from datetime import timezone, timedelta
from agentos.store.timestamp_utils import from_epoch_ms

# UTC
dt_utc = from_epoch_ms(epoch_ms, tz=timezone.utc)
print(dt_utc)  # 2024-01-15 12:00:00+00:00

# PST (UTC-8)
pst = timezone(timedelta(hours=-8))
dt_pst = from_epoch_ms(epoch_ms, tz=pst)
print(dt_pst)  # 2024-01-15 04:00:00-08:00

# JST (UTC+9)
jst = timezone(timedelta(hours=9))
dt_jst = from_epoch_ms(epoch_ms, tz=jst)
print(dt_jst)  # 2024-01-15 21:00:00+09:00
```

### User Timezone Display

```python
from agentos.store.timestamp_utils import from_epoch_ms
from datetime import timezone, timedelta

def display_in_user_timezone(epoch_ms, user_tz_offset):
    """
    Display timestamp in user's timezone

    Args:
        epoch_ms: Epoch milliseconds (UTC)
        user_tz_offset: Timezone offset in hours (e.g., -8 for PST)
    """
    user_tz = timezone(timedelta(hours=user_tz_offset))
    dt = from_epoch_ms(epoch_ms, tz=user_tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

# Example
created_ms = 1705320000000
print(display_in_user_timezone(created_ms, -8))  # PST
print(display_in_user_timezone(created_ms, 9))   # JST
```

---

## Validation

### Range Validation

```python
from agentos.store.timestamp_utils import validate_epoch_ms

# Validate timestamp is reasonable
epoch_ms = user_input_timestamp

if not validate_epoch_ms(epoch_ms):
    raise ValueError(f"Invalid timestamp: {epoch_ms} (outside 2020-2030 range)")
```

### NULL Handling

```python
from agentos.store.timestamp_utils import format_timestamp

# Safe handling of NULL timestamps
created_ms = row.get('created_at_ms')

# format_timestamp returns "" for None
display_time = format_timestamp(created_ms) or "Never"
```

---

## API Response Examples

### REST API Response

```python
from agentos.store.timestamp_utils import format_timestamp

def serialize_task(task_row):
    """Serialize task for API response"""
    return {
        "task_id": task_row['task_id'],
        "title": task_row['title'],
        "status": task_row['status'],
        "created_at": task_row['created_at_ms'],  # Raw epoch_ms
        "created_at_iso": format_timestamp(
            task_row['created_at_ms'],
            fmt="%Y-%m-%dT%H:%M:%SZ"
        ),  # ISO 8601
        "updated_at": task_row['updated_at_ms'],
    }
```

Response:
```json
{
  "task_id": "task_abc123",
  "title": "Fix authentication bug",
  "status": "completed",
  "created_at": 1705320000000,
  "created_at_iso": "2024-01-15T12:00:00Z",
  "updated_at": 1705323600000
}
```

---

## Testing

### Test Timestamp Operations

```python
from agentos.store.timestamp_utils import now_ms, to_epoch_ms

def test_create_session():
    """Test creating session with epoch_ms timestamp"""
    session_id = "test_session"
    created_ms = now_ms()

    # Insert
    conn.execute(
        "INSERT INTO chat_sessions (session_id, created_at_ms) VALUES (?, ?)",
        (session_id, created_ms)
    )

    # Verify
    cursor = conn.execute(
        "SELECT created_at_ms FROM chat_sessions WHERE session_id = ?",
        (session_id,)
    )
    row = cursor.fetchone()

    assert row['created_at_ms'] == created_ms
```

---

## Troubleshooting

### Problem: Timestamps appear as large integers

**Solution**: Use `format_timestamp()` for display:

```python
# Wrong
print(f"Created: {row['created_at_ms']}")
# Output: Created: 1705320000000

# Right
from agentos.store.timestamp_utils import format_timestamp
print(f"Created: {format_timestamp(row['created_at_ms'])}")
# Output: Created: 2024-01-15 12:00:00 UTC
```

### Problem: Timezone confusion

**Solution**: Epoch milliseconds are always UTC. Convert only for display:

```python
from agentos.store.timestamp_utils import now_ms, from_epoch_ms
from datetime import timezone, timedelta

# Store: Always UTC (epoch_ms)
created_ms = now_ms()
conn.execute("INSERT INTO tasks (task_id, created_at_ms) VALUES (?, ?)",
             (task_id, created_ms))

# Display: Convert to user timezone
user_tz = timezone(timedelta(hours=-8))  # PST
dt = from_epoch_ms(created_ms, tz=user_tz)
print(dt.strftime("%Y-%m-%d %H:%M:%S %Z"))
```

### Problem: Migration didn't run

**Solution**: Check schema version and run migration:

```python
from agentos.store.migrator import Migrator
from pathlib import Path

db_path = Path("store/registry.sqlite")
migrations_dir = Path("agentos/store/migrations")

migrator = Migrator(db_path, migrations_dir)
status = migrator.status()

print(f"Current version: v{status['current_version']:02d}")
print(f"Pending migrations: {status['pending_count']}")

if status['pending_count'] > 0:
    migrator.migrate()
```

---

## Additional Resources

- **Migration Report**: `/docs/TASK_7_MIGRATION_REPORT.md`
- **Test Examples**: `/tests/unit/store/test_timestamp_utils.py`
- **Migration Script**: `/agentos/store/migrations/schema_v44_epoch_ms_timestamps.sql`
- **Utility Module**: `/agentos/store/timestamp_utils.py`

---

**Version**: 1.0
**Last Updated**: 2026-01-31
**Part of**: Time & Timestamp Contract (ADR-011)
