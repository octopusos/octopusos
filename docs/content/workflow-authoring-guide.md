# Workflow Authoring Guide

本指南说明如何编写符合 AgentOS v0.6 规范的 Workflow。

## 核心原则

### 🟥 Rule 0：Workflow 不执行，只编排

Workflow **只能做 4 件事**：
1. 定义阶段（phases）
2. 定义每阶段的输入/输出契约
3. 定义允许/禁止的行为
4. 定义"是否允许提问"

🚫 **Workflow 不得**：
- 执行代码
- 修改系统状态
- 调用 agent 执行逻辑
- 包含具体的 prompt 或指令

### 🟥 Rule 1：人工干预 = Question

唯一允许的人类参与形式是**提问**（Question），而不是：
- ❌ approve（审批）
- ❌ override（覆盖）
- ❌ manual_action（手动操作）
- ❌ "你来决定"

### 🟥 Rule 2：提问是"信息缺失触发"

提问必须有明确的触发条件，不能是默认行为：

```yaml
question_policy:
  trigger_when:
    - missing_required_field
    - ambiguity_score > 0.7
    - risk_level == "critical" AND confidence < 0.6
```

### 🟥 Rule 3：Workflow 必须可解释

每个 Workflow 必须能回答：
- **为什么存在**：解决什么问题
- **适用什么场景**：什么时候用
- **什么时候不该用**：边界在哪里
- **每个 phase 的职责**：具体做什么

## 标准结构

### 完整模板

```yaml
id: workflow_name
version: 0.6.0
category: discovery|design|implementation|testing|governance|deployment|operations|learning
description: >
  简洁的单行描述（会显示在列表中）
  
  可选的详细说明（多行）：
  - 核心目标
  - 适用范围
  - 关键约束

phases:
  - id: phase_name
    description: 阶段描述
    requires: [input1, input2]
    produces: [output1, output2]
    allows_questions: true|false
    risk_level: low|medium|high
    
  - id: next_phase
    description: 下一阶段
    requires: [phase_name.output1]
    produces: [final_output]
    allows_questions: false

interaction:
  default_mode: question_only
  question_policy:
    trigger_when:
      - condition1
      - condition2
  allowed_phases: [phase_name]

constraints:
  execution: forbidden
  side_effects: forbidden
  requires_approval: false
  
lineage:
  introduced_in: v0.6
  derived_from: null  # 或 parent_workflow_id
  change_reason: null  # 如果是 evolved 版本

metadata:
  tags: [tag1, tag2]
  related_workflows: [workflow1, workflow2]
  documentation_url: https://...
```

## 字段说明

### 必需字段

#### `id`
- **格式**：`^[a-z0-9_]+$`（小写字母、数字、下划线）
- **示例**：`problem_discovery`, `feature_implementation`
- **规则**：全局唯一，语义化命名

#### `version`
- **格式**：`^\\d+\\.\\d+\\.\\d+$`（语义版本号）
- **示例**：`0.6.0`, `1.2.3`
- **规则**：遵循 semver

#### `category`
- **枚举**：
  - `discovery` - 问题发现和探索
  - `design` - 设计和规划
  - `implementation` - 实现和编码
  - `testing` - 测试和验证
  - `governance` - 治理和审查
  - `deployment` - 部署和发布
  - `operations` - 运维和维护
  - `learning` - 学习和知识整理

#### `description`
- **类型**：字符串（支持多行）
- **长度**：建议 50-500 字符
- **内容**：清晰说明 workflow 的用途

#### `phases`
- **类型**：数组（至少 1 个）
- **每个 phase 必需**：
  - `id`: 阶段标识符
  - `allows_questions`: 布尔值

#### `interaction`
- **必需子字段**：
  - `default_mode`: 固定为 `question_only`
  - `question_policy`: 提问策略

#### `constraints`
- **必需子字段**：
  - `execution`: 固定为 `forbidden`
  - `side_effects`: 固定为 `forbidden`

#### `lineage`
- **Root 版本**：
  ```yaml
  lineage:
    introduced_in: v0.6
    derived_from: null
  ```
- **Evolved 版本**：
  ```yaml
  lineage:
    introduced_in: v0.7
    derived_from: problem_discovery
    change_reason: "Added risk assessment phase"
  ```

## 编写步骤

### Step 1：识别目标场景

明确 workflow 要解决的问题：
- 这个 workflow 在 SDLC 的哪个阶段？
- 输入是什么？输出是什么？
- 谁会使用它？什么时候使用？

### Step 2：分解阶段

将工作分解为逻辑阶段：
- 每个阶段有明确的职责
- 阶段之间有清晰的依赖关系
- 避免过细（< 3 个阶段）或过粗（> 10 个阶段）

### Step 3：定义交互策略

确定哪些阶段允许提问：
- **允许提问**：需求澄清、风险评估、决策制定
- **不允许提问**：纯执行、自动化验证、已有完整信息

### Step 4：设定约束

明确 workflow 的边界：
- 什么是允许的
- 什么是禁止的
- 需要什么前置条件

### Step 5：编写文档

确保可解释性：
- 描述清晰易懂
- 每个阶段有说明
- 提供使用示例

## 最佳实践

### ✅ 好的 Workflow

```yaml
id: code_review
version: 0.6.0
category: governance
description: Review code changes for quality and risk.

phases:
  - id: diff_analysis
    description: Analyze code differences
    requires: [diff, context]
    produces: [change_summary]
    allows_questions: false
    
  - id: risk_assessment
    description: Assess risks of changes
    requires: [change_summary]
    produces: [risk_report]
    allows_questions: true  # 可能需要澄清风险等级
    
  - id: improvement_suggestions
    description: Suggest improvements
    requires: [risk_report]
    produces: [suggestions]
    allows_questions: false

interaction:
  default_mode: question_only
  question_policy:
    trigger_when:
      - risk_level == "critical"
      - confidence < 0.6
  allowed_phases: [risk_assessment]

constraints:
  execution: forbidden
  side_effects: forbidden
```

**为什么好**：
- 阶段清晰
- 依赖明确
- 只在风险评估时允许提问
- 有明确的触发条件

### ❌ 不好的 Workflow

```yaml
id: do_everything
version: 1.0.0
category: implementation
description: Do all the things.

phases:
  - id: step1
    allows_questions: true
  - id: step2
    allows_questions: true
  - id: step3
    allows_questions: true

interaction:
  default_mode: question_only
  question_policy:
    trigger_when: []  # ❌ 没有触发条件

constraints:
  execution: allowed  # ❌ 违反 Rule 0
```

**为什么不好**：
- 描述模糊
- 阶段无意义（step1, step2）
- 所有阶段都允许提问但无触发条件
- 违反约束规则

## 常见模式

### 模式 1：探索型 Workflow

适用于需求不明确的场景：

```yaml
phases:
  - id: exploration
    allows_questions: true
  - id: hypothesis
    allows_questions: true
  - id: validation
    allows_questions: false

question_policy:
  trigger_when:
    - ambiguity_score > 0.5
    - missing_critical_info
```

### 模式 2：执行型 Workflow

适用于需求明确的场景：

```yaml
phases:
  - id: plan
    allows_questions: false
  - id: execute
    allows_questions: false
  - id: verify
    allows_questions: false

question_policy:
  trigger_when:
    - blocker_detected  # 只在遇到阻塞时提问
```

### 模式 3：审查型 Workflow

适用于质量门禁场景：

```yaml
phases:
  - id: automated_checks
    allows_questions: false
  - id: manual_review
    allows_questions: true
  - id: decision
    allows_questions: true

question_policy:
  trigger_when:
    - risk_level == "high"
    - confidence < 0.7
```

## 验证清单

在提交 Workflow 前检查：

- [ ] `id` 遵循命名规范
- [ ] `version` 是有效的 semver
- [ ] `category` 是标准枚举值之一
- [ ] `description` 清晰说明用途
- [ ] 至少有 1 个 phase
- [ ] 每个 phase 有 `id` 和 `allows_questions`
- [ ] `interaction.default_mode` 是 `question_only`
- [ ] `question_policy.trigger_when` 有明确条件
- [ ] `constraints.execution` 是 `forbidden`
- [ ] `constraints.side_effects` 是 `forbidden`
- [ ] `lineage` 信息完整
- [ ] YAML 语法正确
- [ ] 能通过 schema 验证

## 测试 Workflow

### 本地验证

```bash
# 转换 YAML 为 JSON 并验证 schema
uv run python scripts/convert_workflows.py \
  --input docs/content/workflows/my_workflow.yaml \
  --validate

# 注册到本地数据库
uv run agentos content register \
  --type workflow \
  --file examples/workflows/my_workflow.json

# 测试 explain 功能
uv run agentos content explain my_workflow
```

### Schema 验证

```python
from agentos.core.content import ContentRegistry

registry = ContentRegistry()

# 加载 workflow
with open('my_workflow.json') as f:
    workflow = json.load(f)

# 注册（会自动验证 schema）
try:
    workflow_id = registry.register(workflow)
    print(f"✅ Workflow registered: {workflow_id}")
except ValueError as e:
    print(f"❌ Validation failed: {e}")
```

## 提交贡献

如果你创建了有用的 Workflow，欢迎贡献：

1. Fork AgentOS 仓库
2. 在 `docs/content/workflows/` 创建 YAML 文件
3. 运行 `scripts/convert_workflows.py` 生成 JSON
4. 添加到 `docs/content/workflow-catalog.md`
5. 运行测试：`uv run python -m pytest tests/test_v06_workflows.py`
6. 提交 PR

## 参考资源

- [Workflow Catalog](workflow-catalog.md) - 18 个标准 Workflow 示例
- [Content Registry Overview](index.md) - Content 系统概述
- [Schema 定义](../../agentos/schemas/content/workflow.schema.json)

---

**版本**: v0.6.0  
**更新日期**: 2026-01-25
