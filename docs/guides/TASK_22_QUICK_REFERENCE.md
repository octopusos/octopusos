# Task #22 Quick Reference - InfoNeed Memory System

## Quick Start

### 1. Basic Usage

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier
from agentos.core.memory.info_need_writer import InfoNeedMemoryWriter

# Classification automatically writes to MemoryOS
classifier = InfoNeedClassifier()
result = await classifier.classify(
    message="What is the latest Python version?",
    session_id="my-session"
)

# Query judgments
writer = InfoNeedMemoryWriter()
judgments = await writer.query_recent_judgments(
    session_id="my-session",
    time_range="24h"
)
```

### 2. Update Outcome (User Feedback)

```python
# After user responds
await writer.update_judgment_outcome_by_message_id(
    message_id=result.message_id,
    outcome="user_proceeded",
    user_action="used_web_search"
)
```

### 3. Deduplication Check

```python
from agentos.core.memory.schema import InfoNeedJudgment

question_hash = InfoNeedJudgment.create_question_hash(question)
similar = await writer.find_similar_judgment(
    question_hash=question_hash,
    time_window=timedelta(hours=1)
)

if similar:
    # Reuse previous judgment
    print(f"Using cached: {similar.decision_action}")
```

### 4. Get Statistics

```python
stats = await writer.get_judgment_stats(
    session_id="my-session",
    time_range="7d"
)

print(f"Total: {stats['total_judgments']}")
print(f"Avg latency: {stats['avg_latency_ms']:.2f}ms")
print(f"By type: {stats['by_type']}")
```

### 5. Cleanup Old Data

```python
writer = InfoNeedMemoryWriter(ttl_days=30)
deleted = await writer.cleanup_old_judgments()
print(f"Deleted {deleted} old judgments")
```

## API Reference

### InfoNeedMemoryWriter

| Method | Description |
|--------|-------------|
| `write_judgment()` | Write judgment to MemoryOS |
| `update_judgment_outcome()` | Update outcome by judgment_id |
| `update_judgment_outcome_by_message_id()` | Update outcome by message_id |
| `query_recent_judgments()` | Query with filters |
| `find_similar_judgment()` | Find by question hash |
| `get_judgment_by_id()` | Get single judgment |
| `get_judgment_stats()` | Get statistics |
| `cleanup_old_judgments()` | TTL cleanup |

### InfoNeedJudgment Fields

| Field | Type | Description |
|-------|------|-------------|
| `judgment_id` | str | Unique ID |
| `session_id` | str | Session ID |
| `message_id` | str | Message ID (unique) |
| `question_text` | str | Original question |
| `question_hash` | str | For deduplication |
| `classified_type` | InfoNeedType | Classification |
| `confidence_level` | ConfidenceLevel | Confidence |
| `decision_action` | DecisionAction | Decision |
| `rule_signals` | dict | Rule signals |
| `llm_confidence_score` | float | LLM score (0-1) |
| `decision_latency_ms` | float | Latency |
| `outcome` | JudgmentOutcome | Outcome |
| `user_action` | str | User action |
| `outcome_timestamp` | datetime | When updated |
| `phase` | str | planning/execution |
| `mode` | str | conversation/task/automation |
| `trust_tier` | str | Trust tier |

### Enums

**InfoNeedType:**
- `local_deterministic`
- `local_knowledge`
- `ambient_state`
- `external_fact_uncertain`
- `opinion`

**ConfidenceLevel:**
- `high`
- `medium`
- `low`

**DecisionAction:**
- `direct_answer`
- `local_capability`
- `require_comm`
- `suggest_comm`

**JudgmentOutcome:**
- `user_proceeded`
- `user_declined`
- `system_fallback`
- `pending`

## Database Schema

**Table:** `info_need_judgments`

**Indexes:**
- `idx_info_need_judgments_session_id`
- `idx_info_need_judgments_classified_type`
- `idx_info_need_judgments_outcome`
- `idx_info_need_judgments_question_hash`
- `idx_info_need_judgments_timestamp`
- `idx_info_need_judgments_composite`

## Testing

```bash
# Unit tests (17 tests)
pytest tests/unit/core/memory/test_info_need_writer.py -v

# Integration tests (7 tests)
pytest tests/integration/memory/test_info_need_memory_e2e.py -v

# Coverage
pytest tests/unit/core/memory/ tests/integration/memory/ \
    --cov=agentos.core.memory --cov-report=term-missing

# Run examples
python3 examples/info_need_memory_usage.py
```

## Files

**Core Implementation:**
- `/agentos/core/memory/schema.py` - Data models
- `/agentos/core/memory/info_need_writer.py` - Writer API
- `/agentos/store/migrations/schema_v38_info_need_judgments.sql` - DB schema

**Tests:**
- `/tests/unit/core/memory/test_info_need_writer.py` - Unit tests
- `/tests/integration/memory/test_info_need_memory_e2e.py` - E2E tests

**Documentation:**
- `/docs/memory/INFO_NEED_MEMORY_GUIDE.md` - Complete guide
- `/examples/info_need_memory_usage.py` - Usage examples
- `/TASK_22_ACCEPTANCE_REPORT.md` - Acceptance report
- `/TASK_22_QUICK_REFERENCE.md` - This file

## Common Patterns

### Pattern 1: Session Analysis

```python
judgments = await writer.query_recent_judgments(
    session_id="session-123",
    time_range="24h"
)

for j in judgments:
    print(f"Q: {j.question_text}")
    print(f"Type: {j.classified_type.value}")
    print(f"Action: {j.decision_action.value}")
    print(f"Outcome: {j.outcome.value}")
```

### Pattern 2: Type-based Analysis

```python
external_facts = await writer.query_recent_judgments(
    classified_type="external_fact_uncertain",
    time_range="7d"
)

print(f"External fact queries: {len(external_facts)}")
```

### Pattern 3: Outcome Analysis

```python
declined = await writer.query_recent_judgments(
    outcome="user_declined",
    time_range="7d"
)

# Analyze what users rejected
for j in declined:
    print(f"Rejected: {j.decision_action.value}")
    print(f"Question: {j.question_text}")
```

### Pattern 4: Performance Monitoring

```python
stats = await writer.get_judgment_stats(time_range="24h")

if stats["avg_latency_ms"] > 200:
    print("WARNING: High latency detected")

print(f"Success rate: {
    stats['by_outcome'].get('user_proceeded', 0) /
    stats['total_judgments'] * 100
}%")
```

## Troubleshooting

**Issue:** Judgment not written to MemoryOS
- Check logs for write errors (non-blocking failures)
- Verify database schema v38 is applied
- Check database permissions

**Issue:** Slow queries
- Verify indexes are created
- Run `ANALYZE info_need_judgments;`
- Check query filters are using indexed columns

**Issue:** High storage usage
- Run cleanup: `await writer.cleanup_old_judgments()`
- Adjust TTL: `InfoNeedMemoryWriter(ttl_days=7)`
- Consider more aggressive retention policy

## Performance Tips

1. **Batch Queries:** Use time_range filters to limit results
2. **Index Usage:** Filter by indexed columns (session_id, timestamp, etc.)
3. **Cleanup Schedule:** Run cleanup_old_judgments() daily via cron
4. **Monitoring:** Track avg_latency_ms and total_judgments trends

## Next Steps

After Task #22, consider:
- Task #21: WebUI Dashboard for judgment analytics
- Task #23: BrainOS decision pattern nodes
- Task #24: Multi-intent question splitter
- Implement automated cleanup scheduling
- Add ML-based pattern detection

## Support

- Full Guide: `/docs/memory/INFO_NEED_MEMORY_GUIDE.md`
- Examples: `/examples/info_need_memory_usage.py`
- Tests: `/tests/unit/core/memory/` and `/tests/integration/memory/`
- Report: `/TASK_22_ACCEPTANCE_REPORT.md`
