# AgentOS v3 User Guide

**Version**: 3.0.0
**Last Updated**: 2026-02-01
**Audience**: End users, system operators, governance teams

---

## Table of Contents

1. [v3 Core Concepts](#chapter-1-v3-core-concepts)
2. [Golden Path详解](#chapter-2-golden-path详解)
3. [Agent→Capability Model](#chapter-3-agentcapability-model)
4. [Decision Workflow使用指南](#chapter-4-decision-workflow使用指南)
5. [Action执行和Rollback](#chapter-5-action执行和rollback)
6. [Evidence和Replay](#chapter-6-evidence和replay)
7. [Governance和Risk管理](#chapter-7-governance和risk管理)
8. [UI操作手册](#chapter-8-ui操作手册)
9. [常见问题FAQ](#chapter-9-常见问题faq)
10. [故障排查](#chapter-10-故障排查)

---

## Chapter 1: v3 Core Concepts

### 1.1 What's New in v3?

AgentOS v3 introduces **OS-Level Capability Governance** - a fundamental architectural shift that treats AI agents as processes with **capability-based permissions**, similar to how modern operating systems manage hardware access.

**Core Philosophy**: **Decisions are NOT Actions**

In v3, we enforce a clear separation:
- **Decision Capabilities**: Planning, evaluation, judgment (side-effect free)
- **Action Capabilities**: Execution, state modification (governed)
- **State Capabilities**: Memory read/write
- **Governance Capabilities**: Permission checks, risk scoring
- **Evidence Capabilities**: Audit, replay, export

### 1.2 Five Domains Architecture

AgentOS v3 organizes all system capabilities into 5 domains:

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentOS v3 Architecture                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  STATE   │  │ DECISION │  │  ACTION  │  │GOVERNANCE│   │
│  │  Domain  │  │  Domain  │  │  Domain  │  │  Domain  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       │              │              │              │        │
│       └──────────────┴──────────────┴──────────────┘        │
│                          │                                   │
│                    ┌──────────┐                             │
│                    │ EVIDENCE │                             │
│                    │  Domain  │                             │
│                    └──────────┘                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### Domain 1: STATE
Manages persistent memory and context.

**Capabilities**:
- `state.memory.read` - Read from memory scopes (global/project/task/agent)
- `state.memory.write` - Write to memory (requires WRITE permission)
- `state.context.snapshot` - Create immutable context snapshot
- `state.context.verify` - Verify context integrity

**Use Cases**:
- Store user preferences: "Call me Pangge"
- Save project settings: tech stack, coding style
- Retrieve agent knowledge base

#### Domain 2: DECISION
Generates plans and evaluates options (NO execution).

**Capabilities**:
- `decision.plan.create` - Create execution plan (DRAFT state)
- `decision.plan.freeze` - Freeze plan (immutable, hash verified)
- `decision.option.evaluate` - Evaluate multiple options with scoring
- `decision.judge.select` - Select best option with rationale
- `decision.record.rationale` - Record decision reasoning

**Use Cases**:
- Create refactoring plan
- Evaluate API design alternatives
- Choose deployment strategy

**CRITICAL**: Decision capabilities CANNOT trigger Action capabilities. This is enforced by PathValidator.

#### Domain 3: ACTION
Executes operations with side effects.

**Capabilities**:
- `action.execute.local` - Execute local commands
- `action.execute.remote` - Execute remote operations
- `action.state.modify` - Modify system state
- `action.file.write` - Write to files
- `action.network.call` - Make network requests

**Use Cases**:
- Run tests
- Deploy code
- Write files
- Call external APIs

**CRITICAL**: Every Action MUST:
1. Check Governance permission first
2. Record Evidence after execution
3. Provide Rollback plan

#### Domain 4: GOVERNANCE
Enforces policies and calculates risk.

**Capabilities**:
- `governance.check.permission` - Check if agent has permission
- `governance.risk.calculate` - Calculate risk score (0-100)
- `governance.policy.evaluate` - Evaluate against policies
- `governance.override.request` - Request human override
- `governance.override.approve` - Approve override (ADMIN only)

**Use Cases**:
- Block unauthorized actions
- Alert on high-risk operations
- Enforce budget constraints
- Require human approval for destructive actions

#### Domain 5: EVIDENCE
Immutable audit trail and replay.

**Capabilities**:
- `evidence.collect` - Record operation evidence (auto-invoked)
- `evidence.link` - Build evidence chains (decision→action→state)
- `evidence.replay` - Replay operations (read-only or validate)
- `evidence.export` - Export audit reports (PDF/JSON/CSV/HTML)
- `evidence.verify` - Verify evidence integrity (SHA256)

**Use Cases**:
- Audit compliance (SOX, GDPR, HIPAA)
- Debug failures with time-travel
- Generate legal discovery reports
- Verify system integrity

### 1.3 Capability Identifier Convention

All capabilities follow the pattern: `<domain>.<component>.<operation>`

**Examples**:
```
state.memory.read           # Read memory
state.memory.write          # Write memory
decision.plan.create        # Create plan
decision.plan.freeze        # Freeze plan
action.execute.local        # Execute local command
governance.check.permission # Check permission
evidence.collect            # Collect evidence
```

**Why Structured IDs?**
- **Discoverability**: Easy to find related capabilities
- **Authorization**: Grant/deny at domain/component level
- **Audit**: Track usage by domain
- **Documentation**: Self-documenting API surface

### 1.4 Permission Levels

AgentOS v3 uses a hierarchical permission model:

```
NONE < READ < PROPOSE < WRITE < ADMIN
```

**Permission Inheritance**: Higher levels include all lower permissions.

| Level | Allowed Operations |
|-------|-------------------|
| **NONE** | No access (default for unknown agents) |
| **READ** | Query capabilities, read memory, view evidence |
| **PROPOSE** | READ + propose changes (requires approval) |
| **WRITE** | PROPOSE + execute actions, modify state |
| **ADMIN** | WRITE + approve proposals, override policies |

**Example Permission Assignment**:
```python
# Chat agents propose memory changes (anti-hallucination)
agent_capability_profile = {
    "agent_id": "chat_agent",
    "capabilities": {
        "state.memory.read": PermissionLevel.READ,
        "state.memory.write": PermissionLevel.PROPOSE,  # Not WRITE!
        "decision.plan.create": PermissionLevel.WRITE,
        "action.execute.local": PermissionLevel.NONE,  # Chat cannot execute
    }
}
```

### 1.5 Golden Path vs Forbidden Paths

**Golden Path** (Allowed):
```
State → Decision → Governance → Action → State → Evidence
```

**Forbidden Paths** (Blocked by PathValidator):
1. ❌ **Decision → Action**: Decisions cannot directly trigger actions
2. ❌ **Action → State**: Actions cannot bypass governance to modify state
3. ❌ **Evidence → Any**: Evidence is write-only (cannot call out)

**Why Enforce This?**
- **Safety**: Prevents accidental execution during planning
- **Auditability**: Every action has a decision trail
- **Governance**: Forces permission checks before execution

---

## Chapter 2: Golden Path详解

### 2.1 What is the Golden Path?

The **Golden Path** is the ideal execution flow that ensures:
- ✅ Every action has a frozen plan
- ✅ Every action checks governance
- ✅ Every action records evidence
- ✅ Every state change is traceable

**9-Step Golden Path**:

```
1. State.read        → Read current context/memory
2. Decision.create   → Create execution plan (DRAFT)
3. Decision.freeze   → Freeze plan (immutable + hash)
4. Governance.check  → Check if agent has permission
5. Governance.risk   → Calculate risk score
6. Action.execute    → Execute plan (if approved)
7. State.write       → Update state (if needed)
8. Evidence.collect  → Record evidence (automatic)
9. Evidence.link     → Link evidence chain
```

### 2.2 Step-by-Step Example

**Scenario**: User asks "Refactor all error handling to use new ErrorWrapper class"

#### Step 1: State.read
```python
# Read current codebase context
memory = state_service.read_memory(
    scope="project",
    key="codebase_structure"
)
# Returns: {"error_handlers": 42, "files": ["src/api.py", ...]}
```

#### Step 2: Decision.create
```python
# Create refactoring plan
plan = decision_service.create_plan(
    task_id="task-refactor-123",
    steps=[
        {
            "step_id": "step-1",
            "action": "search_error_handlers",
            "params": {"pattern": "try-except"},
            "estimated_time_ms": 5000,
        },
        {
            "step_id": "step-2",
            "action": "generate_errorwrapper_code",
            "params": {"template": "error_wrapper.tmpl"},
            "estimated_time_ms": 10000,
        },
        {
            "step_id": "step-3",
            "action": "replace_error_handlers",
            "params": {"dry_run": True},
            "estimated_time_ms": 30000,
        },
        {
            "step_id": "step-4",
            "action": "run_tests",
            "params": {"test_suite": "unit"},
            "estimated_time_ms": 60000,
        },
    ],
    alternatives=[
        {
            "alternative_id": "alt-1",
            "description": "Manual refactoring file by file",
            "rejected_reason": "Too slow (estimated 2 hours)",
        }
    ],
    rationale="Automated refactoring is faster and more consistent",
    created_by="chat_agent",
)
# Plan is now in DRAFT state
```

#### Step 3: Decision.freeze
```python
# Freeze plan (make immutable)
frozen_plan = decision_service.freeze_plan(plan.plan_id)
# Generates SHA256 hash: "7f3a8b9c2d1e..."
# Status: DRAFT → FROZEN
# Any modification attempt now raises ImmutablePlanError
```

#### Step 4: Governance.check
```python
# Check if agent has permission to execute
permission_result = governance_service.check_permission(
    agent_id="chat_agent",
    capability_id="action.execute.local",
    context={
        "task_id": "task-refactor-123",
        "estimated_cost": 0.50,  # $0.50
        "estimated_time_ms": 105000,  # 105 seconds
    },
)
# Returns: {
#     "is_granted": False,  # Chat agent cannot execute!
#     "permission_level": "propose",
#     "reason": "Agent lacks WRITE permission for action.execute.local"
# }
```

**What happens?** Plan is sent to human for approval via Review Queue.

#### Step 5: Governance.risk
```python
# Calculate risk score
risk_score = governance_service.calculate_risk_score(
    agent_id="execution_agent",  # After human approval
    capability_id="action.execute.local",
    context={
        "task_id": "task-refactor-123",
        "plan_id": frozen_plan.plan_id,
        "files_affected": 42,
        "estimated_cost": 0.50,
    },
)
# Returns: {
#     "risk_score": 65,  # Medium-high risk
#     "risk_tier": "T2",
#     "factors": {
#         "files_affected": 42,  # High impact
#         "has_tests": True,     # Risk reduction
#         "dry_run_first": True, # Risk reduction
#     }
# }
```

#### Step 6: Action.execute
```python
# Execute plan (now with permission)
result = action_service.execute(
    plan_id=frozen_plan.plan_id,
    agent_id="execution_agent",
    dry_run=False,
)
# Returns: {
#     "execution_id": "exec-456",
#     "status": "success",
#     "steps_completed": 4,
#     "steps_failed": 0,
#     "output": {
#         "files_modified": 42,
#         "tests_passed": 156,
#         "tests_failed": 0,
#     }
# }
```

#### Step 7: State.write
```python
# Update project state
state_service.write_memory(
    scope="project",
    key="refactoring_history",
    value={
        "task_id": "task-refactor-123",
        "completed_at": utc_now_ms(),
        "files_changed": 42,
        "pattern": "ErrorWrapper",
    },
    written_by="execution_agent",
)
```

#### Step 8: Evidence.collect (Automatic)
```python
# Evidence is automatically collected during execution
# No manual call needed - Evidence.collect is invoked by ActionExecutor
evidence_id = "evidence-789"
# Evidence includes:
# - Operation: action.execute.local
# - Params: {plan_id, agent_id, ...}
# - Result: {files_modified: 42, tests_passed: 156}
# - SHA256 hash: "a1b2c3d4..."
# - Immutable: cannot be modified or deleted
```

#### Step 9: Evidence.link
```python
# Link evidence chain
chain_id = evidence_service.link(
    decision_id=frozen_plan.plan_id,
    action_id="exec-456",
    memory_id="mem-refactor-history",
)
# Creates evidence chain: decision → action → state
# Chain can be queried for audit or replay
```

### 2.3 Why 9 Steps?

Each step serves a specific purpose:

| Step | Purpose | Can Skip? |
|------|---------|-----------|
| 1. State.read | Understand current context | ⚠️ Optional (if context known) |
| 2. Decision.create | Define execution plan | ❌ Required |
| 3. Decision.freeze | Make plan immutable | ❌ Required |
| 4. Governance.check | Verify permission | ❌ Required |
| 5. Governance.risk | Calculate risk | ⚠️ Optional (but recommended) |
| 6. Action.execute | Do the work | ❌ Required |
| 7. State.write | Update state | ⚠️ Optional (if no state change) |
| 8. Evidence.collect | Record evidence | ❌ Required (automatic) |
| 9. Evidence.link | Build audit trail | ✅ Optional (but recommended) |

**Minimum Required Flow**: Steps 2, 3, 4, 6, 8 (5 steps)

### 2.4 Golden Path Performance

**Target**: Complete flow in < 100ms

**Measured Performance** (from tests):
- State.read: ~5ms
- Decision.create: ~10ms
- Decision.freeze: ~5ms
- Governance.check: ~2ms
- Governance.risk: ~8ms
- Action.execute: ~20-50ms (depends on action)
- State.write: ~5ms
- Evidence.collect: ~3ms
- Evidence.link: ~5ms

**Total**: ~63-93ms (within target)

### 2.5 Common Golden Path Variations

#### Variation 1: Read-Only Query
```
State.read → Decision.option.evaluate → Evidence.collect
```
**Use case**: User asks "Which API should I use?"

#### Variation 2: State Update (No Action)
```
State.read → Decision.judge.select → Governance.check → State.write → Evidence
```
**Use case**: User sets preference "Use TypeScript"

#### Variation 3: Multi-Step Action
```
State.read → Decision.create → Decision.freeze →
  Governance.check → Action.execute (step 1) → Evidence.collect →
  Governance.check → Action.execute (step 2) → Evidence.collect →
  ... → State.write → Evidence.link
```
**Use case**: Multi-file refactoring

---

## Chapter 3: Agent→Capability Model

### 3.1 Agent Definition in v3

In v3, agents are defined by their **Capability Profile** - a declarative list of what they can do.

**Old way (v2.0)**: Agents had implicit permissions based on role.

**New way (v3.0)**: Agents have explicit capability grants with permission levels.

**Example Agent Definition**:
```python
{
    "agent_id": "chat_agent_001",
    "agent_type": "chat",
    "name": "ChatGPT Integration Agent",
    "description": "Handles user conversations and proposes actions",
    "capability_profile": {
        # State domain
        "state.memory.read": {
            "permission_level": "read",
            "scopes": ["global", "project", "task"],
        },
        "state.memory.write": {
            "permission_level": "propose",  # Not write!
            "scopes": ["global", "project"],
            "requires_approval": True,
        },

        # Decision domain
        "decision.plan.create": {
            "permission_level": "write",
            "max_steps": 10,
        },
        "decision.plan.freeze": {
            "permission_level": "write",
        },
        "decision.option.evaluate": {
            "permission_level": "write",
        },
        "decision.judge.select": {
            "permission_level": "write",
        },

        # Action domain - NONE
        "action.*": {
            "permission_level": "none",  # Chat cannot execute!
        },

        # Governance domain
        "governance.check.permission": {
            "permission_level": "read",  # Can query, cannot modify
        },

        # Evidence domain
        "evidence.collect": {
            "permission_level": "write",  # Can record evidence
        },
        "evidence.replay": {
            "permission_level": "none",  # Cannot replay
        },
    },
    "metadata": {
        "trust_tier": "T3",  # Low trust (AI agent)
        "max_budget_per_task": 1.00,  # $1
        "created_by": "admin",
    }
}
```

### 3.2 Permission Levels Explained

**NONE**: Agent cannot use this capability at all.
```python
"action.execute.local": {
    "permission_level": "none"
}
# Any attempt raises: PermissionDeniedError
```

**READ**: Agent can query/read, but not modify.
```python
"state.memory.read": {
    "permission_level": "read",
    "scopes": ["global", "project"]
}
# Can: read_memory(scope="global")
# Cannot: write_memory(scope="global")
```

**PROPOSE**: Agent can suggest changes, requires human approval.
```python
"state.memory.write": {
    "permission_level": "propose",
    "requires_approval": True
}
# Creates proposal → Human approves → Write executes
```

**WRITE**: Agent can modify directly (no approval needed).
```python
"decision.plan.create": {
    "permission_level": "write"
}
# Can create plans immediately
```

**ADMIN**: Agent can approve proposals and override policies.
```python
"governance.override.approve": {
    "permission_level": "admin"
}
# Only human admins or system agents should have this
```

### 3.3 Creating Agent Profiles

#### Template 1: Chat Agent (Conservative)
```python
chat_agent_profile = {
    "state.memory.read": "read",
    "state.memory.write": "propose",  # Anti-hallucination
    "decision.*": "write",            # Can plan
    "action.*": "none",               # Cannot execute
    "governance.check.*": "read",
    "evidence.collect": "write",
}
```

#### Template 2: Execution Agent (Trusted)
```python
execution_agent_profile = {
    "state.memory.*": "write",
    "decision.*": "write",
    "action.execute.local": "write",   # Can execute!
    "action.execute.remote": "propose", # Requires approval
    "governance.*": "read",
    "evidence.*": "write",
}
```

#### Template 3: Admin Agent (Full Access)
```python
admin_agent_profile = {
    "state.*": "admin",
    "decision.*": "admin",
    "action.*": "admin",
    "governance.*": "admin",
    "evidence.*": "admin",
}
```

#### Template 4: Read-Only Agent (Audit)
```python
readonly_agent_profile = {
    "state.memory.read": "read",
    "decision.*": "read",
    "action.*": "none",
    "governance.*": "read",
    "evidence.*": "read",  # Can view all evidence
}
```

### 3.4 Registering Agents

**CLI**:
```bash
# Create agent from JSON file
agentos agent create --from-file agent_profile.json

# Create agent inline
agentos agent create \
  --id chat_agent_001 \
  --type chat \
  --capability state.memory.read=read \
  --capability state.memory.write=propose \
  --capability decision.*=write \
  --capability action.*=none
```

**Python API**:
```python
from agentos.core.agent import AgentRegistry

registry = AgentRegistry()

agent = registry.register_agent(
    agent_id="chat_agent_001",
    agent_type="chat",
    capability_profile={
        "state.memory.read": {"permission_level": "read"},
        "state.memory.write": {"permission_level": "propose"},
        # ...
    }
)
```

**REST API**:
```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "chat_agent_001",
    "agent_type": "chat",
    "capability_profile": {
      "state.memory.read": {"permission_level": "read"},
      "state.memory.write": {"permission_level": "propose"}
    }
  }'
```

### 3.5 Querying Agent Capabilities

**Check if agent has permission**:
```python
from agentos.core.governance import GovernanceEngine

governance = GovernanceEngine()

result = governance.check_permission(
    agent_id="chat_agent_001",
    capability_id="action.execute.local",
    context={"task_id": "task-123"}
)

if result.is_granted:
    # Execute action
    pass
else:
    print(f"Permission denied: {result.reason}")
    # Send to Review Queue for human approval
```

**List all agent capabilities**:
```python
from agentos.core.agent import AgentRegistry

registry = AgentRegistry()

profile = registry.get_agent_profile("chat_agent_001")

for capability_id, config in profile.capability_profile.items():
    print(f"{capability_id}: {config['permission_level']}")

# Output:
# state.memory.read: read
# state.memory.write: propose
# decision.plan.create: write
# action.execute.local: none
```

### 3.6 Updating Agent Capabilities

**Add capability**:
```bash
agentos agent grant \
  --agent-id chat_agent_001 \
  --capability action.execute.local \
  --permission write
```

**Revoke capability**:
```bash
agentos agent revoke \
  --agent-id chat_agent_001 \
  --capability action.execute.local
```

**Change permission level**:
```bash
agentos agent update \
  --agent-id chat_agent_001 \
  --capability state.memory.write \
  --permission write  # Upgrade from propose to write
```

---

## Chapter 4: Decision Workflow使用指南

### 4.1 Decision Capabilities Overview

AgentOS v3 provides 5 decision capabilities:

1. **decision.plan.create** - Create execution plan
2. **decision.plan.freeze** - Freeze plan (make immutable)
3. **decision.option.evaluate** - Evaluate multiple options
4. **decision.judge.select** - Select best option
5. **decision.record.rationale** - Record decision reasoning

**Key Principle**: Decision capabilities CANNOT trigger actions. They only produce plans/evaluations.

### 4.2 Creating Plans

**Basic Plan**:
```python
from agentos.core.capability.domains.decision import PlanService

plan_service = PlanService()

plan = plan_service.create_plan(
    task_id="task-123",
    steps=[
        {
            "step_id": "step-1",
            "action": "search_files",
            "params": {"pattern": "*.py"},
            "estimated_time_ms": 5000,
        },
        {
            "step_id": "step-2",
            "action": "run_tests",
            "params": {"suite": "unit"},
            "estimated_time_ms": 30000,
        },
    ],
    alternatives=[
        {
            "alternative_id": "alt-1",
            "description": "Manual testing",
            "rejected_reason": "Too slow",
        }
    ],
    rationale="Automated testing is faster and more reliable",
    created_by="chat_agent",
)

print(f"Plan created: {plan.plan_id}")
print(f"Status: {plan.status}")  # Output: draft
```

**Plan with Dependencies**:
```python
plan = plan_service.create_plan(
    task_id="task-deploy",
    steps=[
        {
            "step_id": "step-1",
            "action": "run_tests",
            "params": {},
            "depends_on": [],  # No dependencies
        },
        {
            "step_id": "step-2",
            "action": "build_docker",
            "params": {},
            "depends_on": ["step-1"],  # Depends on tests
        },
        {
            "step_id": "step-3",
            "action": "push_to_registry",
            "params": {},
            "depends_on": ["step-2"],  # Depends on build
        },
        {
            "step_id": "step-4",
            "action": "deploy_to_prod",
            "params": {},
            "depends_on": ["step-3"],  # Depends on push
        },
    ],
    alternatives=[],
    rationale="Standard deployment pipeline",
    created_by="ci_agent",
)
```

### 4.3 Freezing Plans

**Why Freeze?**
- Makes plan immutable (cannot be modified)
- Generates SHA256 hash for integrity verification
- Required before execution
- Prevents "plan drift" during execution

**Freeze Plan**:
```python
frozen_plan = plan_service.freeze_plan(plan.plan_id)

print(f"Status: {frozen_plan.status}")  # Output: frozen
print(f"Hash: {frozen_plan.plan_hash}")  # Output: 7f3a8b9c...
print(f"Frozen at: {frozen_plan.frozen_at_ms}")

# Verify hash integrity
is_valid = frozen_plan.verify_hash(frozen_plan.plan_hash)
print(f"Hash valid: {is_valid}")  # Output: True
```

**Attempt to modify frozen plan (ERROR)**:
```python
try:
    plan_service.update_plan(
        plan_id=frozen_plan.plan_id,
        steps=[{"step_id": "step-new", "action": "new_action"}]
    )
except ImmutablePlanError as e:
    print(f"Error: {e}")
    # Output: Cannot modify frozen plan: plan-123
```

### 4.4 Evaluating Options

**Evaluate Multiple Options**:
```python
from agentos.core.capability.domains.decision import OptionEvaluator

evaluator = OptionEvaluator()

# Define options
options = [
    {
        "option_id": "opt-1",
        "description": "Use REST API",
        "estimated_cost": 0.10,
        "estimated_time_ms": 5000,
        "risks": ["API rate limiting", "Network failures"],
        "benefits": ["Standard approach", "Well documented"],
    },
    {
        "option_id": "opt-2",
        "description": "Use GraphQL",
        "estimated_cost": 0.15,
        "estimated_time_ms": 8000,
        "risks": ["Complex queries", "Learning curve"],
        "benefits": ["Flexible queries", "Single endpoint"],
    },
    {
        "option_id": "opt-3",
        "description": "Use gRPC",
        "estimated_cost": 0.20,
        "estimated_time_ms": 10000,
        "risks": ["Browser support limited", "Steeper learning curve"],
        "benefits": ["High performance", "Type safety"],
    },
]

# Evaluate options
result = evaluator.evaluate_options(
    decision_context_id="ctx-api-choice",
    options=options,
    evaluated_by="decision_agent",
)

# Print ranked options
for i, option_id in enumerate(result.ranked_options):
    option = next(o for o in options if o["option_id"] == option_id)
    score = result.scores[option_id]
    print(f"{i+1}. {option['description']}: {score:.2f} points")

# Output:
# 1. Use REST API: 85.3 points
# 2. Use GraphQL: 72.1 points
# 3. Use gRPC: 65.8 points

print(f"Recommendation: {result.recommendation}")
print(f"Confidence: {result.confidence:.1f}%")
```

### 4.5 Selecting Best Option

**Select and Record Decision**:
```python
from agentos.core.capability.domains.decision import DecisionJudge

judge = DecisionJudge()

decision = judge.select_option(
    evaluation_id=result.evaluation_id,
    selected_option_id="opt-1",  # Use REST API
    rationale="""
    Selected REST API for the following reasons:
    1. Lowest cost ($0.10 vs $0.15/$0.20)
    2. Fastest execution (5s vs 8s/10s)
    3. Team has most experience with REST
    4. Best documentation and community support
    5. Risks are manageable with retry logic
    """,
    decided_by="decision_agent",
    confidence_level="high",
    alternatives_rejected=[
        {
            "option_id": "opt-2",
            "reason": "GraphQL adds complexity without significant benefit for our use case"
        },
        {
            "option_id": "opt-3",
            "reason": "gRPC is overkill for our performance requirements"
        },
    ],
)

print(f"Decision ID: {decision.decision_id}")
print(f"Evidence ID: {decision.evidence_id}")  # Auto-generated
```

### 4.6 Recording Additional Rationale

**Add Context Later**:
```python
judge.record_rationale(
    decision_id=decision.decision_id,
    rationale="""
    Update (2 weeks later):
    REST API choice was validated. Team successfully delivered
    the feature in 3 days. No rate limiting issues encountered.
    Performance is acceptable (avg 150ms response time).
    """,
    recorded_by="tech_lead",
)
```

---

## Chapter 5: Action执行和Rollback

### 5.1 Action Capabilities Overview

Action capabilities execute operations with side effects:

1. **action.execute.local** - Execute local commands
2. **action.execute.remote** - Execute remote operations
3. **action.state.modify** - Modify system state
4. **action.file.write** - Write to files
5. **action.network.call** - Make network requests

**Critical Requirements**:
- ✅ Must check Governance permission BEFORE execution
- ✅ Must record Evidence AFTER execution
- ✅ Must provide Rollback plan
- ✅ Cannot be called by Decision capabilities (PathValidator blocks)

### 5.2 Executing Actions Safely

**Safe Execution Pattern**:
```python
from agentos.core.capability.domains.action import ActionExecutor
from agentos.core.capability.domains.governance import GovernanceEngine
from agentos.core.capability.domains.evidence import EvidenceCollector

# 1. Check permission FIRST
governance = GovernanceEngine()
permission = governance.check_permission(
    agent_id="execution_agent",
    capability_id="action.execute.local",
    context={"task_id": "task-123", "command": "rm -rf /tmp/cache"}
)

if not permission.is_granted:
    raise PermissionError(f"Action denied: {permission.reason}")

# 2. Calculate risk
risk_score = governance.calculate_risk_score(
    agent_id="execution_agent",
    capability_id="action.execute.local",
    context={"command": "rm -rf /tmp/cache"}
)

if risk_score > 80:
    # High risk - require human approval
    print(f"High risk detected ({risk_score}/100). Requesting approval...")
    # Send to Review Queue
    return

# 3. Execute action
executor = ActionExecutor()
result = executor.execute(
    capability_id="action.execute.local",
    params={"command": "rm -rf /tmp/cache"},
    agent_id="execution_agent",
    context={"task_id": "task-123"},
)

# 4. Evidence is automatically collected
print(f"Evidence ID: {result.evidence_id}")

# 5. Handle result
if result.status == "success":
    print(f"Action completed: {result.output}")
else:
    print(f"Action failed: {result.error}")
    # Trigger rollback if needed
```

### 5.3 Action with Rollback Plan

**Define Rollback**:
```python
result = executor.execute(
    capability_id="action.file.write",
    params={
        "file_path": "/etc/config.json",
        "content": '{"setting": "new_value"}',
    },
    agent_id="execution_agent",
    context={"task_id": "task-config"},
    rollback_plan={
        "rollback_id": "rollback-123",
        "steps": [
            {
                "action": "file.restore",
                "params": {
                    "file_path": "/etc/config.json",
                    "backup_path": "/etc/config.json.backup",
                },
            }
        ],
    },
)

# If action fails or needs rollback
if result.needs_rollback:
    rollback_result = executor.rollback(
        execution_id=result.execution_id,
        rollback_plan_id="rollback-123",
    )
    print(f"Rollback status: {rollback_result.status}")
```

### 5.4 Side Effects Tracking

**Track File Changes**:
```python
from agentos.core.capability.domains.action import SideEffectsTracker

tracker = SideEffectsTracker()

# Before action
tracker.snapshot_state(
    execution_id="exec-456",
    targets=["file:/etc/config.json", "file:/var/log/app.log"]
)

# Execute action
result = executor.execute(...)

# After action
side_effects = tracker.detect_side_effects(execution_id="exec-456")

for effect in side_effects:
    print(f"Modified: {effect.target}")
    print(f"  Before hash: {effect.before_hash}")
    print(f"  After hash: {effect.after_hash}")
    print(f"  Change type: {effect.change_type}")  # modified/created/deleted

# Output:
# Modified: file:/etc/config.json
#   Before hash: a1b2c3d4...
#   After hash: e5f6g7h8...
#   Change type: modified
```

### 5.5 Rollback Engine

**Automatic Rollback on Failure**:
```python
from agentos.core.capability.domains.action import RollbackEngine

rollback_engine = RollbackEngine()

# Execute multi-step action
results = []
for step in plan.steps:
    result = executor.execute(
        capability_id=step["capability_id"],
        params=step["params"],
        agent_id="execution_agent",
        context={"plan_id": plan.plan_id},
    )
    results.append(result)

    if result.status != "success":
        # Rollback all previous steps
        print(f"Step {step['step_id']} failed. Rolling back...")

        rollback_result = rollback_engine.rollback_execution(
            execution_id=result.execution_id,
            plan_id=plan.plan_id,
        )

        print(f"Rollback completed: {rollback_result.steps_rolled_back} steps")
        break
```

### 5.6 Dry Run Mode

**Test Actions Without Side Effects**:
```python
result = executor.execute(
    capability_id="action.execute.local",
    params={"command": "rm -rf /var/data/*"},
    agent_id="execution_agent",
    context={"task_id": "task-cleanup"},
    dry_run=True,  # Simulate, don't execute
)

print(f"Dry run result:")
print(f"  Would delete: {result.simulation.files_affected}")
print(f"  Estimated time: {result.simulation.estimated_time_ms}ms")
print(f"  Risk score: {result.simulation.risk_score}")

# User reviews simulation
if user_approves:
    # Execute for real
    real_result = executor.execute(
        capability_id="action.execute.local",
        params={"command": "rm -rf /var/data/*"},
        agent_id="execution_agent",
        context={"task_id": "task-cleanup"},
        dry_run=False,  # Real execution
    )
```

---

## Chapter 6: Evidence和Replay

### 6.1 Evidence System Overview

The Evidence domain provides immutable audit trails for all operations.

**Key Features**:
- ✅ Automatic evidence collection for all actions
- ✅ SHA256 integrity verification
- ✅ Immutable (cannot be modified or deleted)
- ✅ Evidence chains (decision→action→state)
- ✅ Replay capabilities (read-only and validate modes)
- ✅ Export for compliance (PDF/JSON/CSV/HTML)

### 6.2 Evidence Collection (Automatic)

Evidence is **automatically collected** for all capability invocations. You don't need to call `evidence.collect` manually.

**How It Works**:
```python
# When you execute an action
result = executor.execute(
    capability_id="action.execute.local",
    params={"command": "test"},
    agent_id="execution_agent",
)

# Evidence is automatically collected:
# - operation_type: action
# - operation_id: exec-123
# - capability_id: action.execute.local
# - params: {"command": "test"}
# - result: {status, output, ...}
# - SHA256 hash: a1b2c3d4...
# - timestamp_ms: 1738454400000

# Evidence ID is included in result
print(f"Evidence ID: {result.evidence_id}")
```

### 6.3 Querying Evidence

**Query by Agent**:
```python
from agentos.core.capability.domains.evidence import EvidenceCollector

collector = EvidenceCollector()

# Get all evidence for an agent
evidence_list = collector.query_by_agent(
    agent_id="execution_agent",
    limit=100,
    offset=0,
)

for evidence in evidence_list:
    print(f"{evidence.timestamp_ms}: {evidence.capability_id}")
    print(f"  Operation: {evidence.operation_id}")
    print(f"  Status: {evidence.result['status']}")
```

**Query by Capability**:
```python
# Get all action executions
action_evidence = collector.query_by_capability(
    capability_id="action.execute.local",
    start_time_ms=utc_now_ms() - (24 * 3600 * 1000),  # Last 24 hours
    end_time_ms=utc_now_ms(),
)

print(f"Actions executed in last 24h: {len(action_evidence)}")
```

**Query by Task**:
```python
# Get all evidence for a specific task
task_evidence = collector.query_by_context(
    context_filter={"task_id": "task-123"},
)

for evidence in task_evidence:
    print(f"{evidence.operation_type}: {evidence.capability_id}")
```

### 6.4 Evidence Chains

**Build Evidence Chain**:
```python
from agentos.core.capability.domains.evidence import EvidenceLinkGraph

link_graph = EvidenceLinkGraph()

# Link decision → action → state
chain_id = link_graph.link(
    decision_id="plan-123",
    action_id="exec-456",
    memory_id="mem-789",
)

print(f"Evidence chain created: {chain_id}")
```

**Query Evidence Chain**:
```python
# Get complete evidence chain
chain = link_graph.get_chain(chain_id)

print(f"Chain: {chain.chain_id}")
print(f"Links: {len(chain.links)}")

for link in chain.links:
    print(f"  {link.from_id} → {link.to_id} ({link.relationship})")

# Output:
#   plan-123 → exec-456 (caused_by)
#   exec-456 → mem-789 (resulted_in)
```

**Multi-Hop Query**:
```python
# Find all evidence reachable from decision
reachable = link_graph.query_chain(
    start_evidence_id="plan-123",
    max_depth=10,
    relationship_types=["caused_by", "resulted_in"],
)

print(f"Found {len(reachable)} related evidence items")
```

### 6.5 Evidence Replay

**Read-Only Replay** (Safe):
```python
from agentos.core.capability.domains.evidence import ReplayEngine, ReplayMode

replay_engine = ReplayEngine()

# Replay in read-only mode (no side effects)
replay_result = replay_engine.replay(
    evidence_id="evidence-456",
    mode=ReplayMode.READ_ONLY,
    replayed_by="debug_agent",
)

print(f"Replay status: {replay_result.status}")
print(f"Original result: {replay_result.original_result}")
print(f"Replayed result: {replay_result.replayed_result}")
print(f"Results match: {replay_result.results_match}")
```

**Validate Mode** (Re-execute):
```python
# Validate mode re-executes and compares results
# Requires ADMIN permission
replay_result = replay_engine.replay(
    evidence_id="evidence-456",
    mode=ReplayMode.VALIDATE,
    replayed_by="admin_agent",
)

if not replay_result.results_match:
    print("WARNING: Replay result differs from original!")
    print(f"Diff: {replay_result.diff}")
    # Output:
    # Diff: {
    #   "added": {"new_field": "value"},
    #   "removed": {"old_field": "value"},
    #   "changed": {"status": {"old": "success", "new": "partial"}}
    # }
```

### 6.6 Evidence Export

**Export to JSON**:
```python
from agentos.core.capability.domains.evidence import ExportEngine, ExportQuery, ExportFormat

export_engine = ExportEngine()

# Export all evidence for a task
export_id = export_engine.export(
    query=ExportQuery(
        agent_id="execution_agent",
        start_time_ms=utc_now_ms() - (7 * 24 * 3600 * 1000),  # Last 7 days
        end_time_ms=utc_now_ms(),
    ),
    format=ExportFormat.JSON,
    exported_by="admin_agent",
)

# Get export package
package = export_engine.get_export(export_id)
print(f"Export file: {package.file_path}")
print(f"File size: {package.file_size_bytes} bytes")
print(f"File hash: {package.file_hash}")
```

**Export to PDF Audit Report**:
```python
# Generate PDF audit report
export_id = export_engine.export(
    query=ExportQuery(
        capability_id="action.execute.local",
        start_time_ms=utc_now_ms() - (30 * 24 * 3600 * 1000),  # Last 30 days
        end_time_ms=utc_now_ms(),
    ),
    format=ExportFormat.PDF,
    exported_by="compliance_officer",
)

# Download report
package = export_engine.get_export(export_id)
print(f"Audit report: {package.file_path}")
# PDF includes:
# - Evidence summary
# - Timeline visualization
# - Risk analysis
# - Compliance status
```

**Export to CSV** (for Excel analysis):
```python
export_id = export_engine.export(
    query=ExportQuery(agent_id="execution_agent"),
    format=ExportFormat.CSV,
    exported_by="analyst",
)

# CSV columns:
# evidence_id, timestamp, agent_id, capability_id, operation_type, status, ...
```

### 6.7 Evidence Integrity Verification

**Verify Evidence Hash**:
```python
# Get evidence
evidence = collector.get_evidence("evidence-456")

# Compute hash
computed_hash = evidence.compute_hash()

# Verify against stored hash
is_valid = evidence.verify_integrity()

if not is_valid:
    print("WARNING: Evidence integrity compromised!")
    print(f"Stored hash: {evidence.integrity.content_hash}")
    print(f"Computed hash: {computed_hash}")
else:
    print("Evidence integrity verified ✓")
```

---

## Chapter 7: Governance和Risk管理

### 7.1 Governance Engine Overview

The Governance domain enforces policies and manages risk across all operations.

**Core Responsibilities**:
- ✅ Permission checking (agent authorization)
- ✅ Risk calculation (operation risk scoring)
- ✅ Policy evaluation (rule-based decisions)
- ✅ Override management (human approvals)
- ✅ Budget enforcement (cost controls)

### 7.2 Policy Registry

**Register Policy**:
```python
from agentos.core.capability.domains.governance import PolicyRegistry

policy_registry = PolicyRegistry()

policy_registry.register_policy({
    "policy_id": "prod_action_policy",
    "name": "Production Action Policy",
    "description": "Strict controls for production actions",
    "rules": [
        {
            "rule_id": "rule-1",
            "capability_pattern": "action.execute.*",
            "agent_pattern": "chat_*",
            "permission_level": "none",  # Chat agents cannot execute
            "reason": "Chat agents lack execution privileges",
        },
        {
            "rule_id": "rule-2",
            "capability_pattern": "action.execute.local",
            "agent_pattern": "execution_*",
            "permission_level": "write",
            "constraints": {
                "max_cost_per_action": 1.00,
                "max_time_ms": 300000,  # 5 minutes
                "requires_approval_if_risk_above": 70,
            },
        },
        {
            "rule_id": "rule-3",
            "capability_pattern": "action.execute.remote",
            "agent_pattern": "*",
            "permission_level": "propose",  # Always require approval
            "reason": "Remote execution is high risk",
        },
    ],
    "metadata": {
        "environment": "production",
        "created_by": "admin",
        "version": "1.0",
    },
})
```

**Query Policies**:
```python
# Get all policies
policies = policy_registry.list_policies()

for policy in policies:
    print(f"{policy.name}: {len(policy.rules)} rules")

# Get specific policy
policy = policy_registry.get_policy("prod_action_policy")
print(f"Policy: {policy.name}")
print(f"Rules: {len(policy.rules)}")
```

### 7.3 Permission Checking

**Check Permission**:
```python
from agentos.core.capability.domains.governance import GovernanceEngine

governance = GovernanceEngine()

# Check if agent can execute action
result = governance.check_permission(
    agent_id="chat_agent",
    capability_id="action.execute.local",
    context={
        "task_id": "task-123",
        "estimated_cost": 0.50,
    },
)

if result.is_granted:
    print("Permission granted ✓")
else:
    print(f"Permission denied: {result.reason}")
    print(f"Suggested action: {result.suggested_action}")
    # Output:
    # Permission denied: Agent lacks WRITE permission
    # Suggested action: Submit to Review Queue for human approval
```

**Permission with Context**:
```python
# Context affects permission decision
result = governance.check_permission(
    agent_id="execution_agent",
    capability_id="action.execute.local",
    context={
        "task_id": "task-123",
        "estimated_cost": 5.00,  # High cost!
        "environment": "production",
    },
)

if not result.is_granted:
    if result.reason == "cost_exceeds_limit":
        print(f"Cost ${result.context['estimated_cost']} exceeds limit ${result.context['max_cost']}")
        # Request budget increase or human override
```

### 7.4 Risk Calculation

**Calculate Risk Score**:
```python
from agentos.core.capability.domains.governance import RiskCalculator

risk_calc = RiskCalculator()

# Calculate risk for action
risk_result = risk_calc.calculate_risk_score(
    agent_id="execution_agent",
    capability_id="action.execute.local",
    context={
        "task_id": "task-deploy",
        "command": "kubectl apply -f production.yaml",
        "environment": "production",
        "estimated_cost": 2.00,
        "files_affected": 15,
        "has_tests": True,
        "has_rollback": True,
    },
)

print(f"Risk Score: {risk_result.risk_score}/100")
print(f"Risk Tier: {risk_result.risk_tier}")  # T1/T2/T3
print(f"Risk Factors:")
for factor, value in risk_result.risk_factors.items():
    print(f"  {factor}: {value}")

# Output:
# Risk Score: 65/100
# Risk Tier: T2 (Medium)
# Risk Factors:
#   environment: production (+20)
#   cost: $2.00 (+10)
#   files_affected: 15 (+15)
#   has_tests: True (-10)
#   has_rollback: True (-10)
```

**Risk Tiers**:
- **T1 (0-33)**: Low risk - auto-approve
- **T2 (34-66)**: Medium risk - review recommended
- **T3 (67-100)**: High risk - human approval required

### 7.5 Override Management

**Request Override**:
```python
from agentos.core.capability.domains.governance import OverrideManager

override_mgr = OverrideManager()

# Agent requests override for denied action
override_request = override_mgr.request_override(
    agent_id="execution_agent",
    capability_id="action.execute.remote",
    reason="""
    Need to deploy hotfix to production immediately.
    Critical bug affecting 50% of users.
    All tests pass. Rollback plan ready.
    """,
    context={
        "task_id": "task-hotfix",
        "severity": "critical",
        "estimated_downtime": "5 minutes",
    },
    requested_by="execution_agent",
)

print(f"Override request: {override_request.request_id}")
print(f"Status: {override_request.status}")  # pending
```

**Approve Override** (ADMIN only):
```python
# Admin reviews and approves
approval = override_mgr.approve_override(
    request_id=override_request.request_id,
    approved_by="admin_user",
    approval_notes="Approved due to critical severity. Monitoring deployment.",
    conditions={
        "max_execution_time_ms": 600000,  # 10 minutes
        "requires_post_action_report": True,
    },
)

print(f"Override approved: {approval.request_id}")
print(f"Valid until: {approval.expires_at_ms}")

# Now agent can execute with override
result = executor.execute(
    capability_id="action.execute.remote",
    params={...},
    agent_id="execution_agent",
    override_token=approval.override_token,  # Use override
)
```

**Reject Override**:
```python
rejection = override_mgr.reject_override(
    request_id=override_request.request_id,
    rejected_by="admin_user",
    rejection_reason="Insufficient testing. Need QA approval first.",
)
```

### 7.6 Budget Enforcement

**Set Budget Limits**:
```python
# Set agent budget
governance.set_agent_budget(
    agent_id="execution_agent",
    max_cost_per_task=5.00,    # $5 per task
    max_cost_per_day=50.00,    # $50 per day
    max_cost_per_month=500.00, # $500 per month
)

# Set capability budget
governance.set_capability_budget(
    capability_id="action.execute.remote",
    max_cost_per_invocation=1.00,  # $1 per call
    max_invocations_per_hour=10,   # Rate limit
)
```

**Check Budget**:
```python
# Check if budget allows action
budget_check = governance.check_budget(
    agent_id="execution_agent",
    capability_id="action.execute.remote",
    estimated_cost=0.80,
    context={"task_id": "task-123"},
)

if not budget_check.within_budget:
    print(f"Budget exceeded: {budget_check.reason}")
    print(f"Current usage: ${budget_check.current_usage}")
    print(f"Budget limit: ${budget_check.budget_limit}")
    # Notify admin or pause task
```

---

## Chapter 8: UI操作手册

### 8.1 WebUI Overview

AgentOS v3 WebUI provides real-time visibility into capability governance.

**Access WebUI**:
```bash
# Start WebUI server
agentos server --web

# Open browser
http://localhost:8000
```

### 8.2 Capability Dashboard

**View All Capabilities**:
1. Navigate to **Governance** → **Capabilities**
2. View 27 registered capabilities across 5 domains
3. Filter by domain: STATE / DECISION / ACTION / GOVERNANCE / EVIDENCE
4. Search by capability ID

**Capability Details**:
- Capability ID: `action.execute.local`
- Domain: ACTION
- Permission Level: WRITE
- Risk Tier: T2 (Medium)
- Usage Count: 1,234 (last 30 days)
- Success Rate: 98.5%

### 8.3 Agent Management

**View Agents**:
1. Navigate to **Agents** → **Agent List**
2. View all registered agents
3. Filter by agent type: chat / execution / admin / readonly

**Agent Profile**:
- Agent ID: `execution_agent_001`
- Type: execution
- Trust Tier: T2
- Capabilities: 15 granted
- Budget: $5.00 per task, $50.00 per day
- Usage: $12.30 (today)

**Grant Capability**:
1. Click on agent
2. Click **Grant Capability**
3. Select capability from dropdown
4. Choose permission level: READ / PROPOSE / WRITE / ADMIN
5. Click **Grant**

**Revoke Capability**:
1. Find capability in agent's list
2. Click **Revoke**
3. Confirm revocation

### 8.4 Review Queue

**View Pending Approvals**:
1. Navigate to **Governance** → **Review Queue**
2. View all pending approval requests
3. Filter by: agent / capability / risk tier

**Approve Request**:
1. Click on request
2. Review details:
   - Agent: execution_agent
   - Capability: action.execute.remote
   - Reason: "Deploy hotfix"
   - Risk Score: 75/100
   - Context: task-hotfix, environment=production
3. Click **Approve** or **Reject**
4. Add approval notes
5. Set expiration (optional)
6. Confirm

### 8.5 Evidence Viewer

**View Evidence**:
1. Navigate to **Evidence** → **Evidence Log**
2. Filter by:
   - Agent ID
   - Capability ID
   - Date range
   - Operation type
3. View evidence details:
   - Evidence ID
   - Timestamp
   - Agent ID
   - Capability ID
   - Params (JSON)
   - Result (JSON)
   - Integrity Hash

**Evidence Chain Visualization**:
1. Click on evidence item
2. Click **View Chain**
3. See visual graph: decision → action → state
4. Hover over nodes for details
5. Click node to jump to evidence

### 8.6 Risk Dashboard

**View Risk Metrics**:
1. Navigate to **Governance** → **Risk Dashboard**
2. View metrics:
   - High Risk Actions (T3): 12 (last 7 days)
   - Medium Risk Actions (T2): 156
   - Low Risk Actions (T1): 1,043
   - Average Risk Score: 42/100
   - Top Risky Agents: execution_agent (65), deploy_agent (71)

**Risk Trends**:
- Line chart: Risk score over time
- Bar chart: Actions by risk tier
- Pie chart: Risk factors distribution

---

## Chapter 9: 常见问题FAQ

### 9.1 Capability Questions

**Q: Can Decision capabilities trigger Action capabilities?**

A: No. This is a fundamental design constraint enforced by PathValidator. Decision capabilities can only:
- Read state (state.memory.read)
- Check governance (governance.check.permission)
- Record evidence (evidence.collect)

They CANNOT:
- Execute actions (action.*)
- Modify state directly (state.memory.write)

**Reason**: Prevents accidental execution during planning phase.

**Q: How do I execute an action after creating a plan?**

A: Follow the Golden Path:
1. Decision.create_plan → Create plan
2. Decision.freeze_plan → Freeze plan
3. Governance.check_permission → Verify permission
4. Action.execute → Execute (if permission granted)

**Q: What happens if I try to call action.execute from decision.plan.create?**

A: PathValidator raises `PathValidationError`:
```
Path validation failed: decision → action is forbidden.
Violated rule: decision→action_forbidden
Reason: Decision capabilities cannot directly trigger actions
Call stack: state → decision → action (blocked)
```

### 9.2 Permission Questions

**Q: What's the difference between PROPOSE and WRITE permission?**

A:
- **PROPOSE**: Agent can suggest changes, but requires human approval
- **WRITE**: Agent can execute immediately without approval

**Example**:
```python
# Chat agent with PROPOSE permission
"state.memory.write": "propose"
# Creates proposal → Human reviews → Approved → Write executes

# Execution agent with WRITE permission
"action.execute.local": "write"
# Executes immediately (if governance allows)
```

**Q: Can I grant different permissions for different scopes?**

A: Yes! Use scope-specific grants:
```python
"state.memory.write": {
    "permission_level": "write",
    "scopes": ["task", "agent"],  # Can write to task/agent scope
}
# Cannot write to global/project scope
```

**Q: How do I grant temporary permissions?**

A: Use time-limited overrides:
```python
override = override_mgr.approve_override(
    request_id="req-123",
    approved_by="admin",
    expires_at_ms=utc_now_ms() + (3600 * 1000),  # 1 hour
)
# Override expires automatically after 1 hour
```

### 9.3 Evidence Questions

**Q: Can I modify evidence after it's created?**

A: No. Evidence is immutable by design. Any modification attempt raises `EvidenceImmutableError`.

**Q: Can I delete old evidence?**

A: No. Evidence cannot be deleted. Use archival/export instead:
```python
# Export old evidence to cold storage
export_engine.export(
    query=ExportQuery(
        start_time_ms=0,
        end_time_ms=utc_now_ms() - (365 * 24 * 3600 * 1000),  # >1 year old
    ),
    format=ExportFormat.JSON,
    exported_by="admin",
)
# Archive exported files to S3/Glacier
```

**Q: How do I debug a failed action?**

A: Use Evidence replay:
```python
# Find evidence for failed action
evidence = collector.query_by_context(
    context_filter={"task_id": "task-failed"}
)

# Replay in read-only mode
replay_result = replay_engine.replay(
    evidence_id=evidence[0].evidence_id,
    mode=ReplayMode.READ_ONLY,
    replayed_by="debug_agent",
)

# Inspect params and result
print(f"Params: {replay_result.original_params}")
print(f"Result: {replay_result.original_result}")
print(f"Error: {replay_result.original_result.get('error')}")
```

### 9.4 Governance Questions

**Q: How do I set up emergency override?**

A: Create emergency policy:
```python
policy_registry.register_policy({
    "policy_id": "emergency_policy",
    "rules": [
        {
            "capability_pattern": "action.*",
            "agent_pattern": "emergency_*",
            "permission_level": "write",
            "constraints": {
                "requires_justification": True,
                "max_duration_ms": 3600000,  # 1 hour
                "audit_level": "comprehensive",
            },
        }
    ],
})

# Create emergency agent
agent_registry.register_agent(
    agent_id="emergency_responder",
    agent_type="emergency",
    capability_profile={
        "action.*": {"permission_level": "write"},
    },
)
```

**Q: How do I enforce budget limits strictly?**

A: Use hard budget limits with auto-pause:
```python
governance.set_agent_budget(
    agent_id="execution_agent",
    max_cost_per_day=50.00,
    enforcement_mode="strict",  # Auto-pause if exceeded
    alert_threshold=0.8,  # Alert at 80%
)

# Budget check happens automatically before action
# If exceeded, raises BudgetExceededError
```

---

## Chapter 10: 故障排查

### 10.1 Permission Denied Errors

**Symptom**: `PermissionDeniedError: Agent lacks WRITE permission`

**Diagnosis**:
```python
# Check agent's capability profile
agent = agent_registry.get_agent("chat_agent")
capability_config = agent.capability_profile.get("action.execute.local")

if capability_config is None:
    print("Capability not granted")
elif capability_config["permission_level"] == "none":
    print("Capability explicitly denied")
elif capability_config["permission_level"] == "propose":
    print("Capability requires approval")
```

**Solution**:
1. Grant permission:
   ```bash
   agentos agent grant \
     --agent-id chat_agent \
     --capability action.execute.local \
     --permission write
   ```

2. Or submit for approval:
   ```python
   override_mgr.request_override(
       agent_id="chat_agent",
       capability_id="action.execute.local",
       reason="Need to execute task-123",
   )
   ```

### 10.2 Path Validation Errors

**Symptom**: `PathValidationError: decision → action is forbidden`

**Diagnosis**:
```python
# Check call stack
validator = PathValidator()
call_stack = validator.get_current_call_stack()

for entry in call_stack:
    print(f"{entry.domain.value} → {entry.capability_id}")

# Output:
# state → state.memory.read
# decision → decision.plan.create
# action → action.execute.local (BLOCKED)
```

**Solution**: Restructure code to follow Golden Path:
```python
# WRONG: Decision directly calls Action
def create_and_execute_plan():
    plan = decision.create_plan(...)
    result = action.execute(...)  # ❌ Forbidden!

# CORRECT: Follow Golden Path
def create_and_execute_plan():
    plan = decision.create_plan(...)
    frozen_plan = decision.freeze_plan(plan.plan_id)
    permission = governance.check_permission(...)
    if permission.is_granted:
        result = action.execute(...)  # ✓ Allowed
```

### 10.3 Evidence Integrity Errors

**Symptom**: `EvidenceIntegrityError: Hash mismatch`

**Diagnosis**:
```python
evidence = collector.get_evidence("evidence-456")

stored_hash = evidence.integrity.content_hash
computed_hash = evidence.compute_hash()

if stored_hash != computed_hash:
    print("Evidence tampered!")
    print(f"Stored: {stored_hash}")
    print(f"Computed: {computed_hash}")
```

**Solution**:
1. Investigate tampering:
   ```bash
   # Check database access logs
   agentos audit query \
     --table evidence_log \
     --where "evidence_id='evidence-456'"
   ```

2. Re-validate all evidence:
   ```python
   all_evidence = collector.query_all()

   for evidence in all_evidence:
       if not evidence.verify_integrity():
           print(f"Invalid: {evidence.evidence_id}")
   ```

3. If database corrupted, restore from backup.

### 10.4 Performance Issues

**Symptom**: Golden Path taking > 200ms

**Diagnosis**:
```python
import time

times = {}

start = time.time()
state_data = state.read_memory(...)
times["state.read"] = (time.time() - start) * 1000

start = time.time()
plan = decision.create_plan(...)
times["decision.create"] = (time.time() - start) * 1000

# ... repeat for all steps

for step, duration_ms in times.items():
    print(f"{step}: {duration_ms:.2f}ms")

# Identify slowest step
```

**Solutions**:

**If PathValidator is slow**:
```python
# Check validation log size
validator.vacuum_old_logs(
    older_than_ms=utc_now_ms() - (30 * 24 * 3600 * 1000)  # > 30 days
)
```

**If Evidence collection is slow**:
```python
# Check evidence log size
collector.vacuum_old_evidence(
    older_than_ms=utc_now_ms() - (90 * 24 * 3600 * 1000)  # > 90 days
)
```

**If Database is slow**:
```bash
# Analyze and optimize
agentos db analyze
agentos db vacuum

# Add indexes if needed
agentos db index \
  --table path_validation_log \
  --columns session_id,from_domain,to_domain
```

### 10.5 Budget Exceeded Errors

**Symptom**: `BudgetExceededError: Daily budget exceeded`

**Diagnosis**:
```python
# Check current usage
usage = governance.get_agent_usage(
    agent_id="execution_agent",
    time_range="day",
)

print(f"Current usage: ${usage.current_cost}")
print(f"Budget limit: ${usage.budget_limit}")
print(f"Percentage: {usage.percentage_used:.1f}%")
```

**Solutions**:

1. Increase budget:
   ```bash
   agentos governance set-budget \
     --agent-id execution_agent \
     --daily 100.00  # Increase to $100/day
   ```

2. Request override:
   ```python
   override_mgr.request_override(
       agent_id="execution_agent",
       capability_id="action.execute.local",
       reason="Critical deployment requires extra budget",
   )
   ```

3. Wait for budget reset (next day/month).

---

## Appendix A: Quick Reference

### Capability Domains
- **STATE**: Memory and context management
- **DECISION**: Planning and option evaluation
- **ACTION**: Execution with side effects
- **GOVERNANCE**: Policies and risk management
- **EVIDENCE**: Audit trail and replay

### Permission Levels
- **NONE**: No access
- **READ**: Query only
- **PROPOSE**: Suggest changes (requires approval)
- **WRITE**: Execute immediately
- **ADMIN**: Full control + approvals

### Golden Path (9 Steps)
1. State.read
2. Decision.create
3. Decision.freeze
4. Governance.check
5. Governance.risk
6. Action.execute
7. State.write
8. Evidence.collect (automatic)
9. Evidence.link

### Forbidden Paths
❌ Decision → Action
❌ Action → State (direct)
❌ Evidence → Any domain

---

## Appendix B: Glossary

**Capability**: A discrete unit of functionality (e.g., state.memory.read)

**Domain**: A logical grouping of capabilities (STATE, DECISION, ACTION, GOVERNANCE, EVIDENCE)

**Permission Level**: The level of access an agent has (NONE/READ/PROPOSE/WRITE/ADMIN)

**Golden Path**: The ideal execution flow ensuring safety and auditability

**Path Validator**: Component that enforces domain transition rules

**Evidence**: Immutable audit record of operations

**Governance**: Policy enforcement and risk management system

**Frozen Plan**: Immutable execution plan with hash verification

**Risk Score**: Calculated risk value (0-100) for an operation

**Risk Tier**: Risk category (T1=low, T2=medium, T3=high)

**Override**: Human approval to bypass policy restrictions

**Rollback Plan**: Instructions to undo an action if needed

---

**Document Version**: 3.0.0
**Last Updated**: 2026-02-01
**Next Review**: 2026-03-01

**Feedback**: Submit issues or suggestions to the AgentOS team.
