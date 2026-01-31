# Extension Registry Database Initialization Fix

**Date**: 2026-01-30
**Issue**: Extension Registry database initialization failure
**Status**: ✅ FIXED

---

## Problem Description

### User-Reported Issue

When users uploaded extensions via the WebUI:

1. User uploads `postman-extension.zip` in the WebUI
2. Backend creates an install tracking record
3. Frontend polls `GET /api/extensions/install/{install_id}`
4. **Error**: API returns 404 - install record not found

### Root Cause Analysis

The `ExtensionRegistry` class was instantiating without ensuring database migrations:

```python
# agentos/core/extensions/registry.py (BEFORE FIX)
def __init__(self, db_path: Optional[Path] = None):
    if db_path is None:
        from agentos.store import get_db_path
        db_path = get_db_path()

    self.db_path = db_path

def _get_connection(self) -> sqlite3.Connection:
    conn = sqlite3.connect(str(self.db_path))  # ❌ Direct connection
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
```

**Problem**:
- The registry directly connected to SQLite without triggering migrations
- The `extension_installs` table (defined in `schema_v33.sql`) was never created
- Queries to `extension_installs` failed with "no such table"
- API returned 404 because the query returned no results

---

## Solution Implemented

### Code Changes

Modified `agentos/core/extensions/registry.py` lines 28-48:

```python
def __init__(self, db_path: Optional[Path] = None):
    """
    Initialize registry

    Args:
        db_path: Database file path (optional, defaults to AgentOS registry)
    """
    if db_path is None:
        from agentos.store import get_db_path, ensure_migrations
        db_path = get_db_path()

        # Ensure database schema is up-to-date
        # This is critical for extension tables (extensions, extension_installs, extension_configs)
        # These tables are defined in schema_v33.sql
        try:
            ensure_migrations(db_path)
        except Exception as e:
            logger.warning(f"Failed to ensure migrations: {e}")
            # Don't block initialization, but log the issue

    self.db_path = db_path
```

### Key Design Decisions

1. **Only trigger migrations for default db_path**: When users provide a custom `db_path` (e.g., in tests), migrations are not automatically triggered. This preserves test isolation.

2. **Fail gracefully**: If migrations fail, log a warning but don't block initialization. This prevents cascading failures.

3. **Import locally**: Import `ensure_migrations` inside the `if` block to avoid circular dependencies.

---

## Verification

### Test 1: Default Database Path

```bash
python3 << 'EOF'
from agentos.core.extensions.registry import ExtensionRegistry
import sqlite3

# Create registry (triggers migrations)
registry = ExtensionRegistry()

# Verify table exists
conn = sqlite3.connect(str(registry.db_path))
cursor = conn.execute("SELECT COUNT(*) FROM extension_installs")
count = cursor.fetchone()[0]
conn.close()

print(f"✓ extension_installs table exists (records: {count})")
EOF
```

**Result**: ✅ PASS - Table exists and is queryable

### Test 2: Custom Database Path

```bash
python3 << 'EOF'
import tempfile
from pathlib import Path
import sqlite3
from agentos.core.extensions.registry import ExtensionRegistry

# Create minimal custom database
temp_db = Path(tempfile.mkdtemp()) / "custom.db"
conn = sqlite3.connect(str(temp_db))
conn.execute("CREATE TABLE schema_version (version TEXT)")
conn.commit()
conn.close()

# Create registry with custom path (should NOT trigger migrations)
registry = ExtensionRegistry(db_path=temp_db)

# Verify migrations did NOT run
conn = sqlite3.connect(str(temp_db))
try:
    cursor = conn.execute("SELECT COUNT(*) FROM extension_installs")
    print("✗ FAIL: Migrations ran when they shouldn't have")
except sqlite3.OperationalError as e:
    if "no such table" in str(e).lower():
        print("✓ PASS: Migrations correctly NOT triggered for custom db_path")
conn.close()
EOF
```

**Result**: ✅ PASS - Migrations not triggered for custom paths

### Test 3: WebUI Upload Scenario

```bash
python3 << 'EOF'
from agentos.core.extensions.registry import ExtensionRegistry
from agentos.core.extensions.models import InstallStatus
import uuid

# Simulate WebUI extension upload
registry = ExtensionRegistry()

# Create install tracking record
install_id = f"webui-test-{uuid.uuid4().hex[:8]}"
registry.create_install_record(
    install_id=install_id,
    extension_id="test.extension",
    status=InstallStatus.INSTALLING
)

# Simulate frontend polling
retrieved = registry.get_install_record(install_id)

if retrieved:
    print(f"✓ PASS: Install record retrieved (no 404)")
    print(f"  install_id: {retrieved.install_id}")
    print(f"  status: {retrieved.status.value}")
else:
    print("✗ FAIL: Install record not found (404 error)")
EOF
```

**Result**: ✅ PASS - Install records can be created and retrieved

---

## Impact Analysis

### Files Modified

- **`agentos/core/extensions/registry.py`**: Added migration trigger in `__init__`

### Files NOT Modified (No Changes Needed)

- **`agentos/webui/api/extensions.py`**: Already uses `ExtensionRegistry()` correctly
- **`agentos/store/__init__.py`**: `ensure_migrations()` already exists and works
- **`agentos/store/migrations/schema_v33.sql`**: Extension tables already defined
- **Tests**: All existing tests continue to work (they use custom db_path)

### Affected Use Cases

| Use Case | Before Fix | After Fix |
|----------|-----------|-----------|
| WebUI extension upload | ❌ 404 error on polling | ✅ Works correctly |
| CLI extension install | ❌ Might fail with missing table | ✅ Works correctly |
| Chat slash commands | ❌ Registry queries fail | ✅ Works correctly |
| Extension listing | ❌ Empty results | ✅ Shows installed extensions |
| Unit tests | ✅ Already working | ✅ Still working |

---

## Database Schema

The fix ensures these tables are created (defined in `schema_v33.sql`):

### `extensions` Table
Stores registered extensions with metadata, capabilities, and permissions.

### `extension_installs` Table
Tracks installation progress for async uploads.

```sql
CREATE TABLE IF NOT EXISTS extension_installs (
    install_id TEXT PRIMARY KEY,
    extension_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('INSTALLING', 'COMPLETED', 'FAILED', 'UNINSTALLING')),
    progress INTEGER DEFAULT 0 CHECK(progress >= 0 AND progress <= 100),
    current_step TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    error TEXT,
    FOREIGN KEY (extension_id) REFERENCES extensions(id) ON DELETE CASCADE
);
```

### `extension_configs` Table
Stores extension-specific configuration.

---

## Migration Path

### For Existing Installations

If users already have AgentOS installed with schema < v0.33:

1. **Next time they start the WebUI**: The fix will automatically trigger `ensure_migrations()`
2. **Schema v33 will be applied**: Extension tables will be created
3. **Extensions will work immediately**: No manual intervention needed

### For New Installations

1. **`agentos init`**: Creates database with `schema_version` table
2. **First WebUI start**: Triggers all migrations (v01 → v33)
3. **ExtensionRegistry init**: `ensure_migrations()` is idempotent (safe to call multiple times)

---

## Testing Checklist

- [x] Unit test: Registry initialization with default path
- [x] Unit test: Registry initialization with custom path
- [x] Integration test: Create and retrieve install record
- [x] Integration test: Update install progress
- [x] Integration test: Complete installation
- [x] Acceptance test: WebUI upload flow end-to-end
- [x] Regression test: Existing unit tests still pass
- [x] Performance test: No significant slowdown on initialization

---

## Rollback Plan

If the fix causes issues:

1. **Revert the commit**:
   ```bash
   git revert <commit-hash>
   ```

2. **Manual workaround** (if needed):
   ```python
   # Add this to agentos/webui/app.py startup
   from agentos.store import ensure_migrations, get_db_path
   ensure_migrations(get_db_path())
   ```

---

## Related Issues

- **Original Bug**: Extension uploads failing with 404 errors
- **Schema Version**: v0.33 (extension system tables)
- **Migration System**: `agentos.store.migrator.auto_migrate()`
- **WebUI API**: `/api/extensions/install/{install_id}`

---

## Future Improvements

1. **Add health check**: Verify extension tables exist on startup
2. **Add admin UI**: Show database schema version and migration status
3. **Add CLI command**: `agentos extensions doctor` to diagnose issues
4. **Add metrics**: Track extension installation success rate

---

## Conclusion

✅ **Fix Status**: Successfully implemented and verified
✅ **Backwards Compatible**: Yes - existing installations will auto-migrate
✅ **Test Coverage**: All critical paths tested
✅ **Performance Impact**: Minimal (migrations only run once)
✅ **User Impact**: Extensions now work correctly in WebUI

**Next Steps**:
- Monitor for any edge cases in production
- Consider adding health checks for extension system
- Update user documentation with troubleshooting guide
