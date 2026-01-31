# NetworkOS Health Check - Implementation Guide

## Overview

NetworkOS includes a comprehensive health check system integrated into AgentOS's doctor and health monitoring infrastructure.

## Features

### Health Checks Performed

1. **DB Exists**: Verifies database file is present at `~/.agentos/store/networkos/db.sqlite`
2. **DB Accessible**: Tests database can be opened and queried
3. **DB Writable**: Performs write test (creates/deletes test event)
4. **Schema Version**: Validates schema is v54 or newer
5. **Required Tables**: Checks existence of core tables
   - `network_tunnels`: Tunnel configurations
   - `network_events`: Event logs
   - `network_routes`: Routing information
   - `tunnel_secrets`: Encrypted credentials
6. **WAL Mode**: Confirms SQLite WAL mode is enabled

### Performance

All checks complete in <2 seconds for optimal UX.

## Usage

### CLI - Doctor Command

```bash
# Run all system health checks (includes NetworkOS)
agentos doctor

# Example output:
# ✅ networkos - NetworkOS database healthy
#   • Passed checks: 6/6
```

Output formats:
- ✅ **PASS**: All checks passed, NetworkOS is operational
- ⚠️ **WARN**: Database not initialized (will be created on first use)
- ❌ **FAIL**: Critical issue detected (see fix suggestions)

### Web API - Health Endpoint

```bash
# Get comprehensive system health
curl http://localhost:8000/api/health

# Response includes:
{
  "status": "ok",
  "components": {
    "networkos": {
      "status": "ok",
      "all_passed": true,
      "passed_count": 6,
      "failed_count": 0,
      "checks_failed": [],
      "message": "NetworkOS health: ok"
    }
  }
}
```

### Python API

```python
from agentos.networkos.health import NetworkOSHealthCheck, get_health_status

# Detailed check
checker = NetworkOSHealthCheck()
all_passed, results = checker.run_all_checks()

if not all_passed:
    print(f"Failed checks: {results['summary']['checks_failed']}")
    for check_name in results['summary']['checks_failed']:
        print(f"  - {check_name}: {results[check_name]['message']}")

# Quick status check
status = get_health_status()
print(f"Status: {status['status']}")  # "ok" | "error"
```

## Troubleshooting

### Common Issues

#### 1. Database Not Found

**Symptom:**
```
❌ check_db_exists: Database not found: ~/.agentos/store/networkos/db.sqlite
```

**Fix:**
```bash
# Initialize via migration
agentos migrate

# Or let NetworkOS auto-create on first use
agentos networkos list  # Will initialize DB
```

#### 2. Schema Version Mismatch

**Symptom:**
```
❌ check_schema_version: Schema version: v50 (current) < v54 (required)
```

**Fix:**
```bash
# Run migration to latest version
agentos migrate
```

#### 3. Missing Tables

**Symptom:**
```
❌ check_required_tables: Missing required tables: network_routes, tunnel_secrets
```

**Fix:**
```bash
# Run schema migration v54
agentos migrate
```

#### 4. WAL Mode Not Enabled

**Symptom:**
```
❌ check_wal_mode: WAL mode not enabled: DELETE (expected WAL)
```

**Fix:**
```bash
# Enable WAL mode
sqlite3 ~/.agentos/store/networkos/db.sqlite 'PRAGMA journal_mode=WAL;'
```

#### 5. Database Read-Only

**Symptom:**
```
❌ check_db_writable: Database is read-only
```

**Fix:**
```bash
# Fix file permissions
chmod 644 ~/.agentos/store/networkos/db.sqlite

# Check parent directory permissions
chmod 755 ~/.agentos/store/networkos/
```

#### 6. Database Locked

**Symptom:**
```
❌ check_db_accessible: Database is locked
```

**Fix:**
```bash
# Check for stale processes
ps aux | grep networkos

# Remove stale lock files (if safe)
rm ~/.agentos/store/networkos/db.sqlite-wal
rm ~/.agentos/store/networkos/db.sqlite-shm

# Restart processes using the database
```

## Integration Points

### 1. CLI Doctor Command

Location: `agentos/core/doctor/checks.py`

Function: `check_networkos_db()` returns `CheckResult` with:
- `status`: PASS/WARN/FAIL
- `summary`: One-line description
- `details`: List of specific issues
- `fix_cmd`: Commands to resolve issues

### 2. Web API Health Endpoint

Location: `agentos/webui/api/health.py`

Function: `check_networkos_health()` returns dict with:
- `status`: "ok" | "warn" | "error"
- `all_passed`: bool
- `passed_count`: int
- `failed_count`: int
- `checks_failed`: List[str]
- `message`: str

### 3. Direct Python Usage

Location: `agentos/networkos/health.py`

Classes:
- `NetworkOSHealthCheck`: Main health checker
- `get_health_status()`: Convenience function

## Testing

### Unit Tests

```bash
# Run health check tests
uv run pytest tests/unit/networkos/test_health.py -v

# Test coverage includes:
# - Healthy database scenario
# - Missing database
# - Read-only database
# - Schema version mismatches
# - Missing tables
# - WAL mode disabled
# - Performance validation (<2s)
```

### Integration Testing

```bash
# Test via doctor command
agentos doctor

# Test via API (requires webui running)
curl http://localhost:8000/api/health | jq '.components.networkos'

# Test direct Python usage
uv run python -c "
from agentos.networkos.health import get_health_status
import json
print(json.dumps(get_health_status(), indent=2))
"
```

## Implementation Details

### Architecture

```
agentos/networkos/health.py
├── NetworkOSHealthCheck (main class)
│   ├── check_db_exists()
│   ├── check_db_accessible()
│   ├── check_db_writable()
│   ├── check_schema_version()
│   ├── check_required_tables()
│   └── check_wal_mode()
└── get_health_status() (convenience wrapper)

Integration Points:
├── agentos/core/doctor/checks.py → check_networkos_db()
└── agentos/webui/api/health.py → check_networkos_health()
```

### Design Principles

1. **Fail-Safe**: Each check handles missing DB gracefully
2. **Actionable Messages**: Every failure includes "Fix:" suggestion
3. **Performance**: All checks complete in <2s
4. **Isolation**: Each check is independent
5. **Clean Up**: Write test creates and deletes test record

### Schema Version Parsing

Supports multiple version formats:
- `v54` (v-prefix)
- `0.54.0` (semantic version)
- `54` (plain number)

Comparison: Extracts numeric version, compares >= 54

### Write Test Strategy

1. Check if `network_events` table exists
2. Insert test event with unique ID: `health_check_{timestamp}`
3. Commit transaction
4. Delete test event
5. Commit transaction

This ensures:
- No test data remains in production DB
- True write capability is tested (not just connection)
- Foreign key constraints are respected (uses valid tunnel_id)

## Migration Guide

If adding new health checks:

1. Add check method to `NetworkOSHealthCheck` class
2. Update `run_all_checks()` to include new check
3. Add test case to `tests/unit/networkos/test_health.py`
4. Update this documentation

Example:
```python
def check_new_feature(self) -> Tuple[bool, str]:
    """Check if new feature is configured correctly."""
    try:
        # Perform check
        if condition_passes:
            return True, "New feature is configured"
        else:
            return False, (
                "New feature not configured\n"
                "Fix: Run configuration command"
            )
    except Exception as e:
        return False, f"Failed to check new feature: {e}"
```

## Production Recommendations

1. **Monitoring**: Check `/api/health` every 60s via uptime monitor
2. **Alerting**: Alert if `networkos.status != "ok"` for >5 minutes
3. **Startup**: Run `agentos doctor` as part of deployment verification
4. **CI/CD**: Include health check tests in test suite

## References

- NetworkOS Store: `agentos/networkos/store.py`
- NetworkOS Schema: `agentos/store/migrations/schema_v54_networkos.sql`
- Doctor System: `agentos/core/doctor/`
- Health API: `agentos/webui/api/health.py`
