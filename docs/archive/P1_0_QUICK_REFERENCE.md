# P1-0 Coverage Top-Off - Quick Reference

**Status:** ✅ COMPLETED
**Date:** 2026-01-30
**Current Coverage:** 46.93%
**Target Coverage:** 65%

---

## 快速导航

### 主要交付文件
1. **详细清单:** [COVERAGE_TOPOFF_LIST.md](./COVERAGE_TOPOFF_LIST.md) - 完整的测试目标和场景
2. **完成报告:** [P1_0_COVERAGE_TOPOFF_COMPLETION.md](./P1_0_COVERAGE_TOPOFF_COMPLETION.md) - 验收报告
3. **分析脚本:** [scripts/analyze_coverage_gap.py](./scripts/analyze_coverage_gap.py) - 可复用的分析工具

### 覆盖率报告
- **XML报告:** `coverage-scope.xml`
- **HTML报告:** `htmlcov-scope/index.html`

---

## 第一跳路径（47% → 65%）

### Phase 1: Quick Wins (0.6h) → 48.5%
```bash
# Target 4 files with small gaps
artifact_service.py (lines 98-99)
runner_audit_integration.py (line 61)
path_filter.py (edge cases)
task_repo_service.py (error paths)
```

### Phase 2: Critical State Machine (3.5h) → 56%
```bash
# HIGHEST PRIORITY
state_machine.py (3.0h, +7.5%)
  - can_transition with invalid states
  - validate_or_raise error paths
  - transition timeout/exception handling
  - get_valid_transitions edge cases

routing_service.py (1.7h, +4.3%)
  - match_route patterns
  - validate_route_metadata
```

### Phase 3: Service Layer (2.5h) → 61%
```bash
service.py (2.5h, +4.6%)
  - create_approve_queue_and_start
  - force_complete_task
  - cancel_task cleanup paths
```

### Phase 4: Rollback & Strategic (3.5h) → 65%+ ✅
```bash
rollback.py (2.1h, +3.5%)
  - safe_cancel_task
  - create_draft_from_existing
  - can_cancel validation

errors.py + states.py + run_mode.py (1.4h, +6.1%)
  - Exception types
  - State helpers
  - Retry backoff
```

**Total:** 10-13 hours → 65% coverage

---

## Top 5 高价值目标

| # | File | Current | Gap | Hours | ROI | Priority |
|---|------|---------|-----|-------|-----|----------|
| 1 | state_machine.py | 52.7% | 47.3% | 3.0h | 25.0 | 🔴 CRITICAL |
| 2 | routing_service.py | 27.7% | 72.3% | 1.7h | 25.5 | 🔴 CRITICAL |
| 3 | artifact_service.py | 89.4% | 10.6% | 0.2h | 48.5 | 🟢 QUICK WIN |
| 4 | service.py | 54.2% | 45.8% | 2.5h | 18.3 | 🔴 CRITICAL |
| 5 | rollback.py | 42.5% | 57.5% | 2.1h | 16.4 | 🔴 CRITICAL |

---

## 新建测试文件清单

```
tests/unit/task/
├── test_state_machine_errors.py          # Phase 2 (NEW)
├── test_state_machine_modes.py           # Phase 2 (NEW)
├── test_routing_service.py               # Phase 2 (NEW)
├── test_service_operations.py            # Phase 3 (EXTEND)
├── test_rollback_operations.py           # Phase 4 (NEW)
├── test_errors_coverage.py               # Phase 4 (NEW)
└── test_run_mode_retry.py                # Phase 4 (NEW)
```

---

## 常用命令

### 生成覆盖率报告
```bash
# 运行 scope 测试并生成覆盖率
./scripts/coverage_scope_task.sh

# 分析覆盖率缺口
python3 scripts/analyze_coverage_gap.py

# 查看 HTML 报告
open htmlcov-scope/index.html
```

### 分析脚本选项
```bash
# 显示帮助
python3 scripts/analyze_coverage_gap.py --help

# 只看 P0 优先级
python3 scripts/analyze_coverage_gap.py --priority P0-QuickWin

# 显示详细函数分析
python3 scripts/analyze_coverage_gap.py --functions

# 显示 Top 20 文件
python3 scripts/analyze_coverage_gap.py --top 20
```

### 运行特定测试
```bash
# Phase 1
pytest tests/unit/task/test_artifact_service.py -v
pytest tests/unit/task/test_runner_audit_integration.py -v

# Phase 2
pytest tests/unit/task/test_state_machine_errors.py -v
pytest tests/unit/task/test_routing_service.py -v

# Phase 3
pytest tests/unit/task/test_service_operations.py -v

# Phase 4
pytest tests/unit/task/test_rollback_operations.py -v
```

---

## 核心测试模板

### state_machine.py 错误处理
```python
# tests/unit/task/test_state_machine_errors.py

def test_can_transition_with_invalid_state():
    """Cover lines 122-126"""
    sm = TaskStateMachine()
    assert sm.can_transition("INVALID", "APPROVED") is False

def test_validate_or_raise_invalid_state():
    """Cover lines 151-156"""
    sm = TaskStateMachine()
    with pytest.raises(InvalidTransitionError):
        sm.validate_or_raise("INVALID", "APPROVED")

def test_transition_timeout_error():
    """Cover lines 337-342"""
    sm = TaskStateMachine()
    with patch.object(sm, '_get_writer') as mock:
        mock.return_value.submit.side_effect = TimeoutError()
        with pytest.raises(TaskStateError):
            sm.transition("test-123", "APPROVED", "test")
```

### 通用错误路径模板
```python
@pytest.mark.parametrize("input,expected", [
    ("valid", "success"),
    ("invalid", "error"),
    (None, "null_error"),
])
def test_all_branches(input, expected):
    result = function_under_test(input)
    assert result == expected
```

---

## 检查点与验证

### Phase 完成后检查
```bash
# 1. 运行覆盖率
./scripts/coverage_scope_task.sh

# 2. 检查进度
python3 scripts/analyze_coverage_gap.py

# 3. 验证目标
# Phase 1: ≥48% ✓
# Phase 2: ≥56% ✓
# Phase 3: ≥61% ✓
# Phase 4: ≥65% ✓✓✓
```

### 验收标准
- [ ] 覆盖率 ≥65%
- [ ] 所有新测试通过
- [ ] 无新引入的失败测试
- [ ] state_machine.py 覆盖率 ≥90%

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 超时测试不稳定 | CI 失败 | 使用确定性 mock |
| 数据库状态污染 | 测试互相干扰 | 隔离 DB fixture |
| 模式验证复杂 | 实现困难 | 从简单模式开始 |

---

## 关键指标

### 当前状态
- **覆盖率:** 46.93% (2100/4475)
- **缺口:** 2375 lines/branches
- **目标:** 65% (需覆盖 808 units)

### 优先级分布
- **P0 (Quick Wins):** 8 files, 23% benefit, 0.5h
- **P1 (Critical):** 6 files, 227% benefit, 15h
- **P2 (Strategic):** 9 files, 142% benefit, 9h
- **P3 (Foundation):** 8 files, 27% benefit, 32h (defer)

---

## 下一步 (P1-1)

1. **启动 Phase 1:** 完成 Quick Wins（0.6h）
2. **攻克 state_machine.py:** 最高优先级目标（3.0h）
3. **完成 Phase 2-4:** 达到 65% 覆盖率（~10h）
4. **验证与报告:** 生成最终覆盖率报告

---

## 参考资料

### 详细文档
- [COVERAGE_TOPOFF_LIST.md](./COVERAGE_TOPOFF_LIST.md) - 完整清单（636 行）
- [P1_0_COVERAGE_TOPOFF_COMPLETION.md](./P1_0_COVERAGE_TOPOFF_COMPLETION.md) - 完成报告（392 行）

### 相关文件
- `coverage-scope.xml` - 覆盖率 XML 数据
- `htmlcov-scope/` - HTML 覆盖率报告
- `scripts/analyze_coverage_gap.py` - 分析工具

### HTML 报告快速访问
```bash
# 总览
open htmlcov-scope/index.html

# state_machine.py
open htmlcov-scope/z_c42913cefdac14cf_state_machine_py.html

# service.py
open htmlcov-scope/z_c42913cefdac14cf_service_py.html
```

---

**最后更新:** 2026-01-30
**状态:** ✅ P1-0 完成，准备启动 P1-1
**预计完成时间:** P1-1 预计 13-15 小时
