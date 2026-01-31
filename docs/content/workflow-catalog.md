# Workflow Catalog

AgentOS v0.6 提供 18 个标准 Workflow，覆盖完整的软件开发生命周期。

## 🔍 Discovery & Planning (5 个)

### 1. problem_discovery

**用途**：识别和框定一个值得解决的真实问题

**适用场景**：
- 项目初期，需求不明确
- 收到模糊的功能请求
- 需要深入理解用户痛点

**不适用场景**：
- 需求已经非常明确
- 纯技术性任务（如升级依赖）

**阶段**：
1. `signal_collection` - 收集信号和证据
2. `problem_framing` - 框定问题边界
3. `success_criteria` - 定义成功标准

**交互策略**：允许提问（当模糊度 > 0.6 或缺少必需字段时）

---

### 2. requirements_definition

**用途**：定义功能性和非功能性需求

**适用场景**：
- 问题已框定，需要具体化需求
- 需要明确验收标准
- 多方利益相关者需要对齐

**不适用场景**：
- 探索性研究（用 problem_discovery）
- 实现细节讨论（用 detailed_design）

**阶段**：
1. `scope_definition` - 定义范围
2. `constraints_capture` - 捕获约束
3. `acceptance_criteria` - 定义验收标准

**交互策略**：允许提问（需要澄清范围或约束时）

---

### 3. system_design

**用途**：产生系统级架构设计

**适用场景**：
- 需要架构决策
- 有多种设计方案需要权衡
- 涉及关键技术选型

**不适用场景**：
- 小型功能实现（直接用 feature_implementation）
- 实现细节（用 detailed_design）

**阶段**：
1. `architecture_options` - 列出架构选项
2. `tradeoff_analysis` - 权衡分析
3. `decision_record` - 记录决策

**交互策略**：允许提问（有冲突约束或关键风险时）

---

### 4. detailed_design

**用途**：定义模块级和接口级设计

**适用场景**：
- 系统设计已完成
- 需要详细的组件设计
- 需要定义接口契约

**不适用场景**：
- 架构级决策（用 system_design）
- 直接编码（用 feature_implementation）

**阶段**：
1. `component_breakdown` - 组件分解
2. `interface_definition` - 接口定义
3. `dependency_mapping` - 依赖映射

**交互策略**：允许在组件分解阶段提问

---

### 5. implementation_planning

**用途**：规划实现步骤和排序

**适用场景**：
- 大型功能需要分步实现
- 有复杂依赖关系
- 需要风险识别

**不适用场景**：
- 小型功能（直接实现）
- 探索性编码

**阶段**：
1. `task_decomposition` - 任务分解
2. `dependency_ordering` - 依赖排序
3. `risk_identification` - 风险识别

**交互策略**：允许在风险识别阶段提问

---

## 💻 Implementation & Testing (4 个)

### 6. feature_implementation

**用途**：实现一个范围明确的功能

**适用场景**：
- 设计已完成
- 需求明确
- 范围可控

**不适用场景**：
- 需求不明确（先用 requirements_definition）
- 大型重构（用 refactoring）

**阶段**：
1. `code_creation` - 代码创建
2. `local_validation` - 本地验证

**交互策略**：不允许提问（必须有完整设计）

---

### 7. refactoring

**用途**：改进内部结构而不改变外部行为

**适用场景**：
- 代码质量下降
- 需要优化结构
- 技术债务偿还

**不适用场景**：
- 功能变更（用 feature_implementation）
- 架构级变更（用 architectural_evolution）

**阶段**：
1. `refactor_intent` - 重构意图
2. `refactor_execution` - 重构执行
3. `regression_check` - 回归检查

**交互策略**：允许在意图确认阶段提问

---

### 8. testing_strategy

**用途**：定义测试覆盖策略

**适用场景**：
- 新功能需要测试计划
- 需要定义测试范围
- 多种测试类型需要协调

**不适用场景**：
- 直接写测试（用 test_implementation）
- 已有明确测试策略

**阶段**：
1. `test_scope` - 测试范围
2. `test_types` - 测试类型
3. `coverage_expectations` - 覆盖期望

**交互策略**：允许在范围定义阶段提问

---

### 9. test_implementation

**用途**：按策略实现测试

**适用场景**：
- 测试策略已定义
- 需要编写具体测试
- 需要分析测试失败

**不适用场景**：
- 没有测试策略（先用 testing_strategy）
- 探索性测试

**阶段**：
1. `test_creation` - 测试创建
2. `failure_analysis` - 失败分析

**交互策略**：允许在失败分析时提问

---

## 🛡️ Governance & Review (3 个)

### 10. code_review

**用途**：审查代码变更的质量和风险

**适用场景**：
- PR/MR 审查
- 质量门禁
- 风险评估

**不适用场景**：
- 安全审查（用 security_review）
- 性能分析（用 performance_analysis）

**阶段**：
1. `diff_analysis` - 差异分析
2. `risk_assessment` - 风险评估
3. `improvement_suggestions` - 改进建议

**交互策略**：允许在风险评估时提问

---

### 11. security_review

**用途**：识别安全风险和缓解措施

**适用场景**：
- 敏感功能实现
- 安全合规检查
- 威胁建模

**不适用场景**：
- 通用代码审查（用 code_review）
- 性能问题（用 performance_analysis）

**阶段**：
1. `threat_modeling` - 威胁建模
2. `vulnerability_analysis` - 漏洞分析
3. `mitigation_plan` - 缓解计划

**交互策略**：允许在威胁建模时提问

---

### 12. performance_analysis

**用途**：分析性能特征

**适用场景**：
- 性能瓶颈识别
- 优化方案评估
- SLA 验证

**不适用场景**：
- 功能性问题
- 安全问题

**阶段**：
1. `bottleneck_identification` - 瓶颈识别
2. `optimization_options` - 优化选项
3. `tradeoff_decision` - 权衡决策

**交互策略**：允许在瓶颈识别和决策时提问

---

## 🚀 Deployment & Release (2 个)

### 13. deployment_planning

**用途**：规划部署和发布

**适用场景**：
- 生产环境发布
- 需要部署策略
- 需要回滚计划

**不适用场景**：
- 开发环境部署
- 简单的代码提交

**阶段**：
1. `rollout_strategy` - 发布策略
2. `rollback_plan` - 回滚计划
3. `readiness_check` - 就绪检查

**交互策略**：允许在发布策略时提问

---

### 14. release_management

**用途**：协调发布活动

**适用场景**：
- 版本发布
- 多团队协作发布
- 需要变更日志

**不适用场景**：
- 单一功能部署（用 deployment_planning）
- hotfix 修复

**阶段**：
1. `release_scope` - 发布范围
2. `change_log` - 变更日志
3. `release_signals` - 发布信号

**交互策略**：允许在范围定义时提问

---

## 🔧 Operations & Maintenance (3 个)

### 15. incident_response

**用途**：响应生产事故

**适用场景**：
- 生产故障
- 紧急问题处理
- 需要快速止损

**不适用场景**：
- 计划内维护（用 maintenance_planning）
- 非紧急问题

**阶段**：
1. `incident_triage` - 事故分级
2. `containment_strategy` - 遏制策略
3. `postmortem_outline` - 事后分析大纲

**交互策略**：允许在分级和策略制定时提问

---

### 16. maintenance_planning

**用途**：规划长期系统维护

**适用场景**：
- 技术债务规划
- 系统升级计划
- 维护窗口安排

**不适用场景**：
- 紧急修复（用 incident_response）
- 架构重构（用 architectural_evolution）

**阶段**：
1. `debt_identification` - 债务识别
2. `prioritization` - 优先级排序
3. `maintenance_schedule` - 维护计划

**交互策略**：允许在债务识别时提问

---

### 17. architectural_evolution

**用途**：引导大规模架构变更

**适用场景**：
- 架构升级
- 技术栈迁移
- 系统重构

**不适用场景**：
- 小型重构（用 refactoring）
- 单一功能实现

**阶段**：
1. `evolution_drivers` - 演化驱动因素
2. `target_state` - 目标状态
3. `migration_strategy` - 迁移策略

**交互策略**：允许在驱动因素和目标状态时提问

---

## 📚 Learning (1 个)

### 18. knowledge_consolidation

**用途**：将经验教训整理为可复用知识

**适用场景**：
- 项目复盘
- 模式提取
- 最佳实践总结

**不适用场景**：
- 实时问题解决
- 具体功能实现

**阶段**：
1. `signal_extraction` - 信号提取
2. `pattern_identification` - 模式识别
3. `codification` - 编码化

**交互策略**：允许在编码化阶段提问

---

## 使用建议

### 如何选择 Workflow？

1. **明确当前阶段**：你处于 SDLC 的哪个阶段？
2. **识别主要目标**：当前任务的核心目标是什么？
3. **检查前置条件**：是否满足 workflow 的前置要求？
4. **评估范围大小**：任务规模是否匹配 workflow？

### 组合使用

Workflow 可以组合使用：

```
problem_discovery 
  → requirements_definition 
  → system_design 
  → implementation_planning 
  → feature_implementation 
  → testing_strategy 
  → test_implementation 
  → code_review 
  → deployment_planning
```

### 自定义 Workflow

如果标准 Workflow 不满足需求，可以：
1. 注册自定义 Workflow
2. 复制现有 Workflow 并修改（记录血缘）
3. 提交 PR 贡献新的标准 Workflow

---

**版本**: v0.6.0  
**更新日期**: 2026-01-25  
**状态**: ✅ 18 个 Workflow 全部可用
