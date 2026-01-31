# DB Integrity Gates - Quick Reference Card

## 🚀 Quick Commands

```bash
# Run all gates
./scripts/gates/run_all_gates.sh

# Install pre-commit hook
./scripts/gates/install_pre_commit_hook.sh

# Run single gate
python3 scripts/gates/gate_no_sqlite_connect_enhanced.py
python3 scripts/gates/gate_no_duplicate_tables.py
python3 scripts/gates/gate_no_sql_in_code.py
python3 scripts/gates/gate_single_db_entry.py
```

## ❌ What's Blocked

| Pattern | Example | Why Blocked |
|---------|---------|-------------|
| Direct connect | `sqlite3.connect("db.sqlite")` | Bypasses unified access |
| New Store classes | `class MySessionStore:` | Creates dual-table system |
| SQL in code | `CREATE TABLE my_table` | Skips migration system |
| Multiple entry points | `def get_db():` | Breaks singleton pattern |
| Hardcoded paths | `"store/registry.sqlite"` | Environment-dependent |

## ✅ Correct Patterns

### Database Access
```python
# ✅ CORRECT
from agentos.core.db import registry_db
conn = registry_db.get_db()

# Query
rows = registry_db.query_all("SELECT * FROM tasks")

# Transaction
with registry_db.transaction() as conn:
    conn.execute("INSERT INTO tasks ...")
```

### Schema Changes
```python
# ✅ CORRECT - Create migration file
# File: agentos/store/migrations/0042_add_feature.py

def upgrade(conn):
    """Add feature table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feature_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)

def downgrade(conn):
    """Remove feature table."""
    conn.execute("DROP TABLE IF EXISTS feature_table")
```

### Store Classes
```python
# ✅ CORRECT - Use existing store
from agentos.core.db import registry_db

class MyDataService:
    def __init__(self):
        # No need to store connection
        pass

    def get_data(self):
        conn = registry_db.get_db()
        return conn.execute("SELECT ...").fetchall()
```

## 🔍 Gate Summary

| # | Gate | Checks | Run Time |
|---|------|--------|----------|
| 1 | Enhanced SQLite Connect | Direct connections, new stores, table creation | ~2-3s |
| 2 | Schema Duplicate | Duplicate tables in database | ~0.5s |
| 3 | SQL in Code | Schema changes outside migrations | ~2-3s |
| 4 | Single Entry Point | Multiple get_db() functions | ~2-3s |

**Total**: ~7-10 seconds

## 🚨 Common Violations & Fixes

### Violation 1: Direct sqlite3.connect()
```python
# ❌ WRONG
import sqlite3
conn = sqlite3.connect("my.db")

# ✅ FIX
from agentos.core.db import registry_db
conn = registry_db.get_db()
```

### Violation 2: Creating Store Classes
```python
# ❌ WRONG
class MySessionStore:
    def __init__(self):
        self.conn = sqlite3.connect("sessions.db")

# ✅ FIX
class MySessionService:
    def get_sessions(self):
        from agentos.core.db import registry_db
        conn = registry_db.get_db()
        return conn.execute("SELECT * FROM chat_sessions").fetchall()
```

### Violation 3: SQL Schema in Code
```python
# ❌ WRONG
def init_tables():
    conn.execute("CREATE TABLE IF NOT EXISTS my_table ...")

# ✅ FIX
# Create: agentos/store/migrations/0042_my_table.py
def upgrade(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS my_table ...")
```

### Violation 4: Multiple get_db()
```python
# ❌ WRONG
def get_db():
    return sqlite3.connect("my.db")

# ✅ FIX
# Delete your get_db(), use:
from agentos.core.db import registry_db
# Always use registry_db.get_db()
```

### Violation 5: Hardcoded DB Path
```python
# ❌ WRONG
db_path = "store/registry.sqlite"

# ✅ FIX
import os
from pathlib import Path
db_path = os.getenv("AGENTOS_DB_PATH", "store/registry.sqlite")
# Or better: use registry_db.get_connection_info()['db_path']
```

## 🛠️ Troubleshooting

### Gate fails locally
1. Read the error message (tells you exactly what's wrong)
2. Find your code in the report
3. Apply the fix from examples above
4. Re-run: `./scripts/gates/run_all_gates.sh`

### Gate fails in CI
1. Check GitHub Actions logs
2. Download "gate-reports" artifact
3. Fix locally first
4. Push again

### False positive
1. Check if file should be whitelisted
2. Add to `WHITELIST` in gate script with comment
3. Create task to remove whitelist entry later

## 🎯 Integration Points

### Pre-commit Hook
```bash
# Install
./scripts/gates/install_pre_commit_hook.sh

# Bypass (emergency only)
git commit --no-verify
```

### CI/CD
- **Runs on**: Push to master/main/develop, all PRs
- **Workflow**: `.github/workflows/gate-db-integrity.yml`
- **Artifacts**: gate-reports-*, database-schema
- **Cannot bypass**: Must fix code or update whitelist

## 📚 Full Documentation

- **Complete Guide**: `docs/GATE_SYSTEM.md`
- **Quick Start**: `scripts/gates/README.md`
- **Implementation**: `GATE_SYSTEM_IMPLEMENTATION_REPORT.md`

## 🆘 Support

- **Chat**: #database or #architecture channels
- **Issues**: GitHub Issues with "Gate System" label
- **Office Hours**: Thursday 2-3pm

## 📊 Current Status (2026-01-31)

- **Total Gates**: 5 (4 enhanced + 1 legacy)
- **Run Time**: ~7-10 seconds
- **Violations Found**: 42 across 26 files
- **Critical Issues**: 1 (task_sessions duplicate)
- **Status**: ✅ Operational, ready for deployment

---

**💡 Pro Tip**: Run gates before committing!
```bash
./scripts/gates/run_all_gates.sh && git commit
```
