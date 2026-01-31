# Migration Guide: v2.0 → v3.0

**Version**: 3.0.0
**Last Updated**: 2026-02-01
**Migration Difficulty**: Medium (8 weeks recommended)

---

## Executive Summary

**AgentOS v3.0 introduces OS-Level Capability Governance** - a fundamental architectural change that requires careful migration planning.

**Key Changes**:
- ✅ Agent definitions → Capability profiles
- ✅ Implicit permissions → Explicit capability grants
- ✅ Ad-hoc execution → Golden Path enforcement
- ✅ Optional audit → Mandatory evidence collection
- ✅ Memory v1.0 → Memory v2.0 (backward compatible)

**Migration Timeline**: 8 weeks
**Rollback Support**: Yes (with caveats)
**Breaking Changes**: 12 identified
**Compatibility Mode**: Available for 6 months

---

## Chapter 1: v2→v3核心变更

### 1.1 Architecture Changes

**v2.0 Architecture** (Before):
```
┌─────────────────────────────────────────┐
│           AgentOS v2.0                   │
├─────────────────────────────────────────┤
│  Chat → Task → Executor → Memory        │
│                                          │
│  - Implicit permissions                 │
│  - Role-based access                    │
│  - Optional audit                       │
│  - No domain boundaries                 │
└─────────────────────────────────────────┘
```

**v3.0 Architecture** (After):
```
┌─────────────────────────────────────────┐
│           AgentOS v3.0                   │
├─────────────────────────────────────────┤
│  STATE → DECISION → GOVERNANCE →        │
│  ACTION → STATE → EVIDENCE              │
│                                          │
│  - Explicit capabilities                │
│  - Capability-based permissions         │
│  - Mandatory evidence                   │
│  - Strict domain boundaries             │
│  - Golden Path enforcement              │
└─────────────────────────────────────────┘
```

### 1.2 Permission Model Changes

**v2.0**: Role-based access control
```python
# v2.0 (OLD)
agent = {
    "agent_id": "chat_agent",
    "role": "assistant",  # Implicit permissions
}

# Role "assistant" grants:
# - Read memory
# - Propose changes
# - Cannot execute
```

**v3.0**: Capability-based access control
```python
# v3.0 (NEW)
agent = {
    "agent_id": "chat_agent",
    "capability_profile": {
        "state.memory.read": {"permission_level": "read"},
        "state.memory.write": {"permission_level": "propose"},
        "decision.plan.create": {"permission_level": "write"},
        "action.execute.local": {"permission_level": "none"},
    },
}
```

### 1.3 Memory System Changes

**v2.0**: Single memory namespace
```python
# v2.0 (OLD)
memory.write("user_name", "Pangge")
# Stored in global namespace
```

**v3.0**: Scoped memory with capability checks
```python
# v3.0 (NEW)
memory.write_memory(
    scope="global",
    key="user_name",
    value="Pangge",
    written_by="chat_agent",
)
# Requires state.memory.write capability
# Permission check enforced
```

**Good News**: v2.0 memory data is automatically migrated to v3.0 global scope!

### 1.4 Execution Model Changes

**v2.0**: Direct execution
```python
# v2.0 (OLD)
result = executor.execute(command="pytest tests/")
# No frozen plan required
# No governance check
# Evidence optional
```

**v3.0**: Golden Path execution
```python
# v3.0 (NEW)
# Step 1: Create plan
plan = decision.create_plan(task_id="task-123", steps=[...])

# Step 2: Freeze plan
frozen_plan = decision.freeze_plan(plan.plan_id)

# Step 3: Check permission
permission = governance.check_permission(agent_id, capability_id, context)

# Step 4: Execute (if approved)
result = executor.execute(
    capability_id="action.execute.local",
    params={"command": "pytest tests/"},
    agent_id="execution_agent",
    context={"plan_id": frozen_plan.plan_id},
)
# Evidence automatically collected
```

---

## Chapter 2: Breaking Changes Checklist

### Breaking Change #1: Agent Definition Format

**Impact**: HIGH
**Affects**: All agent definitions

**v2.0**:
```python
{
    "agent_id": "chat_agent",
    "role": "assistant",
    "permissions": ["read_memory", "propose_changes"],
}
```

**v3.0**:
```python
{
    "agent_id": "chat_agent",
    "capability_profile": {
        "state.memory.read": {"permission_level": "read"},
        "state.memory.write": {"permission_level": "propose"},
        "decision.plan.create": {"permission_level": "write"},
    },
}
```

**Migration**:
```bash
# Automatic migration tool
agentos migrate agent --from-v2 agents_v2.json --to-v3 agents_v3.json
```

### Breaking Change #2: Memory API

**Impact**: MEDIUM
**Affects**: Direct memory.write() calls

**v2.0**:
```python
memory.write("key", "value")
memory.read("key")
```

**v3.0**:
```python
memory_service.write_memory(
    scope="global",
    key="key",
    value="value",
    written_by="agent_id",
)
memory_service.read_memory(scope="global", key="key")
```

**Migration**:
```python
# Compatibility wrapper (temporary)
from agentos.compat.v2 import LegacyMemory

legacy_memory = LegacyMemory()
legacy_memory.write("key", "value")  # Internally calls v3 API
```

### Breaking Change #3: Action Execution API

**Impact**: HIGH
**Affects**: All action execution code

**v2.0**:
```python
result = executor.execute(command="test")
```

**v3.0**:
```python
result = executor.execute(
    capability_id="action.execute.local",
    params={"command": "test"},
    agent_id="execution_agent",
    context={"task_id": "task-123"},
)
```

**Migration**: Use compatibility wrapper or refactor to Golden Path.

### Breaking Change #4: Database Schema

**Impact**: HIGH
**Affects**: Database

**v2.0**: Schema v47

**v3.0**: Schema v52 (5 new schemas)
- v48: Decision capabilities tables
- v49: Action capabilities tables
- v50: Governance capabilities tables
- v51: Evidence capabilities tables
- v52: PathValidator tables

**Migration**: Automatic via `agentos db migrate`

### Breaking Change #5-12: See Appendix A

---

## Chapter 3: Agent Definition Migration

### 3.1 Role → Capability Profile Mapping

**Mapping Table**:

| v2.0 Role | v3.0 Capability Profile |
|-----------|------------------------|
| `admin` | All capabilities = `admin` |
| `assistant` | `state.*` = `read/propose`, `decision.*` = `write`, `action.*` = `none` |
| `executor` | `state.*` = `write`, `decision.*` = `write`, `action.*` = `write` |
| `readonly` | All capabilities = `read` or `none` |

### 3.2 Step-by-Step Agent Migration

**Step 1: Export v2.0 agents**
```bash
agentos v2 agent export --output agents_v2.json
```

**Step 2: Convert to v3.0 format**
```bash
agentos migrate agent \
  --from-v2 agents_v2.json \
  --to-v3 agents_v3.json \
  --validate
```

**Step 3: Review generated profiles**
```bash
cat agents_v3.json
# Review each agent's capability profile
# Adjust permissions as needed
```

**Step 4: Import to v3.0**
```bash
agentos v3 agent import --input agents_v3.json
```

### 3.3 Manual Conversion Example

**v2.0 Agent**:
```json
{
  "agent_id": "deployment_agent",
  "role": "executor",
  "permissions": ["execute_actions", "modify_state"],
  "constraints": {
    "max_cost_per_task": 5.00
  }
}
```

**v3.0 Agent**:
```json
{
  "agent_id": "deployment_agent",
  "agent_type": "execution",
  "capability_profile": {
    "state.memory.read": {"permission_level": "read"},
    "state.memory.write": {"permission_level": "write"},
    "decision.plan.create": {"permission_level": "write"},
    "decision.plan.freeze": {"permission_level": "write"},
    "action.execute.local": {"permission_level": "write"},
    "action.execute.remote": {"permission_level": "propose"},
    "governance.check.permission": {"permission_level": "read"},
    "evidence.collect": {"permission_level": "write"}
  },
  "metadata": {
    "trust_tier": "T2",
    "max_budget_per_task": 5.00,
    "migrated_from_v2": true,
    "original_role": "executor"
  }
}
```

---

## Chapter 4: Memory v2.0 Compatibility

### 4.1 Memory Data Migration

**Good News**: v2.0 memory data is automatically migrated!

**Migration Process**:
```
1. v2.0 memory (unscoped) → v3.0 memory (global scope)
2. Preserve all keys and values
3. Add scope="global" metadata
4. Generate memory_id (ULID)
5. Set created_at_ms from v2.0 timestamp
```

**Verification**:
```python
# After migration, verify data
from agentos.core.capability.domains.state import MemoryService

memory = MemoryService()

# v2.0 data accessible in global scope
items = memory.read_memory(scope="global")

for item in items:
    print(f"{item.key}: {item.value}")
    # Output should match v2.0 data
```

### 4.2 Memory API Compatibility Layer

**Legacy Wrapper** (temporary support):

```python
# agentos/compat/v2/memory.py

class LegacyMemory:
    """
    v2.0 Memory API compatibility wrapper.

    Deprecated: Use MemoryService directly in new code.
    Support ends: 2026-08-01 (6 months)
    """

    def __init__(self):
        from agentos.core.capability.domains.state import MemoryService
        self._service = MemoryService()

    def write(self, key: str, value: Any):
        """Write to global scope (v2.0 behavior)"""
        return self._service.write_memory(
            scope="global",
            key=key,
            value=value,
            written_by="legacy_agent",  # Default agent
        )

    def read(self, key: str) -> Any:
        """Read from global scope (v2.0 behavior)"""
        items = self._service.read_memory(scope="global", key=key)
        if items:
            return items[0].value
        return None

# Usage in legacy code
from agentos.compat.v2 import LegacyMemory

memory = LegacyMemory()
memory.write("user_name", "Pangge")  # Works!
name = memory.read("user_name")      # Works!
```

---

## Chapter 5: 5-Step Migration Process

### Step 1: Evaluate Current Usage

**Assessment Checklist**:
- [ ] List all agents (agent IDs, roles)
- [ ] Identify agent permissions
- [ ] Map agents to capabilities
- [ ] Identify high-risk agents (can execute actions)
- [ ] Document custom memory usage
- [ ] Document custom executor integrations

**Tools**:
```bash
# Generate assessment report
agentos migrate assess --output assessment_report.json

# Review report
cat assessment_report.json
```

**Report Contents**:
```json
{
  "agents": {
    "total": 15,
    "by_role": {
      "admin": 2,
      "assistant": 8,
      "executor": 3,
      "readonly": 2
    }
  },
  "memory_usage": {
    "total_keys": 234,
    "scopes_needed": ["global", "project"],
    "migration_complexity": "low"
  },
  "executor_usage": {
    "total_executions": 1043,
    "needs_golden_path": 1043,
    "migration_complexity": "high"
  },
  "estimated_migration_time": "8 weeks"
}
```

### Step 2: Define Agent Capability Profiles

**For each agent, define**:
1. Required capabilities (minimum)
2. Trust tier (T1/T2/T3)
3. Budget constraints
4. Rate limits

**Template**:
```json
{
  "agent_id": "<agent_id>",
  "agent_type": "chat|execution|admin|readonly",
  "capability_profile": {
    "state.memory.read": {"permission_level": "read"},
    "state.memory.write": {"permission_level": "propose|write"},
    "decision.plan.create": {"permission_level": "write"},
    "action.execute.local": {"permission_level": "none|propose|write"},
    "governance.check.permission": {"permission_level": "read"},
    "evidence.collect": {"permission_level": "write"}
  },
  "metadata": {
    "trust_tier": "T1|T2|T3",
    "max_budget_per_task": 5.00,
    "max_budget_per_day": 50.00
  }
}
```

**Example Profiles**: See Chapter 3.3

### Step 3: Configure Governance Policies

**Policy Template**:
```json
{
  "policy_id": "migration_policy",
  "name": "v2→v3 Migration Policy",
  "rules": [
    {
      "rule_id": "rule-1",
      "capability_pattern": "action.*",
      "agent_pattern": "*_v2",
      "permission_level": "propose",
      "reason": "All v2 agents require approval during migration"
    },
    {
      "rule_id": "rule-2",
      "capability_pattern": "state.memory.write",
      "agent_pattern": "chat_*",
      "permission_level": "propose",
      "reason": "Chat agents must propose memory changes"
    }
  ]
}
```

**Register Policy**:
```bash
agentos governance policy create --from-file migration_policy.json
```

### Step 4: Database Migration

**Schema v47 → v52**:

```bash
# Backup database first!
agentos db backup --output agentos_v2_backup.db

# Run migration
agentos db migrate --from-version 47 --to-version 52

# Verify migration
agentos db verify --expected-version 52
```

**Migration Steps** (automatic):
1. Create v48 tables (decision_plans, decision_options, ...)
2. Create v49 tables (action_executions, side_effects, ...)
3. Create v50 tables (governance_policies, risk_scores, ...)
4. Create v51 tables (evidence_log, evidence_chains, ...)
5. Create v52 tables (path_validation_log)
6. Migrate v2.0 memory → v3.0 global scope
7. Create indexes
8. Update schema_version

**Migration Time**: ~5 minutes for 100MB database

### Step 5: Testing and Validation

**Test Plan** (100+ checks):

**5.1 Agent Tests**:
```bash
# Test agent profiles
agentos test agent --agent-id chat_agent --capability state.memory.read
agentos test agent --agent-id chat_agent --capability action.execute.local
# Expected: PASS (read), FAIL (action denied)
```

**5.2 Memory Tests**:
```bash
# Test memory compatibility
python tests/migration/test_memory_v2_compat.py
# Verify:
# - v2.0 data accessible
# - Scopes work correctly
# - Permissions enforced
```

**5.3 Execution Tests**:
```bash
# Test Golden Path
python tests/migration/test_golden_path.py
# Verify:
# - Plan creation works
# - Plan freeze works
# - Governance checks work
# - Execution works
# - Evidence collected
```

**5.4 Performance Tests**:
```bash
# Run performance benchmarks
pytest tests/performance/test_capability_v3_performance.py
# Verify all targets met:
# - PathValidator < 5ms
# - Registry query < 1ms
# - Permission check < 2ms
# - Golden Path E2E < 100ms
```

**5.5 E2E Integration Tests**:
```bash
# Run full E2E suite
pytest tests/migration/test_v2_to_v3_e2e.py -v
# 50+ E2E scenarios
```

---

## Chapter 6: 8-Week Migration Timeline

### Week 1-2: Assessment and Planning

**Activities**:
- [ ] Run migration assessment
- [ ] Review assessment report
- [ ] Identify migration risks
- [ ] Create detailed migration plan
- [ ] Assign migration team roles
- [ ] Set up staging environment

**Deliverables**:
- Assessment report
- Migration plan document
- Risk register
- Team assignments

### Week 3-4: Agent Profile Definition

**Activities**:
- [ ] Define capability profiles for all agents
- [ ] Map v2.0 roles to v3.0 capabilities
- [ ] Define governance policies
- [ ] Review with security team
- [ ] Create test agents

**Deliverables**:
- Agent capability profile definitions (JSON)
- Governance policy definitions (JSON)
- Security review sign-off

### Week 5: Database Migration (Staging)

**Activities**:
- [ ] Backup production database
- [ ] Set up staging environment
- [ ] Run database migration (v47→v52)
- [ ] Verify data integrity
- [ ] Test memory compatibility
- [ ] Performance baseline tests

**Deliverables**:
- Staging environment (v3.0)
- Migration verification report
- Performance baseline

### Week 6: Code Refactoring and Testing

**Activities**:
- [ ] Refactor executor calls to Golden Path
- [ ] Add capability decorators
- [ ] Update agent initialization
- [ ] Update memory API calls
- [ ] Write migration tests
- [ ] Run unit tests (target: >80% pass)

**Deliverables**:
- Refactored codebase
- Migration tests (100+ checks)
- Test results report

### Week 7: Integration Testing and Bug Fixes

**Activities**:
- [ ] Run E2E integration tests
- [ ] Fix identified bugs
- [ ] Performance optimization
- [ ] Security audit
- [ ] User acceptance testing (UAT)

**Deliverables**:
- Integration test results
- Bug fix commits
- Security audit report
- UAT sign-off

### Week 8: Production Migration

**Activities**:
- [ ] Final production backup
- [ ] Schedule maintenance window
- [ ] Run database migration (production)
- [ ] Deploy v3.0 code
- [ ] Verify all agents working
- [ ] Monitor for issues
- [ ] Document rollback procedures

**Deliverables**:
- Production v3.0 deployment
- Post-migration verification report
- Monitoring dashboards
- Rollback procedures

---

## Chapter 7: Risk and Rollback Strategy

### 7.1 Migration Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Database corruption | Low | Critical | Multiple backups, staging test |
| Agent permission errors | Medium | High | Thorough testing, compatibility mode |
| Performance degradation | Low | Medium | Performance baseline, monitoring |
| Data loss | Very Low | Critical | Backup before migration, verify after |
| API incompatibility | Medium | High | Compatibility layer, gradual rollout |

### 7.2 Rollback Plan

**Rollback Triggers**:
- Critical bug discovered (P0 severity)
- Data integrity issues
- Performance degradation > 50%
- > 20% agents unable to operate

**Rollback Procedure** (2 hours):

**Step 1: Stop v3.0 Services**
```bash
# Stop AgentOS v3.0
agentos server stop

# Verify all processes stopped
ps aux | grep agentos
```

**Step 2: Restore v2.0 Database**
```bash
# Restore from backup
agentos db restore --from-backup agentos_v2_backup.db

# Verify schema version
agentos db version
# Expected: v47
```

**Step 3: Deploy v2.0 Code**
```bash
# Checkout v2.0 tag
git checkout tags/v2.0.0

# Reinstall dependencies
uv sync

# Start v2.0 services
agentos server start
```

**Step 4: Verify Rollback**
```bash
# Test agents
agentos agent list

# Test memory
agentos memory read --key test_key

# Test execution
agentos task create --title "Test task"
```

**Step 5: Notify Stakeholders**
```
Subject: AgentOS v3.0 Rollback Completed

We have rolled back to AgentOS v2.0 due to [REASON].

Impact:
- All services operational
- Data integrity verified
- v3.0 features unavailable

Next Steps:
- Root cause analysis
- Fix identified issues
- Reschedule migration
```

### 7.3 Partial Rollback (Per-Agent)

**Rollback individual agent** without full system rollback:

```bash
# Disable v3.0 capabilities for specific agent
agentos agent update \
  --agent-id problematic_agent \
  --compatibility-mode v2.0

# Agent now uses v2.0 behavior
# (through compatibility layer)
```

---

## Chapter 8: Migration Testing Checklist

### 8.1 Pre-Migration Tests

- [ ] Backup database successful
- [ ] Staging environment set up
- [ ] All agents defined in v3.0 format
- [ ] Governance policies registered
- [ ] Migration scripts tested
- [ ] Rollback procedure documented
- [ ] Team trained on v3.0 concepts

### 8.2 Migration Tests

- [ ] Database schema upgraded (v47→v52)
- [ ] No data loss (row counts match)
- [ ] Memory data migrated correctly
- [ ] Indexes created successfully
- [ ] Foreign key constraints valid
- [ ] Migration completed in expected time

### 8.3 Post-Migration Tests

**Agent Tests** (15 checks):
- [ ] All agents registered
- [ ] Agent capability profiles valid
- [ ] Permission checks work
- [ ] High-risk agents require approval
- [ ] Read-only agents cannot modify state

**Memory Tests** (10 checks):
- [ ] v2.0 data accessible in global scope
- [ ] New scoped memory works (global/project/task/agent)
- [ ] Write permissions enforced
- [ ] Propose workflow works (chat agents)
- [ ] Memory integrity verified

**Execution Tests** (20 checks):
- [ ] Golden Path works end-to-end
- [ ] Plan creation works
- [ ] Plan freeze works
- [ ] Governance checks work
- [ ] Action execution works
- [ ] Evidence automatically collected
- [ ] Evidence chains built correctly
- [ ] Rollback works
- [ ] Decision→Action blocked (PathValidator)
- [ ] Action→State blocked (PathValidator)

**Performance Tests** (15 checks):
- [ ] PathValidator < 5ms
- [ ] Registry query < 1ms
- [ ] Permission check < 2ms
- [ ] Risk score calculation < 10ms
- [ ] Evidence collection < 20ms
- [ ] Golden Path E2E < 100ms
- [ ] Decision throughput > 100 plans/s
- [ ] Action throughput > 50 actions/s
- [ ] Evidence throughput > 200 collections/s
- [ ] No performance degradation vs v2.0

**Integration Tests** (40 checks):
- [ ] WebUI displays v3.0 capabilities
- [ ] Agent management UI works
- [ ] Review Queue works
- [ ] Evidence Viewer works
- [ ] Risk Dashboard works
- [ ] Governance Dashboard works
- [ ] Memory Badge updated
- [ ] API endpoints compatible
- [ ] CLI commands work
- [ ] Logs contain v3.0 events

**Total Checks**: 100+

---

## Chapter 9: Troubleshooting Migration Issues

### Issue #1: Database Migration Fails

**Symptom**: `agentos db migrate` fails with SQL error

**Cause**: Database corruption or incompatible version

**Solution**:
```bash
# Check database version
agentos db version

# If wrong version, restore backup
agentos db restore --from-backup agentos_v2_backup.db

# Re-run migration with verbose logging
agentos db migrate --verbose --log-file migration.log

# Review log
cat migration.log
```

### Issue #2: Agent Permission Denied

**Symptom**: Agent gets `PermissionDeniedError` in v3.0

**Cause**: Capability not granted in profile

**Solution**:
```bash
# Check agent capabilities
agentos agent show --agent-id problematic_agent

# Grant missing capability
agentos agent grant \
  --agent-id problematic_agent \
  --capability action.execute.local \
  --permission write

# Test again
agentos test agent --agent-id problematic_agent
```

### Issue #3: Memory Data Missing

**Symptom**: v2.0 memory data not accessible in v3.0

**Cause**: Migration didn't complete

**Solution**:
```bash
# Check if migration ran
agentos db query "SELECT COUNT(*) FROM memory_items WHERE scope='global'"

# If 0, re-run memory migration
agentos db migrate-memory --from-v2 --to-v3

# Verify data
agentos memory list --scope global
```

### Issue #4: Performance Degradation

**Symptom**: v3.0 slower than v2.0

**Cause**: Missing indexes or bloated logs

**Solution**:
```bash
# Check indexes
agentos db analyze

# Rebuild indexes
agentos db reindex

# Vacuum old logs
agentos db vacuum --older-than 90d

# Run performance tests
pytest tests/performance/test_capability_v3_performance.py
```

---

## Chapter 10: Migration Acceptance Checklist

**Sign-off Requirements**:

### Technical Acceptance
- [ ] All 100+ migration tests pass
- [ ] No P0/P1 bugs identified
- [ ] Performance meets targets
- [ ] Security audit passed
- [ ] Data integrity verified
- [ ] Rollback procedure tested

### Business Acceptance
- [ ] All agents operational
- [ ] No service interruptions
- [ ] User acceptance testing passed
- [ ] Documentation complete
- [ ] Training materials ready
- [ ] Support team trained

### Compliance Acceptance
- [ ] Audit trail complete
- [ ] Evidence collection verified
- [ ] Governance policies active
- [ ] SOX compliance maintained
- [ ] GDPR compliance maintained

**Final Sign-Off**: Require approval from:
- Technical Lead
- Product Manager
- Security Officer
- Compliance Officer

---

## Appendix A: Breaking Changes Reference

### Breaking Change #5: Evidence Collection

**v2.0**: Optional
**v3.0**: Mandatory (automatic)

**Impact**: All actions generate evidence (storage requirements increase)

**Solution**: Plan for increased storage (~100-200 MB per 100k operations)

### Breaking Change #6: PathValidator Enforcement

**v2.0**: No path validation
**v3.0**: Golden Path enforced

**Impact**: Decision→Action calls blocked

**Solution**: Refactor to Golden Path (see Chapter 1.4)

### Breaking Change #7: Frozen Plan Requirement

**v2.0**: Plans optional
**v3.0**: Frozen plan required for actions

**Impact**: Ad-hoc execution not allowed

**Solution**: Always create + freeze plan before action

### Breaking Change #8: Governance Checks

**v2.0**: Optional
**v3.0**: Mandatory for actions

**Impact**: All actions require permission check

**Solution**: Add `governance.check_permission()` before action

### Breaking Change #9: Agent ID Format

**v2.0**: Free-form
**v3.0**: Alphanumeric + underscore only

**Impact**: Agent IDs with special characters invalid

**Solution**: Rename agents or use ID mapping

### Breaking Change #10: Memory Scope Requirement

**v2.0**: Unscoped
**v3.0**: Scope required (global/project/task/agent)

**Impact**: All memory writes need scope

**Solution**: Use "global" for v2.0 compatibility

### Breaking Change #11: Evidence Immutability

**v2.0**: Evidence can be modified
**v3.0**: Evidence immutable

**Impact**: Cannot edit evidence after creation

**Solution**: Export and archive old evidence if needed

### Breaking Change #12: Risk Tier Assignment

**v2.0**: No risk tiers
**v3.0**: All capabilities have risk tier (T1/T2/T3)

**Impact**: High-risk actions require approval

**Solution**: Review and approve high-risk actions in Review Queue

---

## Appendix B: Compatibility Mode

**Availability**: 6 months (until 2026-08-01)

**Usage**:
```python
# Enable v2.0 compatibility mode for agent
agentos agent update \
  --agent-id legacy_agent \
  --compatibility-mode v2.0

# Agent now uses compatibility wrappers
```

**What's Supported**:
- ✅ v2.0 memory API (via LegacyMemory wrapper)
- ✅ v2.0 executor API (via LegacyExecutor wrapper)
- ✅ v2.0 agent permissions (mapped to v3.0)

**What's NOT Supported**:
- ❌ v2.0 database schema (must migrate to v52)
- ❌ v2.0 evidence format (must use v3.0)
- ❌ Skipping PathValidator (always enforced)

**Deprecation Notice**: Compatibility mode will be removed on 2026-08-01. All agents must migrate to native v3.0 by then.

---

**Document Version**: 3.0.0
**Last Updated**: 2026-02-01
**Support**: migrations@agentos.com
