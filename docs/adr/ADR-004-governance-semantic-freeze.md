# ADR-004: Governance Semantic Freeze

**Status**: Accepted
**Date**: 2026-01-28
**Deciders**: Architecture Team
**Related**: ADR-001 (Supervisor Architecture), ADR-002 (Audit Trail), ADR-003 (Guardian Workflow)

---

## Context

After implementing the Governance system (Supervisor, Guardian, Lead Agent, Decision Replay), we need to establish immutable semantic contracts to prevent architectural drift and ensure long-term maintainability.

## Decision

We establish **FOUR semantic freezes** that MUST NOT be violated in future development:

---

### F-1: Governance Replay Semantic Freeze

**Core Definition**: Replay = Explain "Why it happened"

#### ✅ Allowed:
- Query historical decision trace
- Calculate statistics (TopN, percentiles)
- Generate audit reports
- Provide evidence chains

#### ❌ Forbidden:
- **NOT Debug**: Replay is not a debugging tool for runtime issues
- **NOT Recomputation**: Never recalculate decisions with new logic
- **NOT Retroactive Judgment**: Cannot change past decisions ("事后改判")
- **NOT What-if Analysis**: No hypothetical scenario simulation

#### Enforcement:
```python
# All replay operations are READ-ONLY
class TraceAssembler:
    """
    SEMANTIC FREEZE (F-1):
    - Replay explains WHY decisions were made
    - NEVER modifies past decisions
    - NEVER recalculates with new policy
    """
    def get_decision_trace(self, task_id: str) -> list[TraceItem]:
        # READ-ONLY: Query frozen snapshots
        pass
```

#### Rationale:
- **Auditability**: Past decisions must remain immutable for compliance
- **Trust**: Users must trust that history won't be rewritten
- **Reproducibility**: Same query always returns same historical truth

---

### F-2: Guardian Workflow State Freeze

**Core Definition**: Guardian produces verdicts, Supervisor applies state changes

#### State Transition Contract:
```
RUNNING → VERIFYING → GUARD_REVIEW → VERIFIED (or BLOCKED)
```

#### ✅ Allowed:
- Guardian reads task state
- Guardian produces `GuardianVerdictSnapshot` (frozen)
- Supervisor applies verdict to update task state

#### ❌ Forbidden:
- **Guardian NEVER directly modifies task state**
- **NO parallel state modification paths**
- **NO Guardian direct DB writes to tasks table**

#### Enforcement:
```python
# Guardian can only return verdicts
class Guardian(ABC):
    """
    SEMANTIC FREEZE (F-2):
    - Guardian NEVER modifies task state directly
    - Guardian ONLY produces frozen VerdictSnapshot
    - Supervisor is the SOLE state writer
    """
    @abstractmethod
    def verify(self, task: Task) -> GuardianVerdictSnapshot:
        """Returns verdict. NEVER modifies task."""
        pass
```

#### Rationale:
- **Separation of Concerns**: Clear boundary between verification and state management
- **Single Writer**: Prevents race conditions and inconsistent state
- **Auditability**: All state changes traced to Supervisor decisions

---

### F-3: Lead Agent Behavior Freeze

**Core Definition**: Lead Agent is read-only risk miner

#### ✅ Allowed:
- Read historical governance data (task_audits, events)
- Detect risk patterns
- Produce `LeadFinding` records
- Create follow-up tasks for human review

#### ❌ Forbidden:
- **NEVER modify business data** (tasks, sessions, etc.)
- **NEVER auto-fix detected issues**
- **NEVER apply remediation actions**
- **NEVER change system configuration**

#### Enforcement:
```python
class LeadMiner:
    """
    SEMANTIC FREEZE (F-3):
    - Read-only historical data access
    - Produces findings ONLY
    - Creates follow-up tasks for human action
    - NEVER auto-remediates
    """
    def scan(self, window: ScanWindow) -> list[LeadFinding]:
        # READ-ONLY: Query historical data
        # Returns findings, NEVER modifies system
        pass
```

#### Rationale:
- **Safety**: Prevents autonomous system modification
- **Human-in-Loop**: Critical changes require human approval
- **Transparency**: All actions are explicit follow-up tasks

---

### F-4: Decision Audit as Single Source of Truth

**Core Definition**: `task_audits` table + `DecisionSnapshot` = Authoritative source

#### ✅ Allowed:
- Query `task_audits` for governance data
- Derive metrics from decision snapshots
- Use `decision_id` as primary key for replay

#### ❌ Forbidden:
- **NO parallel audit systems** (e.g., separate "shadow audit" table)
- **NO dual-write patterns** (writing same data to multiple tables)
- **NO audit data inference** (reconstructing audit from events)

#### Enforcement:
```sql
-- Single authoritative table
CREATE TABLE task_audits (
    id INTEGER PRIMARY KEY,
    task_id TEXT NOT NULL,
    decision_id TEXT UNIQUE,  -- Authoritative decision ID
    audit_json TEXT NOT NULL,  -- Frozen DecisionSnapshot
    ...
);

-- All replay queries go through task_audits
SELECT * FROM task_audits WHERE decision_id = ?;
```

#### Rationale:
- **Single Source of Truth**: No confusion about which data is authoritative
- **Consistency**: Prevents divergence between multiple audit sources
- **Performance**: Optimized indices on one table, not scattered across many

---

## Consequences

### Positive:
- **Architectural Clarity**: Clear contracts prevent future confusion
- **Maintainability**: Easier to onboard new developers with frozen semantics
- **Security**: Read-only contracts prevent accidental system modification
- **Compliance**: Immutable audit trail meets regulatory requirements

### Negative:
- **Flexibility Loss**: Cannot add "convenient shortcuts" that violate contracts
- **Initial Overhead**: Developers must learn semantic contracts
- **Refactoring Constraints**: Future changes must respect frozen semantics

### Mitigation:
- Document all semantic freezes in code comments
- Add runtime assertions to detect contract violations
- Include freeze validation in CI/CD pipeline

---

## Validation

### Code-Level Enforcement:
```python
# Example: Runtime assertion for F-2
@dataclass(frozen=True)
class GuardianVerdictSnapshot:
    """
    SEMANTIC FREEZE (F-2): Guardian verdicts are immutable.
    Attempting to modify this object will raise FrozenInstanceError.
    """
    verdict_id: str
    status: VerdictStatus
    ...

# Example: Type system enforcement for F-3
class LeadMiner:
    def scan(self, window: ScanWindow) -> list[LeadFinding]:
        """
        SEMANTIC FREEZE (F-3): Returns findings ONLY.
        This method MUST NOT have side effects on business data.
        """
        # All queries use READ-ONLY DB connections
        with self.storage.readonly_cursor() as cursor:
            ...
```

### Documentation Enforcement:
- All ADRs reference semantic freezes
- API documentation includes freeze warnings
- Runbooks highlight frozen contracts

### Review Enforcement:
- Code review checklist includes "Does this violate semantic freeze?"
- CI/CD pipeline runs freeze validation tests
- Architecture review for any freeze-adjacent changes

---

## Rejection Criteria

A proposed change MUST BE REJECTED if it:
1. Allows Replay to modify past decisions (violates F-1)
2. Allows Guardian to directly modify task state (violates F-2)
3. Allows Lead Agent to auto-remediate issues (violates F-3)
4. Creates parallel audit systems (violates F-4)

**No exceptions.** Semantic freezes are architectural invariants.

---

## Related Documents
- [RELEASE_NOTES.md](../../RELEASE_NOTES.md) - User-facing freeze documentation
- [Supervisor Runbook](../governance/supervisor_runbook.md) - Operational guidelines
- [Guardian Verification Runbook](../governance/verification_runbook.md) - Guardian contracts
- [Lead Agent Runbook](../governance/lead_runbook.md) - Lead Agent behavior
- [Decision Replay API](../governance/decision_replay_api.md) - API contracts

---

## Amendments

None. This ADR establishes frozen semantics and MUST NOT be amended.

If business requirements change, create a NEW ADR that explicitly addresses the conflict and provides alternative architecture within freeze constraints.
