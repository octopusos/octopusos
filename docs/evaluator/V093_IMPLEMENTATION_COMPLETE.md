# v0.9.3 Intent Evaluator — Implementation Complete

**Status**: 🟢 **FROZEN - Production Ready**  
**Date**: 2026-01-25  
**Version**: 0.9.3

---

## Overview

The Intent Evaluator is the **multi-intent governance layer** that evaluates sets of Execution Intents for conflicts, plans merges, compares risks, and produces structured evaluation results. It sits between Intent authoring (v0.9.1) and Coordinator execution planning (v0.9.2).

**Chain**: `Intent(s) → Evaluator → Coordinator → ExecutionGraph`

---

## Deliverables

### 1. Schemas (3)

| Schema | Location | Purpose |
|--------|----------|---------|
| intent_set.schema.json | `agentos/schemas/evaluator/` | Collection of intents for evaluation |
| intent_evaluation_result.schema.json | `agentos/schemas/evaluator/` | Evaluation output with conflicts, merge plan, risk comparison |
| intent_merge_plan.schema.json | `agentos/schemas/evaluator/` | Detailed merge operations and resulting intent |

**Key Features**:
- JSON Schema Draft 2020-12
- `additionalProperties: false` (frozen structure)
- Schema version: `"0.9.3"`
- All schemas include:
  - `id` (unique identifier)
  - `lineage` (traceability)
  - `checksum` (SHA-256 integrity)
  - `constraints.execution: "forbidden"` (RL-E1 enforcement)

### 2. Core Engine (7 Classes)

| Class | Location | Responsibility |
|-------|----------|---------------|
| IntentSetLoader | `agentos/core/evaluator/intent_set_loader.py` | Load and validate intent sets with checksum verification |
| IntentNormalizer | `agentos/core/evaluator/intent_normalizer.py` | Normalize intents for consistent comparison (resources, effects, scope) |
| ConflictDetector | `agentos/core/evaluator/conflict_detector.py` | Detect 4 conflict types: resource, effect, order, constraint |
| RiskComparator | `agentos/core/evaluator/risk_comparator.py` | Build risk matrix, compute dominance across 4 dimensions |
| MergePlanner | `agentos/core/evaluator/merge_planner.py` | Plan merges (union/override/reject), generate operations |
| EvaluatorEngine | `agentos/core/evaluator/engine.py` | Main orchestrator: load → normalize → detect → compare → plan → freeze |
| EvaluationExplainer | `agentos/core/evaluator/evaluation_explainer.py` | Generate stable explanations for Gate F snapshots |

**Key Principles**:
- **No Execution**: Evaluator produces governance decisions, never executable payloads (RL-E1)
- **Lineage Required**: All merged intents have `derived_from` + `supersedes` (RL-E2)
- **Deterministic**: Same inputs → same evaluation results (testable via Gate F)

### 3. Examples (3 Scenarios)

| Example | Location | Scenario |
|---------|----------|----------|
| eval_example_mergeable.json | `examples/intents/evaluations/` | Read-only intents, merge_union strategy, no conflicts |
| eval_example_override.json | `examples/intents/evaluations/` | Conflicting intents with clear priority, override_by_priority |
| eval_example_reject.json | `examples/intents/evaluations/` | Conflicting deployments, same priority, reject → QuestionPack |

Each example includes:
- Intent set file
- 2+ source intents
- Complete evaluation result with conflicts, merge plan, risk comparison

### 4. Invalid Fixtures (6 Red Line Violations)

| Fixture | Violation | Purpose |
|---------|-----------|---------|
| eval_has_execute_field.json | RL-E1 | Contains `execute` field in output |
| eval_no_lineage.json | RL-E2 | Missing `derived_from_intent_set` |
| eval_missing_evidence.json | Missing `evidence_refs` in conflicts | |
| eval_invalid_conflict_type.json | Invalid enum value | |
| eval_output_has_subprocess.json | RL-E1 | Contains "subprocess" symbol |
| eval_missing_checksum.json | Missing required field | |

### 5. Gates (10: A-J)

| Gate | Purpose | Implementation |
|------|---------|---------------|
| **A** | Existence and Naming | `v093_gate_a_evaluations_exist.py` - ≥3 examples, unique IDs |
| **B** | Schema Validation | `v093_gate_b_schema_validation.py` - All examples pass schema |
| **C** | Negative Fixtures | `v093_gate_c_negative_fixtures.py` - Invalid fixtures rejected |
| **D** | Static Scan | `v093_gate_d_no_execution_symbols.sh` - No execution symbols |
| **E** | Isolation | `v093_gate_e_isolation.py` - Runs in temp environment |
| **F** | Explain Snapshot | `v093_gate_f_snapshot.py` - Output structure stable |
| **G** | Conflict Detection | `v093_gate_g_conflict_detection.py` - All 4 conflict types detectable |
| **H** | Merge Replay | `v093_gate_h_merge_replay.py` - Merge plans serializable |
| **I** | Risk Consistency | `v093_gate_i_risk_consistency.py` - Risk computation deterministic |
| **J** | Lineage Enforcement | `v093_gate_j_lineage_enforcement.py` - RL-E2 verified |

**Gate Execution**:
```bash
for gate in scripts/gates/v093_gate_*.{py,sh}; do
  [ -f "$gate" ] && (python "$gate" 2>/dev/null || bash "$gate") || exit 1
done
```

### 6. CLI Commands

```bash
agentos evaluator run --input-set <path> --output <path>
agentos evaluator diff <intentA> <intentB>
agentos evaluator merge --strategy <strategy> --inputs <dir> --output <path>
agentos evaluator explain --result <evaluation_result.json>
```

**Implementation**: `agentos/cli/evaluator.py`

### 7. Validation Script

**Script**: `scripts/validate_intent_evaluation.py`

**Usage**:
```bash
# Validate schema
python scripts/validate_intent_evaluation.py --schema <file.json>

# Validate checksum
python scripts/validate_intent_evaluation.py --checksum <file.json>

# Validate red lines
python scripts/validate_intent_evaluation.py --red-lines <file.json>

# All validations
python scripts/validate_intent_evaluation.py --all <file.json>

# Explain
python scripts/validate_intent_evaluation.py --explain <file.json>
```

### 8. Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Intent Evaluator Authoring Guide | `docs/evaluator/intent-evaluator-authoring-guide.md` | How to construct intent sets, understand conflicts, choose strategies |
| V093 Red Lines | `docs/V093_REDLINES.md` | RL-E1 (no execution) and RL-E2 (lineage required) with 3-layer enforcement |
| Implementation Complete | `docs/evaluator/V093_IMPLEMENTATION_COMPLETE.md` | This document |
| Freeze Checklist Report | `docs/evaluator/V093_FREEZE_CHECKLIST_REPORT.md` | Freeze verification checklist |

---

## Red Lines

### RL-E1: Evaluator Must Not Produce Executable Payload

**Enforcement**:
1. **Schema Layer**: `additionalProperties: false` + `constraints.execution: "forbidden"` (constant)
2. **Runtime Layer**: `validate_red_lines()` checks for prohibited fields (`execute`, `shell`, `subprocess`, etc.)
3. **Static Layer**: Gate D scans for execution symbols

**Prohibited**:
- Fields: `execute`, `shell`, `subprocess`, `run`, `command_line`, `script`, `bash`, `python_code`
- Symbols: `subprocess.run`, `os.system`, `eval(`, `exec(`, `import subprocess`

### RL-E2: Merged Intent Must Have Complete Lineage

**Enforcement**:
1. **Schema Layer**: `result_intent.lineage` required, `derived_from` minItems: 1
2. **Runtime Layer**: `MergePlanner.build_result_intent()` enforces lineage population
3. **Gate Layer**: Gate J validates all merged intents have lineage

**Required**:
- `merge_union`: `derived_from` ≥ 1
- `override_by_priority`: `derived_from` ≥ 1 AND `supersedes` ≥ 1

---

## Conflict Detection

### 4 Conflict Types

| Type | Criteria | Example |
|------|----------|---------|
| **resource_conflict** | Same resource + write effects | Both write to `routes.py` |
| **effect_conflict** | Incompatible side effects | `deploy` vs `rollback` |
| **order_conflict** | Dependency not declared | B needs A's output but no sequence |
| **constraint_conflict** | Budget/scope violations | Interaction mode conflicts |

### Merge Strategies

| Strategy | When | Output |
|----------|------|--------|
| **merge_union** | No/low conflicts, read-only | Merged intent with union of commands/workflows/agents |
| **override_by_priority** | Conflicts + clear priority | Higher priority intent with `supersedes` lineage |
| **reject** | Conflicts + no clear priority | QuestionPack for user resolution |

### Risk Comparison

**4 Dimensions**:
1. **effects_risk** (0-100): Based on command effects (read=0, write=30, deploy=70, security=90)
2. **scope_risk** (0-100): Based on env (local=10%, staging=50%, prod=100%) × target breadth
3. **blast_radius** (0-100): Number of affected resources
4. **unknowns** (0-100): Inverse of evidence quality

**Dominance**: A dominates B if A ≥ B in all dimensions

---

## Integration with v0.9.2 Coordinator

**Workflow**:
```
User submits multiple intents
  ↓
Evaluator.evaluate(intent_set)
  ↓
if strategy = merge_union or override:
  result_intent → Coordinator.coordinate() → ExecutionGraph
else if strategy = reject:
  QuestionPack → User → (retry evaluation with selected intent)
```

---

## File Structure

```
agentos/
├── schemas/evaluator/
│   ├── intent_set.schema.json
│   ├── intent_evaluation_result.schema.json
│   └── intent_merge_plan.schema.json
├── core/evaluator/
│   ├── __init__.py
│   ├── intent_set_loader.py
│   ├── intent_normalizer.py
│   ├── conflict_detector.py
│   ├── risk_comparator.py
│   ├── merge_planner.py
│   ├── engine.py
│   └── evaluation_explainer.py
└── cli/
    └── evaluator.py

examples/intents/evaluations/
├── intent_set_*.json (3 sets)
├── intent_*.json (6 source intents)
└── eval_example_*.json (3 evaluation results)

fixtures/evaluator/invalid/
└── eval_*.json (6 invalid fixtures)

scripts/
├── validate_intent_evaluation.py
└── gates/
    ├── v093_gate_a_evaluations_exist.py
    ├── v093_gate_b_schema_validation.py
    ├── v093_gate_c_negative_fixtures.py
    ├── v093_gate_d_no_execution_symbols.sh
    ├── v093_gate_e_isolation.py
    ├── v093_gate_f_snapshot.py
    ├── v093_gate_g_conflict_detection.py
    ├── v093_gate_h_merge_replay.py
    ├── v093_gate_i_risk_consistency.py
    └── v093_gate_j_lineage_enforcement.py

docs/
├── evaluator/
│   ├── intent-evaluator-authoring-guide.md
│   ├── V093_IMPLEMENTATION_COMPLETE.md
│   └── V093_FREEZE_CHECKLIST_REPORT.md
└── V093_REDLINES.md
```

---

## Verification Commands

```bash
# Validate all schemas
for eval in examples/intents/evaluations/eval_example_*.json; do
  python scripts/validate_intent_evaluation.py --schema "$eval" || exit 1
done

# Run all gates
for gate in scripts/gates/v093_gate_*.{py,sh}; do
  [ -f "$gate" ] && (python "$gate" 2>/dev/null || bash "$gate") || exit 1
done

# Test CLI commands
agentos evaluator run --input-set examples/intents/evaluations/intent_set_api_analysis_mergeable.json
agentos evaluator diff examples/intents/evaluations/intent_analyze_api_performance.json \
                       examples/intents/evaluations/intent_analyze_api_security.json
agentos evaluator explain examples/intents/evaluations/eval_example_mergeable.json
```

---

## Change Log

### v0.9.3 (2026-01-25)

**Added**:
- Intent Evaluator engine with 7 core classes
- 3 evaluator schemas (intent_set, evaluation_result, merge_plan)
- 4 conflict detection types
- 3 merge strategies (union, override, reject)
- Risk comparison with 4 dimensions
- 10 gates (A-J) for comprehensive validation
- CLI commands: `agentos evaluator run/diff/merge/explain`
- 2 red lines (RL-E1: no execution, RL-E2: lineage required)

---

## Known Limitations

1. **Priority Inference**: Priority determination is heuristic-based (status, risk). For production, consider explicit priority fields in intent metadata.
2. **Conflict Resolution**: Some complex conflicts (e.g., circular dependencies) may require manual resolution.
3. **Risk Scoring**: Risk dimensions use simple heuristics. Production deployments may need custom risk models.

---

## Next Steps (Post-v0.9.3)

1. **Cloud/Local Model Adapter** (non-core): Extend ModelRouter with provider registry
2. **Enhanced Priority System**: Add explicit priority negotiation protocol
3. **Advanced Conflict Resolution**: Support for complex dependency graphs
4. **Custom Risk Models**: Pluggable risk computation engines

---

**Version**: 0.9.3  
**Status**: 🔒 **FROZEN - Production Ready**  
**Maintained by**: AgentOS Core Team  
**Last Updated**: 2026-01-25
