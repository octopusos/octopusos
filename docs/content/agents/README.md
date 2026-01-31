# Agent Catalog - AgentOS v0.7

## 概述

AgentOS v0.7 引入了**组织模型**（Organizational Model），将现实软件团队的岗位映射为 Agent 定义。

**核心定位**: Agent = 组织岗位，不是 AI 能力

---

## 🚨 五条红线（Red Lines）

v0.7 Agent 必须遵守以下 5 条架构红线，这些红线在注册前由 `AgentRedlineValidator` 强制执行：

### 红线 #1：Agent 不执行 Workflow

```text
Agent may participate in reasoning,
but may not execute, apply, or modify system state.
```

**强制执行**:
- Schema: `constraints.execution` 字段必须存在
- Validator: 检查 `execution = "forbidden"` (v0.7 要求)
- Validator: 检查无 `execute`, `run`, `apply` 字段

### 红线 #2：Agent 不拥有 Command

```text
Agent 不能直接调用 command、绑定脚本、产生 side-effect
```

**强制执行**:
- Schema: 不包含 `commands` 字段定义
- Validator: 检查 `command_ownership = "forbidden"` (v0.7 要求)
- Validator: 检查 YAML 中不存在 `commands`, `actions`, `tools` 字段

### 红线 #3：Agent 只允许提问

```text
人类 ↔ Agent 的唯一交互形式：Question
不存在：approve, override, manual_action
```

**强制执行**:
- Schema: `allowed_interactions` 字段必须存在
- Validator: 检查 `allowed_interactions = ["question"]` (v0.7 要求)
- Validator: 拒绝 `approve`, `override` 等其他交互类型

### 红线 #4：一个 Agent = 一个角色

```text
不允许："Full Stack Agent"、"万能 Agent"
角色混合 = 架构错误
```

**强制执行**:
- Schema: `category` 只能选一个
- Validator: `responsibilities` 数量 ≤ 5（防止职责过载）
- Validator: 禁止 "full_stack", "universal" 等命名模式

### 红线 #5：Agent 是组织模型，不是能力模型

```text
Agent ≠ 模型能力
Agent ≠ prompt 技巧
Agent = 岗位抽象
```

**强制执行**:
- Schema: `category` 必须是组织类别（product, delivery, design, ...）
- Validator: Agent ID 不能包含 "gpt", "model", "ai", "llm" 等字样
- Validator: 描述必须引用现实组织岗位

---

## 13 个 Agent 清单

### 产品与项目层（2 个）

#### 1. Product Manager
- **ID**: `product_manager`
- **类别**: product
- **职责**: 问题定义、需求清晰度、价值评估、利益相关方对齐、产品愿景
- **参与 Workflow**: problem_discovery, requirements_definition, release_management, knowledge_consolidation
- **现实岗位**: Product Manager, Product Owner

#### 2. Project Manager
- **ID**: `project_manager`
- **类别**: delivery
- **职责**: 规划、依赖跟踪、风险协调
- **参与 Workflow**: implementation_planning, deployment_planning, release_management
- **现实岗位**: Project Manager, Delivery Manager, Scrum Master

### 体验与前端（2 个）

#### 3. UI/UX Designer
- **ID**: `ui_ux_designer`
- **类别**: design
- **职责**: 交互设计、视觉规范、可用性一致性
- **参与 Workflow**: system_design, detailed_design, knowledge_consolidation
- **现实岗位**: UI Designer, UX Designer, Design System Owner

#### 4. Frontend Engineer
- **ID**: `frontend_engineer`
- **类别**: engineering
- **职责**: UI 实现、前端逻辑、状态管理
- **参与 Workflow**: detailed_design, feature_implementation, refactoring, test_implementation, code_review
- **现实岗位**: Frontend Engineer

### 后端与数据（2 个）

#### 5. Backend Engineer
- **ID**: `backend_engineer`
- **类别**: engineering
- **职责**: API 实现、业务逻辑、服务集成
- **参与 Workflow**: detailed_design, feature_implementation, refactoring, testing_strategy, code_review
- **现实岗位**: Backend Engineer

#### 6. Database Engineer
- **ID**: `database_engineer`
- **类别**: data
- **职责**: 数据建模、查询优化、迁移策略
- **参与 Workflow**: system_design, detailed_design, performance_analysis, maintenance_planning
- **现实岗位**: DBA, Data Engineer

### 架构层（1 个）

#### 7. System Architect
- **ID**: `system_architect`
- **类别**: architecture
- **职责**: 架构设计、技术选型、系统权衡
- **参与 Workflow**: system_design, architectural_evolution, performance_analysis, security_review
- **现实岗位**: Software Architect, Principal Engineer

### 质量与安全（2 个）

#### 8. QA Engineer
- **ID**: `qa_engineer`
- **类别**: quality
- **职责**: 测试策略、质量评估、回归风险
- **参与 Workflow**: testing_strategy, test_implementation, incident_response, code_review
- **现实岗位**: QA Engineer, Test Engineer

#### 9. Security Engineer
- **ID**: `security_engineer`
- **类别**: security
- **职责**: 威胁建模、漏洞分析、安全指导
- **参与 Workflow**: security_review, system_design, incident_response
- **现实岗位**: Security Engineer, AppSec

### 部署与运行（2 个）

#### 10. DevOps Engineer
- **ID**: `devops_engineer`
- **类别**: operations
- **职责**: 部署自动化、环境一致性、流水线健康
- **参与 Workflow**: deployment_planning, release_management, maintenance_planning, incident_response
- **现实岗位**: DevOps Engineer, Platform Engineer

#### 11. Site Reliability Engineer
- **ID**: `sre_engineer`
- **类别**: operations
- **职责**: 可靠性分析、可观测性、事故领导
- **参与 Workflow**: incident_response, performance_analysis, maintenance_planning
- **现实岗位**: SRE, Reliability Engineer

### 组织学习（2 个）

#### 12. Technical Writer
- **ID**: `technical_writer`
- **类别**: documentation
- **职责**: 文档化、知识结构化、发布说明
- **参与 Workflow**: knowledge_consolidation, release_management
- **现实岗位**: Technical Writer, Developer Advocate

#### 13. Engineering Manager
- **ID**: `engineering_manager`
- **类别**: leadership
- **职责**: 技术方向、优先级排序、债务管理
- **参与 Workflow**: architectural_evolution, maintenance_planning, knowledge_consolidation
- **现实岗位**: Engineering Manager, Team Lead

---

## Agent Schema

Agent 定义遵循 `agentos/schemas/content/agent.schema.json`：

```yaml
id: agent_id
type: agent
version: 0.7.0
category: product|delivery|design|engineering|data|architecture|quality|security|operations|documentation|leadership

description: >
  Agent 职责描述（必须对应现实组织岗位）

responsibilities:
  - 职责1
  - 职责2
  - ...（最多 5 个）

allowed_interactions:
  - question  # v0.7 只允许 question

constraints:
  execution: forbidden  # 🚨 红线 #1
  command_ownership: forbidden  # 🚨 红线 #2
  technical_decision: allowed|forbidden  # 根据角色
  product_decision: allowed|forbidden
  architecture_decision: allowed|forbidden
  feature_implementation: allowed|forbidden
  deployment_operation: allowed|forbidden

lineage:
  introduced_in: v0.7
  derived_from: null
  change_reason: null

metadata:
  real_world_roles:
    - 岗位名称1
    - 岗位名称2
  typical_workflows:
    - workflow_id1
    - workflow_id2
  tags:
    - tag1
    - tag2
```

---

## Agent-Workflow 映射

完整的 Agent ↔ Workflow ↔ Phase 映射关系见 `agent_workflow_mapping.yaml`。

**注意**: 映射关系是"组织知识"，记录"现实中通常由谁负责哪些工作流的哪些阶段"，不是执行配置。

---

## 使用方法

### 注册 Agents

```bash
# 批量注册所有 agents
uv run python scripts/register_agents.py --source docs/content/agents

# 列出已注册 agents
uv run agentos content list --type agent

# 查看特定 agent
uv run agentos content explain product_manager
```

### 验证 Red Lines

```bash
# 运行红线测试
pytest tests/gates/test_validate_agent_redlines.py -v

# 验证单个 agent
uv run python scripts/register_agents.py --source path/to/agent.yaml --validate-only
```

---

## v0.7 状态

**已完成**:
- ✅ 13 个 Agent 定义（YAML）
- ✅ Agent Schema（最小化）
- ✅ Agent-Workflow 映射表
- ✅ 5 条红线（代码强制执行）
- ✅ 注册脚本
- ✅ CLI 命令（list, explain）

**不在范围内**:
- ❌ Agent 执行逻辑（v0.8+）
- ❌ Command Catalog（v0.8）
- ❌ Agent 编排器（v0.9+）

---

**版本**: v0.7.0  
**状态**: 组织模型完成（可治理、可审查、可注册、可解释）  
**下一步**: v0.8 Command Catalog
