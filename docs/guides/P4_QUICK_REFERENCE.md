# P4 Governance Quick Reference

**Version**: 1.0 | **Date**: 2026-01-31

---

## Core Concepts

### Decision Types
- **NAVIGATION**: Path finding between entities
- **COMPARE**: Snapshot comparison
- **HEALTH**: System health reporting

### Governance Actions (Severity: High → Low)
1. **BLOCK** - Prevents operation
2. **REQUIRE_SIGNOFF** - Needs human approval
3. **WARN** - Logs warning, proceeds
4. **ALLOW** - Normal operation

### Decision Statuses
- **PENDING** - Awaiting evaluation
- **APPROVED** - Allowed to proceed
- **BLOCKED** - Operation rejected
- **SIGNED** - Signoff completed
- **FAILED** - Error occurred

---

## API Quick Reference

### List Decisions
```bash
GET /api/brain/governance/decisions?seed=file:test.py&limit=10
```

### Get Decision
```bash
GET /api/brain/governance/decisions/{decision_id}
```

### Replay Decision (Audit Trail)
```bash
GET /api/brain/governance/decisions/{decision_id}/replay
```

### Sign Decision
```bash
POST /api/brain/governance/decisions/{decision_id}/signoff
Body: {"signed_by": "admin", "note": "Approved"}
```

### Check Can Proceed (Red Line 4)
```bash
GET /api/brain/governance/decisions/{decision_id}/can_proceed
```

### List Rules
```bash
GET /api/brain/governance/rules
```

---

## State Machine

```
PENDING
  ├─[ALLOW]─────────────> APPROVED ✓
  ├─[BLOCK]─────────────> BLOCKED ✗
  ├─[REQUIRE_SIGNOFF]───> SIGNED ✓ (after signoff)
  └─[error]─────────────> FAILED ✗
```

**Terminal states** (no further transitions): APPROVED, BLOCKED, SIGNED, FAILED

---

## Four Red Lines

### Red Line 1: No Decision Without Record
Every Navigation/Compare/Health call generates a DecisionRecord.

**Validation**: Check `decision_records` table for corresponding entry.

---

### Red Line 2: No Hidden Rules
All triggered rules visible in decision record.

**Validation**: Check `rules_triggered` field in record.

```python
record = load_decision_record(store, decision_id)
for rule in record.rules_triggered:
    print(f"{rule.rule_id}: {rule.action.value}")
```

---

### Red Line 3: No History Modification
Decision records are append-only with cryptographic integrity.

**Validation**: Verify hash during replay.

```python
record = load_decision_record(store, decision_id)
computed_hash = record.compute_hash()
assert computed_hash == record.record_hash  # Integrity OK
```

**Tamper Detection**: Hash mismatch indicates modification.

---

### Red Line 4: REQUIRE_SIGNOFF Blocks Operation
Decisions with REQUIRE_SIGNOFF verdict cannot proceed until signed.

**Enforcement**:

```python
from agentos.core.brain.governance.state_machine import can_proceed_with_verdict

can_proceed, reason = can_proceed_with_verdict(status, final_verdict)
if not can_proceed:
    return 403  # Forbidden
```

---

## Rule Configuration Cheat Sheet

### Basic Rule Structure

```yaml
rules:
  - id: "rule_id"
    name: "Rule Name"
    applies_to: "NAVIGATION|COMPARE|HEALTH"
    condition:
      type: "field_name"
      operator: "==|!=|>|<|>=|<=|in|contains"
      value: threshold
    action: "ALLOW|WARN|BLOCK|REQUIRE_SIGNOFF"
    rationale: "Why this rule exists"
    enabled: true
    priority: 0-100  # Higher = Earlier
```

### Operators

| Op  | Description | Example |
|-----|-------------|---------|
| ==  | Equal | `status == "CRITICAL"` |
| !=  | Not equal | `count != 0` |
| >   | Greater | `debt > 100` |
| <   | Less | `confidence < 0.5` |
| >=  | Greater/equal | `severity >= 0.7` |
| <=  | Less/equal | `coverage <= 0.3` |
| in  | In list | `status in ["A", "B"]` |
| contains | List has | `list contains "x"` |

---

## Built-in Rules Summary

### Navigation (4 rules)

| Rule | Priority | Action | Trigger |
|------|----------|--------|---------|
| High Risk Block | 100 | BLOCK | severity >= 0.7 |
| Many Blind Spots | 80 | SIGNOFF | blind_spots >= 3 |
| Low Confidence | 60 | WARN | confidence < 0.5 |
| Low Coverage | 50 | WARN | coverage < 0.4 |

### Compare (4 rules)

| Rule | Priority | Action | Trigger |
|------|----------|--------|---------|
| Health Drop | 90 | BLOCK | health_change < -0.2 |
| Degradation | 80 | SIGNOFF | assessment = DEGRADED |
| Coverage Drop | 60 | WARN | coverage_drop < -10% |
| Entity Removal | 50 | WARN | removed >= 10 |

### Health (4 rules)

| Rule | Priority | Action | Trigger |
|------|----------|--------|---------|
| Low Coverage | 100 | BLOCK | coverage < 0.3 |
| Critical Level | 90 | SIGNOFF | level = CRITICAL |
| Declining Trend | 70 | WARN | trend = DEGRADING |
| High Debt | 60 | WARN | debt >= 50 |

---

## Decision Fields by Type

### Navigation Outputs

```python
{
  "current_zone": "SAFE|DARK|KNOWN|UNKNOWN",
  "paths_count": int,
  "max_risk_level": "LOW|MEDIUM|HIGH",
  "total_blind_spots": int,
  "avg_confidence": float,  # 0-1
  "blind_spot_severity": float,  # 0-1
  "coverage_percentage": float  # 0-1
}
```

### Compare Outputs

```python
{
  "overall_assessment": "IMPROVED|STABLE|DEGRADED",
  "health_score_change": float,  # -1 to 1
  "entities_added": int,
  "entities_removed": int,
  "entities_weakened": int,
  "coverage_change_percentage": float
}
```

### Health Outputs

```python
{
  "current_health_level": "HEALTHY|DEGRADING|CRITICAL",
  "current_health_score": float,  # 0-100
  "coverage_trend_direction": "IMPROVING|STABLE|DEGRADING",
  "blind_spot_trend_direction": "IMPROVING|STABLE|DEGRADING",
  "warnings_count": int,
  "cognitive_debt_count": int,
  "coverage_percentage": float  # 0-1
}
```

---

## Common Tasks

### Add Custom Rule

1. Edit `rules_config.yaml`
2. Add rule entry
3. Validate: `python3 -c "import yaml; yaml.safe_load(open('rules_config.yaml'))"`
4. Reload: `get_all_rules(reload=True)`

### Disable Rule

```yaml
  - id: "rule_id"
    enabled: false
```

### Review Decision

```bash
# 1. Get decision ID from record
curl http://localhost:8000/api/brain/governance/decisions?limit=1

# 2. Replay decision
curl http://localhost:8000/api/brain/governance/decisions/{id}/replay

# 3. Check integrity
# Look for: "integrity_check": {"passed": true}
```

### Sign Decision

```bash
curl -X POST http://localhost:8000/api/brain/governance/decisions/{id}/signoff \
  -H "Content-Type: application/json" \
  -d '{"signed_by": "admin", "note": "Reviewed and approved"}'
```

### Test Rule

```python
from agentos.core.brain.governance.rule_loader import build_condition_function

config = {"type": "coverage", "operator": "<", "value": 0.4}
fn = build_condition_function(config)

assert fn({"coverage": 0.3}) == True
assert fn({"coverage": 0.5}) == False
```

---

## Troubleshooting

### Rule Not Triggering
- Check `enabled: true`
- Verify field name: `print(outputs.keys())`
- Test condition: `condition_fn(outputs)`
- Match decision type: `applies_to: "NAVIGATION"`

### Wrong Verdict
- Multiple rules triggered?
- Most restrictive action wins
- Check: `record.rules_triggered`

### Slow Performance
- Too many rules? (> 50)
- Complex conditions?
- Profile: `time.time()` around `apply_governance_rules()`

### Integrity Check Failed
- Data tampered or corrupted
- Review: `replay_decision()` warnings
- Investigate: Check database logs

---

## Python Code Snippets

### Load and Verify Record

```python
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.governance.decision_recorder import load_decision_record

store = SQLiteStore("brain.db")
store.connect()

record = load_decision_record(store, decision_id)
if not record.verify_integrity():
    print("⚠️ Record integrity compromised!")

store.close()
```

### Apply Rules

```python
from agentos.core.brain.governance.rule_engine import apply_governance_rules
from agentos.core.brain.governance.decision_record import DecisionType

inputs = {"seed": "file:test.py"}
outputs = {"coverage_percentage": 0.2, "paths_count": 1}

triggers, verdict = apply_governance_rules(
    DecisionType.NAVIGATION,
    inputs,
    outputs
)

print(f"Verdict: {verdict.value}")
for t in triggers:
    print(f"  {t.rule_id}: {t.action.value}")
```

### Check Can Proceed

```python
from agentos.core.brain.governance.state_machine import can_proceed_with_verdict
from agentos.core.brain.governance.decision_record import DecisionStatus, GovernanceAction

can_proceed, reason = can_proceed_with_verdict(
    DecisionStatus.PENDING,
    GovernanceAction.REQUIRE_SIGNOFF
)

if not can_proceed:
    print(f"Blocked: {reason}")
```

### Create Decision Record

```python
from agentos.core.brain.governance.decision_record import (
    DecisionRecord,
    DecisionType,
    GovernanceAction
)
from datetime import datetime, timezone
import uuid

record = DecisionRecord(
    decision_id=str(uuid.uuid4()),
    decision_type=DecisionType.NAVIGATION,
    seed="file:example.py",
    inputs={"seed": "file:example.py"},
    outputs={"paths_count": 2},
    rules_triggered=[],
    final_verdict=GovernanceAction.ALLOW,
    confidence_score=0.8,
    timestamp=datetime.now(timezone.utc).isoformat()
)

record.record_hash = record.compute_hash()
```

---

## Database Schema

### decision_records

```sql
CREATE TABLE decision_records (
    decision_id TEXT PRIMARY KEY,
    decision_type TEXT NOT NULL,
    seed TEXT NOT NULL,
    inputs TEXT NOT NULL,        -- JSON
    outputs TEXT NOT NULL,       -- JSON
    rules_triggered TEXT NOT NULL,  -- JSON
    final_verdict TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    timestamp TEXT NOT NULL,
    snapshot_ref TEXT,
    signed_by TEXT,
    sign_timestamp TEXT,
    sign_note TEXT,
    status TEXT NOT NULL,
    record_hash TEXT NOT NULL
);
```

### decision_signoffs

```sql
CREATE TABLE decision_signoffs (
    signoff_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    signed_by TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    note TEXT NOT NULL,
    FOREIGN KEY (decision_id) REFERENCES decision_records(decision_id)
);
```

---

## Performance Targets

| Metric | Target | Actual |
|--------|--------|--------|
| Decision record overhead | < 10ms | ~4.5ms ✓ |
| Rule evaluation | < 5ms | ~1ms ✓ |
| Hash computation | < 2ms | ~1ms ✓ |
| Database insert | < 5ms | ~2ms ✓ |
| Replay full audit | < 50ms | ~30ms ✓ |
| Test suite execution | < 1s | 0.45s ✓ |

---

## File Locations

| File | Purpose |
|------|---------|
| `agentos/core/brain/governance/decision_record.py` | Data models |
| `agentos/core/brain/governance/decision_recorder.py` | Recording logic |
| `agentos/core/brain/governance/rule_engine.py` | Rule evaluation |
| `agentos/core/brain/governance/rule_loader.py` | YAML loading |
| `agentos/core/brain/governance/state_machine.py` | State transitions |
| `agentos/core/brain/governance/rules_config.yaml` | Rule config |
| `agentos/webui/api/brain_governance.py` | REST API |
| `tests/integration/brain/governance/test_p4_complete.py` | Test suite |

---

## Environment Variables

```bash
# Override default rules config
export BRAINOS_RULES_CONFIG=/path/to/custom_rules.yaml

# Database location
export BRAINOS_DB_PATH=/path/to/brain.db
```

---

## Additional Resources

- **Full Implementation Report**: `P4_GOVERNANCE_IMPLEMENTATION_REPORT.md`
- **Rules Manual**: `P4_GOVERNANCE_RULES_MANUAL.md`
- **Completion Report**: `P4_PROJECT_COMPLETION_REPORT.md`
- **Test Suite**: `tests/integration/brain/governance/test_p4_complete.py`

---

**Quick Reference Version**: 1.0
**Print-Friendly**: Yes
**Last Updated**: 2026-01-31
