# ADR-011: Time & Timestamp Contract

## Status
**Accepted** | Implemented

**Date**: 2026-01-31
**Authors**: AgentOS Team
**Semantic Freeze**: YES - This is a system-wide contract

## Context

AgentOS as an Agent Operating System needs to handle numerous timestamps across its components:
- Chat session creation/update times
- Message send times
- Task execution times
- Audit log timestamps
- Governance decision timestamps
- Token usage tracking timestamps

### Historical Problems

Before implementing this ADR, the system experienced several timezone-related issues:

1. **Timezone Information Loss**
   - Database stored SQLite `CURRENT_TIMESTAMP` returning `YYYY-MM-DD HH:MM:SS` (no timezone marker)
   - Python used `datetime.fromisoformat()` creating naive datetime objects
   - API returned `.isoformat()` without `Z` suffix

2. **Frontend Timezone Confusion**
   - JavaScript `new Date("2026-01-31T12:34:56")` was interpreted as **local timezone**
   - Cross-timezone users saw incorrect times
   - Time sorting and comparison became problematic

3. **Python 3.12+ Compatibility**
   - `datetime.utcnow()` was deprecated (DeprecationWarning)
   - Code mixed usage of `datetime.now()` and `datetime.utcnow()`

4. **Data Consistency Risks**
   - Unable to accurately compare timestamps from different sources
   - Event ordering could be incorrect
   - Cross-server time synchronization difficulties

### Business Impact

- **User Experience**: Cross-timezone users saw incorrect time displays
- **Data Integrity**: Audit log timestamps were unreliable
- **System Maintainability**: Timezone bugs were difficult to diagnose and fix

## Decision

AgentOS adopts the following **Time & Timestamp Contract**:

### Core Principles (MUST)

#### 1. System Internal Time Always Uses Aware UTC

```python
# ✅ Correct
from agentos.core.time import utc_now
from datetime import timezone

now = utc_now()  # aware UTC datetime
# or
now = datetime.now(timezone.utc)  # aware UTC datetime

# ❌ Forbidden
now = datetime.now()  # naive datetime
now = datetime.utcnow()  # naive datetime (and deprecated)
```

**Rationale**:
- Naive datetime has no timezone information, easily misinterpreted as local time
- Aware UTC eliminates ambiguity - all systems correctly understand it
- UTC is the international standard, suitable for distributed systems

#### 2. API Transport Always Uses ISO 8601 UTC with Z

```python
# ✅ Correct
from agentos.webui.api.time_format import iso_z

api_response = {
    "created_at": iso_z(session.created_at)  # "2026-01-31T12:34:56.789012Z"
}

# ❌ Forbidden
api_response = {
    "created_at": session.created_at.isoformat()  # May lack Z suffix
}
```

**Rationale**:
- Z suffix explicitly identifies UTC timezone
- Frontend can parse correctly without misinterpreting as local time
- Complies with RFC 3339 standard

#### 3. Database Storage Uses Epoch Milliseconds

```sql
-- ✅ Recommended (new tables)
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at_ms INTEGER,  -- epoch milliseconds
    updated_at_ms INTEGER
);

-- ⚠️ Compatible (old tables)
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP,      -- preserve backward compatibility
    created_at_ms INTEGER      -- new field
);
```

**Rationale**:
- Epoch milliseconds are integers, no timezone ambiguity
- Cross-database, cross-language portable
- Good sorting and comparison performance
- Sufficient precision (millisecond level)

#### 4. Frontend Display Converts to User Local Timezone

```javascript
// ✅ Correct
const isoString = "2026-01-31T12:34:56.789Z";  // Receive from API
const date = new Date(isoString);  // Auto-convert to local timezone
const display = date.toLocaleString();  // Display localized time

// ❌ Forbidden
const naiveString = "2026-01-31T12:34:56";  // No Z
const date = new Date(naiveString);  // Ambiguous!
```

**Rationale**:
- Users expect to see times in their own timezone
- Browser automatically handles timezone conversion
- Prerequisite is backend must provide explicit UTC time

### Implementation Requirements

#### Python Code Standards

```python
# Time retrieval
from agentos.core.time import utc_now, utc_now_ms, utc_now_iso

now = utc_now()           # datetime (aware UTC)
timestamp = utc_now_ms()  # int (epoch milliseconds)
iso_str = utc_now_iso()   # str (ISO 8601 with Z)

# Time conversion
from agentos.webui.api.time_format import iso_z, ensure_utc, parse_db_time

api_time = iso_z(dt)                  # datetime → ISO Z
utc_dt = ensure_utc(dt)               # any dt → aware UTC
db_dt = parse_db_time(db_value)       # database value → aware UTC

# Database operations
from agentos.store.timestamp_utils import now_ms, from_epoch_ms, to_epoch_ms

# Write
conn.execute("INSERT INTO sessions (created_at_ms) VALUES (?)", (now_ms(),))

# Read
row = conn.execute("SELECT created_at_ms FROM sessions").fetchone()
dt = from_epoch_ms(row["created_at_ms"])
```

#### API Response Format

All time fields in API responses must:
- Format: `YYYY-MM-DDTHH:MM:SS.ffffffZ`
- Timezone: UTC (Z suffix)
- Precision: Microseconds (6 decimal places)

```json
{
  "session_id": "abc123",
  "created_at": "2026-01-31T12:34:56.789012Z",
  "updated_at": "2026-01-31T12:35:00.123456Z"
}
```

#### Database Schema

**New Tables** (recommended):
```sql
CREATE TABLE new_table (
    id TEXT PRIMARY KEY,
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    INDEX idx_created (created_at_ms DESC)
);
```

**Old Table Migration** (dual-write strategy):
```sql
-- Add new field
ALTER TABLE old_table ADD COLUMN created_at_ms INTEGER;

-- Migrate existing data
UPDATE old_table
SET created_at_ms = CAST((julianday(created_at) - 2440587.5) * 86400000 AS INTEGER)
WHERE created_at_ms IS NULL;

-- Create index
CREATE INDEX idx_created_ms ON old_table(created_at_ms DESC);
```

**Python Dual Write**:
```python
@dataclass
class Session:
    created_at: datetime
    created_at_ms: Optional[int] = None

    @classmethod
    def from_db_row(cls, row):
        # Prioritize reading _ms
        if row.get("created_at_ms"):
            created_at = from_epoch_ms(row["created_at_ms"])
        else:
            created_at = parse_db_time(row["created_at"])

        return cls(created_at=created_at, created_at_ms=to_epoch_ms(created_at))

    def to_db_dict(self):
        # Dual write
        return {
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "created_at_ms": self.created_at_ms or to_epoch_ms(self.created_at)
        }
```

#### JavaScript Frontend Code

```javascript
// Send to backend: Use UTC
const timestamp = new Date().toISOString();  // "2026-01-31T12:34:56.789Z"

// Receive and display: Auto-convert to local
function formatTimestamp(isoString) {
    const date = new Date(isoString);  // Auto-parse Z as UTC
    return date.toLocaleString();  // Display localized time
}

// Relative time
function timeAgo(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    // ... other logic
}
```

### Enforcement Mechanisms

#### 1. CI/CD Gate

```bash
# scripts/check_datetime_usage.sh
#!/bin/bash
# Check forbidden datetime API usage

# Forbid datetime.utcnow()
if rg "datetime\.utcnow\(\)" --type py agentos/; then
    echo "ERROR: datetime.utcnow() is forbidden"
    exit 1
fi

# Forbid datetime.now() without timezone
if rg "datetime\.now\(\)" --type py agentos/ | grep -v "timezone"; then
    echo "ERROR: datetime.now() without timezone is forbidden"
    exit 1
fi
```

#### 2. Unit Tests

```python
# tests/unit/test_time_contract.py

def test_no_naive_datetime_in_models():
    """Ensure all models return aware datetime"""
    session = ChatSession.from_db_row(mock_row)
    assert session.created_at.tzinfo == timezone.utc

def test_api_responses_have_z_suffix():
    """Ensure all API responses have Z suffix"""
    response = client.get("/api/sessions")
    for session in response.json():
        assert session["created_at"].endswith("Z")
```

#### 3. Code Review Checklist

When reviewing PRs, must check:
- [ ] New time fields use `*_at_ms` naming
- [ ] API responses use `iso_z()` serialization
- [ ] Database reads use `parse_db_time()` or `from_epoch_ms()`
- [ ] New code uses `utc_now()` instead of `datetime.now()`

## Consequences

### Positive ✅

1. **Clear Timezone Semantics**
   - All times are UTC, no ambiguity
   - Consistent cross-timezone user experience

2. **Data Consistency**
   - Timestamps can be accurately compared
   - Event ordering is correct
   - Audit logs are reliable

3. **Python 3.12+ Compatibility**
   - Avoid DeprecationWarning
   - Use best practice APIs

4. **Frontend Friendly**
   - Z suffix allows JavaScript to parse correctly
   - Auto-localized display

5. **Performance Optimization**
   - Epoch milliseconds sort quickly
   - Integer comparison is efficient
   - Good index performance

6. **Improved Maintainability**
   - Unified time handling entry points
   - Reduced timezone-related bugs
   - Easier code reviews

### Negative ⚠️

1. **Migration Cost**
   - Need to migrate old database tables (mitigated through dual-write)
   - Developers need to learn new APIs
   - Initial team education required

2. **Storage Overhead**
   - Dual-write period has duplicate fields (acceptable)
   - Epoch milliseconds less intuitive than TIMESTAMP (but more reliable)

3. **Serialization Overhead**
   - `iso_z()` slightly slower than `.isoformat()` (millisecond level, negligible)

4. **Backward Compatibility**
   - Old code may need updates (automated through tooling scripts)

### Mitigation Strategies

1. **Progressive Migration**
   - P0: API layer fixes (immediate effect)
   - P1: Database dual-write (smooth transition)
   - P2: Global standardization (long-term)

2. **Tooling Support**
   - `agentos.core.time` module: unified entry point
   - `timestamp_utils.py`: database utilities
   - `time_format.py`: API utilities
   - Automation scripts: batch replacement

3. **Complete Documentation**
   - ADR explaining rationale and solution
   - Usage guide and examples
   - FAQ

4. **CI Enforcement**
   - Auto-check forbidden patterns
   - PR comment prompts
   - Test coverage of contract

## Implementation Status

### Completed ✅

- [x] P0-Task #1: Enhanced time_format.py hard contract functions
- [x] P0-Task #2: Unified all API returns to use iso_z()
- [x] P0-Task #3: Fixed models_base.py DB reads
- [x] P0-Task #4: Added API time format integration tests
- [x] P0-Task #5: Replaced datetime.utcnow()
- [x] P0-Task #6: Replaced datetime.now() calls without timezone
- [x] P1-Task #7: Added epoch_ms fields to DB schema
- [x] P1-Task #8: Implemented dual-write logic
- [x] P1-Task #9: Added lazy migration logic
- [x] P2-Task #10: Created unified clock module
- [x] P2-Task #11: Global replacement to clock.utc_now()
- [x] P2-Task #12: Added CI gate
- [x] P2-Task #13: Wrote this ADR
- [x] P2-Task #14: Frontend defensive checks

### Metrics

- **Files Modified**: 180+ files
- **Code Replacements**: 700+ locations
- **New Tests**: 100+ test cases
- **Test Pass Rate**: 100%
- **Modules Covered**: Core, WebUI API, Store, CLI

## References

### Standards

- [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339.html) - Date and Time on the Internet: Timestamps
- [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) - Data elements and interchange formats
- [PEP 615](https://peps.python.org/pep-0615/) - Support for the IANA Time Zone Database in the Standard Library

### Internal Documentation

- [Time Format Module](../../agentos/webui/api/time_format.py) - API time formatting utilities
- [Clock Module](../../agentos/core/time/clock.py) - Unified clock module
- [Timestamp Utils](../../agentos/store/timestamp_utils.py) - Database timestamp utilities
- [Usage Guide](../EPOCH_MS_USAGE_GUIDE.md) - Epoch milliseconds usage guide
- [Development Guide](../DEVELOPMENT.md) - Development standards

### Migration Reports

- [Task #7 Migration Report](../TASK_7_MIGRATION_REPORT.md) - DB schema migration
- [Task #11 Completion Report](../../TASK_11_COMPLETION_REPORT.md) - Global replacement report

### Python datetime Best Practices

- [Python datetime documentation](https://docs.python.org/3/library/datetime.html)
- [Real Python: Using Python datetime](https://realpython.com/python-datetime/)
- [Python 3.12 Migration Guide](https://docs.python.org/3/whatsnew/3.12.html#deprecated)

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-31 | AgentOS Team | Initial version |

---

**Semantic Freeze Notice**: This ADR defines a system-wide contract. Any changes require team consensus and must be documented as a new ADR revision.
