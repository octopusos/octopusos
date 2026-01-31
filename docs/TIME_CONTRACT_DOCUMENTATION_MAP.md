# Time & Timestamp Contract - Documentation Map

Visual guide to all documentation related to the Time & Timestamp Contract.

---

## Document Hierarchy

```
Time & Timestamp Contract Documentation
│
├── [CONTRACT] ADR-011: Time & Timestamp Contract
│   ├── File: docs/adr/ADR-011-time-timestamp-contract.md
│   ├── Size: 13KB (439 lines)
│   ├── Status: Accepted + Implemented
│   └── Semantic Freeze: YES
│
├── [QUICK REF] Time Contract Quick Reference
│   ├── File: docs/TIME_CONTRACT_QUICK_REF.md
│   ├── Size: 3.1KB
│   └── Purpose: Developer quick lookup
│
├── [GUIDE] Epoch Milliseconds Usage Guide
│   ├── File: docs/EPOCH_MS_USAGE_GUIDE.md
│   ├── Size: 11KB
│   └── Purpose: Detailed usage examples
│
├── [REPORT] Task #7 Migration Report
│   ├── File: docs/TASK_7_MIGRATION_REPORT.md
│   ├── Size: 10KB
│   └── Purpose: Database migration documentation
│
├── [REPORT] Task #11 Completion Report
│   ├── File: TASK_11_COMPLETION_REPORT.md
│   ├── Purpose: Global code replacement documentation
│   └── Scope: 152 files, 606 replacements
│
└── [REPORT] Task #13 Completion Report
    ├── File: TASK_13_ADR_COMPLETION_REPORT.md
    ├── Size: 10KB
    └── Purpose: ADR creation completion documentation
```

---

## Document Purpose Matrix

| Document | Audience | Purpose | When to Use |
|----------|----------|---------|-------------|
| **ADR-011** | Architects, Senior Devs | Understand WHY and design decisions | Architecture review, system design |
| **Quick Reference** | All Developers | Quick lookup of patterns | Daily coding, PR reviews |
| **Usage Guide** | All Developers | Learn HOW to use utilities | Implementing features, onboarding |
| **Task #7 Report** | DBAs, Backend Devs | Database migration details | Schema changes, migrations |
| **Task #11 Report** | All Developers | Understand scope of changes | Code review, understanding history |
| **Task #13 Report** | Project Managers, Leads | ADR completion verification | Project tracking, acceptance |

---

## Reading Path by Role

### New Developer Onboarding

1. Start: **Quick Reference** (5 min read)
   - Get basic do's and don'ts
   - See common patterns

2. Then: **Usage Guide** (15 min read)
   - Learn detailed usage
   - Study examples

3. Finally: **ADR-011** (optional, 30 min read)
   - Understand rationale
   - Learn enforcement mechanisms

### Senior Developer / Architect

1. Start: **ADR-011** (30 min read)
   - Understand complete context
   - Review design decisions

2. Then: **Task Reports** (20 min read)
   - Understand implementation scope
   - Review metrics and validation

3. Reference: **Quick Reference** (as needed)
   - Daily lookup during coding

### Code Reviewer

1. Have Open: **Quick Reference**
   - Verify code follows contract
   - Check common patterns

2. Reference: **ADR-011 - Enforcement Section**
   - Verify checklist items
   - Ensure compliance

3. Check: **Usage Guide** (when uncertain)
   - Clarify specific usage questions

---

## Key Concepts Cross-Reference

### Core Principles

Where to find details on each principle:

| Principle | ADR-011 | Quick Ref | Usage Guide |
|-----------|---------|-----------|-------------|
| **1. Aware UTC** | §2.1 | Page 1 | §2 Migration |
| **2. ISO Z Format** | §2.2 | Page 1 | §14 API Response |
| **3. Epoch MS** | §2.3 | Page 2 | §1-13 All |
| **4. Local Display** | §2.4 | Page 2 | §11 Timezone |

### Implementation Patterns

| Pattern | Quick Ref | Usage Guide | Source Code |
|---------|-----------|-------------|-------------|
| **Get current time** | Page 1 | §1 | `agentos/core/time/clock.py` |
| **API serialization** | Page 2 | §14 | `agentos/webui/api/time_format.py` |
| **DB read/write** | Page 2 | §1-2 | `agentos/store/timestamp_utils.py` |
| **Frontend display** | Page 2 | N/A | `agentos/webui/static/js/` |

---

## Enforcement Documentation

### Where to Find Enforcement Rules

| Enforcement Type | Document | Section |
|------------------|----------|---------|
| **CI/CD Gate** | ADR-011 | §3.1 Enforcement Mechanisms |
| **Unit Tests** | ADR-011 | §3.2 Enforcement Mechanisms |
| **Code Review** | ADR-011 | §3.3 Enforcement Mechanisms |
| **Gate Script** | See | `scripts/check_datetime_usage.sh` |
| **Test Examples** | See | `tests/unit/test_time_contract.py` |

---

## Quick Links

### Primary Documents

- [ADR-011: Time & Timestamp Contract](adr/ADR-011-time-timestamp-contract.md)
- [Quick Reference](TIME_CONTRACT_QUICK_REF.md)
- [Usage Guide](EPOCH_MS_USAGE_GUIDE.md)

### Implementation Reports

- [Task #7 Migration Report](TASK_7_MIGRATION_REPORT.md)
- [Task #11 Completion Report](../TASK_11_COMPLETION_REPORT.md)
- [Task #13 Completion Report](../TASK_13_ADR_COMPLETION_REPORT.md)

### Source Code

- [Clock Module](../agentos/core/time/clock.py)
- [Time Format Module](../agentos/webui/api/time_format.py)
- [Timestamp Utils](../agentos/store/timestamp_utils.py)

### Standards

- [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339.html)
- [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601)
- [PEP 615](https://peps.python.org/pep-0615/)

---

## Document Statistics

| Document | Size | Lines | Word Count | Est. Read Time |
|----------|------|-------|------------|----------------|
| ADR-011 | 13KB | 439 | ~2,600 | 30 min |
| Quick Reference | 3.1KB | ~80 | ~600 | 5 min |
| Usage Guide | 11KB | 511 | ~1,800 | 15 min |
| Task #7 Report | 10KB | ~200 | ~1,500 | 10 min |
| Task #11 Report | ~8KB | 405 | ~2,400 | 15 min |
| Task #13 Report | 10KB | ~250 | ~1,800 | 10 min |
| **Total** | **55KB** | **~1,885** | **~10,700** | **85 min** |

---

## Maintenance

### How to Keep Documentation Synchronized

When making changes to the Time & Timestamp Contract:

1. **Code Changes**
   - Update source code first
   - Run all tests
   - Update inline documentation

2. **Documentation Updates**
   - Quick Reference: Update examples if patterns change
   - Usage Guide: Add new examples if utilities added
   - ADR-011: Create new revision if contract changes

3. **Semantic Freeze Process**
   - Requires team consensus for ADR-011 changes
   - Document as new ADR revision (v2.0)
   - Update all cross-references

### Document Ownership

| Document | Owner | Review Cycle |
|----------|-------|--------------|
| ADR-011 | Architecture Team | On contract change (rare) |
| Quick Reference | Engineering Team | Quarterly |
| Usage Guide | Engineering Team | Quarterly |
| Task Reports | Project Lead | On completion (historical) |

---

## FAQ

### Q: Where do I start?

**A**: For daily development, start with the **Quick Reference**. For understanding rationale, read **ADR-011**.

### Q: I need to implement a new time-related feature. Which docs?

**A**:
1. Check **Quick Reference** for patterns
2. Read relevant sections in **Usage Guide**
3. Consult **ADR-011** enforcement section before submitting PR

### Q: I'm reviewing a PR with time-related changes. What to check?

**A**:
1. Open **Quick Reference** for quick pattern verification
2. Check **ADR-011 §3.3** for review checklist
3. Verify no forbidden patterns (see ADR-011 §2.1)

### Q: How do I propose a change to the contract?

**A**:
1. Read **ADR-011** completely
2. Draft proposed change with rationale
3. Submit to Architecture Team for consensus
4. If approved, create ADR-011 v2.0

---

**Last Updated**: 2026-01-31
**Maintained By**: AgentOS Architecture Team
