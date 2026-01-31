# AgentOS Engineering Badges

**Purpose**: Classify projects by their engineering characteristics to guide future decision-making.

---

## Badge Categories

### 🔒 Invariant Project

**Definition**: Changes system-level guarantees or contracts that all code must follow.

**Characteristics**:
- Affects core assumptions
- Requires Semantic Freeze protection
- Enforced via CI/CD gates
- Breaking changes require ADR revision

**Examples**:
- ✅ **Time & Timestamp Contract (ADR-011)** - System-wide UTC requirement
- Security Policy Enforcement
- API Versioning Contract
- Data Encryption at Rest

**Review Requirements**:
- Team consensus required
- ADR mandatory
- Test coverage ≥ 95%
- CI gate implementation

---

### ⚡ Zero-Regression Infrastructure Change

**Definition**: Modifies core infrastructure without breaking existing functionality.

**Characteristics**:
- No API changes
- 100% backward compatible
- Comprehensive test coverage
- Rollback capability

**Examples**:
- ✅ **Time & Timestamp Contract Migration** - Dual-write + lazy migration
- Database engine upgrade
- Cache layer replacement
- Logging framework migration

**Requirements**:
- Dual-write or blue-green deployment
- Integration tests cover all paths
- Performance benchmarks
- Rollback plan documented

---

### 🤖 AI Unattended Execution

**Definition**: Project executed entirely by AI agents with zero human intervention during execution.

**Characteristics**:
- Human provides high-level strategy
- AI agents execute autonomously
- Parallel/sequential coordination
- Self-validation via tests

**Examples**:
- ✅ **Time & Timestamp Contract (14 tasks, 7 agents, 2.5 hours)**
- Code refactoring campaigns
- Documentation generation
- Test coverage improvements

**Success Criteria**:
- Zero manual file edits during execution
- All tests pass autonomously
- Clear completion criteria
- Reproducible process

---

### 🏗️ Technical Debt Elimination

**Definition**: Removes accumulated technical debt that poses maintenance or quality risks.

**Characteristics**:
- Addresses systemic issues
- Improves maintainability
- Reduces future bug risk
- May not add features

**Examples**:
- ✅ **Time & Timestamp Contract** - Eliminated naive datetime usage
- Deprecation removal
- Dead code cleanup
- Test coverage improvements

---

### 🎯 Migration Project

**Definition**: Transitions from old technology/pattern to new, with zero downtime requirement.

**Characteristics**:
- Multi-phase strategy
- Dual-write/lazy migration
- Backward compatibility
- Gradual rollout

**Examples**:
- ✅ **Epoch Milliseconds Migration** - TIMESTAMP → epoch_ms
- Database migration (MySQL → PostgreSQL)
- Framework upgrade (Flask → FastAPI)
- Cloud provider migration

**Best Practices**:
- P0 (stop bleeding) → P1 (safe transition) → P2 (governance)
- Feature flags for gradual rollout
- Monitoring and alerts
- Rollback plan at each phase

---

## Badge Combinations

Some projects earn multiple badges:

### Time & Timestamp Contract (Tasks #1-14)

```
✅ Invariant Project
✅ Zero-Regression Infrastructure Change
✅ AI Unattended Execution
✅ Technical Debt Elimination
✅ Migration Project
```

**Why all 5?**
- **Invariant**: Establishes system-wide UTC contract (ADR-011)
- **Zero-Regression**: 100% backward compatible, 150+ tests pass
- **AI Unattended**: 7 agents, 14 tasks, 2.5 hours, zero manual intervention
- **Debt Elimination**: Removed naive datetime, deprecated APIs
- **Migration**: Dual-write + lazy migration for zero downtime

---

## Using Badges

### During Planning

Ask yourself:
- Is this an **Invariant Project**? → Requires ADR + Semantic Freeze
- Needs **Zero Regression**? → Plan dual-write strategy
- Can use **AI Unattended**? → Break into autonomous tasks
- Is this **Debt Elimination**? → Prioritize over features
- Is this a **Migration**? → Use P0/P1/P2 strategy

### During Review

Check:
- Badges match reality?
- Required artifacts present? (ADR, tests, gates, etc.)
- Success criteria met?

### During Retrospective

Evaluate:
- Which badges were accurate?
- Which techniques worked?
- What to replicate next time?

---

## Badge Assignment Process

1. **Self-Assessment**: Team proposes badges during planning
2. **Validation**: Review against badge definitions
3. **Documentation**: Record in project completion report
4. **Retrospective**: Confirm badges were appropriate

---

## Future Badges (To Define)

Potential badges to add as patterns emerge:
- 🔥 Performance Critical
- 🛡️ Security Hardening
- 📊 Data Pipeline
- 🌐 Multi-Region Deployment
- 🔄 Breaking Change
- 📚 Documentation Overhaul

---

## References

- **Case Study**: [Timezone Hard Contract Migration](methodology/CASE_STUDY_TIMEZONE_HARD_CONTRACT.md)
- **ADR Example**: [ADR-011 Time & Timestamp Contract](adr/ADR-011-time-timestamp-contract.md)
- **Migration Report**: [Timestamp Migration Final Report](TIMESTAMP_MIGRATION_FINAL_REPORT.md)

---

**Version**: 1.0
**Date**: 2026-01-31
**Status**: Active - Growing as patterns emerge
