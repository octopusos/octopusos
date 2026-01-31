## Lease and Recovery System - Technical Specification

**Version**: 1.0.0
**Status**: Implemented
**Date**: 2026-01-29
**Task**: #8 - Worker lease + heartbeat + recovery sweep

---

## Overview

The Lease and Recovery System provides distributed work item management with automatic failure detection and recovery. It ensures that work items are processed exactly once, even in the face of worker crashes, network partitions, or other failures.

### Key Features

- **Atomic Lease Acquisition**: Compare-and-Swap based lease acquisition prevents conflicts
- **Heartbeat Mechanism**: Background threads automatically renew leases
- **Automatic Recovery**: Watchdog process detects expired leases and recovers work items
- **Retry Logic**: Failed work items are automatically retried (configurable max attempts)
- **Audit Trail**: Error boundary checkpoints provide complete failure history

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Worker Pool Architecture                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │   Worker 1   │         │   Worker 2   │                  │
│  ├──────────────┤         ├──────────────┤                  │
│  │ LeaseManager │         │ LeaseManager │                  │
│  │ Heartbeat    │         │ Heartbeat    │                  │
│  └──────┬───────┘         └──────┬───────┘                  │
│         │                        │                          │
│         v                        v                          │
│  ┌──────────────────────────────────────┐                   │
│  │         work_items (database)        │                   │
│  │  - Lease management                  │                   │
│  │  - Status tracking                   │                   │
│  │  - Retry counting                    │                   │
│  └───────────────┬──────────────────────┘                   │
│                  │                                           │
│                  v                                           │
│  ┌──────────────────────────────────────┐                   │
│  │       RecoverySweep (watchdog)       │                   │
│  │  - Scan for expired leases           │                   │
│  │  - Re-queue or mark failed           │                   │
│  │  - Create error checkpoints          │                   │
│  └──────────────────────────────────────┘                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. LeaseManager

**Location**: `agentos/core/worker_pool/lease.py`

#### Purpose
Manages atomic lease acquisition, renewal, and release for work items.

#### Key Methods

##### `acquire_lease(lease_duration_seconds, work_type_filter, task_id_filter) -> Optional[Lease]`

Atomically acquires a lease on the highest priority pending work item.

**Algorithm**:
1. SELECT work_item_id WHERE status='pending' (with optional filters)
2. UPDATE work_item SET status='in_progress', lease_holder=worker_id WHERE work_item_id=...
3. If rows_affected == 1: success, return Lease
4. Else: no work available, return None

**Parameters**:
- `lease_duration_seconds` (default: 300): How long the lease is valid
- `work_type_filter`: Optional filter by work type
- `task_id_filter`: Optional filter by task

**Returns**: `Lease` object or `None` if no work available

**Thread-Safety**: Uses SQLite's row-level locking for atomic CAS

##### `renew_lease(work_item_id, lease_duration_seconds) -> bool`

Extends lease expiry by sending a heartbeat.

**Algorithm**:
1. UPDATE work_items SET heartbeat_at=now(), lease_expires_at=now()+duration
2. WHERE work_item_id=... AND lease_holder=worker_id AND status='in_progress'
3. If rows_affected == 1: success, return True
4. Else: check reason (expired, conflict, etc.), raise appropriate exception

**Parameters**:
- `work_item_id`: ID of work item to renew
- `lease_duration_seconds` (default: 300): Extension duration

**Returns**: `True` if successful

**Raises**:
- `LeaseExpiredError`: If lease already expired
- `LeaseConflictError`: If held by another worker

##### `release_lease(work_item_id, success, output_data, error) -> bool`

Releases lease and marks work item as completed or failed.

**Parameters**:
- `work_item_id`: ID of work item
- `success`: Whether work completed successfully
- `output_data`: Result data (if successful)
- `error`: Error message (if failed)

**Algorithm**:
```python
if success:
    UPDATE work_items SET
        status='completed',
        output_data=...,
        lease_holder=NULL
else:
    UPDATE work_items SET
        status='failed',
        error_message=...,
        lease_holder=NULL
```

#### Usage Example

```python
from agentos.core.worker_pool import LeaseManager

# Initialize manager
manager = LeaseManager(conn, worker_id="worker-abc-123")

# Try to acquire work
lease = manager.acquire_lease(lease_duration_seconds=300)

if lease:
    try:
        # Process work item
        result = do_work(lease.input_data)

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
```

---

### 2. HeartbeatThread

**Location**: `agentos/core/worker_pool/heartbeat.py`

#### Purpose
Background thread that automatically renews leases at regular intervals.

#### Key Features
- Runs in separate daemon thread
- Configurable heartbeat interval (default: 30 seconds)
- Automatic shutdown on lease loss or error
- Failure detection (max 3 consecutive failures)

#### Constructor Parameters

```python
HeartbeatThread(
    lease_manager: LeaseManager,
    work_item_id: str,
    interval_seconds: int = 30,
    lease_duration_seconds: int = 300,
    max_failures: int = 3,
    on_lease_lost: Optional[Callable[[], None]] = None
)
```

**Parameters**:
- `lease_manager`: LeaseManager instance
- `work_item_id`: Work item to send heartbeats for
- `interval_seconds` (default: 30): How often to send heartbeats
- `lease_duration_seconds` (default: 300): How long to extend lease each time
- `max_failures` (default: 3): Max consecutive failures before giving up
- `on_lease_lost`: Optional callback when lease is lost

#### Methods

##### `start() -> None`
Starts the heartbeat thread.

##### `stop(wait=True, timeout=5.0) -> None`
Stops the heartbeat thread.

**Parameters**:
- `wait`: Whether to wait for thread to finish
- `timeout`: Maximum wait time in seconds

##### `is_running() -> bool`
Returns whether thread is currently running.

#### Usage Example

```python
from agentos.core.worker_pool import HeartbeatThread, start_heartbeat

# Method 1: Using convenience function
heartbeat = start_heartbeat(
    conn=conn,
    work_item_id="work-123",
    worker_id="worker-abc",
    interval_seconds=30
)

# ... do work ...

heartbeat.stop()

# Method 2: Manual construction
from agentos.core.worker_pool import LeaseManager, HeartbeatThread

manager = LeaseManager(conn, "worker-abc")
heartbeat = HeartbeatThread(
    lease_manager=manager,
    work_item_id="work-123",
    interval_seconds=30,
    on_lease_lost=lambda: logger.error("Lease lost!")
)

heartbeat.start()
# ... do work ...
heartbeat.stop()
```

#### Important Notes

**SQLite Threading**: Each thread must create its own database connection. Do NOT share connections across threads.

**Recommended Pattern**:
```python
def heartbeat_with_own_connection(db_path, work_item_id, worker_id):
    """Heartbeat function that creates its own connection"""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    manager = LeaseManager(conn, worker_id)
    heartbeat = HeartbeatThread(manager, work_item_id)
    heartbeat.start()
    return heartbeat
```

---

### 3. RecoverySweep

**Location**: `agentos/core/recovery/recovery_sweep.py`

#### Purpose
Watchdog process that periodically scans for expired leases and recovers work items.

#### Key Features
- Automatic detection of expired leases
- Retry logic with configurable max attempts
- Error boundary checkpoint creation
- Cleanup of old checkpoints
- Background thread mode or one-time scan

#### Constructor Parameters

```python
RecoverySweep(
    conn: sqlite3.Connection,
    scan_interval_seconds: int = 60,
    create_checkpoints: bool = True,
    cleanup_old_checkpoints: bool = True,
    checkpoint_retention_limit: int = 100
)
```

**Parameters**:
- `conn`: Database connection
- `scan_interval_seconds` (default: 60): How often to scan
- `create_checkpoints` (default: True): Whether to create error checkpoints
- `cleanup_old_checkpoints` (default: True): Whether to cleanup old checkpoints
- `checkpoint_retention_limit` (default: 100): Max checkpoints per task

#### Methods

##### `start() -> None`
Starts the recovery sweep background thread.

##### `stop(wait=True, timeout=10.0) -> None`
Stops the background thread.

##### `scan_and_recover() -> RecoveryStats`
Performs a single scan and recovery pass.

**Returns**: `RecoveryStats` object with:
- `expired_found`: Number of expired leases found
- `recovered`: Number of work items re-queued
- `failed`: Number permanently failed (max retries exceeded)
- `checkpoints_created`: Number of error checkpoints created
- `errors`: Number of errors encountered
- `scan_duration_ms`: Scan duration in milliseconds

##### `get_statistics() -> Dict[str, Any]`
Returns overall statistics:
- `is_running`: Whether sweep is active
- `total_scans`: Total number of scans performed
- `total_recovered`: Total work items recovered
- `total_failed`: Total work items failed
- `last_scan`: Stats from last scan

#### Recovery Algorithm

```python
FOR each work_item WHERE status='in_progress' AND lease_expires_at < now():
    1. Increment retry_count

    2. IF retry_count < max_retries:
         - Set status = 'pending'  (re-queue for retry)
         - Clear lease_holder and lease_expires_at
         - Set error_message = 'Lease expired - retry N/M'
       ELSE:
         - Set status = 'failed'  (permanent failure)
         - Clear lease_holder and lease_expires_at
         - Set error_message = 'Max retries exceeded'

    3. IF create_checkpoints:
         - Create error_boundary checkpoint with details
         - Include: error, retry_count, expired_lease metadata

    4. Commit changes

5. IF cleanup_old_checkpoints:
     - For each task with > retention_limit checkpoints:
       - Delete oldest checkpoints, keep most recent N
```

#### Usage Example

```python
from agentos.core.recovery import RecoverySweep

# One-time scan
sweep = RecoverySweep(conn)
stats = sweep.scan_and_recover()
print(f"Recovered {stats.recovered} work items")

# Background mode
sweep = RecoverySweep(
    conn,
    scan_interval_seconds=60,
    create_checkpoints=True
)
sweep.start()

# ... system runs ...

# Stop sweep
sweep.stop()

# Get statistics
stats = sweep.get_statistics()
print(f"Total scans: {stats['total_scans']}")
print(f"Total recovered: {stats['total_recovered']}")
```

---

## Database Schema

### work_items Table

```sql
CREATE TABLE work_items (
    work_item_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    work_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 0,

    -- Lease management
    lease_holder TEXT,              -- Worker ID holding lease
    lease_acquired_at TIMESTAMP,    -- When lease acquired
    lease_expires_at TIMESTAMP,     -- When lease expires
    heartbeat_at TIMESTAMP,         -- Last heartbeat time

    -- Retry management
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Data
    input_data TEXT,
    output_data TEXT,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);
```

### Status State Machine

```
pending ──────────────────────> failed (max retries)
  │                                  ↑
  │                                  │
  ↓                                  │
in_progress ──> completed            │
  │             (terminal)           │
  │                                  │
  ├──────────> failed ───────────────┘
  │             (terminal)
  │
  └──────────> expired ──> pending (retry)
                          or failed
```

### Lease States

| Field | Value | Meaning |
|-------|-------|---------|
| `lease_holder` | NULL | No active lease |
| `lease_holder` | "worker-123" | Lease held by worker |
| `lease_expires_at` | future | Lease still valid |
| `lease_expires_at` | past | Lease expired (needs recovery) |
| `heartbeat_at` | recent | Worker alive |
| `heartbeat_at` | stale (>2 min) | Worker may be dead |

---

## Configuration Recommendations

### Lease Duration

**Rule of thumb**: 2x expected task execution time

- **Short tasks** (< 1 minute): 5 minutes (300s)
- **Medium tasks** (1-10 minutes): 10 minutes (600s)
- **Long tasks** (10+ minutes): 30 minutes (1800s)

### Heartbeat Interval

**Rule of thumb**: lease_duration / 10

- 5-minute lease → 30-second heartbeat
- 10-minute lease → 60-second heartbeat
- 30-minute lease → 180-second heartbeat

### Recovery Sweep Interval

**Rule of thumb**: lease_duration / 5

- 5-minute lease → 60-second scan
- 10-minute lease → 120-second scan

### Max Retries

- **Idempotent operations**: 3-5 retries
- **Non-idempotent operations**: 1-2 retries
- **Expensive operations**: 1 retry

---

## Operational Patterns

### Pattern 1: Worker with Automatic Heartbeat

```python
from agentos.core.worker_pool import LeaseManager, start_heartbeat

def worker_main(conn, worker_id):
    """Worker that processes work items with automatic heartbeat"""
    manager = LeaseManager(conn, worker_id)

    while True:
        # Acquire next work item
        lease = manager.acquire_lease(lease_duration_seconds=300)

        if not lease:
            time.sleep(5)  # No work available
            continue

        # Start heartbeat
        heartbeat = start_heartbeat(
            conn=conn,
            work_item_id=lease.work_item_id,
            worker_id=worker_id,
            interval_seconds=30
        )

        try:
            # Process work
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
            # Stop heartbeat
            heartbeat.stop()
```

### Pattern 2: Watchdog Service

```python
from agentos.core.recovery import RecoverySweep
import signal
import sys

def run_watchdog(conn):
    """Run recovery sweep as a service"""
    sweep = RecoverySweep(
        conn,
        scan_interval_seconds=60,
        create_checkpoints=True,
        cleanup_old_checkpoints=True
    )

    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        print("Shutting down watchdog...")
        sweep.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start sweep
    sweep.start()
    print("Watchdog started")

    # Keep alive
    while sweep.is_running():
        time.sleep(10)

        # Print stats periodically
        stats = sweep.get_statistics()
        if stats['last_scan']:
            print(f"Last scan: recovered={stats['last_scan']['recovered']}, "
                  f"failed={stats['last_scan']['failed']}")
```

### Pattern 3: Integration with Task Runner

```python
from agentos.core.worker_pool import LeaseManager
from agentos.core.recovery import RecoverySweep

class TaskRunner:
    """Task runner with integrated lease management"""

    def __init__(self, conn, worker_id):
        self.conn = conn
        self.worker_id = worker_id
        self.lease_manager = LeaseManager(conn, worker_id)
        self.recovery_sweep = RecoverySweep(conn)

    def start(self):
        """Start recovery sweep and worker"""
        self.recovery_sweep.start()
        self._run_worker()

    def stop(self):
        """Stop recovery sweep"""
        self.recovery_sweep.stop()

    def _run_worker(self):
        """Main worker loop"""
        while True:
            lease = self.lease_manager.acquire_lease()
            if lease:
                self._process_work_item(lease)
```

---

## Monitoring and Debugging

### Key Metrics

1. **Lease Health**:
   ```sql
   SELECT
       COUNT(*) as active_leases,
       COUNT(CASE WHEN heartbeat_at < datetime('now', '-2 minutes') THEN 1 END) as stale_leases
   FROM work_items
   WHERE status = 'in_progress';
   ```

2. **Recovery Stats**:
   ```python
   stats = sweep.get_statistics()
   print(f"Total recovered: {stats['total_recovered']}")
   print(f"Total failed: {stats['total_failed']}")
   print(f"Recovery rate: {stats['total_recovered'] / (stats['total_recovered'] + stats['total_failed']):.2%}")
   ```

3. **Retry Distribution**:
   ```sql
   SELECT retry_count, COUNT(*) as count
   FROM work_items
   WHERE status IN ('completed', 'failed')
   GROUP BY retry_count;
   ```

### Debugging Expired Leases

```sql
SELECT
    work_item_id,
    lease_holder,
    julianday('now') - julianday(heartbeat_at) * 24 * 60 as minutes_since_heartbeat,
    julianday('now') - julianday(lease_expires_at) * 24 * 60 as minutes_since_expiry
FROM work_items
WHERE status = 'in_progress'
  AND lease_expires_at < datetime('now')
ORDER BY lease_expires_at ASC;
```

---

## Testing

### Unit Tests

- `tests/integration/test_lease_takeover.py` - Lease acquisition and conflict tests
- `tests/integration/test_recovery_sweep.py` - Recovery sweep tests

### Integration Tests

Run comprehensive tests:
```bash
python3 test_task8_basic.py
```

### Test Coverage

- ✅ Lease acquisition (atomic CAS)
- ✅ Lease conflict prevention (two workers, one item)
- ✅ Lease renewal via heartbeat
- ✅ Heartbeat thread lifecycle
- ✅ Recovery sweep (expired lease detection)
- ✅ Retry logic (re-queue vs permanent failure)
- ✅ Error checkpoint creation
- ✅ Checkpoint cleanup
- ✅ Priority-based work item ordering
- ✅ Lease release (success and failure)

---

## Limitations and Future Work

### Current Limitations

1. **SQLite Threading**: HeartbeatThread requires its own database connection (SQLite limitation)
2. **No Distributed Locking**: Assumes single database (SQLite or PostgreSQL with serializable isolation)
3. **No Worker Registry**: No centralized worker health monitoring

### Future Enhancements

1. **PostgreSQL Support**: Full support for PostgreSQL with advisory locks
2. **Worker Registry**: Track active workers and their health status
3. **Distributed Tracing**: OpenTelemetry integration for lease lifecycle tracking
4. **Metrics Export**: Prometheus metrics for lease duration, recovery rates, etc.
5. **Dynamic Lease Duration**: Adjust lease duration based on historical execution time

---

## References

- Database Schema: `docs/specs/RECOVERY_DATABASE_SCHEMA.md`
- Quick Reference: `docs/specs/RECOVERY_QUICK_REFERENCE.md`
- Migration: `agentos/store/migrations/schema_v30.sql`
- Tests: `tests/integration/test_lease_takeover.py`, `test_recovery_sweep.py`

---

**End of Specification**
