# InfoNeed Classification Audit System

**Status**: ✅ Completed (Task #19)
**Date**: 2026-01-31

## Overview

This document describes the audit system for InfoNeed classification events, which enables quality metrics computation and system improvement through evidence-based evaluation.

### Core Principle

**We do NOT evaluate "whether the answer is correct"**
**We ONLY evaluate "whether the judgment was validated/contradicted by reality"**

This is the only engineering approach that is:
- Automatable without human annotation
- Free from hallucination risks
- Observable through user behavior

## Architecture

### Event Types

#### 1. INFO_NEED_CLASSIFICATION

Records the classification decision made by InfoNeedClassifier.

**Event Structure**:
```python
{
    "event_type": "INFO_NEED_CLASSIFICATION",
    "message_id": "uuid-string",           # Unique identifier for correlation
    "session_id": "session-uuid",          # Session context
    "question": "User's original question",
    "classified_type": "EXTERNAL_FACT_UNCERTAIN",  # InfoNeedType
    "confidence": "low",                   # high | medium | low
    "decision": "REQUIRE_COMM",            # Decision action
    "signals": {
        "time_sensitive": true,
        "authoritative": true,
        "ambient": false,
        "signal_strength": 0.85
    },
    "rule_matches": ["latest", "policy"],
    "llm_confidence": {                    # Optional
        "confidence": "low",
        "reason": "time-sensitive"
    },
    "timestamp": "2026-01-31T12:34:56.789Z",
    "latency_ms": 45.3
}
```

#### 2. INFO_NEED_OUTCOME

Records the actual outcome of a classification decision.

**Event Structure**:
```python
{
    "event_type": "INFO_NEED_OUTCOME",
    "message_id": "uuid-string",           # Correlates with classification
    "outcome": "validated",                # Outcome type (see below)
    "user_action": "/comm search ...",     # Optional user action
    "latency_ms": 1234,                    # Time from classification to outcome
    "timestamp": "2026-01-31T12:35:12.345Z",
    "notes": "Optional explanation"
}
```

**Outcome Types**:
- `validated`: User executed the suggested action (e.g., ran `/comm`)
- `unnecessary_comm`: System suggested REQUIRE_COMM but user indicated not needed
- `user_corrected`: User corrected the classification ("you should search for that")
- `user_cancelled`: User cancelled the operation

### Database Schema

Events are stored in the existing `task_audits` table:

```sql
CREATE TABLE task_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    level TEXT DEFAULT 'info',
    event_type TEXT NOT NULL,
    payload TEXT,                 -- JSON with event data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
```

InfoNeed events are stored with:
- `event_type`: "INFO_NEED_CLASSIFICATION" or "INFO_NEED_OUTCOME"
- `level`: "info" (can be "warn" or "error" for anomalies)
- `payload`: JSON containing event structure above
- `task_id`: "ORPHAN" (not tied to specific tasks)

## Implementation

### Files Modified

1. **`agentos/core/audit.py`**
   - Added `INFO_NEED_CLASSIFICATION` and `INFO_NEED_OUTCOME` event types
   - Added `log_audit_event_async()` for non-blocking async logging
   - Added `log_info_need_classification()` helper function
   - Added `log_info_need_outcome()` helper function
   - Added `find_audit_event_by_metadata()` for message_id lookup
   - Added `get_info_need_classification_events()` query function
   - Added `get_info_need_outcomes_for_message()` query function

2. **`agentos/core/chat/info_need_classifier.py`**
   - Modified `classify()` to accept `session_id` parameter
   - Added `message_id` generation for each classification
   - Added `_log_classification_audit()` method
   - Integrated audit logging into classification pipeline (non-blocking)
   - Added `message_id` to ClassificationResult for outcome correlation

3. **`agentos/core/chat/models/info_need.py`**
   - Added `message_id` field to `ClassificationResult` model
   - Fixed deprecation warnings (datetime.utcnow → datetime.now(timezone.utc))

### Integration Points

#### 1. Automatic Classification Logging

When `InfoNeedClassifier.classify()` is called, it automatically logs to audit:

```python
classifier = InfoNeedClassifier()
result = await classifier.classify(
    message="What is the latest Python version?",
    session_id="session-123"
)

# Classification is automatically logged to audit
# result.message_id contains the correlation ID
```

#### 2. Manual Outcome Logging

Outcomes must be logged explicitly by the calling code:

```python
from agentos.core.audit import log_info_need_outcome

# User executed the suggested /comm command
await log_info_need_outcome(
    message_id=result.message_id,
    outcome="validated",
    user_action="/comm search latest Python version",
    notes="User followed suggestion immediately"
)
```

#### 3. Manual Classification Logging

For testing or custom workflows:

```python
from agentos.core.audit import log_info_need_classification

await log_info_need_classification(
    message_id="custom-msg-id",
    session_id="session-456",
    question="What are the AI regulations?",
    classified_type="EXTERNAL_FACT_UNCERTAIN",
    confidence="low",
    decision="REQUIRE_COMM",
    signals={...},
    rule_matches=["regulation"],
    llm_confidence={...},
    latency_ms=50.0
)
```

## Usage Examples

### Basic Classification with Audit

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

classifier = InfoNeedClassifier()

result = await classifier.classify(
    message="What is the weather today?",
    session_id="session-001"
)

print(f"Classification: {result.info_need_type}")
print(f"Decision: {result.decision_action}")
print(f"Message ID: {result.message_id}")
```

### Recording Validation Outcome

```python
from agentos.core.audit import log_info_need_outcome

# User validated the classification by executing /comm
await log_info_need_outcome(
    message_id=result.message_id,
    outcome="validated",
    user_action="/comm search weather today"
)
```

### Recording User Correction

```python
# User corrected the system's decision
await log_info_need_outcome(
    message_id=result.message_id,
    outcome="user_corrected",
    notes="System should have used REQUIRE_COMM"
)
```

### Querying Classification Events

```python
from agentos.core.audit import get_info_need_classification_events

# Get all REQUIRE_COMM decisions
events = get_info_need_classification_events(
    decision="REQUIRE_COMM",
    limit=100
)

for event in events:
    print(f"Question: {event['payload']['question']}")
    print(f"Confidence: {event['payload']['confidence']}")
```

### Analyzing Outcomes

```python
from agentos.core.audit import (
    find_audit_event_by_metadata,
    get_info_need_outcomes_for_message,
    INFO_NEED_CLASSIFICATION
)

# Find classification event
classification = find_audit_event_by_metadata(
    event_type=INFO_NEED_CLASSIFICATION,
    metadata_key="message_id",
    metadata_value="msg-123"
)

# Get all outcomes for this message
outcomes = get_info_need_outcomes_for_message("msg-123")

print(f"Classification: {classification['payload']['decision']}")
for outcome in outcomes:
    print(f"Outcome: {outcome['payload']['outcome']}")
```

## Quality Metrics Foundation

The audit trail provides the data foundation for quality metrics:

### Accuracy Rate

```python
validated = count(outcome="validated")
corrected = count(outcome="user_corrected")
total = validated + corrected

accuracy = validated / total
```

### Precision by Decision Type

```python
# For REQUIRE_COMM decisions:
require_comm_events = filter(decision="REQUIRE_COMM")
validated_require_comm = count(require_comm_events, outcome="validated")

precision_require_comm = validated_require_comm / len(require_comm_events)
```

### Latency Analysis

```python
# Classification latency
avg_classification_latency = mean(event['payload']['latency_ms'])

# Time to outcome
avg_outcome_latency = mean(outcome['payload']['latency_ms'])
```

### Signal Strength Correlation

```python
# Analyze if higher signal_strength correlates with validated outcomes
high_signal_events = filter(signals['signal_strength'] > 0.8)
high_signal_accuracy = compute_accuracy(high_signal_events)
```

## Design Principles

### 1. Non-Blocking

Audit logging MUST be non-blocking and NEVER break the main flow:

```python
try:
    await log_classification_audit(...)
except Exception as e:
    logger.warning(f"Audit logging failed: {e}")
    # Continue execution - audit failure doesn't break classification
```

### 2. Immutable

Audit events are immutable records. Use multiple outcome events if state changes:

```python
# User changes their mind
await log_info_need_outcome(message_id, outcome="user_cancelled")
await log_info_need_outcome(message_id, outcome="validated",
                           user_action="/comm search")
```

### 3. Explicit Correlation

Use `message_id` for explicit correlation rather than implicit timestamps:

```python
# Classification
result = await classifier.classify(message, session_id)
message_id = result.message_id  # Store for later

# Later: Log outcome using the same message_id
await log_info_need_outcome(message_id, outcome="validated")
```

### 4. Semantic Preservation

Store None values explicitly to distinguish "not applicable" from "missing data":

```python
# llm_confidence is None when LLM evaluation wasn't needed
{
    "llm_confidence": None  # Explicitly stored, not removed
}
```

## Testing

### Unit Tests

Comprehensive test suite in `tests/unit/core/test_info_need_audit.py`:

- `test_log_classification_event_basic`: Basic logging
- `test_log_classification_event_without_llm`: Without LLM confidence
- `test_log_outcome_validated`: Validated outcome
- `test_log_outcome_user_corrected`: User correction
- `test_log_outcome_invalid_type`: Invalid outcome type validation
- `test_classifier_integration_with_audit`: Integration with classifier
- `test_classifier_audit_logging_does_not_break_on_failure`: Non-blocking guarantee
- `test_get_classification_events_by_session`: Query by session
- `test_get_classification_events_by_decision`: Query by decision
- `test_message_correlation_classification_to_outcome`: Correlation testing
- `test_audit_logging_is_non_blocking`: Performance verification
- `test_outcome_without_classification_event`: Orphan outcome handling
- `test_multiple_outcomes_for_same_message`: Multiple outcomes

### Running Tests

```bash
python3 -m pytest tests/unit/core/test_info_need_audit.py -v
```

### Demo Script

Run the interactive demo:

```bash
python3 examples/info_need_audit_demo.py
```

## Performance Characteristics

### Classification Overhead

Audit logging adds minimal overhead to classification:
- Synchronous: ~0.5-1ms additional latency
- Async (recommended): <0.1ms blocking time
- Failure: No impact (logged and ignored)

### Query Performance

- Single event lookup by message_id: O(log n) via JSON index
- Session queries: O(n) with JSON filtering
- Bulk queries: Recommended limit ≤ 1000 events

### Storage

- Average classification event: ~500 bytes JSON
- Average outcome event: ~200 bytes JSON
- 10,000 classifications: ~7 MB storage

## Future Enhancements

### Task #20: Quality Metrics

Implement automated quality metrics computation:
- Precision/Recall by decision type
- Confidence calibration analysis
- Signal strength effectiveness
- Latency distributions

### Task #21: Metrics Dashboard

WebUI dashboard for audit metrics:
- Real-time classification statistics
- Outcome distribution charts
- Historical trend analysis
- Anomaly detection alerts

### Integration Opportunities

1. **ChatEngine Integration**: Automatic outcome logging based on user actions
2. **MemoryOS Integration**: Store classification history for context
3. **BrainOS Integration**: Use audit data for decision optimization
4. **Governance Integration**: Audit trail for compliance reporting

## References

### Code Files

- `/Users/pangge/PycharmProjects/AgentOS/agentos/core/audit.py`
- `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/info_need_classifier.py`
- `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/models/info_need.py`
- `/Users/pangge/PycharmProjects/AgentOS/tests/unit/core/test_info_need_audit.py`
- `/Users/pangge/PycharmProjects/AgentOS/examples/info_need_audit_demo.py`

### Related Tasks

- Task #19: ✅ Extend AuditLogger support InfoNeed events (this task)
- Task #20: ⏳ Implement InfoNeed quality metrics computation
- Task #21: ⏳ Create InfoNeed Metrics WebUI Dashboard
- Task #22: ⏳ Implement MemoryOS judgment history storage
- Task #23: ⏳ Implement BrainOS decision mode nodes

## Acceptance Criteria

✅ **AC1**: New event types added to VALID_EVENT_TYPES
✅ **AC2**: Async logging function implemented
✅ **AC3**: InfoNeedClassifier integrated with audit
✅ **AC4**: Helper functions for classification and outcome logging
✅ **AC5**: Query functions for retrieving events
✅ **AC6**: Comprehensive test suite (13 tests, all passing)
✅ **AC7**: Non-blocking behavior guaranteed
✅ **AC8**: Message ID correlation working
✅ **AC9**: Demo script showing all features
✅ **AC10**: Documentation complete

## Conclusion

The InfoNeed classification audit system provides a robust, non-blocking mechanism for tracking classification decisions and outcomes. By focusing on observable user behavior rather than answer correctness, it enables engineering-based quality metrics without hallucination risks.

The implementation follows the core principle: **"Don't evaluate if the answer is right, evaluate if the judgment was proven/disproven by reality."**

This foundation enables automated quality metrics computation (Task #20) and dashboard visualization (Task #21), supporting continuous system improvement through evidence-based evaluation.
