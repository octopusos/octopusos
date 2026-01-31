# Content Registry

AgentOS Content Registry 是一个统一的内容管理系统，用于管理所有系统级资产的生命周期、演化和追踪。

## 概述

Content Registry 提供：
- **统一管理**：Agent、Workflow、Command、Rule、Policy、Memory、Fact 的统一注册
- **生命周期控制**：draft → active → deprecated → frozen
- **血缘追踪**：完整的演化历史和变更原因
- **Schema 验证**：强制的结构验证和类型安全
- **审计日志**：所有操作的完整记录

## 核心概念

### Content 类型

AgentOS v0.7 支持 7 种内置 Content 类型：

| 类型 | 状态 | 说明 |
|------|------|------|
| `policy` | ✅ Available | 执行策略（风险容忍度、资源预算、安全约束） |
| `memory` | ✅ Available | 记忆项（组织知识、约定、约束） |
| `fact` | ✅ Available | 事实包（项目扫描结果、结构信息） |
| `workflow` | ✅ Available (v0.6+) | Workflow 定义（多步骤编排） |
| `agent` | ✅ Available (v0.7+) | Agent 定义（组织角色、职责、约束） |
| `command` | 🟡 Placeholder (v0.8+) | 命令定义（可执行动作） |
| `rule` | 🟡 Placeholder (v0.9+) | 治理规则（质量和合规） |

### 生命周期状态

```
draft → active → deprecated
                     ↓
                  frozen (immutable)
```

- **draft**：初始状态，可修改
- **active**：已激活，正在使用
- **deprecated**：已弃用，不推荐使用
- **frozen**：冻结，完全不可变

### 血缘（Lineage）

每个 Content 必须有可解释的血缘：

**Root 版本**（第一个版本）：
```json
{
  "metadata": {
    "is_root": true,
    "parent_version": null
  }
}
```

**Evolved 版本**（演化版本）：
```json
{
  "metadata": {
    "is_root": false,
    "parent_version": "1.0.0",
    "change_reason": "Added error handling for edge cases"
  }
}
```

## Workflow Content

### 什么是 Workflow？

Workflow 是**组织经验的结晶**，不是执行逻辑。它定义了：
- 多个阶段（phases）及其依赖关系
- 每个阶段的输入/输出契约
- 允许/禁止的行为
- 何时允许提问

### v0.6 Workflow Catalog

AgentOS v0.6 提供 **18 个标准 Workflow**，覆盖完整的软件开发生命周期：

**Discovery & Planning (5)**
1. `problem_discovery` - 识别和框定问题
2. `requirements_definition` - 定义功能和非功能需求
3. `system_design` - 系统级架构设计
4. `detailed_design` - 模块级和接口级设计
5. `implementation_planning` - 实现步骤和排序规划

**Implementation & Testing (4)**
6. `feature_implementation` - 实现一个范围明确的功能
7. `refactoring` - 改进内部结构而不改变行为
8. `testing_strategy` - 定义测试覆盖策略
9. `test_implementation` - 按策略实现测试

**Governance & Review (3)**
10. `code_review` - 审查代码变更的质量和风险
11. `security_review` - 识别安全风险和缓解措施
12. `performance_analysis` - 分析性能特征

**Deployment & Release (2)**
13. `deployment_planning` - 规划部署和发布
14. `release_management` - 协调发布活动

**Operations & Maintenance (3)**
15. `incident_response` - 响应生产事故
16. `maintenance_planning` - 规划长期系统维护
17. `architectural_evolution` - 引导大规模架构变更

**Learning (1)**
18. `knowledge_consolidation` - 将经验教训整理为可复用知识

📖 详细目录见：[Workflow Catalog](workflow-catalog.md)

## Agent Content

### 什么是 Agent？

Agent 是**组织岗位的建模**，不是 AI 能力。它定义了：
- 角色职责和边界
- 允许/禁止的决策类型
- 参与的 Workflow 和阶段
- 5 条红线约束（不执行、不拥有 Command、只提问）

### v0.7 Agent Catalog

AgentOS v0.7 提供 **13 个标准 Agent**，覆盖完整的软件组织结构：

**产品与项目层 (2)**
1. `product_manager` - 产品经理（问题定义、需求清晰度）
2. `project_manager` - 项目经理（规划、依赖跟踪）

**体验与前端 (2)**
3. `ui_ux_designer` - UI/UX 设计师（交互设计、视觉规范）
4. `frontend_engineer` - 前端工程师（UI 实现、状态管理）

**后端与数据 (2)**
5. `backend_engineer` - 后端工程师（API 实现、业务逻辑）
6. `database_engineer` - 数据库工程师（数据建模、查询优化）

**架构层 (1)**
7. `system_architect` - 系统架构师（架构设计、技术选型）

**质量与安全 (2)**
8. `qa_engineer` - 测试工程师（测试策略、质量评估）
9. `security_engineer` - 安全工程师（威胁建模、漏洞分析）

**部署与运行 (2)**
10. `devops_engineer` - DevOps 工程师（部署自动化、CI/CD）
11. `sre_engineer` - SRE 工程师（可靠性、可观测性）

**组织学习 (2)**
12. `technical_writer` - 技术文档（文档化、知识结构化）
13. `engineering_manager` - 工程经理（技术方向、优先级排序）

📖 详细目录见：[Agent Catalog](agent-catalog.md)

## CLI 使用

### 查看所有 Content 类型

```bash
uv run agentos content types
```

### 列出 Content

```bash
# 列出所有 workflow
uv run agentos content list --type workflow

# 列出所有 agent
uv run agentos content list --type agent

# 列出所有活跃的 workflow
uv run agentos content list --type workflow --status active

# 限制结果数量
uv run agentos content list --type workflow --limit 10
```

### 解释 Content

```bash
# 获取 workflow 的详细解释
uv run agentos content explain problem_discovery

# 获取 agent 的详细解释
uv run agentos content explain product_manager

# 输出：
# - 为什么存在
# - 适用什么场景
# - 什么时候不该用
# - 职责和约束（agent）
# - 每个 phase 的职责（workflow）
```

### 查看 Content 历史

```bash
# 查看 workflow 演化历史
uv run agentos content history problem_discovery

# 查看 agent 演化历史
uv run agentos content history product_manager

# 查看版本差异
uv run agentos content diff problem_discovery --from 0.6.0 --to 0.7.0
```

### 注册自定义 Content

```bash
# 从 JSON 文件注册 workflow
uv run agentos content register --type workflow --file my-workflow.json

# 使用脚本批量注册 agent
uv run python scripts/register_agents.py --auto-activate

# 激活 content
uv run agentos content activate my-workflow
uv run agentos content activate my-agent

# 冻结 content（使其不可变）
uv run agentos content freeze my-workflow --version 1.0.0
```

## Schema 参考

### Workflow Schema

Workflow Content 必须符合 `content/workflow.schema.json`。

### Agent Schema

Agent Content 必须符合 `content/agent.schema.json`。

**必需字段**：
- `id`: Workflow 标识符（lowercase, underscore separated）
- `version`: 语义版本号（semver）
- `category`: 分类（discovery/design/implementation/...）
- `description`: 详细描述
- `phases`: 阶段数组（至少 1 个）
- `interaction`: 交互策略
- `constraints`: 约束
- `lineage`: 血缘信息

**示例**：

```yaml
id: problem_discovery
version: 0.6.0
category: discovery
description: Identify and frame a real problem worth solving.

phases:
  - id: signal_collection
    allows_questions: true
  - id: problem_framing
    allows_questions: true
  - id: success_criteria
    allows_questions: true

interaction:
  mode: question_only
  question_policy:
    trigger_when:
      - ambiguity_score > 0.6
      - missing_required_field

constraints:
  execution: forbidden
  side_effects: forbidden

lineage:
  introduced_in: v0.6
```

## 编写指南

详细的 Workflow 编写规范见：[Workflow Authoring Guide](workflow-authoring-guide.md)

## 架构决策

相关的架构决策记录（ADR）：
- [ADR-006: Policy Evolution Safety](../adr/ADR-006-policy-evolution-safety.md)
- [ADR-005: Self-Heal Learning](../adr/ADR-005-self-heal-learning.md)

## 相关文档

- [Workflow Catalog](workflow-catalog.md) - 完整的 Workflow 列表和说明
- [Agent Catalog](agent-catalog.md) - 完整的 Agent 列表和说明
- [Workflow Authoring Guide](workflow-authoring-guide.md) - 如何编写 Workflow
- [Memory Governance](../MEMORY_GOVERNANCE_V04.md) - 记忆管理策略
- [Architecture Risks](../ARCHITECTURE_RISKS.md) - 架构风险分析
