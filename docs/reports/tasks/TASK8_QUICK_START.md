# Task #8 Quick Start Guide

**Worker Lease + Heartbeat + Recovery Sweep**

---

## 🚀 Quick Usage

### 1. Worker with Automatic Heartbeat

```python
from agentos.core.worker_pool import LeaseManager, start_heartbeat

conn = get_db()
worker_id = "worker-001"

# Create lease manager
manager = LeaseManager(conn, worker_id)

# Main worker loop
while True:
    # Try to acquire work
    lease = manager.acquire_lease(lease_duration_seconds=300)

    if not lease:
        time.sleep(5)  # No work available
        continue

    # Start automatic heartbeat
    heartbeat = start_heartbeat(
        conn=conn,
        work_item_id=lease.work_item_id,
        worker_id=worker_id,
        interval_seconds=30
    )

    try:
        # Do the actual work
        result = process_work_item(lease.input_data)

        # Release successfully
        manager.release_lease(
            lease.work_item_id,
            success=True,
            output_data=result
        )

    except Exception as e:
        # Release with error
        manager.release_lease(
            lease.work_item_id,
            success=False,
            error=str(e)
        )

    finally:
        # Always stop heartbeat
        heartbeat.stop()
```

### 2. Recovery Watchdog Service

```python
from agentos.core.recovery import RecoverySweep

conn = get_db()

# Create recovery sweep
sweep = RecoverySweep(
    conn,
    scan_interval_seconds=60,    # Scan every 60 seconds
    create_checkpoints=True,      # Create error checkpoints
    cleanup_old_checkpoints=True  # Clean up old checkpoints
)

# Start in background
sweep.start()

# Keep alive
while sweep.is_running():
    time.sleep(10)

    # Print stats periodically
    stats = sweep.get_statistics()
    print(f"Total recovered: {stats['total_recovered']}")
```

### 3. One-Time Recovery Scan

```python
from agentos.core.recovery import RecoverySweep

conn = get_db()
sweep = RecoverySweep(conn)

# Run scan once
stats = sweep.scan_and_recover()

print(f"Expired leases found: {stats.expired_found}")
print(f"Work items recovered: {stats.recovered}")
print(f"Work items failed: {stats.failed}")
print(f"Scan duration: {stats.scan_duration_ms:.1f}ms")
```

---

## 📊 Key Configuration

| Setting | Default | Recommendation |
|---------|---------|----------------|
| `lease_duration_seconds` | 300 | 2x expected task time |
| `heartbeat_interval` | 30 | lease_duration / 10 |
| `sweep_interval` | 60 | lease_duration / 5 |
| `max_retries` | 3 | 3-5 for idempotent ops |

### Example Configurations

**Fast tasks (< 1 minute)**:
```python
lease_duration_seconds = 300    # 5 minutes
heartbeat_interval = 30          # 30 seconds
sweep_interval = 60              # 1 minute
```

**Medium tasks (1-10 minutes)**:
```python
lease_duration_seconds = 600    # 10 minutes
heartbeat_interval = 60          # 1 minute
sweep_interval = 120             # 2 minutes
```

**Long tasks (10+ minutes)**:
```python
lease_duration_seconds = 1800   # 30 minutes
heartbeat_interval = 180         # 3 minutes
sweep_interval = 360             # 6 minutes
```

---

## 🔍 Monitoring

### Check Active Leases

```sql
SELECT
    work_item_id,
    lease_holder,
    julianday('now') - julianday(heartbeat_at) * 24 * 60 as minutes_since_heartbeat
FROM work_items
WHERE status = 'in_progress'
ORDER BY heartbeat_at DESC;
```

### Check Recovery Stats

```python
stats = sweep.get_statistics()
print(f"Total scans: {stats['total_scans']}")
print(f"Total recovered: {stats['total_recovered']}")
print(f"Total failed: {stats['total_failed']}")
```

### Find Stale Leases

```sql
SELECT
    COUNT(*) as active_leases,
    COUNT(CASE WHEN heartbeat_at < datetime('now', '-2 minutes') THEN 1 END) as stale_leases
FROM work_items
WHERE status = 'in_progress';
```

---

## 🐛 Troubleshooting

### Problem: Leases expiring too quickly

**Solution**: Increase lease duration
```python
lease = manager.acquire_lease(lease_duration_seconds=600)  # 10 minutes
```

### Problem: SQLite threading error in HeartbeatThread

**Cause**: SQLite connections cannot be shared across threads

**Solution**: Each thread needs its own connection
```python
# DON'T: Share connection
heartbeat = start_heartbeat(conn=main_conn, ...)  # ❌

# DO: Pass db path, create connection in thread
def heartbeat_with_own_conn(db_path, work_item_id, worker_id):
    conn = sqlite3.connect(db_path)
    return start_heartbeat(conn, work_item_id, worker_id)
```

### Problem: Work items stuck in pending

**Check**: Are workers running?
```sql
SELECT COUNT(*) FROM work_items WHERE status = 'pending';
```

**Check**: Are there any active workers?
```sql
SELECT DISTINCT lease_holder FROM work_items WHERE status = 'in_progress';
```

---

## 📚 API Reference

### LeaseManager

```python
class LeaseManager:
    def __init__(self, conn: sqlite3.Connection, worker_id: str)

    def acquire_lease(
        lease_duration_seconds: int = 300,
        work_type_filter: Optional[str] = None,
        task_id_filter: Optional[str] = None
    ) -> Optional[Lease]

    def renew_lease(
        work_item_id: str,
        lease_duration_seconds: int = 300
    ) -> bool

    def release_lease(
        work_item_id: str,
        success: bool = True,
        output_data: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> bool

    def check_lease_status(work_item_id: str) -> Dict[str, Any]

    def get_my_leases() -> List[Dict[str, Any]]
```

### HeartbeatThread

```python
class HeartbeatThread:
    def __init__(
        lease_manager: LeaseManager,
        work_item_id: str,
        interval_seconds: int = 30,
        lease_duration_seconds: int = 300,
        max_failures: int = 3,
        on_lease_lost: Optional[Callable] = None
    )

    def start() -> None
    def stop(wait: bool = True, timeout: float = 5.0) -> None
    def is_running() -> bool

# Convenience function
def start_heartbeat(
    conn: sqlite3.Connection,
    work_item_id: str,
    worker_id: str,
    interval_seconds: int = 30,
    lease_duration_seconds: int = 300,
    on_lease_lost: Optional[Callable] = None
) -> HeartbeatThread
```

### RecoverySweep

```python
class RecoverySweep:
    def __init__(
        conn: sqlite3.Connection,
        scan_interval_seconds: int = 60,
        create_checkpoints: bool = True,
        cleanup_old_checkpoints: bool = True,
        checkpoint_retention_limit: int = 100
    )

    def start() -> None
    def stop(wait: bool = True, timeout: float = 10.0) -> None
    def is_running() -> bool

    def scan_and_recover() -> RecoveryStats

    def get_statistics() -> Dict[str, Any]
```

---

## 📖 Full Documentation

- **Technical Spec**: `docs/specs/LEASE_AND_RECOVERY.md`
- **Database Schema**: `docs/specs/RECOVERY_DATABASE_SCHEMA.md`
- **Quick Reference**: `docs/specs/RECOVERY_QUICK_REFERENCE.md`
- **Tests**: `tests/integration/test_lease_takeover.py`, `test_recovery_sweep.py`

---

## ✅ Verification

Run tests to verify installation:
```bash
python3 test_task8_basic.py
```

Expected output:
```
============================================================
✅ ALL TESTS PASSED
============================================================
```
