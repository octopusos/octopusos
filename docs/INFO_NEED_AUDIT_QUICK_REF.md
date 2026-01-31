# InfoNeed Audit System - Quick Reference

**Task #19 Completion Summary** | 2026-01-31

## What Was Built

Extended AuditLogger to support InfoNeed classification audit events, enabling quality metrics computation through observable user behavior.

## Core Principle

✅ **Evaluate whether judgments are validated/disproven by reality**
❌ **NOT whether answers are semantically correct**

This is the only automatable, hallucination-free evaluation approach.

## Event Types

### INFO_NEED_CLASSIFICATION

Records classification decisions:

```python
await log_info_need_classification(
    message_id="uuid",
    session_id="session-id",
    question="What is the latest Python version?",
    classified_type="EXTERNAL_FACT_UNCERTAIN",
    confidence="low",
    decision="REQUIRE_COMM",
    signals={...},
    rule_matches=[...],
    llm_confidence={...},
    latency_ms=45.3
)
```

### INFO_NEED_OUTCOME

Records actual outcomes:

```python
await log_info_need_outcome(
    message_id="uuid",
    outcome="validated",  # validated | unnecessary_comm | user_corrected | user_cancelled
    user_action="/comm search ...",
    notes="Optional explanation"
)
```

## Quick Usage

### Automatic Logging (Recommended)

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

classifier = InfoNeedClassifier()
result = await classifier.classify(
    message="What is the weather?",
    session_id="session-123"
)

# Classification automatically logged
# Use result.message_id for outcome correlation
```

### Manual Outcome Logging

```python
from agentos.core.audit import log_info_need_outcome

await log_info_need_outcome(
    message_id=result.message_id,
    outcome="validated",
    user_action="/comm search weather"
)
```

### Querying Events

```python
from agentos.core.audit import (
    get_info_need_classification_events,
    get_info_need_outcomes_for_message,
    find_audit_event_by_metadata,
    INFO_NEED_CLASSIFICATION
)

# Get all REQUIRE_COMM decisions
events = get_info_need_classification_events(
    decision="REQUIRE_COMM",
    limit=100
)

# Get outcomes for a specific message
outcomes = get_info_need_outcomes_for_message("msg-id")

# Find classification by message_id
event = find_audit_event_by_metadata(
    event_type=INFO_NEED_CLASSIFICATION,
    metadata_key="message_id",
    metadata_value="msg-123"
)
```

## Key Features

✅ **Non-Blocking**: Audit failures never break main flow
✅ **Async-Safe**: Full async support with `log_audit_event_async()`
✅ **Correlated**: `message_id` links classification to outcome
✅ **Queryable**: Filter by session, decision, outcome, etc.
✅ **Semantic Preservation**: None values explicitly stored
✅ **Tested**: 13 unit tests, all passing

## Files Modified

| File | Changes |
|------|---------|
| `agentos/core/audit.py` | Added 2 event types, 6 helper functions, async support |
| `agentos/core/chat/info_need_classifier.py` | Integrated audit logging, added session_id param |
| `agentos/core/chat/models/info_need.py` | Added message_id field, fixed datetime warnings |

## Testing

```bash
# Run unit tests
python3 -m pytest tests/unit/core/test_info_need_audit.py -v

# Run demo
python3 examples/info_need_audit_demo.py
```

## Performance

- Classification overhead: <1ms
- Async overhead: <0.1ms (non-blocking)
- Query single event: O(log n)
- Storage: ~500 bytes per classification

## Outcome Types Explained

| Outcome | Meaning | Example |
|---------|---------|---------|
| `validated` | User executed suggested action | User ran `/comm search` as suggested |
| `unnecessary_comm` | System over-suggested communication | System said REQUIRE_COMM but user knew answer |
| `user_corrected` | User corrected classification | User said "you should search for that" |
| `user_cancelled` | User cancelled operation | User abandoned the interaction |

## Quality Metrics (Task #20)

Audit data enables these metrics:

```python
# Accuracy
accuracy = validated / (validated + corrected)

# Precision by decision type
precision_require_comm = validated_require_comm / total_require_comm

# Signal strength correlation
high_signal_accuracy = compute_accuracy(signal_strength > 0.8)
```

## Next Steps

- **Task #20**: Implement quality metrics computation
- **Task #21**: Create metrics WebUI dashboard
- **Task #22**: Store judgment history in MemoryOS
- **Task #23**: Create decision mode nodes in BrainOS

## References

- Full documentation: `docs/INFO_NEED_AUDIT_IMPLEMENTATION.md`
- Test suite: `tests/unit/core/test_info_need_audit.py`
- Demo script: `examples/info_need_audit_demo.py`
- Core implementation: `agentos/core/audit.py`

## Example Output

```
Classification Result:
  Type: external_fact_uncertain
  Decision: require_comm
  Confidence: low
  Message ID: 8f4c66cb-a568-4e12-98af-04c363f412dc

Audit Event Created:
  Audit ID: 6291
  Event Type: INFO_NEED_CLASSIFICATION
  Latency: 0.65ms
  Signal Strength: 0.85

Outcome Logged:
  Result: validated
  Action: /comm search latest Python version
  Latency: 4.27ms
```

## Design Principles

1. **Non-Blocking**: Audit failures never break business logic
2. **Immutable**: Events are append-only records
3. **Explicit Correlation**: Use message_id, not timestamps
4. **Semantic Preservation**: Store None explicitly
5. **Observable Behavior**: Track user actions, not answer correctness

---

**Status**: ✅ Completed
**Tests**: 13/13 passing
**Documentation**: Complete
**Demo**: Working
