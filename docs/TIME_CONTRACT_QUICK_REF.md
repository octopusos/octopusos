# Time & Timestamp Contract - Quick Reference

## Quick Rules

### DO ✅

```python
# Get current time
from agentos.core.time import utc_now
now = utc_now()

# API serialization
from agentos.webui.api.time_format import iso_z
response = {"created_at": iso_z(dt)}

# Database read
from agentos.webui.api.time_format import parse_db_time
dt = parse_db_time(row["created_at"])

# Database write (epoch ms)
from agentos.store.timestamp_utils import now_ms
conn.execute("INSERT ... VALUES (?)", (now_ms(),))
```

### DON'T ❌

```python
# ❌ Deprecated
from datetime import datetime
now = datetime.utcnow()

# ❌ Naive datetime
now = datetime.now()

# ❌ API return without Z
response = {"created_at": dt.isoformat()}
```

## Contract Summary

| Layer | Standard | Format |
|-------|----------|--------|
| **Python Internal** | Aware UTC datetime | `datetime.now(timezone.utc)` |
| **API Transport** | ISO 8601 with Z | `"2026-01-31T12:34:56.789012Z"` |
| **Database Storage** | Epoch milliseconds | `1738329296789` (INTEGER) |
| **Frontend Display** | User local timezone | Auto-converted by browser |

## Common Patterns

### 1. Creating Records

```python
from agentos.store.timestamp_utils import now_ms

conn.execute(
    "INSERT INTO sessions (session_id, created_at_ms) VALUES (?, ?)",
    (session_id, now_ms())
)
```

### 2. API Response

```python
from agentos.webui.api.time_format import iso_z

return {
    "session_id": session.id,
    "created_at": iso_z(session.created_at),
    "updated_at": iso_z(session.updated_at)
}
```

### 3. Querying Recent Records

```python
from agentos.store.timestamp_utils import now_ms

# Last hour
one_hour_ago = now_ms() - 3600 * 1000
cursor.execute(
    "SELECT * FROM sessions WHERE created_at_ms > ?",
    (one_hour_ago,)
)
```

### 4. Frontend Display

```javascript
// Receive from API
const isoString = "2026-01-31T12:34:56.789Z";

// Parse and display
const date = new Date(isoString);  // Auto-parse UTC
const display = date.toLocaleString();  // User's timezone

// Relative time
function timeAgo(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}
```

## Key Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `agentos.core.time.clock` | Unified time entry point | `utc_now()`, `utc_now_ms()`, `utc_now_iso()` |
| `agentos.webui.api.time_format` | API time formatting | `iso_z()`, `ensure_utc()`, `parse_db_time()` |
| `agentos.store.timestamp_utils` | Database utilities | `now_ms()`, `from_epoch_ms()`, `to_epoch_ms()` |

## See Also

- [Full ADR](adr/ADR-011-time-timestamp-contract.md) - Complete architecture decision record
- [Usage Guide](EPOCH_MS_USAGE_GUIDE.md) - Detailed usage examples
- [Clock Module](../agentos/core/time/clock.py) - Source code
- [Time Format Module](../agentos/webui/api/time_format.py) - Source code
