# Intent Builder (v0.9.4) - README

## 🎯 定位

Intent Builder 是 AgentOS 执行流水线的入口组件，将自然语言输入转换为结构化的 ExecutionIntent (v0.9.1)。

### 执行流水线位置

```
自然语言输入 (NL Request)
    ↓
[v0.9.4 Intent Builder] ← 本组件
    ↓
ExecutionIntent (v0.9.1)
    ↓
[v0.9.2 Coordinator Engine]
    ↓
ExecutionGraph + QuestionPack
```

## 🚨 RED LINES（不可违背的原则）

1. **禁止执行** - Builder 不执行任何命令（无 `subprocess`/`shell`/`exec`）
2. **禁止编造** - 所有 workflow/agent/command 必须来自 ContentRegistry
3. **full_auto 约束** - `full_auto` 模式下 `question_budget=0`，不生成问题
4. **证据必需** - 每个选择（workflow/agent/command）必须有 `evidence_refs`

## 🚀 快速开始

### 1. 创建 NL 请求文件

```yaml
# examples/nl/my_request.yaml
id: nl_req_my_task
schema_version: "0.9.4"
project_id: "my_project"
input_text: |
  请为 UserService 类添加文档注释，包括：
  - 类级别的 docstring
  - 每个公共方法的参数说明
  - 使用示例
context_hints:
  files:
    - "src/services/UserService.ts"
  areas:
    - "docs"
created_at: "2026-01-25T10:00:00Z"
checksum: "..."
lineage:
  introduced_in: "0.9.4"
  derived_from: []
  supersedes: []
```

### 2. 运行 Builder

```bash
# 基础用法
agentos builder run --input examples/nl/my_request.yaml --out outputs/builder/

# 指定策略
agentos builder run --input my_request.yaml --policy semi_auto

# 使用自定义 DB（测试用）
agentos builder run --input my_request.yaml --db /tmp/test_registry.sqlite
```

### 3. 查看解释

```bash
agentos builder explain --input examples/nl/my_request.yaml
```

### 4. 验证输出

```bash
agentos builder validate --file outputs/builder/nl_req_my_task.output.json
```

## 📊 核心概念

### NL Request（自然语言请求）

输入格式，包含：
- `input_text`: 自然语言描述
- `context_hints`: 可选的上下文提示（files/modules/areas）
- `lineage`: 血缘关系

Schema: `agentos/schemas/execution/nl_request.schema.json`

### Intent Builder Output

输出格式，包含：
- `execution_intent`: 生成的 ExecutionIntent (v0.9.1)
- `question_pack`: 问题包（仅 interactive/semi_auto 模式）
- `selection_evidence`: 选择证据（每个选择的归因）
- `builder_audit`: Builder 审计信息

Schema: `agentos/schemas/execution/intent_builder_output.schema.json`

### Evidence Refs（证据引用）

格式：`type:identifier:detail`

类型：
- `nl_input:start:end` - NL 输入文本片段（字符位置）
- `registry:content_id:version` - Registry 内容引用
- `rule:rule_id` - 规则引用
- `context_hint:type:value` - 上下文提示

示例：
```json
[
  "nl_input:0:100",
  "registry:documentation:1.0.0",
  "rule:r02_lineage_required"
]
```

### Question Pack（问题包）

当 Builder 检测到歧义时生成的问题列表：

```json
{
  "questions": [
    {
      "question_id": "q_missing_actions",
      "type": "blocker",
      "blocking_level": "critical",
      "question_text": "没有检测到明确的操作，请说明要执行的具体任务？",
      "context": "...",
      "evidence_refs": ["nl_input:0:100"]
    }
  ],
  "budget_used": 1,
  "policy": "blockers_only"
}
```

## 🎮 执行策略

### full_auto（全自动）

- **特点**: 零交互，自动决策
- **question_budget**: 0（强制）
- **适用**: 低风险、明确的任务
- **RED LINE**: 不能有任何问题

```bash
agentos builder run --input my_request.yaml --policy full_auto
```

### semi_auto（半自动）

- **特点**: 仅在关键决策点提问
- **question_budget**: 10（默认）
- **question_policy**: `blockers_only`
- **适用**: 中等风险、大部分明确的任务

```bash
agentos builder run --input my_request.yaml --policy semi_auto
```

### interactive（交互式）

- **特点**: 允许更多提问和澄清
- **question_budget**: 20（默认）
- **question_policy**: `conceptual_only`
- **适用**: 高风险、复杂或模糊的任务

```bash
agentos builder run --input my_request.yaml --policy interactive
```

## 🔗 与其他版本的关系

### v0.9.1 - ExecutionIntent

Builder 生成的 `execution_intent` 严格符合 v0.9.1 Intent Schema：
- 包含所有必需字段（26 个）
- 遵循所有约束（execution=forbidden, no_fabrication=true）
- 通过 allOf 验证（full_auto/risk/write 约束）

### v0.9.2 - Coordinator Engine

Builder 的输出可以直接传递给 Coordinator：

```bash
# Step 1: Build Intent
agentos builder run --input my_request.yaml --out outputs/

# Step 2: Coordinate
agentos coordinate --intent outputs/nl_req_my_task.intent.json --policy semi_auto
```

### v0.6/v0.7/v0.8 - Content Registry

Builder 从 Registry 查询：
- v0.6 的 18 workflows
- v0.7 的 13 agents
- v0.8 的 40 commands

不编造内容 ID，只选择已注册的内容。

## 📝 示例场景

### 低风险：文档任务

```yaml
input_text: "为 PageLayout 组件添加 JSDoc 注释"
areas: ["docs"]
```

→ 生成：
- risk: `low`
- mode: `semi_auto` 或 `full_auto`
- workflows: `documentation`
- agents: `technical_writer`

### 中风险：API 开发

```yaml
input_text: "实现用户个人资料更新 API，添加单元测试"
areas: ["backend", "tests"]
```

→ 生成：
- risk: `medium`
- mode: `semi_auto`
- workflows: `api_design`, `testing_strategy`
- agents: `backend_engineer`, `qa_engineer`
- requires_review: `["architecture"]`

### 高风险：数据库迁移

```yaml
input_text: "添加权限系统，新增 permissions 表，迁移现有数据"
areas: ["backend", "data", "security"]
```

→ 生成：
- risk: `high`
- mode: `interactive` 或 `semi_auto`（不能 full_auto）
- workflows: `database_migration`, `security_review`
- agents: `backend_engineer`, `security_engineer`
- requires_review: `["data", "security", "architecture"]`
- question_pack: 包含数据迁移相关问题

## 🛠️ 开发指南

### 扩展 Builder

如需添加自定义逻辑：

1. **扩展 NLParser**: 添加更多关键词检测
2. **扩展 RegistryQueryService**: 改进匹配算法
3. **扩展 EvidenceBuilder**: 添加新的证据类型
4. **扩展 QuestionGenerator**: 添加新的问题模板

### 模型集成（预留）

Builder 预留了 `model_router` 接口：

```python
builder = IntentBuilder(registry, model_router=my_router)
```

目前使用 `rule_based`，未来可接入 LLM。

## 🧪 测试

```bash
# 运行所有 gates
python scripts/gates/v094_gate_a_existence.py
python scripts/gates/v094_gate_b_schema_validation.py
python scripts/gates/v094_gate_c_negative_fixtures.py
bash scripts/gates/v094_gate_d_no_execution_symbols.sh
python scripts/gates/v094_gate_e_db_isolation.py
python scripts/gates/v094_gate_f_explain_snapshot.py

# 一键验证
bash scripts/verify_v094_builder.sh
```

## 📚 相关文档

- [V094_AUTHORING_GUIDE.md](./V094_AUTHORING_GUIDE.md) - NL 输入编写指南
- [V094_FREEZE_CHECKLIST_REPORT.md](./V094_FREEZE_CHECKLIST_REPORT.md) - 冻结级验收报告
- [intent.schema.json](../../agentos/schemas/execution/intent.schema.json) - ExecutionIntent Schema (v0.9.1)

## 🔒 冻结状态

**状态**: 🔒 **FROZEN** (v0.9.4)

Schemas 已冻结（`additionalProperties: false`），不可随意修改字段。

如需变更，必须：
1. 创建新版本（v0.9.5）
2. 保持向后兼容
3. 更新所有 gates
4. 重新验收

---

**版本**: 0.9.4  
**最后更新**: 2026-01-25  
**维护**: AgentOS Core Team
