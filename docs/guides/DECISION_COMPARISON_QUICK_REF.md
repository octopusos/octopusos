# Decision Comparison View - Quick Reference

**AgentOS v3 Shadow Classifier System**

## Overview

The Decision Comparison View is a WebUI dashboard for comparing active (executed) and shadow (hypothetical) classifier decisions. It helps humans evaluate which shadow version is worth migrating to production.

## API Endpoints

### 1. List Decision Comparisons

```http
GET /api/v3/decision-comparison/list
```

**Query Parameters:**
- `active_version` (string, default: "v1") - Active classifier version
- `time_range` (string, default: "24h") - Time range: 24h, 7d, 30d, custom
- `start_time` (string, optional) - Start time for custom range (ISO format)
- `end_time` (string, optional) - End time for custom range (ISO format)
- `session_id` (string, optional) - Filter by session ID
- `info_need_type` (string, optional) - Filter by info need type
- `limit` (int, default: 100) - Results per page (1-1000)
- `offset` (int, default: 0) - Pagination offset

**Example:**
```bash
curl "http://localhost:8000/api/v3/decision-comparison/list?active_version=v1&time_range=24h&limit=20"
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "decision_set_id": "abc123",
        "message_id": "msg_456",
        "session_id": "session_789",
        "question_text": "What is the status of PR #123?",
        "timestamp": "2026-01-31T10:00:00Z",
        "active_decision": {
          "version": "v1",
          "decision_action": "REQUIRE_COMM",
          "info_need_type": "EXTERNAL_FACT_UNCERTAIN",
          "confidence_level": "medium"
        },
        "shadow_versions": ["v2-shadow-a", "v2-shadow-b"],
        "shadow_count": 2,
        "has_evaluation": true
      }
    ],
    "total_count": 312,
    "limit": 20,
    "offset": 0,
    "filters": {
      "session_id": null,
      "active_version": "v1",
      "time_range": "24h",
      "info_need_type": null
    }
  },
  "error": null
}
```

### 2. Get Decision Detail

```http
GET /api/v3/decision-comparison/{decision_set_id}
```

**Example:**
```bash
curl "http://localhost:8000/api/v3/decision-comparison/abc123"
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "decision_set_id": "abc123",
    "message_id": "msg_456",
    "session_id": "session_789",
    "question_text": "What is the status of PR #123?",
    "timestamp": "2026-01-31T10:00:00Z",
    "context_snapshot": {},
    "active_decision": {
      "candidate_id": "active_001",
      "version": "v1",
      "version_type": "active",
      "decision_action": "REQUIRE_COMM",
      "info_need_type": "EXTERNAL_FACT_UNCERTAIN",
      "confidence_level": "medium",
      "reason_codes": ["uncertain_info"],
      "outcome": {
        "executed": true,
        "result": "completed",
        "signals": []
      },
      "score": 0.75,
      "score_details": {
        "base_score": 1.0,
        "raw_score": 0.75,
        "signal_contributions": []
      }
    },
    "shadow_decisions": [
      {
        "candidate_id": "shadow_002",
        "version": "v2-shadow-a",
        "version_type": "shadow",
        "version_description": "Expanded keyword matching",
        "decision_action": "DIRECT_ANSWER",
        "info_need_type": "LOCAL_KNOWLEDGE",
        "confidence_level": "high",
        "reason_codes": ["cached_info"],
        "outcome": {
          "executed": false,
          "hypothetical_result": "not_executed",
          "signals": []
        },
        "score": 0.85,
        "score_details": {},
        "shadow_metadata": {
          "warning": "NOT EXECUTED - Hypothetical evaluation only"
        }
      }
    ],
    "comparison": {
      "best_shadow_version": "v2-shadow-a",
      "best_shadow_score": 0.85,
      "active_score": 0.75,
      "score_delta": 0.10,
      "would_change_decision": true
    }
  },
  "error": null
}
```

### 3. Get Comparison Summary

```http
GET /api/v3/decision-comparison/summary
```

**Query Parameters:**
- `active_version` (string, required) - Active classifier version
- `shadow_versions` (string, required) - Comma-separated shadow version IDs
- `session_id` (string, optional) - Filter by session ID
- `info_need_type` (string, optional) - Filter by info need type
- `time_range` (string, default: "24h") - Time range
- `start_time` (string, optional) - Start time for custom range
- `end_time` (string, optional) - End time for custom range

**Example:**
```bash
curl "http://localhost:8000/api/v3/decision-comparison/summary?active_version=v1&shadow_versions=v2-shadow-a,v2-shadow-b&time_range=7d"
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "active_version": "v1",
    "shadow_comparisons": [
      {
        "shadow_version": "v2-shadow-a",
        "sample_count": 312,
        "divergence_rate": 0.48,
        "improvement_rate": 0.15,
        "better_count": 220,
        "worse_count": 50,
        "neutral_count": 42,
        "recommendation": "CONSIDER_MIGRATION"
      },
      {
        "shadow_version": "v2-shadow-b",
        "sample_count": 312,
        "divergence_rate": 0.35,
        "improvement_rate": -0.05,
        "better_count": 100,
        "worse_count": 180,
        "neutral_count": 32,
        "recommendation": "DO_NOT_MIGRATE"
      }
    ],
    "filters": {}
  },
  "error": null
}
```

## Frontend Usage

### Accessing the View

Navigate to the AgentOS WebUI and open the Decision Comparison view:

```javascript
// In main.js or navigation handler
const decisionComparisonView = new DecisionComparisonView(container);
```

### View Modes

1. **List View** (default)
   - Shows paginated list of decision comparisons
   - Filter by time range, session, info need type
   - Click item to view details

2. **Detail View**
   - Side-by-side comparison of active and shadow decisions
   - Shows Reality Alignment Scores
   - Clear visual distinction (active=green, shadow=orange)
   - Prominent "NOT EXECUTED" warnings for shadow decisions

3. **Summary View**
   - Aggregated statistics for multiple shadow versions
   - Color-coded recommendations
   - Metrics: divergence rate, improvement rate, better/worse/neutral counts

### Filters

```javascript
// Set filters programmatically
view.filters = {
    sessionId: 'session_123',
    activeVersion: 'v1',
    timeRange: '7d',
    infoNeedType: 'EXTERNAL_FACT_UNCERTAIN',
    offset: 0,
    limit: 20
};
view.refresh();
```

## Interpretation Guide

### Reality Alignment Score

Range: 0.0 (poor) to 1.0 (perfect)

- **0.7-1.0 (Green):** Good alignment with reality
- **0.4-0.7 (Orange):** Moderate alignment
- **0.0-0.4 (Red):** Poor alignment

### Recommendations

- **STRONGLY_RECOMMEND_MIGRATION:** >10% improvement, >2x better decisions
- **CONSIDER_MIGRATION:** >10% improvement
- **MARGINAL_IMPROVEMENT:** 0-10% improvement
- **NO_CLEAR_WINNER:** No significant difference
- **DO_NOT_MIGRATE:** Worse performance
- **INSUFFICIENT_DATA:** <50 samples

### Decision Actions

- **REQUIRE_COMM:** Trigger communication with user
- **DIRECT_ANSWER:** Provide direct answer (no communication)
- **AMBIENT_STATE:** Query is about ambient state
- **USER_CLARIFICATION:** Need user clarification

### Info Need Types

- **EXTERNAL_FACT_UNCERTAIN:** External fact, uncertain
- **LOCAL_KNOWLEDGE:** Local knowledge available
- **AMBIENT_STATE:** Ambient state query
- **USER_CLARIFICATION:** Need user clarification

## Visual Indicators

### Badges

- **🟢 EXECUTED** - Active decision (executed in production)
- **🟠 NOT EXECUTED** - Shadow decision (hypothetical only)
- **Scored** - Has Reality Alignment Score

### Colors

- **Green Border:** Active decision (executed)
- **Orange Border:** Shadow decision (not executed)
- **Orange Warning Box:** Shadow warning message
- **Green Score:** Good alignment (≥0.7)
- **Orange Score:** Moderate alignment (0.4-0.7)
- **Red Score:** Poor alignment (<0.4)

## Common Workflows

### 1. Evaluate a Shadow Version

```bash
# Step 1: Get summary to see overall performance
curl "/api/v3/decision-comparison/summary?active_version=v1&shadow_versions=v2-shadow-a&time_range=7d"

# Step 2: If promising, drill into specific decisions
curl "/api/v3/decision-comparison/list?active_version=v1&time_range=7d"

# Step 3: Review detailed comparisons
curl "/api/v3/decision-comparison/{decision_set_id}"
```

### 2. Compare Multiple Shadow Versions

```bash
# Get summary for all shadow versions
curl "/api/v3/decision-comparison/summary?active_version=v1&shadow_versions=v2-shadow-a,v2-shadow-b,v2-shadow-c&time_range=7d"

# Sort by improvement_rate to find best candidate
```

### 3. Filter by Problem Area

```bash
# Focus on EXTERNAL_FACT_UNCERTAIN decisions
curl "/api/v3/decision-comparison/list?active_version=v1&info_need_type=EXTERNAL_FACT_UNCERTAIN&time_range=7d"
```

### 4. Session-Specific Analysis

```bash
# Analyze specific session
curl "/api/v3/decision-comparison/list?active_version=v1&session_id=session_123&time_range=24h"
```

## Troubleshooting

### No Data Returned

**Problem:** API returns empty items array

**Solutions:**
- Check time range (try longer range like 30d)
- Verify active_version exists
- Check if shadow decisions are being logged
- Verify session_id filter (remove to see all sessions)

### Missing Scores

**Problem:** score and score_details are null

**Solutions:**
- Scores require shadow evaluations to be completed
- Check if ShadowEvaluator is running
- Verify audit logs contain SHADOW_EVALUATION_COMPLETED events
- Allow time for evaluation to complete

### Invalid Time Range

**Problem:** 400 error with "Invalid time_range"

**Solutions:**
- Use valid presets: 24h, 7d, 30d, custom
- For custom: provide both start_time and end_time in ISO format
- Example: `2026-01-01T00:00:00Z`

### 404 Not Found

**Problem:** decision_set_id not found

**Solutions:**
- Verify decision_set_id is correct
- Check if decision was logged to audit trail
- Use list endpoint to find valid IDs

## Best Practices

1. **Start with Summary View**
   - Get overview of all shadow versions
   - Identify best candidates

2. **Use Appropriate Time Ranges**
   - 24h: Real-time monitoring
   - 7d: Weekly evaluation
   - 30d: Long-term trends

3. **Focus on High Sample Counts**
   - Need ≥50 samples for reliable recommendations
   - More samples = more confidence

4. **Look for Consistent Improvement**
   - Check across different info_need_types
   - Verify across multiple sessions

5. **Read Shadow Warnings**
   - Remember: shadow decisions are NOT EXECUTED
   - They are hypothetical evaluations only

## Integration Points

### DecisionComparator

```python
from agentos.core.chat.decision_comparator import get_comparator

comparator = get_comparator()
comparison = comparator.compare_versions(
    active_version="v1",
    shadow_version="v2-shadow-a",
    time_range=(start_time, end_time)
)
```

### Audit Logs

```python
from agentos.core.audit import get_decision_sets, get_shadow_evaluations_for_decision_set

# Get decision sets
decision_sets = get_decision_sets(
    session_id="session_123",
    active_version="v1",
    has_shadow=True
)

# Get evaluations
evaluations = get_shadow_evaluations_for_decision_set("decision_set_123")
```

### Shadow Registry

```python
from agentos.core.chat.shadow_registry import get_shadow_registry

registry = get_shadow_registry()
active_shadows = registry.get_active_shadows()
version_info = registry.get_version_info("v2-shadow-a")
```

## Related Documentation

- `DECISION_COMPARISON_VIEW_ACCEPTANCE_REPORT.md` - Full acceptance report
- `docs/v3/SHADOW_CLASSIFIER_SYSTEM.md` - v3 architecture
- `agentos/core/chat/decision_comparator.py` - Core comparison logic
- `agentos/core/chat/shadow_evaluator.py` - Score calculation

## Support

For issues or questions:
1. Check audit logs for decision events
2. Verify shadow classifiers are registered and active
3. Ensure shadow evaluations are running
4. Review acceptance report for known limitations

---

**Version:** 1.0.0
**Last Updated:** 2026-01-31
**Maintainer:** AgentOS Team
