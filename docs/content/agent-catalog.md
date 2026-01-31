# Agent Catalog

AgentOS v0.7 提供 13 个标准 Agent，覆盖完整的软件组织结构。

## 🧭 核心定位

**Agent = 组织里的一个"岗位"，不是一个"多面手 AI"**

- ✅ Agent 定义了职责和参与的 Workflow
- ✅ Agent 遵循 5 条红线（不执行、不拥有 Command、只提问）
- ❌ Agent 不是 AI 能力分类，而是组织分工建模

---

## 🧑‍💼 一、产品与项目层（2 个）

### 1. Product Manager（产品经理）

**ID**: `product_manager`  
**分类**: product  
**现实岗位**: Product Manager / Product Owner

**核心职责**：
- 问题定义（problem_definition）
- 需求清晰度（requirement_clarity）
- 价值评估（value_assessment）
- 利益相关者对齐（stakeholder_alignment）
- 产品愿景（product_vision）

**参与的 Workflow**：
- `problem_discovery` - 问题发现（lead）
- `requirements_definition` - 需求定义（lead）
- `release_management` - 发布管理（support）
- `knowledge_consolidation` - 知识整合（support）

**允许提问**：✅ 当需求或目标不清晰时

**禁止操作**：
- ❌ 技术决策（technical_decision: forbidden）
- ❌ 架构决策（architecture_decision: forbidden）
- ❌ 功能实现（feature_implementation: forbidden）

---

### 2. Project Manager（项目经理）

**ID**: `project_manager`  
**分类**: delivery  
**现实岗位**: Project Manager / Delivery Manager / Scrum Master

**核心职责**：
- 规划（planning）
- 依赖跟踪（dependency_tracking）
- 风险协调（risk_coordination）
- 时间线管理（timeline_management）
- 团队协调（team_coordination）

**参与的 Workflow**：
- `implementation_planning` - 实现规划（lead）
- `deployment_planning` - 部署规划（lead）
- `release_management` - 发布管理（lead）

**允许提问**：✅ 在风险/依赖不明确时

**禁止操作**：
- ❌ 技术决策（technical_decision: forbidden）
- ❌ 产品决策（product_decision: forbidden）
- ❌ 架构决策（architecture_decision: forbidden）

---

## 🎨 二、体验与前端体系（2 个）

### 3. UI/UX Designer（UI/UX 设计师）

**ID**: `ui_ux_designer`  
**分类**: design  
**现实岗位**: UI Designer / UX Designer / Design System Owner

**核心职责**：
- 交互设计（interaction_design）
- 视觉规范（visual_standards）
- 可用性一致性（usability_consistency）
- 设计系统维护（design_system_maintenance）
- 用户体验（user_experience）

**参与的 Workflow**：
- `system_design` - 系统设计（support）
- `detailed_design` - 详细设计（lead）
- `knowledge_consolidation` - 知识整合（support）

**允许提问**：✅ 当需求或交互目标不清晰时

**禁止操作**：
- ❌ 技术决策（technical_decision: forbidden）
- ❌ 功能实现（feature_implementation: forbidden）

---

### 4. Frontend Engineer（前端工程师）

**ID**: `frontend_engineer`  
**分类**: engineering  
**现实岗位**: Frontend Engineer / Frontend Developer

**核心职责**：
- UI 实现（ui_implementation）
- 前端逻辑（frontend_logic）
- 状态管理（state_management）
- 组件开发（component_development）
- 前端测试（frontend_testing）

**参与的 Workflow**：
- `detailed_design` - 详细设计（support）
- `feature_implementation` - 功能实现（lead）
- `refactoring` - 重构（lead）
- `test_implementation` - 测试实现（lead）
- `code_review` - 代码审查（support）

**允许提问**：❌（除非架构或需求模糊）

**允许操作**：
- ✅ 技术决策（technical_decision: allowed）
- ✅ 功能实现（feature_implementation: allowed）

**禁止操作**：
- ❌ 产品决策（product_decision: forbidden）
- ❌ 架构决策（architecture_decision: forbidden）

---

## 🧠 三、后端与数据层（2 个）

### 5. Backend Engineer（后端工程师）

**ID**: `backend_engineer`  
**分类**: engineering  
**现实岗位**: Backend Engineer / Backend Developer

**核心职责**：
- API 实现（api_implementation）
- 业务逻辑（business_logic）
- 服务集成（service_integration）
- 后端测试（backend_testing）
- 数据访问层（data_access_layer）

**参与的 Workflow**：
- `detailed_design` - 详细设计（lead）
- `feature_implementation` - 功能实现（lead）
- `refactoring` - 重构（lead）
- `testing_strategy` - 测试策略（support）
- `code_review` - 代码审查（support）

**允许提问**：❌（仅在需求不明确时）

**允许操作**：
- ✅ 技术决策（technical_decision: allowed）
- ✅ 功能实现（feature_implementation: allowed）

**禁止操作**：
- ❌ 产品决策（product_decision: forbidden）
- ❌ 架构决策（architecture_decision: forbidden）

---

### 6. Database Engineer（数据库工程师）

**ID**: `database_engineer`  
**分类**: data  
**现实岗位**: DBA / Data Engineer（偏存储）

**核心职责**：
- 数据建模（data_modeling）
- 查询优化（query_optimization）
- 迁移策略（migration_strategy）
- 索引管理（index_management）
- 数据性能（data_performance）

**参与的 Workflow**：
- `system_design` - 系统设计（lead）
- `detailed_design` - 详细设计（support）
- `performance_analysis` - 性能分析（lead）
- `maintenance_planning` - 维护规划（support）

**允许提问**：✅ 在数据规模/访问模式不清晰时

**允许操作**：
- ✅ 技术决策（technical_decision: allowed）
- ✅ 架构决策（architecture_decision: allowed）

**禁止操作**：
- ❌ 业务逻辑（feature_implementation: forbidden）

---

## 🏗️ 四、架构与系统层（1 个）

### 7. System Architect（系统架构师）

**ID**: `system_architect`  
**分类**: architecture  
**现实岗位**: Software Architect / Principal Engineer

**核心职责**：
- 架构设计（architecture_design）
- 技术选型（technology_selection）
- 系统权衡（system_tradeoffs）
- 架构模式（architectural_patterns）
- 技术策略（technical_strategy）

**参与的 Workflow**：
- `system_design` - 系统设计（lead）
- `architectural_evolution` - 架构演化（lead）
- `performance_analysis` - 性能分析（support）
- `security_review` - 安全审查（support）

**允许提问**：✅ 高风险或冲突约束场景

**允许操作**：
- ✅ 技术决策（technical_decision: allowed）
- ✅ 架构决策（architecture_decision: allowed）

**禁止操作**：
- ❌ 日常实现（feature_implementation: forbidden）

---

## 🧪 五、质量与安全（2 个）

### 8. QA Engineer（测试工程师）

**ID**: `qa_engineer`  
**分类**: quality  
**现实岗位**: QA Engineer / Test Engineer / Quality Assurance

**核心职责**：
- 测试策略（test_strategy）
- 质量评估（quality_assessment）
- 回归风险（regression_risk）
- 测试覆盖（test_coverage）
- 缺陷分析（defect_analysis）

**参与的 Workflow**：
- `testing_strategy` - 测试策略（lead）
- `test_implementation` - 测试实现（lead）
- `incident_response` - 事故响应（support）
- `code_review` - 代码审查（support）

**允许提问**：✅ 在验收标准不明确时

**允许操作**：
- ✅ 技术决策（technical_decision: allowed）

**禁止操作**：
- ❌ 功能设计（feature_implementation: forbidden）

---

### 9. Security Engineer（安全工程师）

**ID**: `security_engineer`  
**分类**: security  
**现实岗位**: Security Engineer / AppSec / Application Security

**核心职责**：
- 威胁建模（threat_modeling）
- 漏洞分析（vulnerability_analysis）
- 安全指导（security_guidance）
- 风险评估（risk_assessment）
- 合规审查（compliance_review）

**参与的 Workflow**：
- `security_review` - 安全审查（lead）
- `system_design` - 系统设计（support）
- `incident_response` - 事故响应（support）

**允许提问**：✅ 风险等级或攻击面不清晰时

**允许操作**：
- ✅ 技术决策（technical_decision: allowed）
- ✅ 架构决策（architecture_decision: allowed）

**禁止操作**：
- ❌ 功能实现（feature_implementation: forbidden）

---

## 🚀 六、部署与运行（2 个）

### 10. DevOps Engineer（运维工程师）

**ID**: `devops_engineer`  
**分类**: operations  
**现实岗位**: DevOps Engineer / Platform Engineer

**核心职责**：
- 部署自动化（deployment_automation）
- 环境一致性（environment_consistency）
- 流水线健康（pipeline_health）
- 基础设施即代码（infrastructure_as_code）
- CI/CD 管理（ci_cd_management）

**参与的 Workflow**：
- `deployment_planning` - 部署规划（lead）
- `release_management` - 发布管理（support）
- `maintenance_planning` - 维护规划（support）
- `incident_response` - 事故响应（support）

**允许提问**：❌（除非环境约束不清）

**允许操作**：
- ✅ 技术决策（technical_decision: allowed）
- ✅ 部署操作（deployment_operation: allowed）

**禁止操作**：
- ❌ 功能设计（feature_implementation: forbidden）

---

### 11. SRE Engineer（SRE 工程师）

**ID**: `sre_engineer`  
**分类**: operations  
**现实岗位**: SRE / Site Reliability Engineer / Reliability Engineer

**核心职责**：
- 可靠性分析（reliability_analysis）
- 可观测性（observability）
- 事故领导（incident_leadership）
- SLA/SLO 管理（sla_slo_management）
- 容量规划（capacity_planning）

**参与的 Workflow**：
- `incident_response` - 事故响应（lead）
- `performance_analysis` - 性能分析（support）
- `maintenance_planning` - 维护规划（lead）

**允许提问**：✅ 在系统行为不确定时

**允许操作**：
- ✅ 技术决策（technical_decision: allowed）
- ✅ 架构决策（architecture_decision: allowed）
- ✅ 部署操作（deployment_operation: allowed）

**禁止操作**：
- ❌ 新功能开发（feature_implementation: forbidden）

---

## 📚 七、组织学习与治理（2 个）

### 12. Technical Writer（技术文档）

**ID**: `technical_writer`  
**分类**: documentation  
**现实岗位**: Technical Writer / Developer Advocate（文档侧）

**核心职责**：
- 文档化（documentation）
- 知识结构化（knowledge_structuring）
- 发布说明（release_notes）
- 用户指南（user_guides）
- API 文档（api_documentation）

**参与的 Workflow**：
- `knowledge_consolidation` - 知识整合（lead）
- `release_management` - 发布管理（lead）

**允许提问**：✅ 内容不完整时

**禁止操作**：
- ❌ 技术决策（technical_decision: forbidden）
- ❌ 实现（feature_implementation: forbidden）

---

### 13. Engineering Manager（工程经理）

**ID**: `engineering_manager`  
**分类**: leadership  
**现实岗位**: Engineering Manager / Team Lead（偏管理）

**核心职责**：
- 技术方向（technical_direction）
- 优先级排序（prioritization）
- 债务管理（debt_management）
- 团队成长（team_growth）
- 战略规划（strategic_planning）

**参与的 Workflow**：
- `architectural_evolution` - 架构演化（support）
- `maintenance_planning` - 维护规划（lead）
- `knowledge_consolidation` - 知识整合（support）

**允许提问**：✅ 战略不清晰时

**允许操作**：
- ✅ 技术决策（technical_decision: allowed）
- ✅ 产品决策（product_decision: allowed）
- ✅ 架构决策（architecture_decision: allowed）

**禁止操作**：
- ❌ 日常实现（feature_implementation: forbidden）

---

## 🚨 5 条红线（强制执行）

### 红线 #1：Agent 不执行 Workflow

**定义**：Agent may participate in reasoning, but may not execute, apply, or modify system state.

**强制执行**：
- ✅ Schema 约束：`constraints.execution = "forbidden"`
- ✅ Runtime Gate：检查 Agent 定义中是否有 execute() 方法引用
- ✅ 代码注释：在 Agent 类中标注禁止区

### 红线 #2：Agent 不拥有 Command

**定义**：Agent 不能直接调用 command、绑定脚本、产生 side-effect

**强制执行**：
- ✅ Schema 约束：`constraints.command_ownership = "forbidden"`
- ✅ Runtime Gate：检查 Agent YAML 中不存在 commands/actions 字段
- ✅ 代码注释：明确标注 Agent 与 Command 的分离

### 红线 #3：Agent 只允许提问

**定义**：人类 ↔ Agent 的唯一交互形式：Question（不存在 approve, override, manual_action）

**强制执行**：
- ✅ Schema 约束：`allowed_interactions = ["question"]`
- ✅ Runtime Gate：验证 allowed_interactions 只包含 "question"
- ✅ 代码注释：明确交互边界

### 红线 #4：一个 Agent = 一个角色

**定义**：不允许"Full Stack Agent"、"万能 Agent"（角色混合 = 架构错误）

**强制执行**：
- ✅ Schema 约束：category 只能选一个（enum 单选）
- ✅ Runtime Gate：检查 responsibilities 数量 ≤ 5（防止职责过载）
- ✅ 代码注释：在文档中明确反模式示例

### 红线 #5：Agent 是组织模型，不是能力模型

**定义**：Agent ≠ 模型能力，Agent ≠ prompt 技巧，Agent = 岗位抽象

**强制执行**：
- ✅ Schema 约束：category 必须是组织类别（product, delivery, design, ...）
- ✅ Runtime Gate：禁止 Agent ID 包含 "gpt", "model", "ai" 等字样
- ✅ 代码注释：在文档中明确区分 Agent 与 LLM Model

---

## 📋 使用建议

### 如何选择 Agent？

1. **明确当前角色**：你处于组织的哪个岗位？
2. **识别主要职责**：当前任务的核心职责是什么？
3. **查看参与的 Workflow**：该 Agent 参与哪些工作流？
4. **检查约束**：该 Agent 允许做什么、禁止做什么？

### Agent ↔ Workflow 映射

详细的 Agent-Workflow-Phase 映射关系请参考：
- `docs/content/agent_workflow_mapping.yaml`

---

## 🔧 开发者指南

### 注册 Agent

```bash
# 验证 Agent 红线
uv run python scripts/register_agents.py --validate-only

# 注册所有 Agent
uv run python scripts/register_agents.py --auto-activate

# 列出已注册的 Agent
uv run python scripts/register_agents.py --list

# 或使用 CLI
uv run agentos content list --type agent
```

### 创建自定义 Agent

如果标准 Agent 不满足需求，可以：

1. 创建新的 YAML 文件（遵循 `agent.schema.json`）
2. 验证红线：`python scripts/register_agents.py --validate-only`
3. 注册：`python scripts/register_agents.py --source your_agents_dir`
4. 提交 PR 贡献新的标准 Agent

### 扩展 Agent

如需演化现有 Agent：

1. 复制现有 Agent YAML
2. 修改 `version`（递增）
3. 设置 `lineage.derived_from` 和 `change_reason`
4. 验证并注册

---

**版本**: v0.7.0  
**更新日期**: 2026-01-25  
**状态**: ✅ 13 个 Agent 全部可用
