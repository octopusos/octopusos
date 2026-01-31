# AgentOS v3 文档索引

## 概述

AgentOS v3 引入了 **Shadow Evaluation + Controlled Adaptation** 系统，实现了分类器的安全进化机制。

**核心理念**: 系统在"不改变行为"的前提下，学会比较"如果当时这样判断会不会更好"。

---

## 📖 文档导航

### 🎯 快速入门

1. **[v3 实施完成报告](./V3_IMPLEMENTATION_COMPLETE.md)** ⭐ 必读
   - 完整的系统概述
   - 分阶段交付成果
   - 使用指南和最佳实践
   - 工作流程示例

### 🏗️ 技术架构

2. **[Shadow Classifier Registry](./SHADOW_CLASSIFIER_REGISTRY.md)**
   - Shadow 分类器注册和管理
   - 多版本并行运行机制
   - 配置文件格式

3. **[Shadow Classifier Registry 快速参考](./SHADOW_CLASSIFIER_REGISTRY_QUICK_REF.md)**
   - API 快速查询
   - 常见使用场景
   - 故障排除

4. **[Audit Log v3 Schema](./AUDIT_LOG_V3_SCHEMA.md)**
   - 扩展的审计日志结构
   - 多决策记录机制
   - 查询接口

### 📊 评估系统

5. **Shadow Score Calculator** (位于根目录)
   - Reality Alignment Score 计算逻辑
   - 用户行为信号权重
   - 评分可解释性

6. **Decision Comparator** (位于根目录)
   - Active vs Shadow 对比指标
   - 改进率计算
   - 聚合分析

### 🤖 BrainOS 集成

7. **Improvement Proposal Generation** (位于根目录)
   - 自动提案生成逻辑
   - 风险评估算法
   - 定时任务配置

8. **Review Queue API** (位于根目录)
   - 人工审查接口
   - 批准/拒绝流程
   - 审计追踪

### 🔧 工具链

9. **Classifier Version Manager** (位于根目录)
   - 版本号管理
   - 变更日志
   - 回滚机制

10. **Classifier Migration Tool** (位于根目录)
    - Shadow → Active 安全迁移
    - 前置条件验证
    - 一键回滚

---

## 🗂️ 验收报告

所有任务的详细验收报告位于项目根目录：

- `DECISION_CANDIDATE_ACCEPTANCE_REPORT.md` - Task #1
- `SHADOW_CLASSIFIER_REGISTRY_ACCEPTANCE_REPORT.md` - Task #2
- `TASK_3_AUDIT_LOG_ACCEPTANCE_REPORT.md` - Task #3
- `SHADOW_SCORE_CALCULATOR_ACCEPTANCE_REPORT.md` - Task #4
- `TASK_5_DECISION_COMPARATOR_ACCEPTANCE_REPORT.md` - Task #5
- `DECISION_COMPARISON_VIEW_ACCEPTANCE_REPORT.md` - Task #6
- `TASK_7_IMPROVEMENT_PROPOSAL_ACCEPTANCE_REPORT.md` - Task #7
- `IMPROVEMENT_PROPOSAL_GENERATION_ACCEPTANCE_REPORT.md` - Task #8
- Review Queue API 验收报告 - Task #9
- Classifier Version Manager 验收报告 - Task #10
- Classifier Migration Tool 验收报告 - Task #11

---

## 🚀 快速开始

### 1. 查看当前 Shadow 状态

```bash
# 查看所有 Shadow Classifiers
python3 -c "from agentos.core.chat.shadow_registry import get_shadow_registry; \
print(get_shadow_registry().get_active_shadows())"
```

### 2. 查看决策对比

访问 WebUI:
```
http://localhost:8000/
```

导航到 "Decision Comparison" 视图。

### 3. 生成改进提案

```bash
# 手动触发（Dry Run）
python3 -m agentos.jobs.improvement_proposal_generation \
  --shadow=v2-shadow-a \
  --dry-run

# 实际生成
python3 -m agentos.jobs.improvement_proposal_generation \
  --shadow=v2-shadow-a
```

### 4. 审查提案

```bash
# 查看待审查提案
curl http://localhost:8000/api/v3/review-queue

# 批准提案
curl -X POST http://localhost:8000/api/v3/review-queue/BP-001/approve
```

### 5. 迁移 Shadow

```bash
# 验证前置条件
agentos classifier migrate verify --shadow v2-shadow-a

# 执行迁移
agentos classifier migrate to-active --shadow v2-shadow-a
```

---

## 📊 系统架构图

```
User Question
    ↓
InfoNeedClassifier System (Active + Shadow)
    ↓
DecisionSet Storage (Audit Log v3)
    ↓
Reality Alignment Score (Shadow Evaluator)
    ↓
Decision Comparator (对比分析)
    ↓
WebUI Dashboard (可视化)
    ↓
BrainOS Proposal Generator (自动建议)
    ↓
Review Queue API (人工审查)
    ↓
Version Manager (版本管理)
    ↓
Migration Tool (安全迁移)
```

---

## 🎯 核心原则（红线机制）

### ❌ 明确禁止

- BrainOS 不能直接修改 InfoNeedClassifier 决策
- Shadow 结果永不影响实时用户行为
- 不使用"答案正确性"作为反馈信号
- 未经人类确认的规则不能自动上线

### ✅ 唯一允许

- 并行模拟（Shadow Registry）
- 事后对比（Decision Comparator）
- 证据积累（Reality Alignment Score）
- 人工确认后迁移（Review Queue + Migration Tool）

---

## 📈 关键指标

### 代码产出
- **生产代码**: 35 个文件，~8,500 行
- **测试代码**: 40 个文件，~10,200 行
- **文档**: 25 个文件，~5,000 行

### 测试覆盖
- **总测试数**: 365+
- **通过率**: 100%
- **测试类型**: 单元测试、集成测试、E2E 测试

### 数据库
- **新增表**: 8 个
- **新增索引**: 40+
- **Schema 版本**: v38 → v42

---

## 🔗 相关文档

### 上层架构
- [Evolvable System Architecture](../EVOLVABLE_SYSTEM_ARCHITECTURE.md)
- [Evolvable System Developer Guide](../EVOLVABLE_SYSTEM_DEVELOPER_GUIDE.md)

### 相关系统
- [Info Need Classifier Integration](../INFO_NEED_CLASSIFIER_INTEGRATION_SUMMARY.md)
- [Info Need Audit Implementation](../INFO_NEED_AUDIT_IMPLEMENTATION.md)
- [Info Need Metrics Dashboard](../INFO_NEED_METRICS_DASHBOARD.md)

### 测试和验收
- [Acceptance Tests README](../../tests/acceptance/README_ACCEPTANCE_TESTS.md)
- [Evolvable System Acceptance Tests](../../tests/acceptance/test_evolvable_system_acceptance.py)

---

## 📞 支持

### 问题排查

1. **Shadow 没有运行？**
   - 检查配置文件：`agentos/config/shadow_classifiers.yaml`
   - 确认 `enabled: true`
   - 查看日志：`agentos/logs/shadow_registry.log`

2. **Decision Comparison View 没有数据？**
   - 确认 Shadow 已运行一段时间（至少 24 小时）
   - 检查数据库：`SELECT COUNT(*) FROM decision_candidates`
   - 运行 Shadow Score 计算

3. **提案生成失败？**
   - 检查样本数是否足够（>= 50）
   - 确认 Shadow 和 Active 有显著差异
   - 查看日志：`agentos/logs/proposal_generation.log`

### 常见问题

**Q: Shadow 决策会影响用户吗？**
A: 不会。Shadow 决策仅用于事后分析，永不触发外部操作。

**Q: 多久可以看到改进提案？**
A: 建议至少运行 7 天收集足够样本（>= 100）后再生成提案。

**Q: 迁移失败了怎么办？**
A: 使用 `agentos classifier migrate rollback` 立即回滚，系统会在 5 分钟内恢复。

**Q: 可以同时运行多个 Shadow 吗？**
A: 可以，但建议初期只运行 1-2 个，稳定后再增加。

---

## 📅 更新日志

### v3.0.0 (2026-01-31)
- ✅ 完整实施 Shadow Evaluation + Controlled Adaptation 系统
- ✅ 11 个核心任务全部完成
- ✅ 365+ 测试通过
- ✅ 生产就绪

---

## 👥 贡献者

感谢以下 Agent 的贡献：
- ae10553 - DecisionCandidate 数据模型
- abb3e6a - Shadow Classifier Registry
- a9dca2a - Audit Log 扩展
- ae50b6f - Shadow Score 计算引擎
- a3edd82 - 决策对比指标生成
- a9cb804 - Decision Comparison View
- a404b7f - ImprovementProposal 模型
- a4ec252 - BrainOS 改进提案生成
- a508908 - Review Queue API
- a88e37f - Classifier 版本化工具
- a7b6a1e - Shadow → Active 迁移工具

**协调者**: Claude Sonnet 4.5

---

*最后更新: 2026-01-31*
