# AgentOS v3 Developer Guide

**Version**: 3.0.0
**Last Updated**: 2026-02-01
**Audience**: Backend developers, systems architects, capability authors

---

## Table of Contents

1. [v3架构深度解析](#chapter-1-v3架构深度解析)
2. [Capability原子定义规范](#chapter-2-capability原子定义规范)
3. [五大Domain API完整参考](#chapter-3-五大domain-api完整参考)
4. [黄金路径实现原理](#chapter-4-黄金路径实现原理)
5. [PathValidator源码解析](#chapter-5-pathvalidator源码解析)
6. [Evidence系统设计](#chapter-6-evidence系统设计)
7. [Agent开发最佳实践](#chapter-7-agent开发最佳实践)
8. [新Capability开发指南](#chapter-8-新capability开发指南)
9. [Policy编写和测试](#chapter-9-policy编写和测试)
10. [性能优化建议](#chapter-10-性能优化建议)
11. [扩展点和插件系统](#chapter-11-扩展点和插件系统)
12. [安全考虑和合规性](#chapter-12-安全考虑和合规性)

---

## Chapter 1: v3架构深度解析

### 1.1 Architecture Overview

AgentOS v3 adopts a **Domain-Driven Design (DDD)** architecture with strict domain boundaries.

```
┌─────────────────────────────────────────────────────────────────┐
│                     AgentOS v3 Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Capability Registry                       │  │
│  │  - 27 capabilities across 5 domains                       │  │
│  │  - Capability metadata (risk, audit requirements)         │  │
│  │  - Query API: O(1) lookup by ID                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Path Validator                          │  │
│  │  - Enforces Golden Path rules                             │  │
│  │  - Blocks forbidden paths (decision→action)               │  │
│  │  - Call stack tracking per session                        │  │
│  │  - Performance: <5ms per validation                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ↓                                   │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐     │
│  │  STATE   │ DECISION │  ACTION  │GOVERNANCE│ EVIDENCE │     │
│  │  Domain  │  Domain  │  Domain  │  Domain  │  Domain  │     │
│  │          │          │          │          │          │     │
│  │ 4 caps   │ 5 caps   │ 7 caps   │ 6 caps   │ 5 caps   │     │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘     │
│                              │                                   │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Database Layer                          │  │
│  │  - SQLite (default) / PostgreSQL (production)             │  │
│  │  - 5 schema versions (v48-v52)                            │  │
│  │  - Indexed for <1ms queries                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

**1. Domain Isolation**

Each domain is self-contained with its own:
- Data models (`models.py`)
- Business logic (`*_service.py`)
- Database tables (schema)
- Tests (`tests/unit/core/capability/<domain>/`)

**Example Structure**:
```
agentos/core/capability/domains/
├── state/
│   ├── __init__.py
│   ├── models.py          # State, MemoryItem, ContextSnapshot
│   ├── memory_service.py  # Memory CRUD
│   ├── context_service.py # Context management
│   └── tests/
├── decision/
│   ├── __init__.py
│   ├── models.py          # Plan, Option, EvaluationResult
│   ├── plan_service.py    # Plan lifecycle
│   ├── option_evaluator.py
│   ├── judge.py
│   └── tests/
├── action/
│   ├── models.py          # ActionExecution, SideEffect, RollbackPlan
│   ├── action_executor.py
│   ├── side_effects_tracker.py
│   ├── rollback_engine.py
│   └── tests/
├── governance/
│   ├── models.py          # Policy, RiskScore, Override
│   ├── governance_engine.py
│   ├── policy_registry.py
│   ├── risk_calculator.py
│   ├── override_manager.py
│   └── tests/
└── evidence/
    ├── models.py          # Evidence, EvidenceChain, ReplayResult
    ├── evidence_collector.py
    ├── evidence_link_graph.py
    ├── replay_engine.py
    ├── export_engine.py
    └── tests/
```

**2. Capability as First-Class Citizen**

Every operation is modeled as a capability invocation:

```python
@dataclass
class CapabilityInvocation:
    """
    Represents a capability call.

    Tracked by PathValidator and recorded in Evidence.
    """
    invocation_id: str           # Unique ID (ULID)
    capability_id: str           # e.g., "decision.plan.create"
    agent_id: str                # Who invoked it
    params: Dict[str, Any]       # Input parameters
    context: Dict[str, Any]      # Execution context
    timestamp_ms: int            # When invoked
    result: Optional[Any] = None # Result (after execution)
    evidence_id: Optional[str] = None  # Evidence reference
```

**3. Explicit Dependencies**

Dependencies are declared, not implicit:

```python
# WRONG: Hidden dependency
class PlanService:
    def create_plan(self):
        # Implicitly uses global state
        memory = get_global_memory()

# CORRECT: Explicit dependency
class PlanService:
    def __init__(self, db_path: str, memory_service: MemoryService):
        self.db_path = db_path
        self.memory_service = memory_service  # Explicit!
```

**4. Immutability Where It Matters**

Key data structures are immutable:
- Frozen plans (Plan.status == "frozen")
- Evidence records (cannot be modified or deleted)
- Context snapshots (ContextSnapshot)

**5. Performance Targets**

All operations have explicit performance targets:
- PathValidator: <5ms per validation
- Registry query: <1ms per lookup
- Evidence collection: <20ms per record
- Golden Path E2E: <100ms complete flow

### 1.3 Data Flow

**Example: User requests "Deploy to production"**

```
1. CLI/API receives request
   ↓
2. State.read: Retrieve deployment config
   ↓
3. Decision.create: Generate deployment plan
   ↓
4. Decision.freeze: Make plan immutable
   ↓
5. Governance.check: Verify execution_agent has permission
   ├─ YES → Continue
   └─ NO → Send to Review Queue, STOP
   ↓
6. Governance.risk: Calculate risk score
   ├─ T1 (low) → Continue
   ├─ T2 (med) → Log warning, Continue
   └─ T3 (high) → Require override, STOP
   ↓
7. Action.execute: Execute deployment steps
   ├─ Step 1: Run tests → Success
   ├─ Step 2: Build Docker → Success
   ├─ Step 3: Push to registry → Success
   └─ Step 4: Deploy to k8s → Success
   ↓
8. State.write: Update deployment status
   ↓
9. Evidence.collect: Record all evidence (automatic)
   ↓
10. Evidence.link: Build evidence chain
   ↓
11. Return result to user
```

### 1.4 Key Components

**CapabilityRegistry**
- File: `agentos/core/capability/capability_registry.py`
- Purpose: Central registry for all capabilities
- Methods:
  - `register_capability(definition)` - Register new capability
  - `get_capability(capability_id)` - Query capability (O(1))
  - `list_capabilities(domain=None)` - List all/filtered
  - `check_capability_exists(capability_id)` - Existence check

**PathValidator**
- File: `agentos/core/capability/path_validator.py`
- Purpose: Enforce Golden Path rules
- Methods:
  - `start_session(session_id)` - Start call tracking
  - `validate_call(from_domain, to_domain, ...)` - Validate transition
  - `push_call(entry)` - Add to call stack
  - `pop_call()` - Remove from call stack
  - `end_session()` - Clean up session

**GovernanceEngine**
- File: `agentos/core/capability/domains/governance/governance_engine.py`
- Purpose: Enforce policies and manage risk
- Methods:
  - `check_permission(agent_id, capability_id, context)` - Permission check
  - `calculate_risk_score(...)` - Risk calculation
  - `request_override(...)` - Request approval
  - `approve_override(...)` - Grant approval

**EvidenceCollector**
- File: `agentos/core/capability/domains/evidence/evidence_collector.py`
- Purpose: Immutable audit trail
- Methods:
  - `collect(operation_type, params, result, ...)` - Record evidence
  - `query_by_agent(agent_id)` - Query by agent
  - `query_by_capability(capability_id)` - Query by capability
  - `verify_integrity(evidence_id)` - Verify hash

---

## Chapter 2: Capability原子定义规范

### 2.1 Capability Definition Schema

Every capability follows a strict schema defined in `agentos/core/capability/models.py`:

```python
@dataclass
class CapabilityDefinition:
    """
    Atomic capability definition.

    A capability is the smallest unit of functionality that can be:
    - Authorized (permission check)
    - Audited (evidence collection)
    - Governed (policy enforcement)
    """
    capability_id: str        # Unique ID: domain.component.operation
    domain: CapabilityDomain  # STATE|DECISION|ACTION|GOVERNANCE|EVIDENCE
    name: str                 # Human-readable name
    description: str          # What this capability does
    version: str              # Semantic version (e.g., "1.0.0")

    # Permission requirements
    default_permission: PermissionLevel  # NONE|READ|PROPOSE|WRITE|ADMIN
    requires_frozen_plan: bool           # Must have frozen plan?
    requires_governance_check: bool      # Must check governance first?

    # Risk and audit
    risk_tier: RiskTier       # T1 (low) | T2 (medium) | T3 (high)
    audit_level: AuditLevel   # BASIC | DETAILED | COMPREHENSIVE
    requires_evidence: bool   # Must record evidence?

    # Constraints
    max_execution_time_ms: Optional[int]  # Timeout
    max_cost_per_invocation: Optional[float]  # Budget limit
    rate_limit_per_hour: Optional[int]  # Rate limit

    # Metadata
    created_by: str
    created_at_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 2.2 Domain Assignment Rules

**How to choose domain?**

| Domain | Use When |
|--------|----------|
| **STATE** | Reading/writing persistent data (memory, context) |
| **DECISION** | Planning, evaluating options, making judgments (NO execution) |
| **ACTION** | Executing operations with side effects |
| **GOVERNANCE** | Enforcing policies, calculating risk, approvals |
| **EVIDENCE** | Recording audit trails, replaying, exporting |

**Examples**:

```python
# STATE domain
CapabilityDefinition(
    capability_id="state.memory.read",
    domain=CapabilityDomain.STATE,
    name="Read Memory",
    description="Read from memory scopes (global/project/task/agent)",
    default_permission=PermissionLevel.READ,  # Low barrier
    risk_tier=RiskTier.T1,  # Low risk
    audit_level=AuditLevel.BASIC,
)

# DECISION domain
CapabilityDefinition(
    capability_id="decision.plan.create",
    domain=CapabilityDomain.DECISION,
    name="Create Execution Plan",
    description="Create execution plan (DRAFT state, modifiable)",
    default_permission=PermissionLevel.WRITE,
    requires_frozen_plan=False,  # Creates plan, doesn't need one
    requires_governance_check=False,  # Planning is safe
    risk_tier=RiskTier.T1,
    audit_level=AuditLevel.DETAILED,
    requires_evidence=True,
)

# ACTION domain
CapabilityDefinition(
    capability_id="action.execute.local",
    domain=CapabilityDomain.ACTION,
    name="Execute Local Command",
    description="Execute command on local machine",
    default_permission=PermissionLevel.WRITE,
    requires_frozen_plan=True,  # MUST have frozen plan!
    requires_governance_check=True,  # MUST check permission!
    risk_tier=RiskTier.T2,  # Medium risk
    audit_level=AuditLevel.COMPREHENSIVE,
    requires_evidence=True,  # MUST record evidence!
    max_execution_time_ms=300000,  # 5 minutes
)
```

### 2.3 Capability Naming Convention

**Pattern**: `<domain>.<component>.<operation>`

**Rules**:
1. All lowercase
2. Use dots (.) as separator
3. Domain must be one of: state, decision, action, governance, evidence
4. Component describes the subsystem
5. Operation is a verb

**Good Examples**:
```
state.memory.read
state.memory.write
state.context.snapshot
decision.plan.create
decision.plan.freeze
decision.option.evaluate
action.execute.local
action.execute.remote
action.file.write
governance.check.permission
governance.risk.calculate
evidence.collect
evidence.replay
```

**Bad Examples**:
```
ReadMemory                # Not structured
state.read_memory         # Underscore (use dot)
state.Memory.Read         # Capital letters
action.do_something       # Vague operation
decision.execute          # Wrong domain (decision cannot execute)
```

### 2.4 Registering Capabilities

**Programmatic Registration**:

```python
from agentos.core.capability.capability_registry import CapabilityRegistry
from agentos.core.capability.models import (
    CapabilityDefinition,
    CapabilityDomain,
    PermissionLevel,
    RiskTier,
    AuditLevel,
)

registry = CapabilityRegistry()

# Define capability
capability = CapabilityDefinition(
    capability_id="state.knowledge_base.query",
    domain=CapabilityDomain.STATE,
    name="Query Knowledge Base",
    description="Semantic search over indexed knowledge base",
    version="1.0.0",
    default_permission=PermissionLevel.READ,
    requires_frozen_plan=False,
    requires_governance_check=False,
    risk_tier=RiskTier.T1,
    audit_level=AuditLevel.BASIC,
    requires_evidence=True,
    max_execution_time_ms=5000,  # 5 seconds
    rate_limit_per_hour=1000,  # 1000 queries/hour
    created_by="system",
    created_at_ms=utc_now_ms(),
)

# Register
registry.register_capability(capability)
```

**JSON Definition**:

```json
{
  "capability_id": "state.knowledge_base.query",
  "domain": "state",
  "name": "Query Knowledge Base",
  "description": "Semantic search over indexed knowledge base",
  "version": "1.0.0",
  "default_permission": "read",
  "requires_frozen_plan": false,
  "requires_governance_check": false,
  "risk_tier": "T1",
  "audit_level": "basic",
  "requires_evidence": true,
  "max_execution_time_ms": 5000,
  "rate_limit_per_hour": 1000,
  "created_by": "system",
  "created_at_ms": 1738454400000
}
```

Load from JSON:
```bash
agentos capability register --from-file capability.json
```

---

## Chapter 3: 五大Domain API完整参考

### 3.1 STATE Domain API

**Module**: `agentos.core.capability.domains.state`

**Capabilities**:
1. `state.memory.read` - Read memory
2. `state.memory.write` - Write memory
3. `state.context.snapshot` - Create context snapshot
4. `state.context.verify` - Verify context integrity

**API: MemoryService**

```python
class MemoryService:
    """Memory management service"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def read_memory(
        self,
        scope: str,  # "global" | "project" | "task" | "agent"
        key: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[MemoryItem]:
        """
        Read memory items from scope.

        Args:
            scope: Memory scope
            key: Optional key filter
            agent_id: Agent ID for permission check

        Returns:
            List of matching memory items

        Raises:
            PermissionDeniedError: If agent lacks READ permission
        """

    def write_memory(
        self,
        scope: str,
        key: str,
        value: Any,
        written_by: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Write memory item.

        Args:
            scope: Memory scope
            key: Unique key
            value: JSON-serializable value
            written_by: Agent ID
            metadata: Optional metadata

        Returns:
            Memory item ID

        Raises:
            PermissionDeniedError: If agent lacks WRITE permission
        """

    def delete_memory(
        self,
        memory_id: str,
        deleted_by: str,
    ) -> bool:
        """
        Delete memory item.

        Args:
            memory_id: Memory item ID
            deleted_by: Agent ID

        Returns:
            True if deleted

        Raises:
            PermissionDeniedError: If agent lacks ADMIN permission
        """
```

**API: ContextService**

```python
class ContextService:
    """Context snapshot management"""

    def create_snapshot(
        self,
        context_id: str,
        data: Dict[str, Any],
        created_by: str,
    ) -> ContextSnapshot:
        """
        Create immutable context snapshot.

        Args:
            context_id: Unique context ID
            data: Context data
            created_by: Agent ID

        Returns:
            Context snapshot with hash

        Example:
            snapshot = context_service.create_snapshot(
                context_id="ctx-task-123",
                data={
                    "task_id": "task-123",
                    "files": ["src/api.py", "src/models.py"],
                    "dependencies": ["requests", "pydantic"],
                },
                created_by="decision_agent",
            )
        """

    def verify_snapshot(
        self,
        snapshot_id: str,
    ) -> bool:
        """
        Verify snapshot integrity.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            True if hash matches

        Raises:
            SnapshotTamperedError: If hash mismatch
        """
```

### 3.2 DECISION Domain API

**Module**: `agentos.core.capability.domains.decision`

**Capabilities**:
1. `decision.plan.create` - Create execution plan
2. `decision.plan.freeze` - Freeze plan
3. `decision.option.evaluate` - Evaluate options
4. `decision.judge.select` - Select best option
5. `decision.record.rationale` - Record rationale

**API: PlanService**

```python
class PlanService:
    """Execution plan management"""

    def create_plan(
        self,
        task_id: str,
        steps: List[Dict],
        alternatives: List[Dict],
        rationale: str,
        created_by: str,
    ) -> Plan:
        """
        Create execution plan (DRAFT state).

        Args:
            task_id: Parent task ID
            steps: Ordered list of steps
            alternatives: Rejected alternatives with reasons
            rationale: Decision rationale
            created_by: Agent ID

        Returns:
            Plan in DRAFT state

        Example:
            plan = plan_service.create_plan(
                task_id="task-123",
                steps=[
                    {
                        "step_id": "step-1",
                        "action": "search_files",
                        "params": {"pattern": "*.py"},
                        "estimated_time_ms": 5000,
                    },
                ],
                alternatives=[
                    {
                        "alternative_id": "alt-1",
                        "description": "Manual search",
                        "rejected_reason": "Too slow",
                    }
                ],
                rationale="Automated search is faster",
                created_by="decision_agent",
            )
        """

    def freeze_plan(
        self,
        plan_id: str,
    ) -> Plan:
        """
        Freeze plan (make immutable).

        Args:
            plan_id: Plan ID

        Returns:
            Frozen plan with SHA256 hash

        Raises:
            ImmutablePlanError: If already frozen
            PlanNotFoundError: If plan doesn't exist

        Example:
            frozen_plan = plan_service.freeze_plan("plan-456")
            print(frozen_plan.plan_hash)  # 7f3a8b9c...
        """

    def verify_plan_hash(
        self,
        plan_id: str,
        expected_hash: str,
    ) -> bool:
        """
        Verify plan integrity.

        Args:
            plan_id: Plan ID
            expected_hash: Expected SHA256 hash

        Returns:
            True if hash matches

        Raises:
            PlanTamperedError: If hash mismatch
        """
```

**API: OptionEvaluator**

```python
class OptionEvaluator:
    """Option evaluation engine"""

    def evaluate_options(
        self,
        decision_context_id: str,
        options: List[Dict],
        evaluated_by: str,
        scoring_weights: Optional[Dict] = None,
    ) -> EvaluationResult:
        """
        Evaluate and rank options.

        Args:
            decision_context_id: Context ID
            options: List of options to evaluate
            evaluated_by: Agent ID
            scoring_weights: Custom weights (optional)

        Returns:
            Evaluation result with ranked options

        Example:
            result = evaluator.evaluate_options(
                decision_context_id="ctx-api-choice",
                options=[
                    {
                        "option_id": "opt-1",
                        "description": "REST API",
                        "estimated_cost": 0.10,
                        "estimated_time_ms": 5000,
                        "risks": ["Rate limiting"],
                        "benefits": ["Standard", "Well documented"],
                    },
                    {
                        "option_id": "opt-2",
                        "description": "GraphQL",
                        "estimated_cost": 0.15,
                        "estimated_time_ms": 8000,
                        "risks": ["Complex queries"],
                        "benefits": ["Flexible"],
                    },
                ],
                evaluated_by="decision_agent",
                scoring_weights={
                    "cost": 0.3,
                    "time": 0.3,
                    "risk": 0.2,
                    "benefits": 0.2,
                },
            )

            print(result.ranked_options)  # ["opt-1", "opt-2"]
            print(result.recommendation)  # "Use REST API"
            print(result.confidence)      # 0.85
        """
```

### 3.3 ACTION Domain API

**Module**: `agentos.core.capability.domains.action`

**Capabilities**:
1. `action.execute.local` - Execute local command
2. `action.execute.remote` - Execute remote operation
3. `action.state.modify` - Modify system state
4. `action.file.write` - Write to file
5. `action.file.delete` - Delete file
6. `action.network.call` - Make network request
7. `action.database.execute` - Execute database query

**API: ActionExecutor**

```python
class ActionExecutor:
    """Action execution engine"""

    def execute(
        self,
        capability_id: str,
        params: Dict[str, Any],
        agent_id: str,
        context: Dict[str, Any],
        dry_run: bool = False,
        rollback_plan: Optional[Dict] = None,
    ) -> ActionExecutionResult:
        """
        Execute action with governance and evidence collection.

        This is the ONLY way to execute actions in v3. It enforces:
        1. Governance permission check
        2. Evidence collection
        3. Side effects tracking
        4. Rollback capability

        Args:
            capability_id: Action capability ID
            params: Action parameters
            agent_id: Executing agent
            context: Execution context (task_id, plan_id, etc.)
            dry_run: Simulate without executing
            rollback_plan: Rollback instructions

        Returns:
            Execution result with evidence_id

        Raises:
            PermissionDeniedError: If governance denies
            FrozenPlanRequiredError: If no frozen plan in context
            ActionExecutionError: If execution fails

        Example:
            result = executor.execute(
                capability_id="action.execute.local",
                params={"command": "pytest tests/"},
                agent_id="execution_agent",
                context={
                    "task_id": "task-123",
                    "plan_id": "plan-456",
                },
                rollback_plan={
                    "steps": [
                        {"action": "restore_files", "params": {...}}
                    ]
                },
            )

            print(result.status)       # "success" | "failure"
            print(result.output)       # Command output
            print(result.evidence_id)  # "evidence-789"
        """

    def rollback(
        self,
        execution_id: str,
        rollback_plan_id: str,
    ) -> RollbackResult:
        """
        Rollback action execution.

        Args:
            execution_id: Original execution ID
            rollback_plan_id: Rollback plan ID

        Returns:
            Rollback result

        Example:
            rollback_result = executor.rollback(
                execution_id="exec-456",
                rollback_plan_id="rollback-123",
            )
        """
```

### 3.4 GOVERNANCE Domain API

**Module**: `agentos.core.capability.domains.governance`

**Capabilities**:
1. `governance.check.permission` - Check permission
2. `governance.risk.calculate` - Calculate risk score
3. `governance.policy.evaluate` - Evaluate against policies
4. `governance.override.request` - Request override
5. `governance.override.approve` - Approve override (ADMIN)
6. `governance.budget.check` - Check budget

**API: GovernanceEngine**

```python
class GovernanceEngine:
    """Governance enforcement engine"""

    def check_permission(
        self,
        agent_id: str,
        capability_id: str,
        context: Dict[str, Any],
    ) -> PermissionCheckResult:
        """
        Check if agent has permission.

        Args:
            agent_id: Agent ID
            capability_id: Capability ID
            context: Context (task_id, estimated_cost, etc.)

        Returns:
            Permission check result

        Example:
            result = governance.check_permission(
                agent_id="chat_agent",
                capability_id="action.execute.local",
                context={"task_id": "task-123"},
            )

            if result.is_granted:
                # Execute action
            else:
                print(f"Denied: {result.reason}")
                # Send to Review Queue
        """

    def calculate_risk_score(
        self,
        agent_id: str,
        capability_id: str,
        context: Dict[str, Any],
    ) -> RiskScoreResult:
        """
        Calculate risk score (0-100).

        Args:
            agent_id: Agent ID
            capability_id: Capability ID
            context: Context with risk factors

        Returns:
            Risk score result with tier and factors

        Example:
            risk = governance.calculate_risk_score(
                agent_id="execution_agent",
                capability_id="action.execute.local",
                context={
                    "command": "rm -rf /var/data/*",
                    "environment": "production",
                    "estimated_cost": 2.00,
                },
            )

            print(risk.risk_score)  # 75
            print(risk.risk_tier)   # "T3" (high)
            print(risk.risk_factors)
            # {
            #   "destructive_command": 30,
            #   "production_env": 20,
            #   "high_cost": 15,
            #   ...
            # }
        """
```

### 3.5 EVIDENCE Domain API

**Module**: `agentos.core.capability.domains.evidence`

**Capabilities**:
1. `evidence.collect` - Collect evidence (automatic)
2. `evidence.link` - Build evidence chains
3. `evidence.replay` - Replay operations
4. `evidence.export` - Export audit reports
5. `evidence.verify` - Verify integrity

**API: EvidenceCollector**

```python
class EvidenceCollector:
    """Evidence collection engine"""

    def collect(
        self,
        operation_type: OperationType,
        operation_id: str,
        capability_id: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        """
        Collect operation evidence.

        This is automatically called by ActionExecutor.
        Manual calls are rare.

        Args:
            operation_type: STATE | DECISION | ACTION | GOVERNANCE
            operation_id: Unique operation ID
            capability_id: Capability ID
            params: Input parameters
            result: Operation result
            context: Context (agent_id, task_id, etc.)

        Returns:
            Evidence ID

        Example:
            evidence_id = collector.collect(
                operation_type=OperationType.ACTION,
                operation_id="exec-456",
                capability_id="action.execute.local",
                params={"command": "pytest"},
                result={"status": "success", "tests_passed": 42},
                context={"agent_id": "execution_agent"},
            )
        """

    def query_by_agent(
        self,
        agent_id: str,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        limit: int = 100,
    ) -> List[Evidence]:
        """
        Query evidence by agent.

        Args:
            agent_id: Agent ID
            start_time_ms: Start timestamp (optional)
            end_time_ms: End timestamp (optional)
            limit: Max results

        Returns:
            List of evidence records

        Example:
            evidence_list = collector.query_by_agent(
                agent_id="execution_agent",
                start_time_ms=utc_now_ms() - (24 * 3600 * 1000),
                limit=100,
            )
        """
```

---

## Chapter 4: 黄金路径实现原理

### 4.1 Golden Path State Machine

The Golden Path is implemented as a state machine with validation at each transition.

**State Machine Diagram**:

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ↓ (1) state.memory.read
┌─────────────┐
│ CONTEXT_   │
│  LOADED    │
└─────┬───────┘
     │
     ↓ (2) decision.plan.create
┌─────────────┐
│ PLAN_       │
│  DRAFTED    │
└─────┬───────┘
     │
     ↓ (3) decision.plan.freeze
┌─────────────┐
│ PLAN_       │
│  FROZEN     │
└─────┬───────┘
     │
     ↓ (4) governance.check.permission
┌─────────────┐
│ PERMISSION_ │
│  CHECKED    │
└─────┬───────┘
     │
     ├─ GRANTED → Continue
     └─ DENIED  → END (Review Queue)
     │
     ↓ (5) governance.risk.calculate
┌─────────────┐
│ RISK_       │
│  ASSESSED   │
└─────┬───────┘
     │
     ├─ T1/T2 → Continue
     └─ T3    → Override Required
     │
     ↓ (6) action.execute
┌─────────────┐
│ ACTION_     │
│  EXECUTED   │
└─────┬───────┘
     │
     ↓ (7) state.memory.write
┌─────────────┐
│ STATE_      │
│  UPDATED    │
└─────┬───────┘
     │
     ↓ (8) evidence.collect (automatic)
┌─────────────┐
│ EVIDENCE_   │
│  RECORDED   │
└─────┬───────┘
     │
     ↓ (9) evidence.link
┌─────────────┐
│   COMPLETE  │
└─────────────┘
```

### 4.2 PathValidator Implementation

**Core Algorithm**:

```python
class PathValidator:
    """
    Validates domain transitions using:
    1. Golden Path rules (GOLDEN_PATH_RULES dict)
    2. Forbidden paths (FORBIDDEN_PATHS set)
    3. Call stack tracking (contextvars)
    """

    def validate_call(
        self,
        from_domain: CapabilityDomain,
        to_domain: CapabilityDomain,
        agent_id: str,
        capability_id: str,
        operation: str,
    ) -> PathValidationResult:
        """
        Validate domain transition.

        Algorithm:
        1. Check if to_domain is in GOLDEN_PATH_RULES[from_domain]
        2. Check if (from_domain, to_domain) in FORBIDDEN_PATHS
        3. Log validation result
        4. Raise PathValidationError if forbidden

        Performance: O(1) hash lookups
        Target: <5ms per validation
        """
        # Check golden path rules
        allowed_domains = GOLDEN_PATH_RULES.get(from_domain, set())

        if to_domain not in allowed_domains:
            # Check if explicitly forbidden
            if (from_domain.value, to_domain.value) in FORBIDDEN_PATHS:
                # Forbidden path detected!
                call_stack = self.get_current_call_stack()
                raise PathValidationError(
                    from_domain=from_domain,
                    to_domain=to_domain,
                    violated_rule=f"{from_domain.value}→{to_domain.value}_forbidden",
                    call_stack=call_stack,
                    reason=f"{from_domain.value} cannot call {to_domain.value}",
                )

        # Allowed - log and continue
        self._log_validation(
            from_domain=from_domain,
            to_domain=to_domain,
            agent_id=agent_id,
            capability_id=capability_id,
            is_allowed=True,
        )

        return PathValidationResult(
            is_allowed=True,
            from_domain=from_domain,
            to_domain=to_domain,
            capability_id=capability_id,
        )
```

**Call Stack Tracking**:

```python
# Thread-safe call stack using contextvars
_call_stack_var: ContextVar[List[CallStackEntry]] = ContextVar("call_stack", default=[])

def push_call(self, entry: CallStackEntry):
    """Add to call stack"""
    stack = _call_stack_var.get()
    stack.append(entry)
    _call_stack_var.set(stack)

def pop_call(self):
    """Remove from call stack"""
    stack = _call_stack_var.get()
    if stack:
        stack.pop()
        _call_stack_var.set(stack)

def get_current_call_stack(self) -> List[CallStackEntry]:
    """Get current call stack (for error messages)"""
    return _call_stack_var.get().copy()
```

### 4.3 Decorator Pattern for Auto-Validation

**@with_path_validation Decorator**:

```python
def with_path_validation(capability_id: str):
    """
    Decorator to automatically validate path before capability execution.

    Usage:
        @with_path_validation("action.execute.local")
        def execute_local_command(command: str, agent_id: str):
            # Implementation
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract agent_id from kwargs
            agent_id = kwargs.get("agent_id") or args[0] if args else None

            # Parse capability domain
            domain_str, _, _ = capability_id.split(".", 2)
            domain = CapabilityDomain(domain_str.upper())

            # Get current domain from call stack
            validator = get_path_validator()
            call_stack = validator.get_current_call_stack()
            from_domain = call_stack[-1].domain if call_stack else None

            # Validate if not first call
            if from_domain:
                validator.validate_call(
                    from_domain=from_domain,
                    to_domain=domain,
                    agent_id=agent_id,
                    capability_id=capability_id,
                    operation=func.__name__,
                )

            # Push call to stack
            validator.push_call(CallStackEntry(
                domain=domain,
                capability_id=capability_id,
                operation=func.__name__,
                agent_id=agent_id,
                timestamp_ms=utc_now_ms(),
            ))

            try:
                # Execute function
                result = func(*args, **kwargs)
                return result
            finally:
                # Pop call from stack
                validator.pop_call()

        return wrapper
    return decorator
```

**Usage Example**:

```python
@with_path_validation("action.execute.local")
def execute_local_command(
    command: str,
    agent_id: str,
    context: Dict[str, Any],
) -> ActionExecutionResult:
    """
    Execute local command.

    PathValidator automatically checks if this call is allowed
    based on the current call stack.
    """
    # Implementation
    pass
```

---

## Chapter 5: PathValidator源码解析

### 5.1 Core Data Structures

**CallStackEntry**:

```python
@dataclass
class CallStackEntry:
    """
    Represents a single call in the call stack.

    Used by PathValidator to track execution flow.
    """
    domain: CapabilityDomain       # Which domain
    capability_id: str             # Full capability ID
    operation: str                 # Operation name
    agent_id: str                  # Who invoked it
    timestamp_ms: int              # When invoked
    context: Dict[str, Any] = field(default_factory=dict)
```

**PathValidationResult**:

```python
@dataclass
class PathValidationResult:
    """Result of path validation"""
    is_allowed: bool               # Validation passed?
    from_domain: CapabilityDomain  # Source domain
    to_domain: CapabilityDomain    # Target domain
    capability_id: str             # Capability being called
    violated_rule: Optional[str] = None  # If denied, which rule
    reason: Optional[str] = None   # Human-readable reason
```

### 5.2 Golden Path Rules Definition

**GOLDEN_PATH_RULES Dictionary**:

```python
GOLDEN_PATH_RULES = {
    # STATE domain can call:
    CapabilityDomain.STATE: {
        CapabilityDomain.DECISION,    # Can invoke decisions
        CapabilityDomain.GOVERNANCE,  # Can check governance
        CapabilityDomain.EVIDENCE,    # Can record evidence
    },

    # DECISION domain can call:
    CapabilityDomain.DECISION: {
        CapabilityDomain.STATE,       # Can read state
        CapabilityDomain.GOVERNANCE,  # Can check governance
        CapabilityDomain.EVIDENCE,    # Can record evidence
        # CANNOT call ACTION!
    },

    # ACTION domain can call:
    CapabilityDomain.ACTION: {
        CapabilityDomain.GOVERNANCE,  # MUST check governance
        CapabilityDomain.EVIDENCE,    # MUST record evidence
        # CANNOT call STATE or DECISION directly
    },

    # GOVERNANCE domain can call:
    CapabilityDomain.GOVERNANCE: {
        CapabilityDomain.STATE,       # Can read state
        CapabilityDomain.DECISION,    # Can read decisions
        CapabilityDomain.ACTION,      # Can approve actions
        CapabilityDomain.EVIDENCE,    # Can record evidence
    },

    # EVIDENCE domain can call:
    CapabilityDomain.EVIDENCE: {
        CapabilityDomain.EVIDENCE,    # Only itself (immutable)
    },
}
```

**FORBIDDEN_PATHS Set**:

```python
FORBIDDEN_PATHS = {
    # Explicitly forbidden paths (fail-fast)
    ("decision", "action"),      # ❌ Decision CANNOT trigger Action
    ("action", "state"),         # ❌ Action CANNOT modify State directly
    ("evidence", "state"),       # ❌ Evidence is write-only
    ("evidence", "decision"),    # ❌ Evidence is write-only
    ("evidence", "action"),      # ❌ Evidence is write-only
    ("evidence", "governance"),  # ❌ Evidence is write-only
}
```

### 5.3 Performance Optimization

**Why <5ms Validation?**

PathValidator uses several optimizations:

**1. Hash-based Lookups** (O(1)):
```python
# Not a list search (O(n))
if to_domain in allowed_domains:  # O(1) set lookup
```

**2. Minimal Database Writes**:
```python
# Log validation asynchronously (non-blocking)
def _log_validation(self, ...):
    self._log_queue.put({
        "from_domain": from_domain,
        "to_domain": to_domain,
        "is_allowed": is_allowed,
        "timestamp_ms": utc_now_ms(),
    })
    # Background thread writes to DB
```

**3. In-Memory Call Stack**:
```python
# Use contextvars (thread-local storage)
_call_stack_var: ContextVar[List[CallStackEntry]]
# No database query needed!
```

**4. Early Exit**:
```python
# Check forbidden paths first (fast fail)
if (from_domain, to_domain) in FORBIDDEN_PATHS:
    raise PathValidationError(...)  # Exit immediately
```

### 5.4 Testing PathValidator

**Unit Test Example**:

```python
def test_decision_cannot_call_action():
    """Test that decision→action is blocked"""
    validator = PathValidator()
    validator.start_session("test-session")

    # Push decision onto call stack
    validator.push_call(CallStackEntry(
        domain=CapabilityDomain.DECISION,
        capability_id="decision.plan.create",
        operation="create_plan",
        agent_id="test_agent",
        timestamp_ms=utc_now_ms(),
    ))

    # Attempt to call action
    with pytest.raises(PathValidationError) as exc_info:
        validator.validate_call(
            from_domain=CapabilityDomain.DECISION,
            to_domain=CapabilityDomain.ACTION,
            agent_id="test_agent",
            capability_id="action.execute.local",
            operation="execute",
        )

    # Verify error message
    assert "decision → action is forbidden" in str(exc_info.value)
    assert exc_info.value.violated_rule == "decision→action_forbidden"

    validator.end_session()
```

---

## Chapter 6: Evidence系统设计

### 6.1 Evidence Collection Architecture

**Automatic Collection**:

Every capability invocation automatically generates evidence:

```
┌─────────────────────────────────────────┐
│        Capability Invocation            │
├─────────────────────────────────────────┤
│ 1. ActionExecutor.execute()             │
│    ↓                                    │
│ 2. Governance.check_permission()        │
│    ↓                                    │
│ 3. Execute operation                    │
│    ↓                                    │
│ 4. EvidenceCollector.collect()          │ ← Automatic!
│    ├─ Compute SHA256 hash              │
│    ├─ Write to evidence_log table      │
│    └─ Return evidence_id               │
│    ↓                                    │
│ 5. Return result with evidence_id      │
└─────────────────────────────────────────┘
```

**Why Automatic?**

Manual evidence collection is error-prone:
- Developers might forget to call `collect()`
- Inconsistent evidence across capabilities
- Security gaps (missing audit trail)

Automatic collection ensures:
- ✅ 100% coverage
- ✅ Consistent format
- ✅ No gaps in audit trail

### 6.2 Evidence Data Model

**Evidence Schema**:

```sql
CREATE TABLE evidence_log (
    evidence_id TEXT PRIMARY KEY,              -- ULID
    operation_type TEXT NOT NULL,              -- state|decision|action|governance
    operation_id TEXT NOT NULL,                -- Unique operation ID
    capability_id TEXT NOT NULL,               -- Capability invoked
    agent_id TEXT NOT NULL,                    -- Who invoked
    params_json TEXT NOT NULL,                 -- Input params (JSON)
    result_json TEXT NOT NULL,                 -- Result (JSON)
    side_effects_json TEXT,                    -- Side effects (JSON, nullable)
    timestamp_ms INTEGER NOT NULL,             -- When invoked
    provenance_json TEXT,                      -- Provenance metadata
    integrity_content_hash TEXT NOT NULL,      -- SHA256 hash
    integrity_signature TEXT,                  -- Digital signature (optional)
    created_at_ms INTEGER NOT NULL,

    -- Indexes for fast queries
    INDEX idx_evidence_agent (agent_id),
    INDEX idx_evidence_capability (capability_id),
    INDEX idx_evidence_timestamp (timestamp_ms),
    INDEX idx_evidence_operation (operation_type, operation_id)
);

-- Triggers to prevent modification/deletion
CREATE TRIGGER prevent_evidence_modification
BEFORE UPDATE ON evidence_log
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Evidence is immutable and cannot be modified');
END;

CREATE TRIGGER prevent_evidence_deletion
BEFORE DELETE ON evidence_log
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Evidence cannot be deleted');
END;
```

### 6.3 Integrity Verification

**SHA256 Hash Calculation**:

```python
def compute_hash(evidence: Evidence) -> str:
    """
    Compute SHA256 hash of evidence content.

    Hash includes:
    - operation_type
    - operation_id
    - capability_id
    - agent_id
    - params_json (sorted keys)
    - result_json (sorted keys)
    - timestamp_ms

    Excludes:
    - evidence_id (generated after hash)
    - integrity_content_hash (self-reference)
    - integrity_signature (computed after hash)
    """
    content = {
        "operation_type": evidence.operation_type.value,
        "operation_id": evidence.operation_id,
        "capability_id": evidence.capability_id,
        "agent_id": evidence.agent_id,
        "params": evidence.params,
        "result": evidence.result,
        "timestamp_ms": evidence.timestamp_ms,
    }

    # Serialize with sorted keys (deterministic)
    content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))

    # Compute SHA256
    hash_obj = hashlib.sha256(content_str.encode('utf-8'))
    return hash_obj.hexdigest()
```

**Verification**:

```python
def verify_integrity(evidence: Evidence) -> bool:
    """
    Verify evidence integrity.

    Returns:
        True if hash matches, False otherwise

    Raises:
        EvidenceIntegrityError: If hash mismatch (severe)
    """
    stored_hash = evidence.integrity.content_hash
    computed_hash = compute_hash(evidence)

    if stored_hash != computed_hash:
        raise EvidenceIntegrityError(
            f"Evidence {evidence.evidence_id} integrity compromised!\n"
            f"Stored hash: {stored_hash}\n"
            f"Computed hash: {computed_hash}"
        )

    return True
```

### 6.4 Evidence Chains

**Chain Data Model**:

```sql
CREATE TABLE evidence_chains (
    chain_id TEXT PRIMARY KEY,
    decision_id TEXT,        -- Plan ID from DECISION domain
    action_id TEXT,          -- Execution ID from ACTION domain
    memory_id TEXT,          -- Memory ID from STATE domain
    links_json TEXT NOT NULL, -- Array of links
    created_at_ms INTEGER NOT NULL,

    INDEX idx_chain_decision (decision_id),
    INDEX idx_chain_action (action_id),
    INDEX idx_chain_memory (memory_id)
);

CREATE TABLE evidence_chain_links (
    link_id TEXT PRIMARY KEY,
    chain_id TEXT NOT NULL,
    from_id TEXT NOT NULL,   -- Source evidence ID
    to_id TEXT NOT NULL,     -- Target evidence ID
    relationship TEXT NOT NULL, -- caused_by|resulted_in|modified|...
    created_at_ms INTEGER NOT NULL,

    INDEX idx_chain_link_from (from_id),
    INDEX idx_chain_link_to (to_id),
    FOREIGN KEY (chain_id) REFERENCES evidence_chains(chain_id)
);
```

**Building Chains**:

```python
def link(
    self,
    decision_id: str,
    action_id: str,
    memory_id: Optional[str] = None,
) -> str:
    """
    Build evidence chain: decision → action → memory

    Args:
        decision_id: Plan ID from decision.plan.create
        action_id: Execution ID from action.execute
        memory_id: Memory ID from state.memory.write (optional)

    Returns:
        Chain ID

    Example:
        chain_id = link_graph.link(
            decision_id="plan-123",
            action_id="exec-456",
            memory_id="mem-789",
        )

        # Chain structure:
        # plan-123 --caused_by--> exec-456 --resulted_in--> mem-789
    """
    chain_id = f"chain-{ULID()}"

    # Create links
    links = [
        EvidenceChainLink(
            link_id=f"link-{ULID()}",
            chain_id=chain_id,
            from_id=decision_id,
            to_id=action_id,
            relationship=ChainRelationship.CAUSED_BY,
            created_at_ms=utc_now_ms(),
        ),
    ]

    if memory_id:
        links.append(EvidenceChainLink(
            link_id=f"link-{ULID()}",
            chain_id=chain_id,
            from_id=action_id,
            to_id=memory_id,
            relationship=ChainRelationship.RESULTED_IN,
            created_at_ms=utc_now_ms(),
        ))

    # Persist chain
    self._save_chain(chain_id, links)

    return chain_id
```

---

## Chapter 7: Agent开发最佳实践

### 7.1 Agent Profile Design

**Principle of Least Privilege**:

Grant minimum permissions needed:

```python
# BAD: Overly permissive
{
    "state.*": "admin",        # Too broad!
    "decision.*": "admin",
    "action.*": "admin",
    "governance.*": "admin",
}

# GOOD: Specific permissions
{
    "state.memory.read": "read",
    "state.memory.write": "propose",  # Requires approval
    "decision.plan.create": "write",
    "decision.plan.freeze": "write",
    "action.*": "none",  # No execution
}
```

**Progressive Permission Model**:

Start restrictive, upgrade as needed:

```python
# Day 1: Chat agent (restrictive)
chat_agent_v1 = {
    "state.memory.read": "read",
    "state.memory.write": "propose",  # Human approval
    "decision.*": "write",
    "action.*": "none",  # No execution
}

# Week 2: After validation, upgrade
chat_agent_v2 = {
    "state.memory.read": "read",
    "state.memory.write": "write",  # Direct write (validated)
    "decision.*": "write",
    "action.execute.local": "propose",  # Can propose actions
}

# Month 1: After extensive validation
chat_agent_v3 = {
    "state.memory.read": "read",
    "state.memory.write": "write",
    "decision.*": "write",
    "action.execute.local": "write",  # Can execute (with governance)
}
```

### 7.2 Error Handling

**Graceful Degradation**:

```python
def execute_with_fallback(agent_id: str, capability_id: str):
    """
    Execute with fallback if permission denied.
    """
    try:
        # Attempt execution
        result = executor.execute(
            capability_id=capability_id,
            params={...},
            agent_id=agent_id,
        )
        return result

    except PermissionDeniedError as e:
        # Fallback 1: Request override
        override_request = override_mgr.request_override(
            agent_id=agent_id,
            capability_id=capability_id,
            reason=f"Needed for task completion: {e}",
        )
        return {"status": "pending_approval", "request_id": override_request.request_id}

    except BudgetExceededError as e:
        # Fallback 2: Use cheaper alternative
        logger.warning(f"Budget exceeded, using cheaper alternative: {e}")
        return execute_cheaper_alternative(agent_id)

    except ActionExecutionError as e:
        # Fallback 3: Attempt rollback
        logger.error(f"Execution failed, attempting rollback: {e}")
        rollback_result = executor.rollback(execution_id=e.execution_id)
        return {"status": "failed_and_rolled_back", "rollback": rollback_result}
```

### 7.3 Testing Agents

**Unit Test Template**:

```python
def test_agent_capability_profile():
    """Test agent has correct capabilities"""
    agent = agent_registry.get_agent("test_agent")

    # Verify expected capabilities
    assert agent.has_capability("state.memory.read")
    assert agent.get_permission_level("state.memory.read") == PermissionLevel.READ

    # Verify forbidden capabilities
    assert not agent.has_capability("action.execute.local")
    assert agent.get_permission_level("action.execute.local") == PermissionLevel.NONE

def test_agent_respects_governance():
    """Test agent respects governance checks"""
    governance = GovernanceEngine()

    # Agent should be denied for action execution
    result = governance.check_permission(
        agent_id="chat_agent",
        capability_id="action.execute.local",
        context={"task_id": "task-test"},
    )

    assert not result.is_granted
    assert "lacks WRITE permission" in result.reason
```

---

## Chapter 8: 新Capability开发指南

### 8.1 Capability Development Checklist

**Before Implementation**:
- [ ] Choose correct domain (STATE/DECISION/ACTION/GOVERNANCE/EVIDENCE)
- [ ] Define capability ID following convention (domain.component.operation)
- [ ] Determine default permission level (NONE/READ/PROPOSE/WRITE/ADMIN)
- [ ] Assess risk tier (T1/T2/T3)
- [ ] Decide if frozen plan required
- [ ] Decide if governance check required
- [ ] Decide if evidence collection required
- [ ] Define rollback plan (if ACTION domain)

**During Implementation**:
- [ ] Implement core logic
- [ ] Add @with_path_validation decorator
- [ ] Add governance check (if required)
- [ ] Add evidence collection (if required)
- [ ] Implement rollback (if ACTION domain)
- [ ] Write unit tests (>80% coverage)
- [ ] Write integration tests (Golden Path)
- [ ] Document API (docstrings)
- [ ] Add to CapabilityRegistry

**After Implementation**:
- [ ] Register capability in registry
- [ ] Update agent profiles to use new capability
- [ ] Add to governance policies
- [ ] Update documentation
- [ ] Run performance benchmarks

### 8.2 Example: Creating state.cache.read

**Step 1: Define Capability**

```python
# File: agentos/core/capability/domains/state/cache_service.py

from agentos.core.capability.decorators import with_path_validation
from agentos.core.capability.models import CapabilityDomain

class CacheService:
    """Cache management service"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    @with_path_validation("state.cache.read")
    def read_cache(
        self,
        key: str,
        agent_id: str,
    ) -> Optional[Any]:
        """
        Read from cache.

        Args:
            key: Cache key
            agent_id: Agent ID (for permission check)

        Returns:
            Cached value or None if not found

        Raises:
            PermissionDeniedError: If agent lacks READ permission
        """
        # Check permission (via decorator)
        # This is automatic via @with_path_validation

        # Implementation
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT value_json FROM cache WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])
        return None
```

**Step 2: Register Capability**

```python
# File: agentos/core/capability/capability_registry.py

from agentos.core.capability.models import (
    CapabilityDefinition,
    CapabilityDomain,
    PermissionLevel,
    RiskTier,
    AuditLevel,
)

# Register in _register_defaults()
def _register_defaults(self):
    # ... existing registrations ...

    # Register state.cache.read
    self.register_capability(CapabilityDefinition(
        capability_id="state.cache.read",
        domain=CapabilityDomain.STATE,
        name="Read Cache",
        description="Read value from cache",
        version="1.0.0",
        default_permission=PermissionLevel.READ,
        requires_frozen_plan=False,
        requires_governance_check=False,
        risk_tier=RiskTier.T1,  # Low risk
        audit_level=AuditLevel.BASIC,
        requires_evidence=True,
        max_execution_time_ms=1000,  # 1 second
        rate_limit_per_hour=10000,  # 10k reads/hour
        created_by="system",
        created_at_ms=utc_now_ms(),
    ))
```

**Step 3: Write Tests**

```python
# File: tests/unit/core/capability/state/test_cache_service.py

def test_cache_read_with_permission():
    """Test cache read with READ permission"""
    cache_service = CacheService(db_path="test.db")

    # Write cache value
    cache_service.write_cache(key="test_key", value="test_value", agent_id="admin")

    # Read with permission
    value = cache_service.read_cache(key="test_key", agent_id="read_agent")

    assert value == "test_value"

def test_cache_read_without_permission():
    """Test cache read denied without permission"""
    cache_service = CacheService(db_path="test.db")

    # Agent without READ permission
    with pytest.raises(PermissionDeniedError):
        cache_service.read_cache(key="test_key", agent_id="no_permission_agent")
```

**Step 4: Update Documentation**

```python
# Add to STATE Domain API section in developer guide
```

---

## Chapter 9: Policy编写和测试

### 9.1 Policy Structure

**Policy Schema**:

```python
{
    "policy_id": "prod_security_policy",
    "name": "Production Security Policy",
    "description": "Strict security controls for production environment",
    "version": "1.0.0",
    "enabled": True,
    "priority": 100,  # Higher priority = evaluated first
    "rules": [
        {
            "rule_id": "rule-1",
            "name": "Block chat agents from executing actions",
            "capability_pattern": "action.*",  # Matches all action capabilities
            "agent_pattern": "chat_*",         # Matches all chat agents
            "permission_level": "none",        # Deny
            "reason": "Chat agents lack execution privileges",
        },
        {
            "rule_id": "rule-2",
            "name": "Require approval for production deployments",
            "capability_pattern": "action.deploy.production",
            "agent_pattern": "*",              # Matches all agents
            "permission_level": "propose",     # Require approval
            "constraints": {
                "requires_frozen_plan": True,
                "requires_tests_passing": True,
                "max_risk_score": 70,
            },
        },
    ],
    "metadata": {
        "environment": "production",
        "owner": "security_team",
        "review_date": "2026-03-01",
    },
}
```

### 9.2 Testing Policies

**Policy Test Template**:

```python
def test_policy_blocks_chat_agent_execution():
    """Test that policy blocks chat agents from executing actions"""
    policy_registry = PolicyRegistry()

    # Register policy
    policy_registry.register_policy({
        "policy_id": "test_policy",
        "rules": [
            {
                "capability_pattern": "action.*",
                "agent_pattern": "chat_*",
                "permission_level": "none",
            }
        ],
    })

    # Create governance engine with policy
    governance = GovernanceEngine(policy_registry=policy_registry)

    # Test permission check
    result = governance.check_permission(
        agent_id="chat_agent_001",
        capability_id="action.execute.local",
        context={},
    )

    assert not result.is_granted
    assert "chat agents lack execution privileges" in result.reason.lower()
```

---

## Chapter 10: 性能优化建议

### 10.1 Database Optimization

**Indexes**:

```sql
-- Evidence table indexes
CREATE INDEX idx_evidence_agent ON evidence_log(agent_id);
CREATE INDEX idx_evidence_capability ON evidence_log(capability_id);
CREATE INDEX idx_evidence_timestamp ON evidence_log(timestamp_ms);

-- Path validation indexes
CREATE INDEX idx_path_session ON path_validation_log(session_id);
CREATE INDEX idx_path_domains ON path_validation_log(from_domain, to_domain);

-- Chain indexes
CREATE INDEX idx_chain_decision ON evidence_chains(decision_id);
CREATE INDEX idx_chain_action ON evidence_chains(action_id);
```

**Vacuum Schedule**:

```python
# Clean up old logs (>90 days)
def vacuum_old_data():
    cutoff_ms = utc_now_ms() - (90 * 24 * 3600 * 1000)

    # Archive old evidence
    archive_evidence_older_than(cutoff_ms)

    # Delete old validation logs
    delete_validation_logs_older_than(cutoff_ms)

    # Run VACUUM
    conn.execute("VACUUM")
```

### 10.2 Caching Strategies

**Capability Registry Cache**:

```python
class CapabilityRegistry:
    def __init__(self):
        self._cache = {}  # In-memory cache

    def get_capability(self, capability_id: str) -> CapabilityDefinition:
        # Check cache first
        if capability_id in self._cache:
            return self._cache[capability_id]

        # Query database
        capability = self._query_db(capability_id)

        # Cache result
        self._cache[capability_id] = capability

        return capability
```

**Agent Profile Cache**:

```python
# Cache agent profiles for 5 minutes
@lru_cache(maxsize=1000, ttl=300)
def get_agent_profile(agent_id: str) -> AgentProfile:
    return agent_registry.query_profile(agent_id)
```

### 10.3 Performance Targets Summary

| Operation | Target | Optimization |
|-----------|--------|--------------|
| PathValidator.validate | <5ms | Hash lookups, in-memory stack |
| Registry.get_capability | <1ms | In-memory cache |
| Governance.check_permission | <2ms | Cached profiles, indexed queries |
| Governance.calculate_risk | <10ms | Optimized scoring algorithm |
| Evidence.collect | <20ms | Async writes, batching |
| Golden Path E2E | <100ms | Parallel governance checks |

---

## Chapter 11: 扩展点和插件系统

### 11.1 Custom Capability Domains

**Extending with Custom Domain**:

```python
# Add custom domain to enum
class CapabilityDomain(Enum):
    STATE = "state"
    DECISION = "decision"
    ACTION = "action"
    GOVERNANCE = "governance"
    EVIDENCE = "evidence"
    CUSTOM = "custom"  # Your custom domain

# Define custom capabilities
custom_capability = CapabilityDefinition(
    capability_id="custom.ml_model.train",
    domain=CapabilityDomain.CUSTOM,
    name="Train ML Model",
    description="Train machine learning model on dataset",
    # ... other fields
)

# Register
registry.register_capability(custom_capability)
```

### 11.2 Plugin Architecture

**Plugin Interface**:

```python
class CapabilityPlugin(ABC):
    """Base class for capability plugins"""

    @abstractmethod
    def get_capabilities(self) -> List[CapabilityDefinition]:
        """Return list of capabilities provided by this plugin"""
        pass

    @abstractmethod
    def execute(
        self,
        capability_id: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """Execute capability"""
        pass

# Example plugin
class MLModelPlugin(CapabilityPlugin):
    def get_capabilities(self):
        return [
            CapabilityDefinition(
                capability_id="custom.ml_model.train",
                # ...
            ),
            CapabilityDefinition(
                capability_id="custom.ml_model.predict",
                # ...
            ),
        ]

    def execute(self, capability_id, params, context):
        if capability_id == "custom.ml_model.train":
            return self._train_model(params)
        elif capability_id == "custom.ml_model.predict":
            return self._predict(params)

# Register plugin
plugin_manager.register_plugin(MLModelPlugin())
```

---

## Chapter 12: 安全考虑和合规性

### 12.1 Security Best Practices

**1. Input Validation**:

```python
def execute_local_command(command: str):
    # Validate command
    if not is_safe_command(command):
        raise UnsafeCommandError(f"Command contains unsafe patterns: {command}")

    # Sanitize paths
    if ".." in command or command.startswith("/"):
        raise UnsafeCommandError(f"Path traversal attempt: {command}")

    # Execute
    ...
```

**2. SQL Injection Prevention**:

```python
# WRONG: String concatenation
query = f"SELECT * FROM evidence WHERE agent_id = '{agent_id}'"

# CORRECT: Parameterized queries
query = "SELECT * FROM evidence WHERE agent_id = ?"
cursor.execute(query, (agent_id,))
```

**3. Least Privilege**:

```python
# Grant minimum required permissions
agent_profile = {
    "state.memory.read": "read",   # Not "write" or "admin"
    "action.execute.local": "none",  # Explicitly deny
}
```

### 12.2 Compliance Support

**SOX Compliance**:
- ✅ Complete audit trail (Evidence system)
- ✅ Immutable records (Evidence cannot be modified/deleted)
- ✅ Approval workflows (Override system)
- ✅ Separation of duties (Permission levels)

**GDPR Compliance**:
- ✅ Data processing logs (Evidence records)
- ✅ Right to access (Evidence export)
- ✅ Data minimization (Scoped memory)
- ✅ Consent tracking (Decision evidence)

**HIPAA Compliance**:
- ✅ Access logs (Evidence by agent)
- ✅ Encryption (at rest and in transit)
- ✅ Audit trails (Comprehensive evidence)
- ✅ Role-based access (Permission levels)

**ISO 27001 Compliance**:
- ✅ Access control (Agent capability profiles)
- ✅ Change management (Evidence chains)
- ✅ Incident response (Rollback engine)
- ✅ Risk management (Risk calculator)

---

## Appendix: API Reference Card

### Quick Reference

**Import Statements**:
```python
from agentos.core.capability.capability_registry import CapabilityRegistry
from agentos.core.capability.path_validator import PathValidator
from agentos.core.capability.domains.state import MemoryService, ContextService
from agentos.core.capability.domains.decision import PlanService, OptionEvaluator, DecisionJudge
from agentos.core.capability.domains.action import ActionExecutor, RollbackEngine
from agentos.core.capability.domains.governance import GovernanceEngine, PolicyRegistry
from agentos.core.capability.domains.evidence import EvidenceCollector, EvidenceLinkGraph
```

**Common Operations**:
```python
# Registry
registry = CapabilityRegistry()
capability = registry.get_capability("state.memory.read")

# Path Validator
validator = PathValidator()
validator.start_session("session-123")
validator.validate_call(from_domain, to_domain, agent_id, capability_id, operation)
validator.end_session()

# Governance
governance = GovernanceEngine()
permission = governance.check_permission(agent_id, capability_id, context)
risk = governance.calculate_risk_score(agent_id, capability_id, context)

# Evidence
collector = EvidenceCollector()
evidence_id = collector.collect(operation_type, operation_id, capability_id, params, result, context)
evidence = collector.get_evidence(evidence_id)
evidence_list = collector.query_by_agent(agent_id)
```

---

**Document Version**: 3.0.0
**Last Updated**: 2026-02-01
**Next Review**: 2026-03-01
