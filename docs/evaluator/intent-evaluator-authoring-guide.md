# Intent Evaluator Authoring Guide (v0.9.3)

## Overview

The Intent Evaluator is a **governance layer** that takes multiple Execution Intents and produces a structured evaluation result containing:
- Conflict detection
- Merge/override strategies
- Risk comparison
- Questions requiring human input

**Core Principle**: Evaluator = Multi-Intent Treatment + Conflict Detection + Merge Planning  
**Prohibition**: No execution payload, no commands, only governance decisions.

---

## Intent Evaluator Workflow

```
Input: Intent Set (2-20 Intents)
  ↓
Evaluator Engine
  ↓
Output: Evaluation Result (conflicts, merge plan, risk comparison, questions)
  ↓
(If merged) → New Intent → Coordinator → Execution Graph
(If questions) → QuestionPack → User → Evaluator (retry)
```

---

## 1. Intent Set Structure

An Intent Set collects multiple intents for evaluation.

### Required Fields

```json
{
  "id": "intent_set_api_refactor_batch",
  "type": "intent_set",
  "schema_version": "0.9.3",
  "created_at": "2026-01-25T10:00:00Z",
  "intent_ids": [
    "intent_refactor_api_routes",
    "intent_add_api_logging",
    "intent_update_api_tests"
  ],
  "context": {
    "project_id": "agentos",
    "env": "local",
    "tags": ["api", "refactor", "batch"]
  },
  "lineage": {
    "introduced_in": "0.9.3",
    "derived_from": []
  },
  "checksum": "<sha256 of intent_ids + context>"
}
```

### Context Fields

- **project_id**: Project identifier (must match all intents)
- **env**: Environment context (`local`, `dev`, `staging`, `prod`)
- **time_window**: Optional time range for execution
- **tags**: Optional tags for categorization

---

## 2. Conflict Types

The Evaluator detects 4 types of conflicts:

### A. Resource Conflict

**Definition**: Two or more intents target the same resource with conflicting operations.

**Example**:
```
Intent A: Write to src/api/routes.py
Intent B: Delete src/api/routes.py
→ Resource Conflict (same file, incompatible operations)
```

**Detection Criteria**:
- Same file/module/service
- Conflicting effects: write + delete, deploy + rollback

### B. Effect Conflict

**Definition**: Intents have incompatible side effects even if resources differ.

**Example**:
```
Intent A: Deploy service v2.0 (effect: deploy)
Intent B: Rollback service to v1.8 (effect: rollback)
→ Effect Conflict (incompatible deployment intentions)
```

**Detection Criteria**:
- Semantic incompatibility: deploy ↔ rollback, create ↔ delete
- Temporal incompatibility: both require exclusive system state

### C. Order Conflict

**Definition**: Intent B depends on Intent A's output, but execution order not specified.

**Example**:
```
Intent A: Generate API schema
Intent B: Generate client SDK from schema
→ Order Conflict (B requires A's output but no dependency declared)
```

**Detection Criteria**:
- Evidence refs in B reference artifacts from A
- Workflow phases show dependency (B.analysis depends on A.implementation)
- Registry dependencies not satisfied

### D. Constraint Conflict

**Definition**: Intents have incompatible constraints or budgets.

**Example**:
```
Intent A: lock_scope.mode = "files", lock_scope.paths = ["/src/api"]
Intent B: lock_scope.mode = "none" (wants to modify any file)
→ Constraint Conflict (A restricts scope, B ignores it)
```

**Detection Criteria**:
- Budget sum exceeds limits (max_cost_usd, max_tokens)
- Lock scope violations
- Interaction mode conflicts (one full_auto, one interactive)

---

## 3. Merge Strategies

The Evaluator determines merge strategy based on conflict analysis:

### A. merge_union (No/Low Conflicts)

**When to Use**:
- No resource conflicts
- All intents are read-only or analyze-only
- Commands can be combined without interference

**Operations**:
- Union all `planned_commands`
- Union all `selected_workflows`
- Union all `selected_agents`
- Union all `evidence_refs`
- Aggregate budgets (sum, then validate limits)
- Aggregate risk (take highest risk level)

**Result Intent**:
- `lineage.derived_from`: [intentA, intentB, ...]
- `lineage.supersedes`: []

**Example**:
```
Intent A: Analyze API performance
Intent B: Analyze API security
→ merge_union → Intent AB: Analyze API (performance + security)
```

### B. override_by_priority (Conflicting, Priority Clear)

**When to Use**:
- Resource/effect conflicts detected
- Intents have explicit or implicit priority
- Higher priority intent should supersede lower

**Priority Determination**:
1. Explicit `priority` field in intent metadata (if exists)
2. Risk level (lower risk > higher risk for safety)
3. Creation timestamp (newer > older)
4. Status (approved > proposed > draft)

**Operations**:
- Keep higher priority intent's conflicting fields
- Merge non-conflicting fields
- Mark lower priority intents as superseded

**Result Intent**:
- `lineage.derived_from`: [highPriorityIntent]
- `lineage.supersedes`: [lowPriorityIntent1, lowPriorityIntent2, ...]

**Example**:
```
Intent A (priority: 5): Refactor API v1
Intent B (priority: 10): Refactor API v2 (includes v1 scope)
→ override_by_priority → Intent B supersedes A
```

### C. reject (Conflicting, Priority Unclear)

**When to Use**:
- Resource/effect conflicts detected
- No clear priority between intents
- Cannot automatically resolve

**Output**:
- No result intent
- `requires_questions[]` populated with resolution options

**Example**:
```
Intent A: Deploy service to staging
Intent B: Deploy different version to staging
→ reject → QuestionPack: "Which version should be deployed?"
```

---

## 4. Risk Comparison

The Evaluator compares intents across 4 risk dimensions:

### Risk Dimensions

#### 1. effects_risk (0-100)
- **Calculation**: Based on planned_commands effects
- read = 0, write = 30, network = 40, deploy = 70, security = 90, data = 80

#### 2. scope_risk (0-100)
- **Calculation**: Based on scope.targets and env
- local = 10, dev = 20, staging = 50, prod = 100
- Multiplied by target breadth (files/modules/areas count)

#### 3. blast_radius (0-100)
- **Calculation**: Number of affected resources × criticality
- 1-5 files = 10, 6-20 files = 30, 21-50 files = 60, 51+ files = 90

#### 4. unknowns (0-100)
- **Calculation**: Inverse of evidence quality
- 0-5 evidence_refs = 90, 6-10 = 60, 11-20 = 30, 21+ = 10

### Risk Matrix Output

```json
{
  "matrix": [
    {
      "intent_id": "intent_a",
      "overall_risk": "medium",
      "dimensions": {
        "effects_risk": 30,
        "scope_risk": 40,
        "blast_radius": 25,
        "unknowns": 50
      }
    }
  ],
  "dominance": [
    {
      "intent_a": "intent_a",
      "intent_b": "intent_b",
      "relationship": "A_dominates_B"
    }
  ]
}
```

### Dominance Rules

- **A dominates B**: A has higher or equal risk in all dimensions
- **B dominates A**: B has higher or equal risk in all dimensions
- **incomparable**: Mixed (A higher in some, B higher in others)

---

## 5. Evaluation Result Structure

```json
{
  "id": "eval_result_api_batch_20260125",
  "type": "intent_evaluation_result",
  "schema_version": "0.9.3",
  "created_at": "2026-01-25T10:05:00Z",
  "input": {
    "intent_set_id": "intent_set_api_refactor_batch",
    "intent_checksums": {
      "intent_refactor_api_routes": "<checksum>",
      "intent_add_api_logging": "<checksum>"
    }
  },
  "evaluation": {
    "conflicts": [
      {
        "conflict_id": "conflict_routes_write",
        "type": "resource_conflict",
        "severity": "medium",
        "intent_ids": ["intent_refactor_api_routes", "intent_add_api_logging"],
        "resource_ref": "src/api/routes.py",
        "description": "Both intents write to the same file",
        "evidence_refs": ["factpack://file_scan/src/api/routes.py"],
        "resolutions": ["merge_union", "override_by_priority"]
      }
    ],
    "merge_plan": {
      "strategy": "merge_union",
      "operations": [
        {
          "op_id": "op_001",
          "operation": "union_commands",
          "source_intent_id": "intent_refactor_api_routes",
          "target_field": "planned_commands",
          "evidence": "Commands are complementary (refactor + logging)"
        }
      ],
      "result_intent_id": "intent_api_refactor_with_logging"
    },
    "risk_comparison": {
      "matrix": [...],
      "dominance": [...]
    }
  },
  "requires_questions": [],
  "constraints": {
    "execution": "forbidden"
  },
  "lineage": {
    "derived_from_intent_set": "intent_set_api_refactor_batch",
    "evaluator_version": "0.9.3"
  },
  "checksum": "<sha256 of evaluation>"
}
```

---

## 6. Red Lines (RL-E1, RL-E2)

### RL-E1: No Execution Payload

**Rule**: Evaluator outputs must NOT contain executable payload.

**Prohibited**:
- Fields: `execute`, `shell`, `subprocess`, `run`, `command_line`
- Symbols: `subprocess.run`, `os.system`, `eval(`, `exec(`

**Enforcement**:
- Schema Layer: `additionalProperties: false` + `constraints.execution: "forbidden"`
- Runtime Layer: `validate_red_lines()` checks for prohibited fields
- Static Layer: Gate D scans JSON for execution symbols

**Valid**:
```json
{
  "constraints": {
    "execution": "forbidden"  // REQUIRED constant
  }
}
```

**Invalid**:
```json
{
  "execute": "python script.py"  // PROHIBITED
}
```

### RL-E2: Merged Intent Must Have Lineage

**Rule**: Any intent produced by merge MUST have complete lineage.

**Required**:
- `lineage.derived_from`: Array of source intent IDs (min 1 for merge_union, min 1 for override)
- `lineage.supersedes`: Array of superseded intent IDs (required for override_by_priority)

**Enforcement**:
- Schema Layer: `result_intent.lineage` required, `derived_from` minItems: 1
- Runtime Layer: `MergePlanner.build_result_intent()` enforces lineage population
- Gate Layer: Gate J validates all merged intents have lineage

**Valid (merge_union)**:
```json
{
  "lineage": {
    "introduced_in": "0.9.3",
    "derived_from": ["intent_a", "intent_b"],  // REQUIRED
    "supersedes": []
  }
}
```

**Valid (override_by_priority)**:
```json
{
  "lineage": {
    "introduced_in": "0.9.3",
    "derived_from": ["intent_high_priority"],
    "supersedes": ["intent_low_priority"]  // REQUIRED for override
  }
}
```

**Invalid**:
```json
{
  "lineage": {
    "introduced_in": "0.9.3",
    "derived_from": [],  // INVALID: empty for merged intent
    "supersedes": []
  }
}
```

---

## 7. Authoring Checklist

### Intent Set
- [ ] At least 2 intent IDs
- [ ] All intent IDs exist and valid
- [ ] Context.project_id matches all intents
- [ ] Context.env is appropriate
- [ ] Checksum calculated (SHA-256 of intent_ids + context)
- [ ] Lineage.introduced_in = "0.9.3"

### Evaluation Result
- [ ] Input.intent_set_id references valid intent set
- [ ] Input.intent_checksums includes all evaluated intents
- [ ] Conflicts array covers all detected conflicts
- [ ] Each conflict has evidence_refs (min 1)
- [ ] Merge_plan.strategy is appropriate for conflicts
- [ ] Risk_comparison.matrix includes all intents
- [ ] Constraints.execution = "forbidden" (RL-E1)
- [ ] Lineage references intent set and evaluator version
- [ ] Checksum calculated

### Merge Plan
- [ ] Strategy matches conflict resolution
- [ ] Source_intent_ids includes all merged intents (min 2)
- [ ] Operations are ordered and complete
- [ ] Each operation has evidence
- [ ] Result_intent conforms to intent.schema.json
- [ ] Result_intent.lineage.derived_from populated (RL-E2)
- [ ] If override: result_intent.lineage.supersedes populated (RL-E2)
- [ ] Lineage.derived_from matches source_intent_ids
- [ ] Checksum calculated

---

## 8. Common Scenarios

### Scenario A: No Conflicts (All Read-Only)
```
Intents: [Analyze API, Scan for vulnerabilities]
→ No conflicts detected
→ merge_union
→ Result: Combined analysis intent
```

### Scenario B: Resource Conflict, Clear Priority
```
Intents: [Refactor API v1 (priority: 5), Refactor API v2 (priority: 10)]
→ Resource conflict: same files
→ override_by_priority (Intent v2)
→ Result: Intent v2, supersedes v1
```

### Scenario C: Resource Conflict, No Priority
```
Intents: [Deploy service A, Deploy service B to same environment]
→ Resource conflict: same deployment target
→ reject
→ Result: QuestionPack asking user to choose
```

### Scenario D: Order Conflict (Dependency)
```
Intents: [Generate schema, Generate SDK from schema]
→ Order conflict detected (SDK needs schema output)
→ merge_union with ordered operations
→ Result: Combined intent with sequential phases
```

---

## 9. Validation

To validate your Intent Set or Evaluation Result:

```bash
# Validate intent set schema
uv run python scripts/validate_intent_evaluation.py --schema intent_set <file.json>

# Validate evaluation result schema
uv run python scripts/validate_intent_evaluation.py --schema evaluation_result <file.json>

# Validate merge plan schema
uv run python scripts/validate_intent_evaluation.py --schema merge_plan <file.json>

# Run all evaluator gates
for gate in scripts/gates/v093_gate_*.py; do
  uv run python "$gate"
done
```

---

## 10. References

- **Schema**: `agentos/schemas/evaluator/intent_evaluation_result.schema.json`
- **Red Lines**: `docs/V093_REDLINES.md`
- **Intent Schema**: `agentos/schemas/execution/intent.schema.json`
- **Examples**: `examples/intents/evaluations/`
- **Invalid Fixtures**: `fixtures/evaluator/invalid/`

---

**Version**: 0.9.3  
**Status**: DRAFT → FROZEN (after Phase 7 complete)  
**Last Updated**: 2026-01-25
