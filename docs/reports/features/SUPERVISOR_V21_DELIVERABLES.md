# Supervisor v21 Integration - Deliverables Overview

## Summary

This document provides an overview of all deliverables for Supervisor v21 integration (redundant column writes for task_audits).

**Objective**: Enable Supervisor to write `source_event_ts` and `supervisor_processed_at` columns to `task_audits` table, allowing Lead Agent to use fast column-based queries instead of slow JSON extraction.

**Performance Impact**: 10x faster decision lag queries for Lead Agent.

---

## Deliverables

### 1. Comprehensive Integration Guide

**File**: `docs/governance/SUPERVISOR_V21_INTEGRATION.md` (792 lines)

**Contents**:
- Section 1: Code locations to modify
- Section 2: Field mapping rules
- Section 3: Implementation plan (detailed pseudo-code)
- Section 4: Backward compatibility strategy
- Section 5: Implementation steps (4 phases)
- Section 6: Validation methods (SQL queries)
- Section 7: Rollback plan
- Section 8: Timeline (D+1 to D+10)
- Section 9: FAQ (6 questions)
- Section 10: Appendices (file list, data dictionary, performance benchmarks)

**Key Sections**:
```
1. 需要修改的代码位置
   - 核心写入点: audit_adapter.py
   - 调用链路: BasePolicy → AuditAdapter

2. 字段映射规则
   - source_event_ts: SupervisorEvent.ts
   - supervisor_processed_at: datetime.now()

3. 实施方案
   - 方案 A（推荐）: 修改 write_audit_event 方法
   - 详细伪代码（可直接参考实现）

4. 向后兼容策略
   - Payload 仍然是 Source of Truth
   - 冗余列可以为 NULL（兼容旧数据）
   - Lead Agent 自动 fallback

5. 实施步骤（4 阶段）
   - 阶段 1: 代码修改 (D+1~D+2)
   - 阶段 2: 联合验证 (D+3)
   - 阶段 3: 投产 (D+4~D+5)
   - 阶段 4: 监控与优化 (D+6~D+10)

6. 验证方法
   - SQL 查询检查填充率
   - 数据一致性验证
   - 性能对比测试

7. 回滚计划
   - 代码回滚不影响功能
   - Schema 保持 v21（无需回滚 migration）

8. 时间表
   - 总计 10 天完成（从代码修改到监控优化）

9. FAQ
   - Q1: 如果 Supervisor 不修改，v21 还有用吗？
   - Q2: source_event_ts 从哪里获取？
   - Q3: 如何测试不破坏现有功能？
   - Q4: 如果冗余列和 payload 不一致怎么办？
   - Q5: 为什么不直接在 payload 里加字段？
   - Q6: 如果忘记传 source_event_ts 怎么办？

10. 附录
    - A. 相关文件清单
    - B. 数据字典
    - C. 性能基准
```

**Use Case**: Complete reference for implementation team.

---

### 2. Quick Implementation Summary

**File**: `SUPERVISOR_V21_IMPLEMENTATION_SUMMARY.md` (compact reference)

**Contents**:
- What needs to change (2 files, 3 methods)
- Code changes at a glance (actual code snippets)
- Field mapping table
- Validation checklist (SQL queries)
- Unit test templates
- Integration test templates
- Timeline table
- Backward compatibility notes
- Rollback plan
- FAQ quick answers

**Key Features**:
- Concise (can be read in 5 minutes)
- Actionable code snippets
- Copy-paste ready test templates

**Use Case**: Quick reference for developers during implementation.

---

### 3. SQL Validation Script

**File**: `scripts/validate_v21_supervisor.sql`

**Contents**:
- 10 validation checks:
  1. Schema version check
  2. Redundant columns exist
  3. Recent decision events (last 10)
  4. Coverage rate (last 1 hour)
  5. Coverage rate (last 24 hours)
  6. Data consistency check
  7. Decision lag calculation (sample)
  8. Index usage check (query plan)
  9. Event type distribution
  10. Summary and recommendations

**Usage**:
```bash
sqlite3 ~/.agentos/store.db < scripts/validate_v21_supervisor.sql
```

**Output Example**:
```
=== 4. Coverage Rate (Last 1 Hour) ===
total_decisions  with_redundant_cols  without_redundant_cols  coverage_pct
---------------  -------------------  ----------------------  ------------
125              122                  3                       97.60

✅ Coverage approaching 100%
```

**Use Case**: Automated validation after deployment.

---

### 4. Python Test Script

**File**: `scripts/test_v21_supervisor_write.py` (executable)

**Contents**:
- Create test Decision object
- Write to task_audits via AuditAdapter
- Verify redundant columns populated
- Verify payload integrity
- Verify data consistency
- Generate test report

**Usage**:
```bash
python scripts/test_v21_supervisor_write.py
```

**Output Example**:
```
==================================================
Test: Write Decision with Redundant Columns
==================================================

1. Writing test decision...
   ✅ Decision written (audit_id=12345)

2. Verifying redundant columns...
   ✅ source_event_ts correct
   ✅ supervisor_processed_at populated

3. Verifying payload integrity...
   ✅ Payload decision_type correct
   ✅ Payload reason correct
   ✅ Payload findings present (1 findings)
   ✅ Payload actions present (1 actions)

5. Test Summary
==================================================
✅ ALL CHECKS PASSED
```

**Use Case**: Quick functional test to verify implementation.

---

## Key Code Locations Identified

### Files to Modify

1. **`agentos/core/supervisor/adapters/audit_adapter.py`**
   - Line 130-174: `write_audit_event()` method
     - ADD: `source_event_ts` and `supervisor_processed_at` parameters
     - UPDATE: SQL INSERT to include redundant columns

   - Line 48-95: `write_decision()` method
     - ADD: `source_event_ts` parameter
     - PASS: `source_event_ts` and `supervisor_processed_at` to `write_audit_event()`

   - Line 97-128: `write_error()` method (optional)
     - ADD: `source_event_ts` parameter
     - PASS: timestamps to `write_audit_event()`

2. **`agentos/core/supervisor/policies/base.py`**
   - Line 56-89: `__call__()` method
     - PASS: `event.ts` to `write_decision()` as `source_event_ts`

### Data Sources Identified

**SupervisorEvent.ts**:
- From EventBus: `event.ts` (original event timestamp)
- From Polling: `created_at` (DB record timestamp)

**Decision.timestamp**:
- Generated when decision is created: `datetime.now(timezone.utc).isoformat()`

**Field Mapping**:
```python
# In BasePolicy.__call__():
source_event_ts = event.ts  # When task entered system

# In AuditAdapter.write_decision():
supervisor_processed_at = datetime.now(timezone.utc).isoformat()  # When decision was made
```

---

## Implementation Checklist

Use this checklist to track implementation progress:

### Phase 1: Code Modification (D+1 ~ D+2)

- [ ] Modify `audit_adapter.py` - `write_audit_event()` method
  - [ ] Add `source_event_ts` parameter
  - [ ] Add `supervisor_processed_at` parameter
  - [ ] Update SQL INSERT statement

- [ ] Modify `audit_adapter.py` - `write_decision()` method
  - [ ] Add `source_event_ts` parameter
  - [ ] Pass `source_event_ts` to `write_audit_event()`
  - [ ] Pass `supervisor_processed_at` to `write_audit_event()`

- [ ] Modify `audit_adapter.py` - `write_error()` method (optional)
  - [ ] Add `source_event_ts` parameter
  - [ ] Pass timestamps to `write_audit_event()`

- [ ] Modify `base.py` - `__call__()` method
  - [ ] Pass `event.ts` to `write_decision()`

- [ ] Add unit tests
  - [ ] Test `write_decision()` with redundant columns
  - [ ] Test payload integrity
  - [ ] Test backward compatibility (NULL columns)

- [ ] Add integration tests
  - [ ] Test end-to-end flow (event → decision → audit)
  - [ ] Test data consistency

- [ ] Code review
  - [ ] Review by Supervisor team lead
  - [ ] Review by Lead Agent team (interface contract)

### Phase 2: Joint Verification (D+3)

- [ ] Deploy to test environment
  - [ ] Run v21 migration
  - [ ] Deploy new Supervisor code

- [ ] Run validation scripts
  - [ ] Run `validate_v21_supervisor.sql`
  - [ ] Run `test_v21_supervisor_write.py`

- [ ] Verify results
  - [ ] Coverage rate > 95%
  - [ ] Data consistency OK
  - [ ] No errors in logs

- [ ] Verify Lead Agent integration
  - [ ] Run Lead scan
  - [ ] Check `lag_source = "columns"` in logs
  - [ ] Verify performance improvement

### Phase 3: Production Deployment (D+4 ~ D+5)

- [ ] Execute v21 migration (production)
- [ ] Deploy new Supervisor code (production)
- [ ] Monitor coverage rate (hourly)
- [ ] Check error rates (no regression)
- [ ] Optional: Run backfill script (for historical data)

### Phase 4: Monitoring & Optimization (D+6 ~ D+10)

- [ ] Monitor coverage rate (target > 95%)
- [ ] Monitor Lead Agent query performance (target 10x improvement)
- [ ] Monitor error rates (target 0 regressions)
- [ ] Generate performance report
- [ ] Document lessons learned

---

## Validation Criteria

### Acceptance Criteria

1. **Functional Requirements**:
   - ✅ Redundant columns (`source_event_ts`, `supervisor_processed_at`) are populated for new decisions
   - ✅ Payload remains complete and unchanged (backward compatibility)
   - ✅ Existing functionality not broken (can still read old data)

2. **Performance Requirements**:
   - ✅ Lead Agent queries 10x faster (using redundant columns vs JSON extraction)
   - ✅ No performance regression in Supervisor write operations

3. **Data Quality Requirements**:
   - ✅ Coverage rate > 95% (new decisions have redundant columns)
   - ✅ Data consistency: `source_event_ts` ≈ `payload.timestamp` (diff < 1 second)
   - ✅ No data loss or corruption

4. **Operational Requirements**:
   - ✅ Backward compatible (can rollback without data issues)
   - ✅ Monitoring in place (coverage rate, consistency checks)
   - ✅ Documentation complete

### Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Coverage Rate (1 hour) | > 95% | SQL query in validation script |
| Data Consistency | diff < 1 second | SQL query in validation script |
| Lead Agent Query Performance | 10x faster | Performance benchmark |
| Error Rate | 0 regressions | Log monitoring |
| Deployment Success | No rollback required | Deployment process |

---

## Files Delivered

```
docs/governance/
  └── SUPERVISOR_V21_INTEGRATION.md        (792 lines, comprehensive guide)

scripts/
  ├── validate_v21_supervisor.sql          (SQL validation script)
  └── test_v21_supervisor_write.py         (Python test script, executable)

/
  ├── SUPERVISOR_V21_IMPLEMENTATION_SUMMARY.md  (Quick reference)
  └── SUPERVISOR_V21_DELIVERABLES.md            (This file)
```

---

## Next Steps

### For Supervisor Team:

1. **Read** `SUPERVISOR_V21_IMPLEMENTATION_SUMMARY.md` (5 min)
2. **Review** `docs/governance/SUPERVISOR_V21_INTEGRATION.md` (detailed implementation)
3. **Implement** code changes following the pseudo-code in Section 3
4. **Test** using `scripts/test_v21_supervisor_write.py`
5. **Validate** using `scripts/validate_v21_supervisor.sql`
6. **Submit** PR with code changes and test results

### For Lead Agent Team:

1. **Review** interface contract (Section 2: Field Mapping Rules)
2. **Verify** v21 migration is correct
3. **Prepare** Lead Agent to use fast path (already implemented)
4. **Coordinate** joint verification (Phase 2)

### For Ops Team:

1. **Review** deployment plan (Section 5: Implementation Steps)
2. **Prepare** production migration script
3. **Set up** monitoring (coverage rate, error rate)
4. **Coordinate** deployment window (Phase 3)

---

## Support

**Questions?**
- Comprehensive Guide: `docs/governance/SUPERVISOR_V21_INTEGRATION.md`
- Quick Reference: `SUPERVISOR_V21_IMPLEMENTATION_SUMMARY.md`
- FAQ: See Section 9 in comprehensive guide

**Issues?**
- Check validation scripts: `scripts/validate_v21_supervisor.sql`
- Run test script: `scripts/test_v21_supervisor_write.py`
- Review rollback plan: Section 7 in comprehensive guide

**Contact**:
- Lead Agent Team: lead-agent@example.com
- Supervisor Team: supervisor@example.com

---

**Version**: 1.0.0
**Created**: 2026-01-28
**Status**: Ready for Implementation
