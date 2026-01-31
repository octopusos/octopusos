# Decision Replay Operations Runbook

## Overview

This runbook provides operational guidance for monitoring and troubleshooting the Decision Replay system.

## Key Metrics

### 1. Decision Trace API Performance

**Metric:** `decision_trace_api_p95_ms`

**What it measures:** 95th percentile response time for `/api/governance/tasks/{task_id}/decision-trace` endpoint

**Healthy range:** < 500ms

**Alert thresholds:**
- Warning: > 500ms
- Critical: > 1000ms

**Common causes:**
- Large trace history (>1000 items)
- Missing database indexes
- Database lock contention
- High concurrent query load

**Remediation:**
1. Check database indexes:
   ```sql
   SELECT name FROM sqlite_master
   WHERE type='index'
   AND tbl_name IN ('task_audits', 'task_events');
   ```

2. Review slow queries:
   ```sql
   EXPLAIN QUERY PLAN
   SELECT * FROM task_audits
   WHERE task_id = ?
   ORDER BY created_at DESC
   LIMIT 200;
   ```

3. Consider pagination:
   - Use smaller `limit` values (50-100 instead of 200)
   - Implement cursor-based pagination correctly

4. Add caching layer if needed:
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def get_cached_trace(task_id, limit, cursor):
       # ... implementation
   ```

### 2. Decision Lag (p95)

**Metric:** `decision_lag_p95_seconds`

**What it measures:** Time from event arrival to decision completion (95th percentile)

**Healthy range:** < 1.0 seconds

**Alert thresholds:**
- Warning: > 1.0 seconds
- Critical: > 5.0 seconds

**Common causes:**
- Supervisor backlog (inbox queue growing)
- Heavy policy evaluation logic
- External service timeouts (LLM calls, etc.)
- Database write contention

**Remediation:**
1. Check inbox backlog:
   ```bash
   curl http://localhost:8080/api/governance/stats/blocked-reasons?window=24h
   ```

2. Review supervisor processing rate:
   ```sql
   SELECT
     COUNT(*) as decisions,
     AVG(CAST((julianday(supervisor_processed_at) - julianday(source_event_ts)) * 86400 AS REAL)) as avg_lag_seconds
   FROM task_audits
   WHERE created_at >= datetime('now', '-1 hour')
   AND source_event_ts IS NOT NULL
   AND supervisor_processed_at IS NOT NULL;
   ```

3. Optimize policy evaluation:
   - Profile slow policy rules
   - Add caching for repeated evaluations
   - Consider async policy execution

4. Scale supervisor workers:
   - Increase worker count if running in multi-process mode
   - Add more supervisor instances behind load balancer

### 3. Blocked Tasks TopN

**Metric:** `blocked_tasks_count`

**What it measures:** Number of distinct tasks currently in BLOCKED state

**Healthy range:** < 10

**Alert thresholds:**
- Warning: > 10 tasks
- Critical: > 50 tasks

**Common causes:**
- Overly strict redline policies
- Configuration errors
- External service failures
- Legitimate security issues

**Remediation:**
1. Get top blocked tasks:
   ```bash
   curl http://localhost:8080/api/governance/stats/blocked-reasons?window=7d&top_n=20
   ```

2. Investigate common reason codes:
   ```sql
   SELECT
     json_extract(payload, '$.decision_snapshot.findings[0].code') as reason_code,
     COUNT(*) as count
   FROM task_audits
   WHERE event_type = 'SUPERVISOR_BLOCKED'
   AND created_at >= datetime('now', '-7 days')
   GROUP BY reason_code
   ORDER BY count DESC
   LIMIT 10;
   ```

3. Review policy rules:
   - Are redlines too strict?
   - Are there false positives?
   - Should policies be updated?

4. Consider allowlists:
   - Add trusted tool patterns
   - Whitelist specific users/tasks
   - Create exception rules

## Common Issues

### Issue 1: Task Stuck in BLOCKED State

**Symptoms:**
- Task remains BLOCKED for extended period
- User reports inability to proceed
- Dashboard shows high blocked count

**Diagnosis:**
```bash
# 1. Get task summary
curl http://localhost:8080/api/governance/tasks/{task_id}/summary

# 2. Get decision trace
curl http://localhost:8080/api/governance/tasks/{task_id}/decision-trace

# 3. Check last decision
curl http://localhost:8080/api/governance/decisions/{decision_id}
```

**Resolution:**
1. Review blocking reason code
2. Check if legitimate security issue
3. If false positive, update policy
4. If one-off issue, manually unblock:
   ```sql
   UPDATE tasks SET status = 'RUNNING' WHERE task_id = ?;
   ```
5. Add audit log entry:
   ```sql
   INSERT INTO task_audits (audit_id, task_id, event_type, payload, created_at)
   VALUES (?, ?, 'MANUAL_UNBLOCK', ?, datetime('now'));
   ```

### Issue 2: Decision Trace Missing Items

**Symptoms:**
- Trace has gaps in timeline
- Expected events not showing up
- Inconsistent count values

**Diagnosis:**
```sql
-- Check for orphaned audits
SELECT COUNT(*) FROM task_audits
WHERE task_id NOT IN (SELECT task_id FROM tasks);

-- Check for missing events
SELECT COUNT(*) FROM task_events
WHERE task_id = ? AND created_at BETWEEN ? AND ?;
```

**Resolution:**
1. Check database foreign key constraints
2. Verify event bus delivery
3. Review supervisor processing logs
4. Check for data retention policies

### Issue 3: High Decision Lag

**Symptoms:**
- Decisions taking > 5 seconds
- Users reporting slow task execution
- Supervisor queue backing up

**Diagnosis:**
```bash
# Check current lag
curl http://localhost:8080/api/governance/stats/decision-lag?window=1h

# Check decision types
curl http://localhost:8080/api/governance/stats/decision-types?window=1h
```

**Resolution:**
1. Profile policy evaluation:
   ```python
   import cProfile

   profiler = cProfile.Profile()
   profiler.enable()
   # ... policy evaluation code
   profiler.disable()
   profiler.print_stats(sort='cumtime')
   ```

2. Optimize database queries:
   - Add missing indexes
   - Use connection pooling
   - Enable query cache

3. Scale horizontally:
   - Add more supervisor instances
   - Use message queue for event distribution

### Issue 4: Statistics Endpoint Timing Out

**Symptoms:**
- `/stats/*` endpoints return 500 or timeout
- High CPU usage during stats queries
- Database locks

**Diagnosis:**
```sql
-- Check audit table size
SELECT COUNT(*) FROM task_audits;

-- Check index usage
EXPLAIN QUERY PLAN
SELECT event_type, COUNT(*)
FROM task_audits
WHERE created_at >= datetime('now', '-24 hours')
GROUP BY event_type;
```

**Resolution:**
1. Add missing indexes:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_task_audits_created_at
   ON task_audits(created_at);

   CREATE INDEX IF NOT EXISTS idx_task_audits_event_type
   ON task_audits(event_type);
   ```

2. Implement result caching:
   ```python
   from functools import lru_cache
   from datetime import datetime, timedelta

   @lru_cache(maxsize=100)
   def get_cached_stats(window: str, cache_key: str):
       # cache_key includes current hour to invalidate cache
       return calculate_stats(window)

   # Usage
   cache_key = datetime.now().strftime("%Y%m%d%H")
   stats = get_cached_stats("24h", cache_key)
   ```

3. Use materialized views or summary tables:
   ```sql
   CREATE TABLE decision_stats_hourly (
     window_start TEXT PRIMARY KEY,
     decision_types TEXT,  -- JSON
     lag_p50 REAL,
     lag_p95 REAL,
     updated_at TEXT
   );
   ```

## Performance Tuning

### Database Optimization

**Required Indexes:**
```sql
-- Task audits
CREATE INDEX idx_task_audits_task_id ON task_audits(task_id);
CREATE INDEX idx_task_audits_decision_id ON task_audits(decision_id);
CREATE INDEX idx_task_audits_created_at ON task_audits(created_at);
CREATE INDEX idx_task_audits_event_type ON task_audits(event_type);

-- Task events
CREATE INDEX idx_task_events_task_id ON task_events(task_id);
CREATE INDEX idx_task_events_created_at ON task_events(created_at);

-- Supervisor inbox
CREATE INDEX idx_supervisor_inbox_task_id ON supervisor_inbox(task_id);
CREATE INDEX idx_supervisor_inbox_status ON supervisor_inbox(status);
```

**Query Optimization:**
```sql
-- Use covering indexes for common queries
CREATE INDEX idx_audits_summary ON task_audits(
  task_id, created_at, event_type, decision_id
);

-- Partial indexes for hot queries
CREATE INDEX idx_audits_recent ON task_audits(created_at)
WHERE created_at >= datetime('now', '-7 days');
```

**Connection Pooling:**
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'sqlite:///store/registry.sqlite',
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30
)
```

### API Response Caching

**Redis Cache:**
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_trace(task_id: str, limit: int, cursor: str = None):
    cache_key = f"trace:{task_id}:{limit}:{cursor}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    # Fetch from database
    trace = fetch_trace_from_db(task_id, limit, cursor)

    # Cache for 5 minutes
    redis_client.setex(cache_key, 300, json.dumps(trace))

    return trace
```

**HTTP Caching Headers:**
```python
from fastapi import Response

@router.get("/tasks/{task_id}/decision-trace")
async def get_trace(task_id: str, response: Response):
    # ... fetch trace

    # Add cache headers
    response.headers["Cache-Control"] = "private, max-age=60"
    response.headers["ETag"] = f'"{task_id}-{trace_hash}"'

    return trace
```

### Rate Limiting

**Token Bucket Rate Limiter:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.get("/tasks/{task_id}/decision-trace")
@limiter.limit("100/minute")
async def get_trace(request: Request, task_id: str):
    # ... implementation
```

## Monitoring Dashboards

### Grafana Dashboard Queries

**Decision Lag Over Time:**
```sql
SELECT
  datetime(created_at) as time,
  AVG(CAST((julianday(supervisor_processed_at) - julianday(source_event_ts)) * 86400 AS REAL)) as lag_seconds
FROM task_audits
WHERE created_at >= datetime('now', '-24 hours')
AND source_event_ts IS NOT NULL
AND supervisor_processed_at IS NOT NULL
GROUP BY datetime(created_at, 'start of hour')
ORDER BY time;
```

**Decision Type Distribution:**
```sql
SELECT
  event_type,
  COUNT(*) as count
FROM task_audits
WHERE created_at >= datetime('now', '-24 hours')
AND event_type LIKE 'SUPERVISOR_%'
GROUP BY event_type;
```

**Blocked Tasks Timeline:**
```sql
SELECT
  date(created_at) as date,
  COUNT(DISTINCT task_id) as blocked_tasks
FROM task_audits
WHERE event_type = 'SUPERVISOR_BLOCKED'
AND created_at >= datetime('now', '-30 days')
GROUP BY date
ORDER BY date;
```

## Backup and Recovery

### Backup Strategy

**Full Backup:**
```bash
# Backup database
sqlite3 store/registry.sqlite ".backup store/registry.backup.sqlite"

# Compress
gzip store/registry.backup.sqlite

# Upload to S3
aws s3 cp store/registry.backup.sqlite.gz s3://backups/registry-$(date +%Y%m%d).sqlite.gz
```

**Incremental Backup:**
```bash
# Use WAL mode for hot backups
sqlite3 store/registry.sqlite "PRAGMA journal_mode=WAL;"

# Backup WAL file
cp store/registry.sqlite-wal store/backups/registry-$(date +%Y%m%d-%H%M).wal
```

### Recovery Procedures

**Restore from Backup:**
```bash
# Restore database
gunzip -c store/registry.backup.sqlite.gz > store/registry.sqlite

# Verify integrity
sqlite3 store/registry.sqlite "PRAGMA integrity_check;"

# Restart services
systemctl restart agentos-webui
```

**Point-in-Time Recovery:**
```bash
# Restore base backup
cp backups/registry-20240128.sqlite store/registry.sqlite

# Apply WAL logs
sqlite3 store/registry.sqlite "PRAGMA wal_checkpoint(FULL);"
```

## Alerts Configuration

### Prometheus Alerts

```yaml
groups:
  - name: governance
    rules:
      - alert: HighDecisionLag
        expr: decision_lag_p95_seconds > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High decision lag detected"
          description: "Decision lag p95 is {{ $value }}s (threshold: 5s)"

      - alert: ManyBlockedTasks
        expr: blocked_tasks_count > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Many tasks are blocked"
          description: "{{ $value }} tasks are currently blocked"

      - alert: SlowTraceAPI
        expr: decision_trace_api_p95_ms > 1000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Decision trace API is slow"
          description: "p95 response time is {{ $value }}ms"
```

## References

- API Documentation: `decision_replay_api.md`
- Schema Contract: `decision_snapshot_contract.md`
- Source Code: `agentos/core/supervisor/trace/`
