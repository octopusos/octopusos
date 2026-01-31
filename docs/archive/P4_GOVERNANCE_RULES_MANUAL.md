# P4 Governance Rules Manual

**Version**: 1.0
**Date**: 2026-01-31
**Audience**: System Administrators, DevOps Engineers

---

## Table of Contents

1. [Introduction](#introduction)
2. [Rule System Architecture](#rule-system-architecture)
3. [Built-in Rules Reference](#built-in-rules-reference)
4. [Custom Rule Development](#custom-rule-development)
5. [Rule Configuration](#rule-configuration)
6. [Testing Rules](#testing-rules)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Introduction

The BrainOS Governance Rules system provides declarative policy enforcement for cognitive decisions. Rules automatically evaluate every Navigation, Compare, and Health decision against configurable criteria and trigger actions (ALLOW/WARN/BLOCK/REQUIRE_SIGNOFF).

### Key Concepts

- **Rule**: A policy that evaluates a decision's inputs/outputs
- **Condition**: A boolean expression (e.g., `coverage < 0.4`)
- **Action**: The governance decision (ALLOW/WARN/BLOCK/REQUIRE_SIGNOFF)
- **Priority**: Evaluation order (higher = earlier)
- **Final Verdict**: Most restrictive action from all triggered rules

### Design Principles

1. **Declarative**: Rules are configuration, not code
2. **Transparent**: All triggered rules recorded in decision
3. **Composable**: Multiple rules can apply to same decision
4. **Auditable**: Rule changes tracked, history preserved

---

## Rule System Architecture

### Evaluation Pipeline

```
Decision Request
    ↓
[Capture Inputs/Outputs]
    ↓
[Load Active Rules] ← rules_config.yaml
    ↓
[Sort by Priority] (100 → 0)
    ↓
[Evaluate Each Rule]
    ├─ Check decision_type match
    ├─ Evaluate condition
    └─ Record trigger (if true)
    ↓
[Determine Final Verdict]
    └─ Most restrictive action
    ↓
[Create Decision Record]
    └─ Save to database
```

### Action Hierarchy

Actions are ordered from most to least restrictive:

1. **BLOCK**: Prevents operation entirely
2. **REQUIRE_SIGNOFF**: Allows only after human approval
3. **WARN**: Proceeds with logged warning
4. **ALLOW**: Proceeds normally

Example: If Rule A triggers WARN and Rule B triggers REQUIRE_SIGNOFF, final verdict is REQUIRE_SIGNOFF.

### Rule Lifecycle

```
rules_config.yaml
    ↓
[Startup: Load Rules]
    ↓
[Runtime: Evaluate Decisions]
    ↓
[Admin: Modify Config]
    ↓
[Reload: get_all_rules(reload=True)]
    ↓
[New Rules Active]
```

---

## Built-in Rules Reference

### Navigation Rules

#### NAV-001: High Risk Block Rule

**Priority**: 100 (Highest)

**Condition**: `blind_spot_severity >= 0.7`

**Action**: BLOCK

**Rationale**: "Path contains high-risk blind spots (severity >= 0.7)"

**Description**: Blocks navigation when path traverses blind spots with severity >= 0.7. Blind spot severity indicates areas of code with extremely low understanding.

**Example Trigger**:
```json
{
  "inputs": {"seed": "file:legacy.py"},
  "outputs": {
    "blind_spot_severity": 0.85,
    "paths_count": 1
  }
}
```

**Why it matters**: High-severity blind spots represent code regions with minimal documentation, tests, or recent activity. Navigating through them increases risk of incorrect recommendations.

**Typical Response**: Improve understanding of blind spot regions before navigation:
1. Add documentation
2. Write tests
3. Run static analysis
4. Human code review

---

#### NAV-002: Low Confidence Warning

**Priority**: 60

**Condition**: `avg_confidence < 0.5`

**Action**: WARN

**Rationale**: "Average path confidence is below 0.5"

**Description**: Warns when navigation confidence score falls below 50%. Confidence score reflects the system's certainty in path recommendations.

**Example Trigger**:
```json
{
  "outputs": {
    "avg_confidence": 0.35,
    "paths_count": 3
  }
}
```

**Why it matters**: Low confidence indicates weak or uncertain relationships between entities. Recommendations may be speculative or based on limited data.

**Typical Response**: Investigate why confidence is low:
- Check if entities are well-connected
- Verify entity types are correct
- Review relationship strengths
- Consider improving graph density

---

#### NAV-003: Many Blind Spots Signoff

**Priority**: 80

**Condition**: `total_blind_spots >= 3`

**Action**: REQUIRE_SIGNOFF

**Rationale**: "Navigation crosses multiple blind spots (>= 3), requires review"

**Description**: Requires human signoff when navigation path crosses 3+ blind spots. Even low-severity blind spots accumulate risk.

**Example Trigger**:
```json
{
  "outputs": {
    "total_blind_spots": 5,
    "paths_count": 2
  }
}
```

**Why it matters**: Multiple blind spots indicate a complex, poorly-understood path. Human review ensures risk is acceptable.

**Signoff Process**:
1. System blocks navigation
2. Admin reviews decision via `/api/brain/governance/decisions/{id}/replay`
3. Admin evaluates risk vs. benefit
4. Admin signs off via `/api/brain/governance/decisions/{id}/signoff`
5. Navigation proceeds

---

#### NAV-004: Low Coverage Warning

**Priority**: 50

**Condition**: `coverage_percentage < 0.4`

**Action**: WARN

**Rationale**: "Path has low coverage (< 40%)"

**Description**: Warns when path entities have less than 40% understanding coverage. Coverage measures how well entities are documented, tested, and analyzed.

**Example Trigger**:
```json
{
  "outputs": {
    "coverage_percentage": 0.30,
    "paths_count": 4
  }
}
```

**Why it matters**: Low coverage suggests entities lack sufficient metadata for reliable recommendations.

**Typical Response**: Improve coverage:
- Run documentation extractors
- Add entity metadata
- Integrate with version control
- Enable additional analyzers

---

### Compare Rules

#### CMP-001: Health Score Drop Block

**Priority**: 90

**Condition**: `health_score_change < -0.2`

**Action**: BLOCK

**Rationale**: "Health score dropped by more than 20%"

**Description**: Blocks comparison when health score drops by >20%. Health score reflects overall graph understanding quality.

**Example Trigger**:
```json
{
  "inputs": {
    "from_snapshot_id": "snapshot-1",
    "to_snapshot_id": "snapshot-2"
  },
  "outputs": {
    "health_score_change": -0.25,
    "overall_assessment": "DEGRADED"
  }
}
```

**Why it matters**: Significant health score drops indicate understanding regression - possibly due to:
- Large code deletions
- Broken relationships
- Missing metadata
- Extractor failures

**Typical Response**: Investigate regression:
1. Review snapshot diffs
2. Check extractor logs
3. Verify entity integrity
4. Consider reverting changes

---

#### CMP-002: Entity Removal Warning

**Priority**: 50

**Condition**: `entities_removed >= 10`

**Action**: WARN

**Rationale**: "More than 10 entities were removed"

**Description**: Warns when comparison shows 10+ entities removed. Large deletions may indicate:
- Code cleanup (good)
- Accidental deletion (bad)
- Scope reduction (neutral)

**Example Trigger**:
```json
{
  "outputs": {
    "entities_removed": 25,
    "entities_added": 5
  }
}
```

**Why it matters**: Entity removal affects graph connectivity and understanding coverage. Large changes should be reviewed.

**Typical Response**: Review removed entities:
- Were they intentionally deleted?
- Do remaining entities reference them?
- Are there broken relationships?

---

#### CMP-003: Degradation Signoff

**Priority**: 80

**Condition**: `overall_assessment == "DEGRADED"`

**Action**: REQUIRE_SIGNOFF

**Rationale**: "Understanding degraded, requires human review"

**Description**: Requires signoff when overall assessment is DEGRADED. Compare engine marks snapshots as degraded when understanding quality decreases across multiple dimensions.

**Example Trigger**:
```json
{
  "outputs": {
    "overall_assessment": "DEGRADED",
    "health_score_change": -0.15,
    "entities_weakened": 40
  }
}
```

**Why it matters**: Degradation indicates systemic understanding loss. Human review ensures:
- Cause is understood
- Impact is acceptable
- Remediation plan exists

**Signoff Checklist**:
- [ ] Root cause identified?
- [ ] Impact scope documented?
- [ ] Remediation plan created?
- [ ] Stakeholders notified?
- [ ] Risk vs. benefit assessed?

---

#### CMP-004: Coverage Drop Warning

**Priority**: 60

**Condition**: `coverage_change_percentage < -10.0`

**Action**: WARN

**Rationale**: "Coverage decreased by more than 10%"

**Description**: Warns when coverage drops by >10%. Coverage changes track understanding breadth.

**Example Trigger**:
```json
{
  "outputs": {
    "coverage_change_percentage": -15.5
  }
}
```

**Why it matters**: Coverage drops may indicate:
- Documentation removed
- Extractor disabled
- Scope narrowed

**Typical Response**: Investigate coverage loss:
- Which entities lost coverage?
- Why did coverage decrease?
- Is it reversible?

---

### Health Rules

#### HLT-001: Critical Health Signoff

**Priority**: 90

**Condition**: `current_health_level == "CRITICAL"`

**Action**: REQUIRE_SIGNOFF

**Rationale**: "Health level is CRITICAL, requires immediate attention"

**Description**: Requires signoff when system health reaches CRITICAL level. Health levels:
- HEALTHY: > 80% coverage, minimal debt
- DEGRADING: 60-80% coverage, moderate debt
- CRITICAL: < 60% coverage, high debt

**Example Trigger**:
```json
{
  "outputs": {
    "current_health_level": "CRITICAL",
    "current_health_score": 45,
    "cognitive_debt_count": 120
  }
}
```

**Why it matters**: CRITICAL health indicates systemic understanding failure. Operations may produce unreliable results.

**Remediation**:
1. Stop low-priority operations
2. Focus on debt reduction
3. Re-run extractors
4. Update metadata
5. Rebuild indices

---

#### HLT-002: High Cognitive Debt Warning

**Priority**: 60

**Condition**: `cognitive_debt_count >= 50`

**Action**: WARN

**Rationale**: "Cognitive debt count is high (>= 50)"

**Description**: Warns when cognitive debt exceeds 50 items. Cognitive debt represents areas needing understanding improvement:
- Undocumented entities
- Weak relationships
- Orphaned nodes
- Missing attributes

**Example Trigger**:
```json
{
  "outputs": {
    "cognitive_debt_count": 75,
    "warnings_count": 12
  }
}
```

**Why it matters**: High debt accumulation reduces recommendation quality over time.

**Debt Reduction Strategies**:
- Document high-debt entities
- Strengthen weak relationships
- Remove orphaned nodes
- Fill missing attributes
- Run consistency checks

---

#### HLT-003: Health Decline Warning

**Priority**: 70

**Condition**: `coverage_trend_direction == "DEGRADING"`

**Action**: WARN

**Rationale**: "Coverage trend is degrading over time"

**Description**: Warns when coverage trend shows consistent degradation. Trend analysis looks at coverage changes over rolling time window.

**Example Trigger**:
```json
{
  "outputs": {
    "coverage_trend_direction": "DEGRADING",
    "current_health_score": 72
  }
}
```

**Why it matters**: Degrading trends indicate systemic issues:
- Extractors failing
- Documentation not keeping pace
- Code complexity increasing

**Typical Response**:
1. Review trend graph
2. Identify inflection point
3. Correlate with events (releases, team changes)
4. Implement corrections

---

#### HLT-004: Low Coverage Block

**Priority**: 100 (Highest)

**Condition**: `coverage_percentage < 0.3`

**Action**: BLOCK

**Rationale**: "Overall coverage below 30%, system health compromised"

**Description**: Blocks operations when overall coverage falls below 30%. At this level, graph understanding is too limited for reliable operations.

**Example Trigger**:
```json
{
  "outputs": {
    "coverage_percentage": 0.25,
    "current_health_level": "CRITICAL"
  }
}
```

**Why it matters**: Below 30% coverage, recommendations become essentially random. System should not operate in this state.

**Recovery Steps**:
1. Halt all operations
2. Run full extraction pipeline
3. Rebuild graph from source
4. Verify extractor configuration
5. Check data source availability

---

## Custom Rule Development

### Rule Configuration Format

Rules are defined in YAML with the following structure:

```yaml
rules:
  - id: "custom_rule_001"              # Unique identifier
    name: "Custom Rule Name"           # Human-readable name
    applies_to: "NAVIGATION"           # NAVIGATION|COMPARE|HEALTH
    condition:                         # Evaluation criteria
      type: "field_name"               # Field to check
      operator: ">="                   # Comparison operator
      value: 0.5                       # Expected value
    action: "WARN"                     # ALLOW|WARN|BLOCK|REQUIRE_SIGNOFF
    rationale: "Why this rule exists"  # Explanation
    enabled: true                      # Enable/disable flag
    priority: 75                       # Evaluation order (0-100)
    description: "Detailed description" # Optional
```

### Supported Operators

| Operator | Description         | Example Usage                    |
|----------|---------------------|----------------------------------|
| ==       | Equal               | `status == "CRITICAL"`           |
| !=       | Not equal           | `paths_count != 0`               |
| >        | Greater than        | `debt_count > 100`               |
| <        | Less than           | `confidence < 0.5`               |
| >=       | Greater or equal    | `severity >= 0.7`                |
| <=       | Less or equal       | `coverage <= 0.3`                |
| in       | Value in list       | `status in ["CRITICAL", "DEGRADED"]` |
| contains | List contains value | `warnings contains "high_risk"`  |

### Available Fields by Decision Type

#### Navigation Fields

**Inputs**:
- `seed` (string): Starting entity
- `goal` (string|null): Target entity
- `max_hops` (int): Maximum path length

**Outputs**:
- `current_zone` (string): SAFE/DARK/KNOWN/UNKNOWN
- `paths_count` (int): Number of paths found
- `max_risk_level` (string): LOW/MEDIUM/HIGH
- `total_blind_spots` (int): Count of blind spots crossed
- `avg_confidence` (float): Average path confidence (0-1)
- `blind_spot_severity` (float): Highest severity (0-1)
- `coverage_percentage` (float): Path coverage (0-1)

#### Compare Fields

**Inputs**:
- `from_snapshot_id` (string): Source snapshot
- `to_snapshot_id` (string): Target snapshot

**Outputs**:
- `overall_assessment` (string): IMPROVED/STABLE/DEGRADED
- `health_score_change` (float): Change in health score
- `entities_added` (int): New entities
- `entities_removed` (int): Deleted entities
- `entities_weakened` (int): Entities with reduced understanding
- `coverage_change_percentage` (float): Coverage delta

#### Health Fields

**Inputs**:
- `window_days` (int): Analysis window
- `granularity` (string): Time granularity

**Outputs**:
- `current_health_level` (string): HEALTHY/DEGRADING/CRITICAL
- `current_health_score` (float): Health score (0-100)
- `coverage_trend_direction` (string): IMPROVING/STABLE/DEGRADING
- `blind_spot_trend_direction` (string): IMPROVING/STABLE/DEGRADING
- `warnings_count` (int): Number of warnings
- `cognitive_debt_count` (int): Total debt items
- `coverage_percentage` (float): Overall coverage (0-1)

### Custom Rule Examples

#### Example 1: Block High-Risk Weekend Deployments

```yaml
  - id: "custom_no_weekend_high_risk"
    name: "No High-Risk Weekend Deployments"
    applies_to: "NAVIGATION"
    condition:
      type: "max_risk_level"
      operator: "=="
      value: "HIGH"
    action: "BLOCK"
    rationale: "High-risk navigation not allowed on weekends"
    enabled: true
    priority: 95
```

**Note**: This example shows rule structure. Time-based conditions require custom implementation.

#### Example 2: Require Signoff for Large Changes

```yaml
  - id: "custom_large_change_signoff"
    name: "Large Change Requires Signoff"
    applies_to: "COMPARE"
    condition:
      type: "entities_removed"
      operator: ">"
      value: 100
    action: "REQUIRE_SIGNOFF"
    rationale: "Changes affecting > 100 entities require review"
    enabled: true
    priority: 85
```

#### Example 3: Warn on Debt Acceleration

```yaml
  - id: "custom_debt_acceleration"
    name: "Cognitive Debt Acceleration Warning"
    applies_to: "HEALTH"
    condition:
      type: "cognitive_debt_count"
      operator: ">"
      value: 150
    action: "WARN"
    rationale: "Debt count exceeds high threshold (150)"
    enabled: true
    priority: 65
```

---

## Rule Configuration

### Configuration File Location

**Default**: `agentos/core/brain/governance/rules_config.yaml`

**Custom**: Set via environment variable or pass path to `load_rules_from_config(path)`

### Adding a New Rule

1. **Open configuration file**:
   ```bash
   vim agentos/core/brain/governance/rules_config.yaml
   ```

2. **Add rule entry**:
   ```yaml
     - id: "my_custom_rule"
       name: "My Custom Rule"
       applies_to: "NAVIGATION"
       condition:
         type: "paths_count"
         operator: ">"
         value: 10
       action: "WARN"
       rationale: "Too many paths found"
       enabled: true
       priority: 60
   ```

3. **Validate syntax**:
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('rules_config.yaml'))"
   ```

4. **Reload rules**:
   ```python
   from agentos.core.brain.governance.rule_loader import get_all_rules
   rules = get_all_rules(reload=True)
   ```

### Disabling a Rule

Set `enabled: false`:

```yaml
  - id: "nav_low_coverage_warn"
    enabled: false  # Rule will not evaluate
```

### Modifying Rule Priority

Change priority value (0-100, higher = earlier):

```yaml
  - id: "my_critical_rule"
    priority: 95  # Evaluates before priority 90 rules
```

### Rule Naming Conventions

- **ID**: `{type}_{purpose}_{action}` (e.g., `nav_high_risk_block`)
- **Name**: Capitalized description (e.g., "High Risk Block Rule")
- **Rationale**: Complete sentence explaining trigger
- **Description**: Optional detailed explanation

---

## Testing Rules

### Unit Testing a Rule

```python
from agentos.core.brain.governance.rule_loader import build_condition_function

# Define condition
config = {
    "type": "coverage_percentage",
    "operator": "<",
    "value": 0.4
}

# Build function
condition_fn = build_condition_function(config)

# Test
assert condition_fn({"coverage_percentage": 0.3}) == True
assert condition_fn({"coverage_percentage": 0.5}) == False
```

### Integration Testing

```python
from agentos.core.brain.governance.rule_engine import apply_governance_rules
from agentos.core.brain.governance.decision_record import DecisionType, GovernanceAction

# Simulate decision
inputs = {"seed": "file:test.py"}
outputs = {"coverage_percentage": 0.2, "paths_count": 1}

# Apply rules
triggers, verdict = apply_governance_rules(
    DecisionType.NAVIGATION,
    inputs,
    outputs
)

# Verify
assert verdict == GovernanceAction.WARN  # Or expected action
assert len(triggers) > 0
assert triggers[0].rule_id == "nav_low_coverage_warn"
```

### End-to-End Testing

```python
from agentos.core.brain.governance.decision_recorder import (
    save_decision_record,
    load_decision_record
)

# Create decision with rules
record = DecisionRecord(...)
record.record_hash = record.compute_hash()
save_decision_record(store, record)

# Load and verify
loaded = load_decision_record(store, record.decision_id)
assert len(loaded.rules_triggered) > 0
assert loaded.verify_integrity() == True
```

---

## Best Practices

### Rule Design

1. **Single Responsibility**: Each rule checks one condition
2. **Clear Rationale**: Explain why rule exists and when it triggers
3. **Appropriate Action**: Match action severity to risk level
4. **Testable Conditions**: Use quantifiable thresholds
5. **Documented Fields**: Document expected field names/types

### Priority Assignment

- **90-100**: Critical safety rules (block dangerous operations)
- **70-89**: Important policy rules (require signoff)
- **50-69**: Guidance rules (warn about issues)
- **0-49**: Informational rules (log events)

### Action Selection

- **BLOCK**: Use for violations that should never proceed
  - Example: Corrupted data, security violations

- **REQUIRE_SIGNOFF**: Use for high-risk but valid operations
  - Example: Large changes, production deployments

- **WARN**: Use for concerning but acceptable operations
  - Example: Low confidence, minor degradation

- **ALLOW**: Explicitly allow (rarely needed, default behavior)

### Configuration Management

1. **Version Control**: Track rules_config.yaml in git
2. **Change Review**: Require PR for rule changes
3. **Testing**: Test rule changes in staging
4. **Documentation**: Document rule intent and history
5. **Monitoring**: Track rule trigger frequency

### Performance Optimization

1. **Limit Rules**: < 50 active rules recommended
2. **Efficient Conditions**: Use simple comparisons (avoid regex)
3. **Early Exit**: Use priority to evaluate critical rules first
4. **Field Indexing**: Ensure commonly-checked fields are indexed

---

## Troubleshooting

### Rule Not Triggering

**Symptom**: Expected rule doesn't appear in decision_records.rules_triggered

**Diagnosis**:

1. Check rule is enabled:
   ```yaml
   enabled: true
   ```

2. Verify field name matches:
   ```python
   print(outputs.keys())  # Check available fields
   ```

3. Test condition in isolation:
   ```python
   condition_fn = build_condition_function(rule_config['condition'])
   print(condition_fn(outputs))  # Should be True
   ```

4. Check decision type matches:
   ```yaml
   applies_to: "NAVIGATION"  # Must match decision_type
   ```

---

### Wrong Final Verdict

**Symptom**: Final verdict differs from expected

**Cause**: Multiple rules triggered, most restrictive action selected

**Solution**: Review all triggered rules:

```python
for trigger in record.rules_triggered:
    print(f"{trigger.rule_id}: {trigger.action.value}")

# Final verdict = most restrictive action
```

**Action Priority**:
1. BLOCK (highest)
2. REQUIRE_SIGNOFF
3. WARN
4. ALLOW (lowest)

---

### Performance Degradation

**Symptom**: Decision recording takes > 10ms

**Diagnosis**:

1. Count active rules:
   ```python
   rules = get_all_rules()
   print(f"Active rules: {len(rules)}")
   ```

2. Profile rule evaluation:
   ```python
   import time
   start = time.time()
   triggers, verdict = apply_governance_rules(...)
   elapsed = time.time() - start
   print(f"Evaluation: {elapsed*1000:.2f}ms")
   ```

**Solutions**:
- Disable unnecessary rules
- Use priority for early exit
- Cache rule objects
- Simplify conditions

---

### Configuration Syntax Error

**Symptom**: `yaml.YAMLError` when loading rules

**Diagnosis**:

```bash
python3 -c "import yaml; yaml.safe_load(open('rules_config.yaml'))"
```

**Common Issues**:
- Indentation (use 2 spaces, not tabs)
- Missing quotes around strings with special chars
- Invalid YAML syntax

**Fix**:
```bash
# Validate YAML
yamllint rules_config.yaml

# Auto-format
yq eval -i '.' rules_config.yaml
```

---

### Rule Conflict

**Symptom**: Multiple rules with same ID

**Diagnosis**:

```bash
grep -E "^\s+- id:" rules_config.yaml | sort | uniq -d
```

**Solution**: Ensure unique IDs:
```yaml
  - id: "nav_rule_001"  # Unique
  - id: "nav_rule_002"  # Unique
```

---

### Field Not Found

**Symptom**: Condition always evaluates False

**Cause**: Field name typo or field not present in outputs

**Diagnosis**:

```python
# Check available fields
print(json.dumps(outputs, indent=2))

# Verify field in condition
config = rule['condition']
print(f"Checking field: {config['type']}")
```

**Solution**: Use correct field name:
```yaml
condition:
  type: "coverage_percentage"  # Must match outputs key exactly
```

---

## Appendix: Rule Quick Reference

### Navigation Rules

| ID                     | Action           | Threshold                |
|------------------------|------------------|--------------------------|
| nav_high_risk_block    | BLOCK            | blind_spot_severity >= 0.7 |
| nav_many_blind_spots   | REQUIRE_SIGNOFF  | total_blind_spots >= 3   |
| nav_low_confidence     | WARN             | avg_confidence < 0.5     |
| nav_low_coverage       | WARN             | coverage_percentage < 0.4 |

### Compare Rules

| ID                     | Action           | Threshold                     |
|------------------------|------------------|-------------------------------|
| cmp_health_drop_block  | BLOCK            | health_score_change < -0.2    |
| cmp_degradation        | REQUIRE_SIGNOFF  | overall_assessment = DEGRADED |
| cmp_coverage_drop      | WARN             | coverage_change < -10%        |
| cmp_entity_removal     | WARN             | entities_removed >= 10        |

### Health Rules

| ID                     | Action           | Threshold                        |
|------------------------|------------------|----------------------------------|
| health_low_coverage    | BLOCK            | coverage_percentage < 0.3        |
| health_critical        | REQUIRE_SIGNOFF  | current_health_level = CRITICAL  |
| health_decline         | WARN             | coverage_trend = DEGRADING       |
| health_debt            | WARN             | cognitive_debt_count >= 50       |

---

**Manual Version**: 1.0
**Last Updated**: 2026-01-31
**Feedback**: Submit issues to governance-rules@example.com
