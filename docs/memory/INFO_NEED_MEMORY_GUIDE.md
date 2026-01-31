# InfoNeed Judgment Memory System Guide

## Overview

The InfoNeed Judgment Memory System (Task #22) implements short-term memory storage for InfoNeed classification decisions in MemoryOS. This enables pattern recognition, system evolution, and performance analysis.

## Core Principle

**Remember HOW we judged, not WHAT we remembered**

- ✅ Store: Question → Classification → Decision Basis → Outcome
- ❌ Don't store: External facts, content summaries, semantic analysis

## Architecture

```
User Question
    ↓
InfoNeedClassifier.classify()
    ↓ (automatic)
InfoNeedMemoryWriter.write_judgment()
    ↓
MemoryOS (info_need_judgments table)
    ↓
Query/Analysis/Feedback
```

## Components

### 1. Schema (`agentos/core/memory/schema.py`)

**InfoNeedJudgment** - Core data model:
- Identifiers: `judgment_id`, `session_id`, `message_id`
- Input: `question_text`, `question_hash` (for deduplication)
- Judgment: `classified_type`, `confidence_level`, `decision_action`
- Basis: `rule_signals`, `llm_confidence_score`, `decision_latency_ms`
- Outcome: `outcome`, `user_action`, `outcome_timestamp`
- Context: `phase`, `mode`, `trust_tier`

### 2. Writer (`agentos/core/memory/info_need_writer.py`)

**InfoNeedMemoryWriter** - Core API:

```python
from agentos.core.memory.info_need_writer import InfoNeedMemoryWriter

writer = InfoNeedMemoryWriter(ttl_days=30)

# Write judgment (automatic from classifier)
judgment_id = await writer.write_judgment(
    classification_result=result,
    session_id="session-123",
    message_id="msg-456",
    question_text="What is the latest Python version?",
    phase="planning",
    mode="conversation",
    latency_ms=125.5
)

# Update outcome (user feedback)
await writer.update_judgment_outcome(
    judgment_id=judgment_id,
    outcome="user_proceeded",
    user_action="used_communication"
)

# Query recent judgments
judgments = await writer.query_recent_judgments(
    session_id="session-123",
    time_range="24h",
    limit=100
)

# Find similar questions (deduplication)
similar = await writer.find_similar_judgment(
    question_hash="abc123...",
    time_window=timedelta(hours=24)
)

# Get statistics
stats = await writer.get_judgment_stats(
    session_id="session-123",
    time_range="7d"
)

# Cleanup old data (TTL)
deleted = await writer.cleanup_old_judgments()
```

### 3. Database Schema (Migration v38)

**Table: info_need_judgments**

```sql
CREATE TABLE info_need_judgments (
    judgment_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL UNIQUE,
    question_text TEXT NOT NULL,
    question_hash TEXT NOT NULL,
    classified_type TEXT NOT NULL,
    confidence_level TEXT NOT NULL,
    decision_action TEXT NOT NULL,
    rule_signals TEXT NOT NULL,  -- JSON
    llm_confidence_score REAL NOT NULL,
    decision_latency_ms REAL NOT NULL,
    outcome TEXT NOT NULL DEFAULT 'pending',
    user_action TEXT,
    outcome_timestamp TEXT,
    phase TEXT NOT NULL,
    mode TEXT,
    trust_tier TEXT
);
```

**Indexes:**
- `idx_info_need_judgments_session_id` - Session queries
- `idx_info_need_judgments_classified_type` - Type analysis
- `idx_info_need_judgments_outcome` - Outcome tracking
- `idx_info_need_judgments_question_hash` - Deduplication
- `idx_info_need_judgments_timestamp` - Time-range queries
- `idx_info_need_judgments_composite` - Complex queries

## Integration

### Automatic Integration with InfoNeedClassifier

The classifier automatically writes to MemoryOS:

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

classifier = InfoNeedClassifier()
result = await classifier.classify(
    message="What is the latest Python version?",
    session_id="session-123"
)

# Judgment is automatically written to MemoryOS
# result.message_id can be used to update outcome later
```

### Manual Outcome Updates (ChatEngine Integration)

```python
from agentos.core.memory.info_need_writer import InfoNeedMemoryWriter

# After processing user response
writer = InfoNeedMemoryWriter()
await writer.update_judgment_outcome_by_message_id(
    message_id=result.message_id,
    outcome="user_proceeded",
    user_action="used_web_search"
)
```

## Use Cases

### 1. Pattern Analysis

Find patterns in user information needs:

```python
# Get all external fact queries in last 7 days
judgments = await writer.query_recent_judgments(
    classified_type="external_fact_uncertain",
    time_range="7d",
    limit=1000
)

# Analyze patterns
for judgment in judgments:
    print(f"Q: {judgment.question_text}")
    print(f"Signals: {judgment.rule_signals}")
    print(f"Outcome: {judgment.outcome}")
```

### 2. Deduplication

Avoid re-classifying identical questions:

```python
question = "What is the latest Python version?"
question_hash = InfoNeedJudgment.create_question_hash(question)

# Check if we've seen this recently
similar = await writer.find_similar_judgment(
    question_hash=question_hash,
    time_window=timedelta(hours=1)
)

if similar:
    # Reuse previous judgment
    print(f"Using cached judgment: {similar.decision_action}")
else:
    # Classify new question
    result = await classifier.classify(question)
```

### 3. Performance Monitoring

Track classification performance:

```python
stats = await writer.get_judgment_stats(
    time_range="24h"
)

print(f"Total judgments: {stats['total_judgments']}")
print(f"Avg latency: {stats['avg_latency_ms']:.2f}ms")
print(f"By type: {stats['by_type']}")
print(f"By outcome: {stats['by_outcome']}")
```

### 4. User Feedback Analysis

Analyze how users respond to decisions:

```python
# Get all user_declined outcomes
declined = await writer.query_recent_judgments(
    outcome="user_declined",
    time_range="7d"
)

# Analyze what types of decisions users reject
for judgment in declined:
    print(f"Type: {judgment.classified_type}")
    print(f"Action: {judgment.decision_action}")
    print(f"User said: {judgment.user_action}")
```

### 5. Session Replay

Replay a user's information need history:

```python
session_history = await writer.query_recent_judgments(
    session_id="session-123",
    time_range="24h"
)

for judgment in session_history:
    print(f"[{judgment.timestamp}] {judgment.question_text}")
    print(f"  → {judgment.decision_action} ({judgment.outcome})")
```

## Difference from Audit Logs

| Feature | Audit Logs | MemoryOS |
|---------|-----------|----------|
| Purpose | Compliance, debugging | Pattern recognition, evolution |
| Mutability | Immutable | Outcomes updated |
| Structure | Event stream | Queryable records |
| Retention | Long-term | TTL-based (30 days default) |
| Query | By task/event | By session/type/outcome |

**Both are complementary:**
- Audit logs provide the immutable event stream
- MemoryOS provides structured, queryable memory

## Configuration

### TTL Configuration

```python
# Default: 30 days
writer = InfoNeedMemoryWriter(ttl_days=30)

# Custom retention
writer = InfoNeedMemoryWriter(ttl_days=7)  # 1 week

# Run cleanup
deleted = await writer.cleanup_old_judgments()
```

### Batch Cleanup (Scheduled Job)

```python
# In scheduled task or cron job
from agentos.core.memory.info_need_writer import InfoNeedMemoryWriter

async def cleanup_job():
    writer = InfoNeedMemoryWriter(ttl_days=30)
    deleted = await writer.cleanup_old_judgments()
    print(f"Cleaned up {deleted} old judgments")
```

## Performance Considerations

### Write Performance
- Async non-blocking writes
- Typical latency: < 10ms
- Does not impact classification performance

### Query Performance
- Indexed by session, type, outcome, timestamp
- Composite index for complex queries
- Typical query: < 50ms for 1000 records

### Storage
- ~1KB per judgment
- 10,000 judgments/day = ~10MB/day
- 30-day retention = ~300MB

## Testing

### Unit Tests (17 tests, ≥90% coverage)

```bash
pytest tests/unit/core/memory/test_info_need_writer.py -v
```

### Integration Tests (7 E2E tests)

```bash
pytest tests/integration/memory/test_info_need_memory_e2e.py -v
```

## Migration

Apply schema migration:

```bash
# Migration runs automatically on first database access
# Or manually:
sqlite3 store/registry.sqlite < agentos/store/migrations/schema_v38_info_need_judgments.sql
```

## Troubleshooting

### Write Failures

Check logs for MemoryOS write failures (non-blocking):

```python
# Logs will show warnings but won't break classification
# Check: logs/agentos.log
```

### Query Performance

If queries are slow:

```sql
-- Check index usage
EXPLAIN QUERY PLAN
SELECT * FROM info_need_judgments
WHERE session_id = ? AND timestamp >= ?;

-- Analyze table
ANALYZE info_need_judgments;
```

### Cleanup Issues

If TTL cleanup fails:

```python
# Manual cleanup
import asyncio
from agentos.core.memory.info_need_writer import InfoNeedMemoryWriter

async def manual_cleanup():
    writer = InfoNeedMemoryWriter(ttl_days=30)
    try:
        deleted = await writer.cleanup_old_judgments()
        print(f"Deleted {deleted} records")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(manual_cleanup())
```

## Future Enhancements

Planned features:
- ML-based pattern detection
- Automatic classification improvement based on outcomes
- Cross-session similarity detection
- Performance prediction models

## References

- Task #19: AuditLogger InfoNeed support
- Task #20: InfoNeed quality metrics
- Task #22: MemoryOS judgment storage (this document)
- Task #23: BrainOS decision pattern nodes
