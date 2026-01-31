# Coordinator Responsibilities (v0.9.2)

**Version**: 0.9.2  
**Status**: Design Specification  
**Date**: 2026-01-25

---

## Core Mission

The Coordinator's **sole mission** is to transform a validated ExecutionIntent into an actionable, auditable execution plan without executing anything.

**One-sentence definition**: "Coordinator is the AI's planning brain, not its hands."

---

## What Coordinator DOES (5 Core Responsibilities)

### 1. Intent Parsing & Validation

**Purpose**: Extract structured information from ExecutionIntent and validate integrity

**Activities**:
- Parse Intent structure (v0.9.1 schema)
- Validate Intent checksum (SHA-256)
- Verify Intent red lines (I1-I5)
- Resolve registry references (workflows, agents, commands, rules)
- Check version drift (registry changes since Intent creation)
- Extract constraints (budgets, lock_scope, requires_review)

**Outputs**:
- `ParsedIntent`: Structured extraction
- `PrecheckReport`: Validation results

**Red Lines Enforced**:
- I1: No execution payload in Intent
- I5: All references must exist in ContentRegistry

**Example**:
```python
parsed = intent_parser.parse(intent)
# Returns:
# - workflows: [{"workflow_id": "docs", "phases": ["analysis", "implementation"]}]
# - agents: [{"agent_id": "doc_agent", "role": "documenter"}]
# - commands: [{"command_id": "scan_files", "effects": ["read"], "risk_level": "low"}]
# - constraints: {"execution": "forbidden", "max_files": 15}
```

---

### 2. Rules Adjudication

**Purpose**: Evaluate every planned action against applicable rules to make machine-decidable judgments

**Activities**:
- Load applicable rules from ContentRegistry
- Evaluate each `planned_command` against rule `when` conditions
- Generate `RuleDecision` for each evaluation (allow/deny/warn/require_review)
- Build evidence chains (why this decision was made)
- Aggregate decisions into `RiskAssessment`
- Detect rule conflicts and resolve per policy

**Outputs**:
- `RuleDecision[]`: One per planned command
- `RiskAssessment`: Overall risk classification
- Rule evaluation records in RunTape

**Red Lines Enforced**:
- All rules must be machine-decidable (structured `when`/`then`)
- All decisions must have evidence_refs (no "gut feelings")
- No "skip rules" allowed

**Example**:
```python
decisions = adjudicator.adjudicate_all(commands, context)
# Returns:
# - RuleDecision(command="modify_file", rule="require_evidence_for_write", decision="allow", evidence_refs=[...])
# - RuleDecision(command="deploy_api", rule="high_risk_requires_review", decision="require_review", evidence_refs=[...])
```

**Decision Types**:
- **allow**: Action permitted, proceed
- **deny**: Action forbidden, Coordinator → ABORTED
- **warn**: Proceed with warning logged
- **require_review**: Action flagged for human review (added to ReviewPack)

---

### 3. Graph Building

**Purpose**: Construct ExecutionGraph representing the execution plan as a DAG

**Activities**:
- Map workflow phases to `phase` nodes
- Map planned commands to `action_proposal` nodes (with evidence_refs)
- Create `decision_point` nodes (rule adjudications)
- Add `question` nodes (if uncertainties exist and policy allows)
- Add `review_gate` nodes (based on requires_review from Intent)
- Build edges (sequential/parallel/conditional)
- Assign nodes to agent swimlanes (role-based responsibility)
- Validate graph topology (DAG, no cycles)
- Perform topological sort (execution order)

**Outputs**:
- `ExecutionGraph`: Nodes, edges, swimlanes, lineage, checksum

**Red Lines Enforced**:
- I4: All `action_proposal` nodes must have `evidence_refs`
- Graph must be a DAG (cycles → BLOCKED)
- All nodes must be reachable
- All nodes must be assigned to swimlanes

**Example**:
```
Nodes:
  - node_phase_001: "Analysis Phase"
  - node_action_001: "Scan Files" (command_ref="scan_python_files", effects=["read"], evidence_refs=[...])
  - node_phase_002: "Implementation Phase"
  - node_action_002: "Add Docstrings" (command_ref="modify_file", effects=["write"], evidence_refs=[...])
  - node_review_001: "Documentation Review" (review_gate)

Edges:
  - edge_001: node_phase_001 → node_action_001 (sequential)
  - edge_002: node_action_001 → node_phase_002 (sequential)
  - edge_003: node_phase_002 → node_action_002 (sequential)
  - edge_004: node_action_002 → node_review_001 (sequential)
```

---

### 4. Question Governance

**Purpose**: Manage question emission and answer integration according to ExecutionPolicy

**Activities**:
- Detect uncertainties during graph construction
- Classify questions (blocker/clarification/optimization/risk_mitigation)
- Check question_budget constraints
- Generate `QuestionPack` with evidence attribution (归因)
- Calculate question impact (which nodes affected)
- Define fallback strategies (if question not answered)
- Wait for `AnswerPack` (in AWAITING_ANSWERS state)
- Integrate answers into ExecutionGraph
- Detect answer-rule conflicts (re-evaluate if needed)

**Outputs**:
- `QuestionPack`: Questions with evidence_refs, impact, fallback
- Updated ExecutionGraph (after answers integrated)

**Red Lines Enforced**:
- I2: full_auto mode → question_budget = 0 (QUESTIONS_EMITTED state skipped)
- All questions must have evidence_refs (归因)
- All questions must have fallback strategy

**Example**:
```python
# Interactive mode: question detected
question = {
    "question_id": "q_migration_strategy",
    "type": "blocker",
    "blocking_level": "critical",
    "question_text": "Should migration be online or offline?",
    "context": "Zero-downtime requirement but potential locking issues detected",
    "evidence_refs": ["scan://database/users_table", "doc://migration_standards.md"],
    "default_strategy": "Use offline migration if not answered (safer)",
    "impact": {"scope": "entire_plan", "affected_nodes": ["node_action_002", "node_action_003"]}
}
```

**Policy Enforcement**:
- **interactive**: All question types allowed
- **semi_auto**: Only `blocker` questions allowed
- **full_auto**: No questions (uncertainty → use fallback or → BLOCKED)

---

### 5. Model Routing

**Purpose**: Select appropriate models for reasoning tasks and record decisions

**Activities**:
- Identify tasks requiring model reasoning (e.g., rule adjudication, graph optimization)
- Select model (local vs cloud) based on:
  - Task type
  - Data sensitivity (confidential data → local model)
  - Cost budget (max_cost_usd from Intent)
  - Policy constraints
- Estimate cost
- Record model routing decisions in RunTape
- Select fallback models if primary unavailable

**Outputs**:
- `ModelRoutingDecision[]`: Model selections with rationale
- Audit log entries

**Red Lines Enforced**:
- Respect data_sensitivity constraints (no cloud model for confidential data)
- Stay within cost budget (max_cost_usd)
- No model routing for execution (Coordinator doesn't execute)

**Example**:
```python
decision = {
    "decision_id": "model_decision_001",
    "task_type": "database_migration_reasoning",
    "model_selected": "claude-3-sonnet",
    "reason": "High-risk database change requires careful reasoning",
    "cost_estimate": 2.5,
    "budget_remaining": 7.5,
    "data_sensitivity": "confidential",
    "fallback_available": true
}
```

---

## What Coordinator DOES NOT DO (Clear Boundaries)

### ❌ 1. Does NOT Execute

**Forbidden Activities**:
- Run shell commands (`subprocess`, `os.system`)
- Execute code (`eval`, `exec`)
- Modify files or directories
- Git operations (`git commit`, `git push`)
- Deploy to servers
- Run tests
- Start/stop services

**Why**: Execution is the responsibility of a separate Executor component. Coordinator only plans.

**Red Line Enforcement**: Gate D static scan detects execution symbols in code.

---

### ❌ 2. Does NOT Bypass Rules or Gates

**Forbidden Activities**:
- Skip rule evaluation ("we'll check later")
- Override rule decisions without evidence
- Fabricate registry content
- Modify global state (registry, memory, files)
- Circumvent red lines

**Why**: Rules and gates are the safety net. Bypassing them breaks auditability and safety.

**Red Line Enforcement**: All rule evaluations recorded in RunTape. No "skip" logic allowed.

---

### ❌ 3. Does NOT Generate Content Not in Registry

**Forbidden Activities**:
- Invent new workflow phases not in registry
- Create ad-hoc agent definitions
- Fabricate command definitions
- Make up rules on the fly

**Why**: I5 red line — all content must come from ContentRegistry for governance.

**Red Line Enforcement**: IntentParser validates all references against registry in PRECHECKED state.

---

### ❌ 4. Does NOT Merge Roles

**Forbidden Activities**:
- Act as "super agent" handling all tasks
- Mix planning and execution
- Directly interact with external systems
- Make decisions outside its state machine

**Why**: Single Responsibility Principle. Coordinator = Planning. Executor = Execution.

---

### ❌ 5. Does NOT Make Opaque Decisions

**Forbidden Activities**:
- "Black box" decisions without rationale
- Rule evaluations without evidence
- Questions without evidence attribution
- Risk assessments without reasoning

**Why**: Auditability is core. Every decision must be explainable and traceable.

**Red Line Enforcement**: All decisions recorded in CoordinatorRunTape with rationale and evidence_refs.

---

## Three Anti-Patterns (Common Mistakes)

### Anti-Pattern 1: Coordinator-as-Executor

**Symptom**: Coordinator starts running commands, modifying files, executing scripts

**Why It's Wrong**: Violates separation of concerns. Planning ≠ Execution.

**Detection**: Gate D static scan finds execution symbols

**Fix**: Remove all execution logic. Coordinator outputs plans; Executor consumes plans.

**Example of Violation**:
```python
# ❌ WRONG
def _handle_graph_finalized(self, context):
    subprocess.run(["git", "commit", "-m", "Add docs"])  # EXECUTION!
    return {"status": "committed"}

# ✅ CORRECT
def _handle_graph_finalized(self, context):
    # Just finalize the graph, don't execute
    graph = self.graph_builder.finalize(context)
    return {"graph": graph}
```

---

### Anti-Pattern 2: Rule-Skipping

**Symptom**: "This command is safe, we don't need to check rules" or "Let's evaluate rules later"

**Why It's Wrong**: Breaks auditability. All actions must be adjudicated.

**Detection**: Gate J checks rule coverage (all action_proposal nodes must have rule evaluations)

**Fix**: Never skip rules. If a rule isn't applicable, document why in RuleDecision.

**Example of Violation**:
```python
# ❌ WRONG
def add_action_proposal(self, command):
    # Skipping rule check because it's "obviously safe"
    node = {"node_type": "action_proposal", "command_ref": command}
    self.graph["nodes"].append(node)

# ✅ CORRECT
def add_action_proposal(self, command, rule_decision):
    # Rule decision required
    if rule_decision.decision == "deny":
        raise ValueError(f"Rule denies command: {command}")
    node = {
        "node_type": "action_proposal",
        "command_ref": command,
        "evidence_refs": rule_decision.evidence_refs
    }
    self.graph["nodes"].append(node)
```

---

### Anti-Pattern 3: Opaque Decision-Making

**Symptom**: Decisions made without evidence or rationale. "The model decided X" with no explanation.

**Why It's Wrong**: Not auditable. Violates transparency.

**Detection**: Manual review of CoordinatorRunTape (decisions should have rationale and evidence)

**Fix**: Every decision must have: `rationale`, `evidence_refs`, alternatives_considered.

**Example of Violation**:
```python
# ❌ WRONG
decision = {
    "decision_id": "d001",
    "outcome": "use_online_migration"
    # No rationale, no evidence!
}

# ✅ CORRECT
decision = {
    "decision_id": "d001",
    "decision_type": "question_emission",
    "inputs": {
        "evidence_refs": ["scan://database/users_table", "intent://zero_downtime_requirement"]
    },
    "rationale": "Intent requires zero downtime but analysis shows potential locking issues. Need user clarification.",
    "outcome": "emit_blocker_question_on_migration_strategy",
    "alternatives_considered": [
        {"alternative": "assume_offline_migration", "reason_rejected": "Violates zero-downtime requirement"}
    ]
}
```

---

## Future Anti-Patterns (Post v0.9.2 - Must Avoid!)

These are **preventive red lines** established to avoid common pitfalls as the system evolves.

### 🚫 Future Anti-Pattern X1: Coordinator-Calls-Executor

**Symptom**: Coordinator directly imports or calls Executor, even for "testing" or "dry-run"

**Why It's Wrong**: Violates architectural isolation. Planning and Execution must be separate modules with zero dependencies.

**Prohibited Code**:
```python
# ❌ ABSOLUTELY FORBIDDEN
from agentos.executor import CommandExecutor

class CoordinatorEngine:
    def coordinate(self, intent):
        graph = self.build_graph(intent)
        # NO! Even for testing!
        executor = CommandExecutor(dry_run=True)
        executor.test_graph(graph)
```

**Correct Pattern**:
```python
# ✅ CORRECT: Zero coupling
class CoordinatorEngine:
    def coordinate(self, intent, policy, factpack):
        # Only produce ExecutionGraph
        graph = self.graph_builder.build_graph(...)
        return CoordinatorRun(graph=graph)

# External orchestration (in main.py or workflow)
coordinator = CoordinatorEngine(registry, memory)
run = coordinator.coordinate(intent, policy, factpack)
# Separate component consumes graph
executor = CommandExecutor()
result = executor.execute(run.graph)
```

**Detection**: Gate X1 (static scan for `import executor` in coordinator module)

**See**: docs/coordinator/FUTURE_RED_LINES.md - Red Line X1

---

### 🚫 Future Anti-Pattern X2: ModelRouter-Does-Adjudication

**Symptom**: ModelRouter makes business decisions (allow/deny/approve) instead of just selecting models

**Why It's Wrong**: Conflates "model selection" (optimization) with "rule adjudication" (governance). Decisions become non-replayable.

**Prohibited Code**:
```python
# ❌ FORBIDDEN: ModelRouter making adjudication decisions
class ModelRouter:
    def decide_if_action_allowed(self, action, rules):
        model = self.select_model("adjudication")
        # NO! This is RulesAdjudicator's job
        return model.evaluate(action, rules)
```

**Correct Pattern**:
```python
# ✅ CORRECT: Separation of concerns
class ModelRouter:
    """ONLY for model selection"""
    def select_model(self, task_type, context) -> ModelDecision:
        # Just recommend a model
        if context["data_sensitivity"] == "confidential":
            return ModelDecision(model="local_llama", reason="Data privacy")
        return ModelDecision(model="claude-3-sonnet", reason="Cloud OK")

class RulesAdjudicator:
    """ONLY for adjudication"""
    def adjudicate(self, command, rules, evidence) -> RuleDecision:
        # May use ModelRouter to pick reasoning model
        model_decision = self.model_router.select_model("rule_reasoning")
        # But adjudication logic stays here
        if command.risk_level == "high":
            return RuleDecision(decision="require_review", evidence=evidence)
```

**Detection**: Code review + Audit Log check (all RuleDecisions must come from RulesAdjudicator)

**See**: docs/coordinator/FUTURE_RED_LINES.md - Red Line X2

---

### 🚫 Future Anti-Pattern X3: Bypassing-ExecutionGraph

**Symptom**: Direct command execution without going through ExecutionGraph. Creating "shortcut" execution paths.

**Why It's Wrong**: Loses auditability, lineage, checksums, and bypasses all Gates.

**Prohibited Code**:
```python
# ❌ FORBIDDEN: Shortcuts bypass all safety mechanisms
class CommandExecutor:
    def run_commands(self, commands: list):
        # NO! Missing lineage, checksum, evidence, Gates
        for cmd in commands:
            self._execute(cmd)
    
    def quick_fix(self, script: str):
        # NO! Temporary scripts bypass graph structure
        os.system(script)

class Coordinator:
    def fast_mode(self, intent):
        # NO! Skipping graph construction
        commands = self._extract_commands(intent)
        executor.run_commands(commands)  # Wrong!
```

**Correct Pattern**:
```python
# ✅ CORRECT: ExecutionGraph is the ONLY entry point
class CommandExecutor:
    def execute(self, graph: ExecutionGraph) -> ExecutionReport:
        """The ONLY entry point - no shortcuts allowed"""
        # 1. Validate schema
        validate_schema(graph, "execution_graph.schema.json")
        # 2. Check lineage
        if not graph.lineage:
            raise ValueError("Graph missing lineage")
        # 3. Verify checksum
        if not self._verify_checksum(graph):
            raise ValueError("Graph checksum mismatch")
        # 4. Run Gates
        if not run_gate_h(graph):
            raise ValueError("Graph failed topology validation")
        # 5. Execute
        return self._execute_graph(graph)
```

**Architecture Contract**:
```
Intent → Coordinator → ExecutionGraph (frozen, checksummed) → Executor → Report
                        ↑
                   ONLY THIS PATH
```

**Detection**: 
- Type checking (Executor.execute() must only accept ExecutionGraph)
- Gate X3 (interface enforcement)
- Code review (no run_commands/run_script methods allowed)

**See**: docs/coordinator/FUTURE_RED_LINES.md - Red Line X3

---

## Responsibility Summary Table

| Activity | Coordinator Responsibility | Executor Responsibility |
|----------|---------------------------|-------------------------|
| Parse Intent | ✅ Yes | ❌ No |
| Validate Rules | ✅ Yes | ❌ No |
| Build Graph | ✅ Yes | ❌ No |
| Ask Questions | ✅ Yes | ❌ No |
| Run Commands | ❌ No | ✅ Yes |
| Modify Files | ❌ No | ✅ Yes |
| Git Commit | ❌ No | ✅ Yes |
| Generate ReviewPack | ✅ Yes | ❌ No |
| Execute Tests | ❌ No | ✅ Yes |
| Monitor Execution | ❌ No | ✅ Yes |

---

## Enforcement Mechanisms

### Schema Layer
- `additionalProperties: false` (frozen structure)
- Required fields enforcement
- Pattern validation (no execution fields)

### Runtime Layer
- Gate D: Static scan for execution symbols
- Gate E: Isolation testing (no global state modification)
- State machine guards (prevent invalid transitions)

### Audit Layer
- CoordinatorRunTape: Every decision recorded
- CoordinatorAuditLog: All events logged
- Evidence attribution: All decisions have evidence_refs

---

## Decision Authority Matrix

| Decision Type | Coordinator Authority | Requires External Input |
|---------------|----------------------|------------------------|
| Rule adjudication | ✅ Full authority | ❌ No (uses evidence + rules) |
| Risk assessment | ✅ Full authority | ❌ No (derived from rule decisions) |
| Graph construction | ✅ Full authority | ❌ No (based on Intent + rules) |
| Question emission | ✅ Full authority | ⚠️ Policy constraints |
| Model selection | ✅ Full authority | ⚠️ Budget + policy |
| Execution timing | ❌ No authority | ✅ Yes (Executor decides) |
| Rollback | ❌ No authority | ✅ Yes (Executor + human) |
| Deployment | ❌ No authority | ✅ Yes (Executor + approval) |

---

**Status**: ✅ Specification Complete  
**Enforcement**: 3-tier (Schema + Runtime + Audit)
