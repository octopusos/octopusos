# P2 战略规划 - 快速参考

**当前状态**: 89/100 (A级)
**目标**: 100/100 (满分)
**总工时**: 7.5小时

---

## 快速路线图

```
当前: 89分 (A级)
  ↓ 1.5h
阶段1: 95分 (A+) ← P2-A
  ↓ 4.0h
阶段2: 99分 (A+) ← P2-B + P2-C
  ↓ 2.0h
阶段3: 100分 (满分) ← P2-D
```

---

## Top 6 高ROI改进项

| 排名 | 改进项 | 得分提升 | 工时 | ROI | 优先级 |
|------|--------|----------|------|-----|--------|
| 1 | 修复Retry E2E环境 | +4分 | 1.0h | 4.0 | **P0** |
| 2 | E2E环境完善 | +2分 | 1.0h | 2.0 | **P0** |
| 3 | 修复Timeout exit_reason | +1分 | 0.5h | 2.0 | **P0** |
| 4 | 添加生命周期回放工具 | +2分 | 1.0h | 2.0 | **P1** |
| 5 | 关键路径通过率提升 | +2分 | 1.5h | 1.33 | **P1** |
| 6 | 提升Scope覆盖率至85% | +2分 | 3.0h | 0.67 | **P1** |

---

## 四个并行任务

### P2-A: E2E环境修复（P0）
- **工时**: 1.5h
- **得分**: +6分 (89 → 95)
- **交付物**:
  1. 修复Retry E2E数据库初始化
  2. 修复Timeout exit_reason
- **验收**: E2E通过率 ≥ 90%

### P2-B: 覆盖率提升（P1）
- **工时**: 3.0h
- **得分**: +2分 (95 → 97)
- **交付物**:
  1. test_state_machine_errors.py
  2. test_work_items_coverage.py
  3. 扩展test_event_service.py
- **验收**: Scope Coverage ≥ 85%
- **可并行**: 与P2-C

### P2-C: 回放工具（P1）
- **工时**: 1.0h
- **得分**: +2分 (97 → 99)
- **交付物**:
  1. scripts/replay_task_lifecycle.py
  2. tests/unit/test_replay_tool.py
- **验收**: 回放脚本可执行
- **可并行**: 与P2-B

### P2-D: 完整性冲刺（P2）
- **工时**: 2.0h
- **得分**: +1分 (99 → 100)
- **交付物**:
  1. E2E测试100%通过
  2. Scope覆盖率90%+
  3. 性能基准测试
- **验收**: 最终得分=100分

---

## 当前得分详情

| 维度 | 得分 | 满分 | 达成率 | 主要问题 |
|------|------|------|--------|----------|
| 1. 核心代码 | 20 | 20 | 100% | 无 ✅ |
| 2. 测试覆盖 | 15 | 20 | 75% | E2E环境、Scope覆盖率 ⚠️ |
| 3. 文档完整性 | 20 | 20 | 100% | 无 ✅ |
| 4. 集成验证 | 16 | 20 | 80% | E2E通过率 ⚠️ |
| 5. 运维/观测 | 18 | 20 | 90% | 回放工具 ⚠️ |
| **总分** | **89** | **100** | **89%** | - |

### 测试维度详情

**Unit测试**: 390/390 passed (100%) ✅
**E2E测试**: 14/28 passed (50%) ❌
- Retry E2E: 3/16 (18.75%) ❌
- Timeout E2E: 4/5 (80%) ⚠️
- Cancel E2E: 7/7 (100%) ✅

**Scope Coverage**:
- 行覆盖: 62.8% (目标90%) ⚠️
- 分支覆盖: 41.53% (目标80%) ⚠️
- 缺口: 27.2%

**Project Coverage**:
- 行覆盖: 42.37% ✅
- 状态: 可追踪 ✅

---

## 立即行动

### Step 1: 启动P2-A（本周）

```bash
# 1. 修复Retry E2E环境
vim tests/integration/task/test_retry_e2e.py
# 添加setup_retry_test_db fixture

# 2. 修复Timeout exit_reason
vim agentos/core/runner/task_runner.py
# 在超时处理中添加metadata

# 3. 验证
pytest tests/integration/task/test_retry_e2e.py -v
pytest tests/integration/task/test_timeout_e2e.py -v
pytest tests/integration/task/ -v

# 预期: 95分 ✅
```

### Step 2: 并行P2-B和P2-C（下周）

**P2-B分支**:
```bash
# 补充测试
touch tests/unit/task/test_state_machine_errors.py
touch tests/unit/task/test_work_items_coverage.py
vim tests/unit/task/test_event_service.py

# 验证覆盖率
./scripts/coverage_scope_task.sh

# 预期: 85%+ ✅
```

**P2-C分支**:
```bash
# 创建回放工具
touch scripts/replay_task_lifecycle.py
chmod +x scripts/replay_task_lifecycle.py

# 添加测试
touch tests/unit/test_replay_tool.py

# 验证
python3 scripts/replay_task_lifecycle.py <task_id>

# 预期: 99分 ✅
```

### Step 3: 冲刺P2-D（第三周）

```bash
# 完整性检查
pytest tests/unit/task -v
pytest tests/integration/task -v
./scripts/coverage_scope_task.sh

# 预期: 100分 ✅
```

---

## 验收标准

### 阶段1（95分）
- ✅ E2E测试通过率 ≥ 90%
- ✅ Retry E2E: 16/16 passed
- ✅ Timeout E2E: 5/5 passed
- ✅ 退出码 = 0

### 阶段2（99分）
- ✅ Scope Coverage ≥ 85%
- ✅ 回放脚本可执行
- ✅ 所有新测试通过

### 阶段3（100分）
- ✅ E2E测试通过率 = 100%
- ✅ Scope Coverage ≥ 90%
- ✅ 性能基准建立

---

## 关键文档

1. **P2_STRATEGIC_PLAN.md** - 完整战略规划
2. **P2_TASK_DEFINITIONS.md** - 详细任务定义
3. **CURRENT_SCORE_BREAKDOWN.md** - 当前评分分解
4. **P2_QUICK_REFERENCE.md** - 本文档

---

## 时间预算

| 阶段 | 任务 | 工时 | 累计工时 | 累计得分 |
|------|------|------|----------|----------|
| 起点 | - | 0h | 0h | 89分 |
| 阶段1 | P2-A | 1.5h | 1.5h | 95分 (A+) |
| 阶段2 | P2-B + P2-C | 4.0h | 5.5h | 99分 (A+) |
| 阶段3 | P2-D | 2.0h | 7.5h | 100分 (满分) |

---

## 关键洞察

1. **快速提升**: 1.5小时即可达成A+（95分）
2. **并行执行**: P2-B和P2-C可同时进行
3. **ROI优先**: P2-A的ROI最高（4.0分/小时）
4. **质量优先**: 62.8%覆盖率是真实可信的
5. **务实路径**: 7.5小时达成满分是可行的

---

**生成时间**: 2026-01-30
**版本**: v1.0
**下一步**: 立即启动P2-A任务
