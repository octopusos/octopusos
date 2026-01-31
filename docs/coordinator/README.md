# Coordinator v0.9.2

**Status**: 🚧 Design Phase  
**Version**: 0.9.2  
**Date**: 2026-01-25

---

## Overview

The **Coordinator** is AgentOS's planning engine that transforms ExecutionIntents (v0.9.1) into actionable, auditable execution plans. It operates on the core principle: **Plan, Don't Execute**.

**What Coordinator Does**:
- ✅ Transforms Intent → ExecutionGraph
- ✅ Adjudicates rules against planned actions
- ✅ Manages question governance (interactive/semi_auto/full_auto)
- ✅ Produces audit trails (RunTape)
- ✅ Generates review packages

**What Coordinator Does NOT Do**:
- ❌ Execute commands
- ❌ Modify files or repositories  
- ❌ Run shell scripts
- ❌ Commit or push code

---

## Quick Start

### Prerequisites
- v0.9.1 ExecutionIntent (frozen)
- ContentRegistry (v0.5+)
- MemoryPack (v0.2 - mandatory)
- ExecutionPolicy
- FactPack (project scan)

### Basic Usage

```python
from agentos.core.coordinator import CoordinatorEngine
from agentos.core.policy import ExecutionPolicy

# Initialize
engine = CoordinatorEngine(registry=registry, memory_service=memory)

# Run coordination
result = engine.coordinate(
    intent=intent_dict,
    policy=ExecutionPolicy.semi_auto(question_budget=3),
    factpack=factpack_dict
)

# Access outputs
execution_graph = result.graph
review_pack = result.review
run_tape = result.tape
```

### CLI Usage

```bash
# Coordinate an intent
agentos coordinate --intent intent_example_low_risk --policy semi_auto --output ./output

# Explain mode (human-readable report)
agentos coordinate explain --intent intent_example_low_risk
```

---

## Key Concepts

### 1. ExecutionGraph
A directed acyclic graph (DAG) representing the execution plan with:
- **Nodes**: phases, action_proposals, decision_points, questions, review_gates
- **Edges**: sequential, parallel, conditional dependencies
- **Swimlanes**: Agent role assignments

### 2. State Machine
13 states governing the coordination lifecycle:
- RECEIVED → PRECHECKED → CONTEXT_BUILT → RULES_EVALUATED → GRAPH_DRAFTED → QUESTIONS_EMITTED (optional) → AWAITING_ANSWERS (optional) → GRAPH_FINALIZED → REVIEW_PACK_BUILT → FROZEN_OUTPUTS → DONE
- Failure states: BLOCKED, ABORTED

### 3. Question Governance
Three modes:
- **interactive**: Allows all questions
- **semi_auto**: Only blocker questions
- **full_auto**: No questions (RED LINE: question_budget = 0)

### 4. Rule Adjudication
Every planned command is adjudicated by rules:
- **allow**: Command permitted
- **deny**: Command forbidden
- **warn**: Proceed with warning
- **require_review**: Manual review needed

### 5. Red Lines
Five critical constraints (from v0.9.1 Intent):
- **I1**: No execution payload
- **I2**: full_auto => question_budget = 0
- **I3**: High risk ≠ full_auto
- **I4**: All actions have evidence_refs
- **I5**: Registry only (no fabricated content)

---

## Documentation Index

### Core Specifications
- **[STATE_MACHINE_SPEC.md](STATE_MACHINE_SPEC.md)** - 13 states, transitions, guards
- **[IMPLEMENTATION_ARCHITECTURE.md](IMPLEMENTATION_ARCHITECTURE.md)** - 7 core classes, data flow
- **[RESPONSIBILITIES.md](RESPONSIBILITIES.md)** - What Coordinator does/doesn't do
- **[AUTHORING_GUIDE.md](AUTHORING_GUIDE.md)** - How to write ExecutionGraphs

### Quality Assurance
- **[V092_FREEZE_CHECKLIST_TEMPLATE.md](V092_FREEZE_CHECKLIST_TEMPLATE.md)** - Freeze criteria

### Schemas
- `agentos/schemas/coordinator/execution_graph.schema.json`
- `agentos/schemas/coordinator/question_pack.schema.json`
- `agentos/schemas/coordinator/answer_pack.schema.json`
- `agentos/schemas/coordinator/coordinator_run_tape.schema.json`
- `agentos/schemas/coordinator/coordinator_audit_log.schema.json`

### Examples
- `examples/coordinator/outputs/` - 3 complete examples

### Gates
- `scripts/gates/v092_gate_a_schemas_exist.py` - Schema existence
- `scripts/gates/v092_gate_b_schema_validation.py` - Batch validation
- `scripts/gates/v092_gate_c_negative_fixtures.py` - Negative testing
- `scripts/gates/v092_gate_d_no_execution_symbols.sh` - Static scan
- `scripts/gates/v092_gate_e_isolation.py` - Isolation test
- `scripts/gates/v092_gate_f_snapshot.py` - Snapshot stability
- `scripts/gates/v092_gate_g_state_machine_completeness.py` - State machine check
- `scripts/gates/v092_gate_h_graph_topology.py` - DAG validation
- `scripts/gates/v092_gate_i_question_governance.py` - Question rules
- `scripts/gates/v092_gate_j_rule_adjudication.py` - Rule coverage

---

## Architecture Overview

```
ExecutionIntent (v0.9.1)
         ↓
    Coordinator Engine
    ├─ IntentParser
    ├─ RulesAdjudicator
    ├─ GraphBuilder
    ├─ QuestionGovernor
    ├─ ModelRouter
    └─ OutputFreezer
         ↓
    Outputs:
    ├─ ExecutionGraph
    ├─ QuestionPack (if interactive/semi_auto)
    ├─ ReviewPack
    ├─ CoordinatorRunTape
    └─ CoordinatorAuditLog
```

---

## Development Status

| Component | Status |
|-----------|--------|
| **Schemas** | ✅ Complete |
| **Examples** | ✅ Complete |
| **State Machine Spec** | ✅ Complete |
| **Architecture Spec** | ✅ Complete |
| **Gate Scripts** | ✅ Complete |
| **Core Implementation** | 🚧 Pending |
| **Tests** | 🚧 Pending |
| **CLI** | 🚧 Pending |

---

## Running Gates

```bash
# Run all gates sequentially
uv run python scripts/gates/v092_gate_a_schemas_exist.py
uv run python scripts/gates/v092_gate_b_schema_validation.py
uv run python scripts/gates/v092_gate_c_negative_fixtures.py
bash scripts/gates/v092_gate_d_no_execution_symbols.sh
uv run python scripts/gates/v092_gate_e_isolation.py
uv run python scripts/gates/v092_gate_f_snapshot.py
uv run python scripts/gates/v092_gate_g_state_machine_completeness.py
uv run python scripts/gates/v092_gate_h_graph_topology.py
uv run python scripts/gates/v092_gate_i_question_governance.py
uv run python scripts/gates/v092_gate_j_rule_adjudication.py
```

---

## Contributing

1. **Read the specs**: STATE_MACHINE_SPEC.md and IMPLEMENTATION_ARCHITECTURE.md
2. **Follow the red lines**: No execution, only planning
3. **Run gates before commit**: All 10 gates must pass
4. **Document decisions**: Add rationale to CoordinatorRunTape

---

## Design Principles

1. **Separation of Concerns**: Planning ≠ Execution
2. **Auditability**: Every decision recorded
3. **Determinism**: Same input → Same output
4. **Safety**: No side effects, read-only registry/memory
5. **Evidence-Based**: All decisions backed by evidence

---

## FAQ

**Q: Why doesn't Coordinator execute the plan?**  
A: Separation of concerns. Coordinator produces auditable plans; execution is handled by a separate executor component.

**Q: Can I skip questions in interactive mode?**  
A: Yes, if the question has a `default_strategy`. The Coordinator will use the fallback.

**Q: What happens if a rule denies an action?**  
A: The Coordinator transitions to ABORTED state with a FailurePack explaining why.

**Q: Can I add custom nodes to the ExecutionGraph?**  
A: No. Node types are fixed: phase, action_proposal, decision_point, question, review_gate.

**Q: How do I debug a BLOCKED state?**  
A: Check the CoordinatorRunTape for the state transition that led to BLOCKED. The `failure_info` will explain the cause.

---

## License

MIT

---

**Version**: 0.9.2  
**Last Updated**: 2026-01-25  
**Maintainer**: AgentOS Team
