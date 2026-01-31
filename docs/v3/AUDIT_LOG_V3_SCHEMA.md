# Audit Log v3 Schema - Shadow Evaluation Support

**Version**: 3.0.0
**Status**: Active
**Owner**: Shadow Evaluation Team
**Last Updated**: 2025-01-31

## Overview

Audit Log v3 extends the existing audit system to support **multi-decision tracking** and **shadow evaluation**. This enables the Shadow Evaluation System to:

1. Record active + shadow classification decisions
2. Capture user behavior signals for Reality Alignment Score computation
3. Log evaluation results for improvement proposals
4. Track decision comparisons for migration decisions

**Critical Design Principle**: Audit Log v3 is **RECORD-ONLY**. It does NOT:
- Compute scores or metrics
- Generate improvement proposals
- Make migration decisions
- Execute any business logic

All analysis and decision-making is performed by other components that consume the audit log data.

---

## Event Types

### 1. DECISION_SET_CREATED

Records a complete decision set containing:
- **Active decision** (v1): The classification decision currently used in production
- **Shadow decisions** (v2.a, v2.b, ...): Parallel classifications from experimental classifiers

**Purpose**: Enable Shadow Evaluation System to compare decisions and compute Reality Alignment Scores.

**Trigger**: After InfoNeedClassifier and shadow classifiers complete classification

**Data Structure**:

```json
{
  "event_type": "DECISION_SET_CREATED",
  "level": "info",
  "payload": {
    "decision_set_id": "ds-abc123",          // Unique ID for this decision set
    "message_id": "msg-456",                  // Correlates with user behavior signals
    "session_id": "session-789",              // Session where classification occurred
    "question_text": "What is the latest Python version?",
    "question_hash": 1234567890,              // For duplicate detection
    "active_version": "v1.0.0",               // Active classifier version
    "shadow_versions": ["v2.0-alpha", "v2.0-beta"],  // Shadow classifier versions
    "active_decision": {
      "info_need_type": "EXTERNAL_FACT_UNCERTAIN",
      "decision_action": "REQUIRE_COMM",
      "confidence_level": "low",
      "reasoning": "Time-sensitive query requires current data",
      "rule_signals": { ... },
      "llm_confidence": { ... }
    },
    "shadow_decisions": [
      {
        "info_need_type": "LOCAL_KNOWLEDGE",
        "decision_action": "DIRECT_ANSWER",
        "confidence_level": "high",
        "reasoning": "Python versioning is well-established"
      },
      {
        "info_need_type": "OPINION",
        "decision_action": "SUGGEST_COMM",
        "confidence_level": "medium",
        "reasoning": "May benefit from external validation"
      }
    ],
    "context_snapshot": {
      "execution_phase": "planning",
      "conversation_mode": "chat",
      "rag_chunks": 3,
      "memory_facts": 5
    },
    "timestamp": "2025-01-31T10:30:00.000Z"
  }
}
```

**Key Fields**:
- `decision_set_id`: Unique identifier for this decision set (UUID)
- `message_id`: Correlates with USER_BEHAVIOR_SIGNAL events
- `question_hash`: Integer hash of question_text for duplicate detection
- `shadow_decisions`: Array of shadow classification results (can be empty)
- `context_snapshot`: Optional context data captured at classification time

---

### 2. USER_BEHAVIOR_SIGNAL

Records user behavior signals that indicate the quality of a classification decision. These signals are used to compute **Reality Alignment Scores**.

**Purpose**: Provide ground truth for evaluating whether classification decisions matched user needs.

**Trigger**: Various points in user interaction flow (see Signal Types below)

**Data Structure**:

```json
{
  "event_type": "USER_BEHAVIOR_SIGNAL",
  "level": "info",
  "payload": {
    "message_id": "msg-456",                  // Correlates with DECISION_SET_CREATED
    "session_id": "session-789",
    "signal_type": "user_followup_override",  // See Signal Types below
    "signal_data": {
      "user_action": "/comm search Python latest version",
      "delay_seconds": 5,
      "override_reason": "wanted current info"
    },
    "timestamp": "2025-01-31T10:30:05.000Z"
  }
}
```

**Signal Types**:

| Signal Type | Meaning | Impact on Score | Example |
|-------------|---------|-----------------|---------|
| `smooth_completion` | User accepted response, no friction | ✅ Positive | User reads answer and moves on |
| `user_followup_override` | User immediately contradicted decision | ❌ Negative | System said DIRECT_ANSWER, user ran /comm |
| `delayed_comm_request` | User later manually requested communication | ⚠️ Moderate Negative | User initially accepted but then searched |
| `reask_same_question` | User re-asked same question (dissatisfied) | ❌ Negative | User didn't find answer satisfactory |
| `phase_violation` | Decision caused phase conflict or error | ❌ Strong Negative | REQUIRE_COMM in planning phase |
| `abandoned_response` | User interrupted or abandoned interaction | ⚠️ Moderate Negative | User closed without reading |
| `explicit_feedback` | User provided thumbs up/down | ✅/❌ Strong | Direct feedback from user |

**Signal Data Fields** (vary by signal_type):

**smooth_completion**:
```json
{
  "interaction_duration_seconds": 30,
  "followup_questions": 0,
  "user_satisfaction": "implied_high"
}
```

**user_followup_override**:
```json
{
  "user_action": "/comm search <query>",
  "delay_seconds": 5,
  "override_reason": "wanted current info"
}
```

**reask_same_question**:
```json
{
  "previous_message_id": "msg-123",
  "time_gap_seconds": 60,
  "question_hash_match": true
}
```

**phase_violation**:
```json
{
  "violation_type": "comm_in_planning_phase",
  "current_phase": "planning",
  "required_phase": "execution",
  "error_shown": true
}
```

---

### 3. SHADOW_EVALUATION_COMPLETED

Records the computed Reality Alignment Scores for a decision set. These scores are computed by the **Shadow Score Calculator** based on user behavior signals.

**Purpose**: Track evaluation results for improvement proposals and migration decisions.

**Trigger**: After Shadow Score Calculator processes a decision set with sufficient signals

**Data Structure**:

```json
{
  "event_type": "SHADOW_EVALUATION_COMPLETED",
  "level": "info",
  "payload": {
    "evaluation_id": "eval-xyz",              // Unique evaluation ID
    "decision_set_id": "ds-abc123",           // Correlates with DECISION_SET_CREATED
    "message_id": "msg-456",
    "session_id": "session-789",
    "active_score": 0.65,                     // Reality Alignment Score for active (0.0-1.0)
    "shadow_scores": {
      "v2.0-alpha": 0.85,                     // Shadow performed better
      "v2.0-beta": 0.90                       // This shadow performed even better
    },
    "signals_used": [
      "user_followup_override",
      "delayed_comm_request"
    ],
    "evaluation_time_ms": 45.2,
    "evaluation_method": "reality_alignment",
    "timestamp": "2025-01-31T10:35:00.000Z"
  }
}
```

**Key Fields**:
- `active_score`: Reality Alignment Score for active decision (0.0 = misaligned, 1.0 = perfectly aligned)
- `shadow_scores`: Scores for each shadow version
- `signals_used`: Which signal types were used in computation
- `evaluation_method`: Scoring algorithm used (default: "reality_alignment")

**Score Interpretation**:
- **0.9 - 1.0**: Excellent alignment, decision matched user needs perfectly
- **0.7 - 0.9**: Good alignment, minor friction
- **0.5 - 0.7**: Moderate alignment, noticeable friction
- **0.3 - 0.5**: Poor alignment, significant friction
- **0.0 - 0.3**: Severe misalignment, decision contradicted user needs

---

### 4. DECISION_COMPARISON

Records the comparison between active and shadow decisions, capturing divergences and differences.

**Purpose**: Enable Comparison Engine to identify patterns and generate improvement proposals.

**Trigger**: After Comparison Engine analyzes a decision set

**Data Structure**:

```json
{
  "event_type": "DECISION_COMPARISON",
  "level": "info",
  "payload": {
    "comparison_id": "cmp-123",
    "decision_set_id": "ds-abc123",
    "active_version": "v1.0.0",
    "shadow_version": "v2.0-alpha",
    "comparison_result": {
      "decision_diverged": true,              // Did info_need_type differ?
      "action_diverged": true,                // Did decision_action differ?
      "active_action": "REQUIRE_COMM",
      "shadow_action": "DIRECT_ANSWER",
      "confidence_delta": 0.4,                // Difference in confidence
      "reasoning_similarity": 0.3,            // Similarity of reasoning text
      "divergence_severity": "high"           // low/medium/high
    },
    "comparison_type": "decision_divergence",
    "timestamp": "2025-01-31T10:36:00.000Z"
  }
}
```

**Comparison Result Fields**:
- `decision_diverged`: Boolean indicating if classification types differ
- `action_diverged`: Boolean indicating if recommended actions differ
- `confidence_delta`: Absolute difference in confidence levels (0.0-1.0)
- `reasoning_similarity`: Cosine similarity of reasoning text (0.0-1.0)
- `divergence_severity`: Categorical assessment (low/medium/high)

**Comparison Types**:
- `decision_divergence`: Classification type differs
- `action_divergence`: Recommended action differs
- `confidence_divergence`: Significant difference in confidence
- `reasoning_analysis`: Semantic comparison of reasoning

---

## Query Examples

### Get all decision sets with shadow decisions

```python
from agentos.core.audit import get_decision_sets

# Get recent decision sets that have shadow decisions
decision_sets = get_decision_sets(
    has_shadow=True,
    limit=100
)

for ds in decision_sets:
    payload = ds["payload"]
    print(f"Decision set: {payload['decision_set_id']}")
    print(f"  Active: {payload['active_decision']['decision_action']}")
    print(f"  Shadows: {len(payload['shadow_decisions'])}")
```

### Get user behavior signals for a message

```python
from agentos.core.audit import get_user_behavior_signals_for_message

# Get all signals for a specific message
signals = get_user_behavior_signals_for_message("msg-456")

for signal in signals:
    payload = signal["payload"]
    print(f"Signal: {payload['signal_type']}")
    print(f"  Data: {payload['signal_data']}")
```

### Get shadow evaluations for a decision set

```python
from agentos.core.audit import get_shadow_evaluations_for_decision_set

# Get evaluation results
evaluations = get_shadow_evaluations_for_decision_set("ds-abc123")

for eval in evaluations:
    payload = eval["payload"]
    print(f"Active score: {payload['active_score']}")
    print(f"Shadow scores: {payload['shadow_scores']}")
```

### Correlate decision set with signals and evaluation

```python
# Step 1: Get decision set
decision_sets = get_decision_sets(session_id="session-789", limit=1)
ds_payload = decision_sets[0]["payload"]

# Step 2: Get signals using message_id
message_id = ds_payload["message_id"]
signals = get_user_behavior_signals_for_message(message_id)

# Step 3: Get evaluation using decision_set_id
decision_set_id = ds_payload["decision_set_id"]
evaluations = get_shadow_evaluations_for_decision_set(decision_set_id)

# Now we have complete picture:
# - What decisions were made (decision_sets)
# - How user reacted (signals)
# - What scores were computed (evaluations)
```

---

## Data Flow

### 1. Classification Phase
```
User Question
    ↓
InfoNeedClassifier.classify() → Active Decision (v1)
    ↓
Shadow Classifiers (parallel) → Shadow Decisions (v2.a, v2.b, ...)
    ↓
log_decision_set() → DECISION_SET_CREATED event
```

### 2. Interaction Phase
```
User Interaction
    ↓
Behavior Detection (various triggers)
    ↓
log_user_behavior_signal() → USER_BEHAVIOR_SIGNAL events
```

### 3. Evaluation Phase (offline)
```
Shadow Score Calculator (periodic job)
    ↓
Load: DECISION_SET_CREATED + USER_BEHAVIOR_SIGNAL
    ↓
Compute: Reality Alignment Scores
    ↓
log_shadow_evaluation() → SHADOW_EVALUATION_COMPLETED event
```

### 4. Comparison Phase (offline)
```
Comparison Engine
    ↓
Load: DECISION_SET_CREATED + SHADOW_EVALUATION_COMPLETED
    ↓
Compare: Active vs Shadow decisions
    ↓
log_decision_comparison() → DECISION_COMPARISON event
```

---

## Database Schema

All v3 events are stored in the existing `task_audits` table:

```sql
CREATE TABLE task_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,                -- FK to tasks table (uses "ORPHAN" for non-task events)
    level TEXT NOT NULL,                   -- info|warn|error
    event_type TEXT NOT NULL,              -- Event type constant
    payload TEXT NOT NULL,                 -- JSON-encoded event data
    created_at INTEGER NOT NULL,           -- Unix timestamp (UTC)
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

-- Indexes for v3 queries
CREATE INDEX idx_task_audits_event_type ON task_audits(event_type);
CREATE INDEX idx_task_audits_created_at ON task_audits(created_at);
```

**JSON Query Support**:

SQLite 3.38+ provides JSON functions for querying payload:

```sql
-- Find decision sets for a session
SELECT * FROM task_audits
WHERE event_type = 'DECISION_SET_CREATED'
AND json_extract(payload, '$.session_id') = 'session-789';

-- Find signals for a message
SELECT * FROM task_audits
WHERE event_type = 'USER_BEHAVIOR_SIGNAL'
AND json_extract(payload, '$.message_id') = 'msg-456';

-- Find decision sets with shadows
SELECT * FROM task_audits
WHERE event_type = 'DECISION_SET_CREATED'
AND json_array_length(json_extract(payload, '$.shadow_decisions')) > 0;
```

---

## Usage Guidelines

### For Shadow Evaluation System

1. **Record ALL decisions** (active + shadow), even if shadows are disabled
2. **Capture behavior signals** as soon as they occur (don't batch)
3. **Log evaluations** only after computing scores (don't log partial results)
4. **Correlate by message_id** when analyzing decision quality

### For Developers

1. **Never compute scores in log functions** - log functions only record data
2. **Use async functions** (`log_audit_event_async`) in hot paths to avoid blocking
3. **Include context snapshots** when available for richer analysis
4. **Validate signal types** - use documented signal_type values

### For Analysts

1. **Join on message_id** to correlate decisions with behavior
2. **Filter by has_shadow=True** to focus on shadow evaluation data
3. **Track evaluation_time_ms** to identify performance issues
4. **Analyze signal patterns** to understand user friction points

---

## Migration Notes

### From Audit v2 to v3

**Backward Compatibility**: v3 is fully backward compatible with v2. All existing event types and functions continue to work.

**New Dependencies**: None. v3 uses existing `task_audits` table and JSON functions.

**Breaking Changes**: None.

**New Capabilities**:
- Multi-decision tracking (active + shadow)
- User behavior signal capture
- Shadow evaluation logging
- Decision comparison tracking

---

## Related Documentation

- [Shadow Evaluation System Architecture](./SHADOW_EVALUATION_ARCHITECTURE.md)
- [Reality Alignment Score Computation](./REALITY_ALIGNMENT_SCORE.md)
- [Decision Comparison Engine](./DECISION_COMPARISON_ENGINE.md)
- [InfoNeed Classification Guide](../chat/INFO_NEED_CLASSIFICATION.md)

---

## Appendix: Complete Event Type Reference

| Event Type | Purpose | Frequency | Data Size | TTL |
|------------|---------|-----------|-----------|-----|
| `DECISION_SET_CREATED` | Record classification decisions | Per user message | ~2-5 KB | 90 days |
| `USER_BEHAVIOR_SIGNAL` | Capture user behavior | Per interaction event | ~0.5-1 KB | 90 days |
| `SHADOW_EVALUATION_COMPLETED` | Record evaluation scores | Per batch (daily) | ~1-2 KB | 365 days |
| `DECISION_COMPARISON` | Record decision comparisons | Per evaluation | ~1-2 KB | 365 days |

**Storage Estimate**: ~10 MB per 1000 decision sets with full signals and evaluations.
