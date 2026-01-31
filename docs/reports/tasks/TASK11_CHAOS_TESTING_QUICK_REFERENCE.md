# Task #11: Chaos Testing Quick Reference

**Quick access guide for running chaos tests, interpreting results, and troubleshooting.**

Version: 1.0.0 | Last Updated: 2026-01-29

---

## Quick Start

### Run All Tests

```bash
# Run everything
pytest tests/chaos/ tests/performance/ tests/stress/ -v

# Run with coverage
pytest tests/chaos/ tests/performance/ tests/stress/ \
  --cov=agentos.core.checkpoints \
  --cov=agentos.core.worker_pool \
  --cov=agentos.core.recovery \
  --cov=agentos.core.idempotency \
  --cov-report=html

# Quick smoke test (fast tests only)
pytest tests/chaos/ -m "not slow" -v
```

### Run Specific Test Categories

```bash
# Chaos tests only
pytest tests/chaos/test_chaos_scenarios.py -v -s

# Performance benchmarks only
pytest tests/performance/test_recovery_performance.py -v -s

# Stress tests only
pytest tests/stress/test_concurrent_stress.py -v -s
```

---

## Chaos Test Scenarios

### Kill -9 Recovery
```bash
pytest tests/chaos/test_chaos_scenarios.py::TestScenario1_Kill9Recovery -v -s
```
**Expected**: Checkpoints survive process kill, recovery possible
**Duration**: ~10 seconds

### Concurrent Checkpoints
```bash
pytest tests/chaos/test_chaos_scenarios.py::TestScenario2_ConcurrentCheckpoints -v -s
```
**Expected**: 90%+ success rate, no deadlocks
**Duration**: ~15 seconds

### Lease Expiration
```bash
pytest tests/chaos/test_chaos_scenarios.py::TestScenario3_LeaseExpiration -v -s
```
**Expected**: Expired lease recovered and taken over
**Duration**: ~10 seconds

### Recovery Sweep Stress
```bash
pytest tests/chaos/test_chaos_scenarios.py::TestScenario4_RecoverySweepStress -v -s
```
**Expected**: 100/100 leases recovered in < 5 seconds
**Duration**: ~10 seconds

### LLM Cache Stress
```bash
pytest tests/chaos/test_chaos_scenarios.py::TestScenario5_LLMCacheStress -v -s
```
**Expected**: 50% hit rate, 1000 cache hits
**Duration**: ~5 seconds

### Tool Replay Stress
```bash
pytest tests/chaos/test_chaos_scenarios.py::TestScenario6_ToolReplayStress -v -s
```
**Expected**: 50% replay rate, 500 replays
**Duration**: ~5 seconds

### Full E2E Recovery
```bash
pytest tests/chaos/test_chaos_scenarios.py::TestScenario7_FullE2E -v -s
```
**Expected**: Task recovers and completes after crash
**Duration**: ~15 seconds
**Note**: Marked as `@pytest.mark.slow`

---

## Performance Benchmarks

### Checkpoint Creation Latency
```bash
pytest tests/performance/test_recovery_performance.py::TestCheckpointCreationPerformance::test_checkpoint_creation_latency -v -s
```
**Target**: Average < 10ms, P95 < 20ms
**Iterations**: 100

### Checkpoint Verification Latency
```bash
pytest tests/performance/test_recovery_performance.py::TestCheckpointCreationPerformance::test_checkpoint_verification_latency -v -s
```
**Target**: Average < 15ms, P95 < 30ms
**Iterations**: 50

### LLM Cache Lookup Latency
```bash
pytest tests/performance/test_recovery_performance.py::TestLLMCachePerformance::test_llm_cache_lookup_latency -v -s
```
**Target**: Average < 5ms, P95 < 10ms
**Iterations**: 1000

### Tool Replay Latency
```bash
pytest tests/performance/test_recovery_performance.py::TestToolReplayPerformance::test_tool_replay_latency -v -s
```
**Target**: Average < 5ms, P95 < 10ms
**Iterations**: 1000

### Full Workflow Latency
```bash
pytest tests/performance/test_recovery_performance.py::TestEndToEndPerformance::test_full_checkpoint_workflow_latency -v -s
```
**Target**: Average < 30ms
**Iterations**: 50

---

## Stress Tests

### 100 Concurrent Tasks
```bash
pytest tests/stress/test_concurrent_stress.py::TestConcurrentTaskExecution::test_100_concurrent_tasks -v -s
```
**Expected**: 95%+ success rate, 475+/500 checkpoints
**Duration**: ~30 seconds
**Workers**: 100

### Database Contention
```bash
pytest tests/stress/test_concurrent_stress.py::TestConcurrentTaskExecution::test_concurrent_checkpoint_conflicts -v -s
```
**Expected**: 90%+ success rate under high contention
**Duration**: ~15 seconds
**Workers**: 20 (all on same task)

### Lease Contention
```bash
pytest tests/stress/test_concurrent_stress.py::TestWorkerPoolStress::test_lease_contention -v -s
```
**Expected**: All workers acquire leases, fair distribution
**Duration**: ~10 seconds
**Workers**: 20

### Recovery Sweep Large Scale
```bash
pytest tests/stress/test_concurrent_stress.py::TestRecoverySweepStress::test_recovery_sweep_large_scale -v -s
```
**Expected**: 1000/1000 recovered in < 10 seconds
**Duration**: ~10 seconds
**Items**: 1000

---

## Interpreting Results

### Success Indicators

✅ **All Tests Pass**
```
======================= 17 passed in 5.23s =======================
```

✅ **Performance Metrics Within Thresholds**
```
Checkpoint Creation Performance:
  Average:    5.23ms  ✓ (threshold: 10ms)
  P95:        12.45ms ✓ (threshold: 20ms)
```

✅ **High Success Rate Under Stress**
```
Concurrent Task Execution Results:
  Successes:    96/100 (96.0%) ✓ (threshold: 95%)
  Checkpoints:  480/500        ✓ (threshold: 475)
```

### Warning Indicators

⚠️ **Marginal Performance**
```
Checkpoint Creation Performance:
  Average:    9.87ms  ⚠️ (near threshold: 10ms)
  P95:        19.23ms ⚠️ (near threshold: 20ms)
```
**Action**: Monitor in production, consider optimization

⚠️ **High Failure Rate**
```
Concurrent Task Execution Results:
  Successes:    92/100 (92.0%) ⚠️ (below threshold: 95%)
  Failures:     8/100  (8.0%)
```
**Action**: Investigate failures, check database configuration

### Failure Indicators

❌ **Test Failure**
```
FAILED tests/chaos/test_chaos_scenarios.py::TestScenario1_Kill9Recovery
AssertionError: No checkpoints created before crash
```
**Action**: Check database permissions, verify schema

❌ **Performance Degradation**
```
Checkpoint Creation Performance:
  Average:    25.43ms  ❌ (threshold: 10ms)
  P95:        52.11ms  ❌ (threshold: 20ms)
```
**Action**: Check database size, run VACUUM, check disk I/O

---

## Common Issues & Quick Fixes

### Issue: Database Locked

**Symptoms**:
```
sqlite3.OperationalError: database is locked
```

**Quick Fix**:
```python
# Enable WAL mode
import sqlite3
conn = sqlite3.connect("store/registry.sqlite")
conn.execute("PRAGMA journal_mode = WAL")
conn.commit()
```

---

### Issue: Tests Hang

**Symptoms**:
- Tests don't complete
- Process stuck in sleep

**Quick Fix**:
```bash
# Run with timeout
pytest tests/chaos/ --timeout=60 -v

# Kill stuck processes
ps aux | grep pytest | awk '{print $2}' | xargs kill -9
```

---

### Issue: Import Errors

**Symptoms**:
```
ModuleNotFoundError: No module named 'agentos'
```

**Quick Fix**:
```bash
# Ensure correct Python path
export PYTHONPATH=/Users/pangge/PycharmProjects/AgentOS:$PYTHONPATH

# Or install in development mode
pip install -e .
```

---

### Issue: Low Cache Hit Rate

**Symptoms**:
```
LLM cache hit rate: 15.2% ⚠️ (expected: 50%)
```

**Diagnosis**:
```python
from agentos.core.idempotency import LLMOutputCache

cache = LLMOutputCache()
stats = cache.get_stats()
print(f"Hits: {stats['cache_hits']}, Misses: {stats['cache_misses']}")

# Check cache contents
from agentos.store import get_db
conn = get_db()
cursor = conn.execute("SELECT COUNT(*) FROM idempotency_keys WHERE idempotency_key LIKE 'llm-cache:%'")
print(f"Cache entries: {cursor.fetchone()[0]}")
```

**Quick Fix**:
- Verify prompts are identical (whitespace matters)
- Check cache expiration settings
- Clear and rebuild cache if corrupted

---

### Issue: Checkpoint Verification Failures

**Symptoms**:
```
CheckpointError: Checkpoint verification failed
```

**Diagnosis**:
```python
from agentos.core.checkpoints import CheckpointManager

manager = CheckpointManager()
checkpoint = manager.get_checkpoint("ckpt-abc123")

if checkpoint:
    print(f"Verified: {checkpoint.verified}")
    print(f"Evidence: {checkpoint.evidence_pack.to_dict()}")

    # Try to verify manually
    is_valid = manager.verify_checkpoint(checkpoint.checkpoint_id)
    print(f"Manual verification: {is_valid}")
```

**Quick Fix**:
- Use simpler evidence types (COMMAND_EXIT instead of ARTIFACT_EXISTS)
- Disable auto_verify temporarily: `CheckpointManager(auto_verify=False)`
- Check file paths exist

---

### Issue: Recovery Sweep Slow

**Symptoms**:
```
Recovery sweep completed in 25.43s ❌ (threshold: 10s)
```

**Diagnosis**:
```python
from agentos.core.recovery import RecoverySweep
from agentos.store import get_db

conn = get_db()
sweep = RecoverySweep(conn)
stats = sweep.scan_and_recover()

print(f"Duration: {stats.scan_duration_ms}ms")
print(f"Expired: {stats.expired_found}")
print(f"Errors: {stats.errors}")
```

**Quick Fix**:
```sql
-- Add missing index
CREATE INDEX IF NOT EXISTS idx_work_items_lease
ON work_items(lease_expires_at)
WHERE status = 'in_progress';

-- Analyze query performance
EXPLAIN QUERY PLAN
SELECT work_item_id FROM work_items
WHERE status = 'in_progress' AND lease_expires_at < CURRENT_TIMESTAMP;
```

---

## Production Checklist

### Pre-Flight

- [ ] All chaos tests pass
- [ ] All performance benchmarks within thresholds
- [ ] All stress tests pass with 95%+ success
- [ ] Database WAL mode enabled
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Team trained on recovery procedures

### Post-Deploy

- [ ] Smoke test in production
- [ ] Monitor checkpoint creation rate
- [ ] Monitor lease expiration rate
- [ ] Monitor cache hit rates
- [ ] Check for database lock errors
- [ ] Verify alert thresholds appropriate
- [ ] Schedule periodic checkpoint cleanup

---

## Monitoring Queries

### Check Checkpoint Health

```sql
-- Recent checkpoint creation rate
SELECT
    DATE(created_at) as date,
    COUNT(*) as checkpoints_created
FROM checkpoints
WHERE created_at > datetime('now', '-7 days')
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Checkpoint types distribution
SELECT
    checkpoint_type,
    COUNT(*) as count,
    AVG(sequence_number) as avg_sequence
FROM checkpoints
GROUP BY checkpoint_type;
```

### Check Lease Health

```sql
-- Expired leases
SELECT COUNT(*) as expired_leases
FROM work_items
WHERE status = 'in_progress'
  AND lease_expires_at < CURRENT_TIMESTAMP;

-- Lease duration distribution
SELECT
    lease_holder,
    COUNT(*) as leases_held,
    AVG((julianday(lease_expires_at) - julianday(lease_acquired_at)) * 24 * 60) as avg_duration_minutes
FROM work_items
WHERE status = 'in_progress'
GROUP BY lease_holder;
```

### Check Cache Health

```sql
-- Cache hit rate (LLM)
SELECT
    COUNT(*) as total_entries,
    SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as succeeded,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
FROM idempotency_keys
WHERE idempotency_key LIKE 'llm-cache:%';

-- Cache age distribution
SELECT
    CASE
        WHEN julianday('now') - julianday(created_at) < 1 THEN '< 1 day'
        WHEN julianday('now') - julianday(created_at) < 7 THEN '1-7 days'
        WHEN julianday('now') - julianday(created_at) < 30 THEN '7-30 days'
        ELSE '> 30 days'
    END as age_bucket,
    COUNT(*) as count
FROM idempotency_keys
GROUP BY age_bucket;
```

---

## Performance Tuning Tips

### Database Optimization

```sql
-- Enable WAL mode (if not already)
PRAGMA journal_mode = WAL;

-- Increase cache size
PRAGMA cache_size = -64000;  -- 64MB

-- Use memory for temp tables
PRAGMA temp_store = MEMORY;

-- Optimize for performance
PRAGMA synchronous = NORMAL;

-- Enable memory-mapped I/O
PRAGMA mmap_size = 268435456;  -- 256MB

-- Analyze tables for query optimization
ANALYZE;
```

### Index Maintenance

```sql
-- Check index usage
SELECT name, tbl_name FROM sqlite_master WHERE type = 'index';

-- Add missing indexes
CREATE INDEX IF NOT EXISTS idx_checkpoints_task_seq
ON checkpoints(task_id, sequence_number DESC);

CREATE INDEX IF NOT EXISTS idx_work_items_status_priority
ON work_items(status, priority DESC);

-- Rebuild indexes if fragmented
REINDEX;
```

### Checkpoint Cleanup

```sql
-- Find tasks with excessive checkpoints
SELECT
    task_id,
    COUNT(*) as checkpoint_count
FROM checkpoints
GROUP BY task_id
HAVING COUNT(*) > 100
ORDER BY checkpoint_count DESC;

-- Clean up old checkpoints (keep last 100 per task)
DELETE FROM checkpoints
WHERE checkpoint_id IN (
    SELECT checkpoint_id
    FROM checkpoints c1
    WHERE (
        SELECT COUNT(*)
        FROM checkpoints c2
        WHERE c2.task_id = c1.task_id
          AND c2.sequence_number > c1.sequence_number
    ) >= 100
);
```

---

## Contact & Support

**Documentation**: [TASK11_CHAOS_TESTING_COMPLETION.md](./TASK11_CHAOS_TESTING_COMPLETION.md)

**Test Files**:
- Chaos: `tests/chaos/test_chaos_scenarios.py`
- Performance: `tests/performance/test_recovery_performance.py`
- Stress: `tests/stress/test_concurrent_stress.py`

**Recovery System Components**:
- CheckpointManager: `agentos/core/checkpoints/manager.py`
- LeaseManager: `agentos/core/worker_pool/lease.py`
- RecoverySweep: `agentos/core/recovery/recovery_sweep.py`
- LLMOutputCache: `agentos/core/idempotency/llm_cache.py`
- ToolLedger: `agentos/core/idempotency/tool_ledger.py`

---

**Last Updated**: 2026-01-29
**Version**: 1.0.0
