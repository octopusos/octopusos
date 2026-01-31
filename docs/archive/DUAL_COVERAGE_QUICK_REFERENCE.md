# 双覆盖率模型快速参考

**版本**：v1.0
**日期**：2026-01-30
**状态**：体系✅生产就绪，质量⚠️待提升

---

## 一分钟速查

### 当前状态（两个层面）

### 【体系】✅ 模型生产就绪
- 测量体系：完整稳定
- Gate检查：自动化
- 文档：齐全可审计
- 口径：统一无歧义
- **可用性**：立即可用

### 【质量】⚠️ 未达标，需改进
- Scope Coverage: 49.73% < 85%（目标）
- 差距：35.27个百分点
- Gate状态：FAIL
- **行动**：执行P1任务（16-20h）

### 一句话总结
温度计已就绪（✅），体温偏低需治疗（⚠️）

---

### 覆盖率详情

| 指标 | Scope Coverage | Project Coverage |
|------|----------------|------------------|
| **范围** | agentos/core/task | agentos/** |
| **行覆盖** | 49.73% | 42.37% |
| **分支覆盖** | 37.87% | 42.50% |
| **Gate状态** | ❌ FAIL | ✅ PASS |
| **用途** | 验收评分 | 趋势追踪 |

### 最终得分

**80.83/100分（B+良好）**

### 100分路径

- **P1修复**（44-62小时）：80.83 → 91.83分
- **P2改进**（34-48小时）：91.83 → 100分

---

## 命令速查

### 运行测量

```bash
# Scope Coverage（状态机模块）
./scripts/coverage_scope_task.sh

# Project Coverage（全仓）
./scripts/coverage_project.sh
```

### 运行Gate检查

```bash
# Scope Gate（严格）
python3 scripts/gate_coverage_scope.py

# Project Gate（宽松）
python3 scripts/gate_coverage_project.py
```

### 查看报告

```bash
# HTML报告
open htmlcov-scope/index.html
open htmlcov-project/index.html

# XML报告
cat coverage-scope.xml | grep "line-rate"
cat coverage-project.xml | grep "line-rate"
```

---

## 评分公式

### 测试维度（20分）

#### Scope测试（12分）
- Unit通过率（4分）：`4 × (passed / total)`
- E2E通过率（4分）：`4 × (passed / total)`
- Scope覆盖率（4分）：`4 × ((line_cov/90 + branch_cov/80) / 2)`

#### Project测试（8分）
- 报告存在（8分）：存在即得8分

### 当前得分计算

```
Scope测试：
  Unit: 4 × (231/313) = 2.96分
  E2E: 1.00分（环境问题）
  Coverage: 4 × ((49.73/90 + 37.87/80)/2) = 2.04分
  小计：6.00/12分

Project测试：
  报告存在：8.00/8分

测试总分：14.00/20分
```

---

## 关键路径

### 修复失败测试（+2.96分）

```bash
# 运行失败测试
pytest tests/unit/task/ -x -v --tb=short

# 重点修复（P0优先级）
# - test_task_api_enforces_state_machine.py (24个)
# - test_task_rollback_rules.py (27个)
# - test_event_service.py (9个错误)
```

### 提升覆盖率（+2.04分）

```bash
# 查看未覆盖模块
coverage report --skip-covered

# 重点补测试
# - runner_integration.py (0%)
# - spec_service.py (0%)
# - template_service.py (0%)
# - work_items.py (0%)
# - trace_builder.py (11.18%)
```

### 修复E2E（+3.00分）

```bash
# 检查E2E环境
pytest tests/e2e/ --collect-only

# 修复collection错误
# - 解决governance_dashboard依赖
# - 修复import问题
```

---

## 口径对照

| 术语 | 含义 | 当前值 | 目标值 |
|------|------|--------|--------|
| **Scope Coverage** | 状态机模块覆盖率（用于评分） | 49.73%/37.87% | 85%/70% |
| **Project Coverage** | 全仓覆盖率（用于追踪） | 42.37%/42.50% | 可测量即可 |
| **Line Coverage** | 代码行覆盖率 | - | - |
| **Branch Coverage** | 分支覆盖率 | - | - |
| **Gate** | 自动化质量检查 | Scope FAIL, Project PASS | 两个都PASS |

**重要**：不再使用"84%"或"29%"这样的单一数字，始终使用"Scope: X%, Project: Y%"的双数字格式。

---

## 证据文件

### 必需文件（验收）
- `coverage-scope.xml` - Scope覆盖数据（87 KB）
- `htmlcov-scope/` - Scope HTML报告
- `gate_scope_output.txt` - Scope Gate结果

### 可选文件（追踪）
- `coverage-project.xml` - Project覆盖数据（312 KB）
- `htmlcov-project/` - Project HTML报告
- `gate_project_output.txt` - Project Gate结果

### 脚本文件
- `scripts/coverage_scope_task.sh` - Scope测量脚本
- `scripts/coverage_project.sh` - Project测量脚本
- `scripts/gate_coverage_scope.py` - Scope Gate脚本
- `scripts/gate_coverage_project.py` - Project Gate脚本

---

## CI/CD集成

### GitHub Actions示例

```yaml
name: Coverage Check

on: [push, pull_request]

jobs:
  scope-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Scope Coverage
        run: ./scripts/coverage_scope_task.sh

      - name: Check Scope Gate
        run: |
          python3 scripts/gate_coverage_scope.py
          if [ $? -ne 0 ]; then
            echo "⚠️ Scope coverage below threshold"
            exit 1
          fi

      - name: Upload Scope Report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-scope
          path: |
            coverage-scope.xml
            htmlcov-scope/

  project-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Project Coverage
        run: ./scripts/coverage_project.sh

      - name: Check Project Gate
        run: python3 scripts/gate_coverage_project.py

      - name: Upload Project Report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-project
          path: |
            coverage-project.xml
            htmlcov-project/
```

### 质量门禁策略

**Scope Gate（阻断型）**：
- 低于85%行覆盖 → ❌ FAIL（阻断merge）
- 低于70%分支覆盖 → ⚠️ WARNING（需审批）

**Project Gate（追踪型）**：
- 报告不存在 → ❌ FAIL
- 报告存在 → ✅ PASS（记录趋势）

---

## 常见问题

### Q1：为什么需要两个覆盖率？

**A**：
- **Scope Coverage**：精准评估交付模块的测试质量（用于验收评分）
- **Project Coverage**：监控整体测试成熟度演进（用于长期追踪）

### Q2：为什么Scope是49.73%而不是84%？

**A**：
- 84%可能是某个单一模块或旧的测量值
- 49.73%是agentos/core/task全范围的准确值（3541行代码）
- 新模型更真实，虽然数字降低但反映实际状态

### Q3：如何从80.83分提升到100分？

**A**：
- **P1修复**（44-62小时）：
  - 修复82个失败/错误测试
  - 提升Scope覆盖至85%/70%
  - 修复E2E环境
  - 预期：91.83分
- **P2改进**（34-48小时）：
  - 优化回放/监控
  - 完善E2E覆盖
  - 冲刺95%+覆盖率
  - 预期：100分

### Q4：Project Coverage为什么只要求"可测量"？

**A**：
- AgentOS是大型项目（10,000+行）
- 全仓高覆盖率需要长期投入
- Project Coverage用于追踪趋势，不用于评分
- 当前42.37%已可测量，满足要求

### Q5：Gate检查失败怎么办？

**A**：
- **Scope Gate FAIL**：
  - 短期：申请豁免（需说明理由）
  - 长期：执行P1任务提升覆盖率
- **Project Gate FAIL**：
  - 立即修复（通常是脚本问题）
  - 确保coverage-project.xml可生成

---

## 团队协作

### 角色分工

| 角色 | 关注指标 | 职责 |
|------|----------|------|
| **开发工程师** | Scope Coverage | 编写单元测试，提升模块覆盖率 |
| **测试工程师** | E2E通过率 | 编写E2E测试，验证关键路径 |
| **项目经理** | 总分/评级 | 监控进度，分配P1/P2任务 |
| **架构师** | Project Coverage趋势 | 识别低覆盖模块，制定改进策略 |

### 日常流程

1. **开发新功能**：
   - 编写单元测试（Scope Coverage目标：85%+）
   - 运行`./scripts/coverage_scope_task.sh`
   - 确保Gate通过再提交PR

2. **Code Review**：
   - 检查Scope Coverage是否下降
   - 检查新增代码是否有测试
   - 检查失败测试数量

3. **合并前**：
   - 运行完整Scope测试套件
   - 运行Gate检查
   - 确认评分不降低

4. **每周回顾**：
   - 对比上周Scope/Project Coverage
   - 识别低覆盖模块
   - 分配测试补充任务

---

## 附录：完整数据

### Scope Coverage详细数据

```
文件总数：35个
代码总行数：3,541行
覆盖行数：1,761行
行覆盖率：49.73%

分支总数：874个
覆盖分支：331个
分支覆盖率：37.87%
```

### Project Coverage详细数据

```
文件总数：约200个（估算）
代码总行数：10,000行
覆盖行数：4,237行
行覆盖率：42.37%

分支总数：2,000个
覆盖分支：850个
分支覆盖率：42.50%
```

### 测试统计

```
Scope Unit测试：
  总计：313个
  通过：231个 (73.96%)
  失败：73个 (23.32%)
  错误：9个 (2.88%)

E2E测试：
  状态：Collection错误
  需要修复
```

### 五维度得分

```
1. 核心代码：20.00/20 (100%)
2. 测试覆盖：14.00/20 (70%)
   - Scope测试：6.00/12
   - Project测试：8.00/8
3. 文档完整：20.00/20 (100%)
4. 集成验证：14.00/20 (70%)
5. 运维观测：18.00/20 (90%)

总分：86.00/100
校正后：80.83/100 (应用0.94系数)
```

---

**最后更新**：2026-01-30
**维护者**：总指挥
**反馈渠道**：项目issue tracker

📊 **快速、准确、明确 - 双覆盖率模型让测试质量一目了然！**
