# P1-0: Coverage Top-Off 清单生成 - 文档索引

**任务状态:** ✅ COMPLETED
**完成时间:** 2026-01-30
**当前覆盖率:** 46.93% → **目标:** 65%

---

## 📋 快速访问

### 核心文档（按使用频率）

1. **[P1_0_QUICK_REFERENCE.md](./P1_0_QUICK_REFERENCE.md)** ⭐
   - 最常用的快速参考
   - 第一跳路径概览
   - Top 5 高价值目标
   - 常用命令和测试模板

2. **[COVERAGE_TOPOFF_LIST.md](./COVERAGE_TOPOFF_LIST.md)** 📊
   - 完整的 Top-Off 清单（636 行）
   - 10 个详细章节 + 2 个附录
   - 包含所有测试场景和代码示例

3. **[P1_0_COVERAGE_TOPOFF_COMPLETION.md](./P1_0_COVERAGE_TOPOFF_COMPLETION.md)** ✅
   - 任务验收报告（392 行）
   - 关键发现与分析
   - 成功标准验证

### 工具脚本

4. **[scripts/analyze_coverage_gap.py](./scripts/analyze_coverage_gap.py)** 🛠️
   - 可复用的覆盖率分析工具
   - 支持命令行参数
   - 自动化缺口识别

---

## 📈 覆盖率现状

```
总覆盖率: 46.93% (2100/4475 lines+branches)
目标缺口: 808 lines/branches (to reach 65%)
分析文件: 31 files in agentos/core/task/
```

### 优先级分布

| 优先级 | 文件数 | 预估收益 | 预估工时 | ROI |
|--------|--------|----------|----------|-----|
| P0-QuickWin | 8 | 22.5% | 0.5h | 46 |
| P1-Critical | 6 | 226.6% | 15.2h | 15 |
| P2-Strategic | 9 | 142.2% | 8.7h | 16 |
| P3-Foundation | 8 | 26.9% | 32.2h | 0.8 |

---

## 🎯 第一跳路径（47% → 65%）

```
Phase 1 (0.6h)  → 48.5%  [Quick Wins]
Phase 2 (3.5h)  → 56.0%  [Critical State Machine] ⚠️ HIGHEST PRIORITY
Phase 3 (2.5h)  → 61.0%  [Service Layer]
Phase 4 (3.5h)  → 65.0%+ [Rollback & Strategic] ✅ TARGET
Phase 5 (3.0h)  → 68.0%  [Optional]
```

**预计总时长:** 10-15 小时

---

## 🔥 Top 5 高价值目标

1. **state_machine.py** (ROI: 25.0) 🔴
   - 当前: 52.7% → 目标: 100%
   - 工时: 3.0h
   - 关键: 错误处理、超时、模式验证

2. **routing_service.py** (ROI: 25.5) 🔴
   - 当前: 27.7% → 目标: 100%
   - 工时: 1.7h
   - 关键: 路由匹配、元数据验证

3. **artifact_service.py** (ROI: 48.5) 🟢
   - 当前: 89.4% → 目标: 100%
   - 工时: 0.2h
   - 关键: 错误路径 (lines 98-99)

4. **service.py** (ROI: 18.3) 🔴
   - 当前: 54.2% → 目标: 100%
   - 工时: 2.5h
   - 关键: approve/cancel/force-complete

5. **rollback.py** (ROI: 16.4) 🔴
   - 当前: 42.5% → 目标: 100%
   - 工时: 2.1h
   - 关键: 安全取消、草稿创建

---

## 📝 新建测试文件清单

```
tests/unit/task/
├── test_state_machine_errors.py          # Phase 2
├── test_state_machine_modes.py           # Phase 2
├── test_routing_service.py               # Phase 2
├── test_service_operations.py            # Phase 3 (extend)
├── test_rollback_operations.py           # Phase 4
├── test_errors_coverage.py               # Phase 4
└── test_run_mode_retry.py                # Phase 4
```

---

## 🚀 快速开始

### 1. 查看当前覆盖率
```bash
# 生成覆盖率报告
./scripts/coverage_scope_task.sh

# 分析缺口
python3 scripts/analyze_coverage_gap.py

# 查看 HTML 报告
open htmlcov-scope/index.html
```

### 2. 开始 Phase 1 (Quick Wins)
```bash
# 查看 Quick Reference
cat P1_0_QUICK_REFERENCE.md

# 查看详细测试场景
open COVERAGE_TOPOFF_LIST.md  # Section E.1

# 运行现有测试
pytest tests/unit/task/test_artifact_service.py -v
```

### 3. 攻克 state_machine.py (Phase 2)
```bash
# 查看详细测试场景
open COVERAGE_TOPOFF_LIST.md  # Section E.1

# 创建新测试文件
touch tests/unit/task/test_state_machine_errors.py

# 参考测试模板
# 见 COVERAGE_TOPOFF_LIST.md Section E.1
```

---

## 🛠️ 分析工具使用

### 基本用法
```bash
python3 scripts/analyze_coverage_gap.py
```

### 高级选项
```bash
# 只看 P0 优先级
python3 scripts/analyze_coverage_gap.py --priority P0-QuickWin

# 显示详细函数分析
python3 scripts/analyze_coverage_gap.py --functions

# 显示 Top 20 文件
python3 scripts/analyze_coverage_gap.py --top 20

# 查看帮助
python3 scripts/analyze_coverage_gap.py --help
```

---

## 📚 文档结构

### COVERAGE_TOPOFF_LIST.md (26 KB, 636 lines)
```
Section A: Top 10 未覆盖文件
Section B: Top 20 未覆盖函数
Section C: ROI 分析
Section D: 第一跳路径（5 个 Phase）
Section E: 详细测试场景（含代码示例）
Section F: 测试基础设施
Section G: 覆盖率度量
Section H: 风险缓解
Section I: 成功指标
Section J: 后续步骤
Appendix A: 文件级汇总
Appendix B: 脚本使用
```

### P1_0_COVERAGE_TOPOFF_COMPLETION.md (13 KB, 392 lines)
```
一、任务目标
二、交付成果
三、关键发现
四、第一跳路径
五、详细测试场景示例
六、测试基础设施
七、可操作性验证
八、风险识别与缓解
九、成功标准验证
十、后续行动项
十一、度量标准
十二、参考资料
```

### P1_0_QUICK_REFERENCE.md (7 KB)
```
- 快速导航
- 第一跳路径
- Top 5 高价值目标
- 新建测试文件
- 常用命令
- 核心测试模板
- 检查点与验证
- 风险与缓解
```

---

## ✅ 验收标准

### 主要成果
- [x] COVERAGE_TOPOFF_LIST.md（完整清单）
- [x] analyze_coverage_gap.py（分析脚本）
- [x] Top 10 文件列表
- [x] Top 20 函数列表
- [x] 第一跳路径（5 个 Phase）

### 质量指标
- [x] 具备可操作性（明确文件、函数、工时）
- [x] ROI 排序（按收益/小时）
- [x] 测试代码示例（pytest 模板）
- [x] 验证步骤（每 Phase 有检查点）

---

## 📞 常见问题

### Q1: 如何开始 P1-1？
**A:** 阅读 [P1_0_QUICK_REFERENCE.md](./P1_0_QUICK_REFERENCE.md)，从 Phase 1 的 Quick Wins 开始。

### Q2: 如何查看特定文件的覆盖率？
**A:** 运行 `./scripts/coverage_scope_task.sh`，然后打开 `htmlcov-scope/index.html`，搜索文件名。

### Q3: 如何验证覆盖率提升？
**A:** 每个 Phase 完成后运行 `python3 scripts/analyze_coverage_gap.py`，检查总覆盖率是否达到目标。

### Q4: 哪个文件最重要？
**A:** `state_machine.py` (Phase 2) 是最高优先级，3.0h 可提升 7.5%。

### Q5: 如何重新生成覆盖率报告？
**A:** 运行 `./scripts/coverage_scope_task.sh`，等待约 2-3 分钟。

---

## 🎓 测试模板速查

### 错误路径覆盖
```python
def test_function_with_error():
    with patch('module.dependency') as mock:
        mock.side_effect = Exception("error")
        with pytest.raises(ExpectedException):
            function_under_test()
```

### 分支覆盖
```python
@pytest.mark.parametrize("input,expected", [
    ("valid", "success"),
    ("invalid", "error"),
])
def test_branches(input, expected):
    assert function(input) == expected
```

### 超时测试
```python
def test_timeout():
    with patch('module.get_writer') as mock:
        mock.return_value.submit.side_effect = TimeoutError()
        with pytest.raises(TaskStateError):
            function_under_test()
```

---

## 📊 进度跟踪

### Checkpoint 检查清单
```
□ Phase 1 完成: 覆盖率 ≥48%
□ Phase 2 完成: 覆盖率 ≥56%
□ Phase 3 完成: 覆盖率 ≥61%
□ Phase 4 完成: 覆盖率 ≥65% ✅ TARGET
□ Phase 5 完成: 覆盖率 ≥68% (optional)
```

### 测试文件创建清单
```
□ tests/unit/task/test_state_machine_errors.py
□ tests/unit/task/test_state_machine_modes.py
□ tests/unit/task/test_routing_service.py
□ tests/unit/task/test_service_operations.py (extend)
□ tests/unit/task/test_rollback_operations.py
□ tests/unit/task/test_errors_coverage.py
□ tests/unit/task/test_run_mode_retry.py
```

---

## 📅 时间线

| Phase | 描述 | 工时 | 目标覆盖率 | 状态 |
|-------|------|------|-----------|------|
| Phase 1 | Quick Wins | 0.6h | 48.5% | ⏳ Pending |
| Phase 2 | Critical State Machine | 3.5h | 56.0% | ⏳ Pending |
| Phase 3 | Service Layer | 2.5h | 61.0% | ⏳ Pending |
| Phase 4 | Rollback & Strategic | 3.5h | 65.0%+ | ⏳ Pending |
| Phase 5 | Remaining (Optional) | 3.0h | 68.0% | ⏳ Pending |

**预计总时长:** 10-15 小时

---

## 🔗 相关链接

- [Coverage Report (HTML)](./htmlcov-scope/index.html)
- [Coverage Report (XML)](./coverage-scope.xml)
- [Analysis Script](./scripts/analyze_coverage_gap.py)
- [Coverage Task Script](./scripts/coverage_scope_task.sh)

---

**最后更新:** 2026-01-30
**任务状态:** ✅ COMPLETED
**下一步:** 启动 P1-1 - 执行第一跳路径
