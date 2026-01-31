# AgentOS Rules Authoring Guide（规则编写指南）

本指南帮助你创建符合 v0.9 标准的 AgentOS Rules。

---

## 🎯 Rule 0：遵守五条红线

在编写任何 rule 前，必须理解并遵守以下红线：

1. **RL1**: Rule 不包含执行指令
2. **RL2**: Rule 必须可审计（evidence_required）
3. **RL3**: Rule 必须可机器判定（predicate 结构化）
4. **RL4**: Rule 必须声明适用范围（scope）
5. **RL5**: Rule 必须有 lineage

详见 `README.md` 红线章节。

---

## 📋 标准 Rule 结构

### 最小模板

```yaml
id: rule_r<nn>_<short_name>
type: rule
title: "<Human-readable title>"
description: "<Detailed description of what this rule enforces>"
version: "0.9.0"
status: active

lineage:
  introduced_in: "v0.9"
  derived_from: null
  supersedes: []

constraints:
  execution: forbidden

rule:
  severity: error  # info|warn|error|block
  scope:
    applies_to_types: ["workflow", "agent", "command"]
    applies_to_risk: ["medium", "high"]
    applies_to_phases: ["implementation", "review"]
  
  when:
    <structured_condition>: true
  
  then:
    decision: deny  # allow|deny|warn|require_review
    reason: "<Human-readable reason>"
    required_changes:
      - "<Change 1>"
      - "<Change 2>"
  
  evidence_required:
    - "<evidence_type_1>"
    - "<evidence_type_2>"

metadata:
  tags: ["tag1", "tag2"]
  author: "AgentOS Team"
```

### 完整模板

```yaml
id: rule_r<nn>_<short_name>
type: rule
title: "<Human-readable title (5-200 chars)>"
description: >
  <Detailed description of what this rule enforces.
  Explain the rationale, use cases, and consequences.
  (10-2000 chars)>
version: "0.9.0"
status: active  # draft|active|deprecated

lineage:
  introduced_in: "v0.9"      # 首次引入版本
  derived_from: null         # 父 rule ID（root 为 null）
  supersedes: []             # 替代的旧 rule IDs

constraints:
  execution: forbidden       # 🚨 RL1: 必须为 forbidden

rule:
  severity: error            # 🚨 RL3: info|warn|error|block
  
  scope:                     # 🚨 RL4: 至少一个非空
    applies_to_types:        # workflow|agent|command|policy|memory|fact|rule
      - "workflow"
      - "command"
    applies_to_risk:         # low|medium|high|critical
      - "high"
      - "critical"
    applies_to_phases:       # setup|analysis|...|postmortem
      - "implementation"
      - "review"
  
  when:                      # 🚨 RL3: 结构化条件（不能是字符串）
    any_of:                  # 或 all_of
      - field_exists: "forbidden_field"
      - field_missing: "required_field"
      - custom_condition: true
  
  then:                      # 🚨 RL3: 结构化决策（不能是字符串）
    decision: deny           # allow|deny|warn|require_review
    reason: "Human-readable reason for this decision"
    required_changes:        # 可选
      - "Change description 1"
      - "Change description 2"
  
  evidence_required:         # 🚨 RL2: 非空数组
    - "content_source_yaml"
    - "schema_validation"
    - "factpack"

metadata:                    # 可选
  tags:
    - "category1"
    - "category2"
  related_rules:
    - "rule_r01_no_execution"
  documentation_url: "https://example.com/docs"
  author: "Your Name"
  examples:
    - "Example use case 1"
```

---

## 🔧 字段详解

### 必需字段

#### `id`
- **格式**: `rule_r<nn>_<short_name>`
  - `<nn>`: 两位数字（01-99）
  - `<short_name>`: 下划线分隔的短名称
- **示例**: `rule_r01_no_execution`, `rule_r12_rollback_plan_required_high_risk`
- **约束**: 必须唯一，必须与文件名匹配（`<id>.yaml`）

#### `type`
- **固定值**: `"rule"`

#### `version`
- **格式**: `<major>.<minor>.<patch>`
- **示例**: `"0.9.0"`
- **说明**: v0.9 首次引入的 rules 都是 `0.9.0`

#### `title`
- **长度**: 5-200 字符
- **要求**: 简洁、描述性强
- **示例**: `"No execution is allowed in content plane"`

#### `description`
- **长度**: 10-2000 字符
- **要求**: 详细说明规则的用途、原因、影响
- **建议**: 包含适用场景和不适用场景

#### `status`
- **枚举**: `draft`, `active`, `deprecated`
- **说明**:
  - `draft`: 开发中，未正式使用
  - `active`: 正式启用
  - `deprecated`: 已废弃，被新规则替代

#### `lineage`（🚨 RL5）
- **必须字段**: `introduced_in`, `derived_from`, `supersedes`
- **示例**:
  ```yaml
  lineage:
    introduced_in: "v0.9"     # 格式: v<major>.<minor>
    derived_from: null         # root 版本为 null
    supersedes: []             # 替代的旧规则（可为空数组）
  ```

#### `constraints`（🚨 RL1）
- **必须字段**: `execution`
- **固定值**: `execution: forbidden`
- **说明**: 强制 rules 不包含执行逻辑

#### `rule`
整个 rule 的核心逻辑，包含 5 个必需子字段：

##### `rule.severity`（🚨 RL3）
- **枚举**: `info`, `warn`, `error`, `block`
- **说明**:
  - `info`: 信息提示，不影响流程
  - `warn`: 警告，记录但允许通过
  - `error`: 错误，默认拒绝（需修正）
  - `block`: 阻塞，无法通过（红线级别）

##### `rule.scope`（🚨 RL4）
至少一个子字段非空：
- `applies_to_types`: content 类型数组
  - 可选值: `workflow`, `agent`, `command`, `policy`, `memory`, `fact`, `rule`
- `applies_to_risk`: 风险级别数组
  - 可选值: `low`, `medium`, `high`, `critical`
- `applies_to_phases`: 工作流阶段数组
  - 可选值: `setup`, `analysis`, `design`, `implementation`, `validation`, `review`, `release`, `operations`, `postmortem`

##### `rule.when`（🚨 RL3）
- **类型**: object（结构化条件）
- **禁止**: 字符串（如 `when: "if risk is high"`）
- **推荐模式**:
  ```yaml
  when:
    any_of:          # 或 all_of
      - field_exists: "execute"
      - field_missing: "lineage"
      - risk_level_high: true
  ```

##### `rule.then`（🚨 RL3）
- **类型**: object（结构化决策）
- **必须字段**: `decision`
- **decision 枚举**: `allow`, `deny`, `warn`, `require_review`
- **可选字段**: `reason`, `required_changes`
- **示例**:
  ```yaml
  then:
    decision: deny
    reason: "Execution payload is forbidden"
    required_changes:
      - "Remove execute field"
  ```

##### `rule.evidence_required`（🚨 RL2）
- **类型**: array（非空）
- **说明**: 判定规则需要哪些证据
- **常见值**:
  - `content_source_yaml`: YAML 源文件
  - `schema_validation`: Schema 验证结果
  - `factpack`: Factpack 扫描结果
  - `project_scan`: 项目扫描结果
  - `registry_query_result`: Registry 查询
  - `risk_assessment`: 风险评估
  - `audit_log_entry`: 审计日志

---

## 📝 编写步骤

### Step 1: 确定规则目的

回答以下问题：
1. 这条规则要防止什么问题？
2. 适用于哪些 content types / risk levels / phases？
3. 违反规则的后果是什么？
4. 需要哪些证据来判定？

### Step 2: 分配 ID 和命名

- 查看 `catalog.md` 确定下一个可用编号（如 R13）
- 起一个描述性的短名称（如 `rollback_required`）
- 组合成 ID：`rule_r13_rollback_required`

### Step 3: 填写基本字段

```yaml
id: rule_r13_rollback_required
type: rule
title: "Rollback plan required for destructive operations"
description: >
  All commands with destructive effects (delete, drop) must include
  a rollback_plan to undo changes if execution fails.
version: "0.9.0"
status: draft  # 先用 draft，测试通过后改为 active
```

### Step 4: 定义 lineage

```yaml
lineage:
  introduced_in: "v0.9"
  derived_from: null  # 新规则，无父版本
  supersedes: []      # 不替代其他规则
```

### Step 5: 设置 constraints

```yaml
constraints:
  execution: forbidden  # 固定值
```

### Step 6: 编写 rule 逻辑

```yaml
rule:
  severity: error  # 选择合适的级别
  
  scope:  # 至少一个非空
    applies_to_types: ["command"]
    applies_to_risk: ["high", "critical"]
    applies_to_phases: ["implementation", "review"]
  
  when:  # 结构化条件
    all_of:
      - effect_kind_is_delete: true
      - rollback_plan_missing: true
  
  then:  # 结构化决策
    decision: deny
    reason: "Destructive commands must have rollback plan"
    required_changes:
      - "Add rollback_plan field"
      - "Specify undo steps"
  
  evidence_required:  # 非空
    - "command_effects"
    - "rollback_plan"
```

### Step 7: 添加 metadata（可选）

```yaml
metadata:
  tags: ["rollback", "safety", "destructive"]
  related_rules: ["rule_r12_rollback_plan_required_high_risk"]
  author: "Your Name"
```

### Step 8: 保存文件

- 文件名必须与 ID 匹配：`rule_r13_rollback_required.yaml`
- 路径：`docs/content/rules/p0/rule_r13_rollback_required.yaml`

---

## ✅ 验证清单

提交前检查：

### 红线检查
- [ ] `constraints.execution` 是 `forbidden`（RL1）
- [ ] `rule.evidence_required` 非空数组（RL2）
- [ ] `rule.when` 和 `rule.then` 是结构化对象（RL3）
- [ ] `rule.severity` 是 info/warn/error/block（RL3）
- [ ] `rule.scope` 至少一个字段非空（RL4）
- [ ] `lineage` 包含 introduced_in/derived_from/supersedes（RL5）

### 结构检查
- [ ] ID 格式正确（`rule_r<nn>_<name>`）
- [ ] 文件名与 ID 匹配（`<id>.yaml`）
- [ ] `type` 是 `"rule"`
- [ ] `version` 格式正确（`X.Y.Z`）
- [ ] `title` 长度 5-200 字符
- [ ] `description` 长度 10-2000 字符

### 逻辑检查
- [ ] `when` 条件清晰、可验证
- [ ] `then.decision` 是有效枚举值
- [ ] `scope` 范围合理
- [ ] `evidence_required` 类型明确

---

## 🧪 本地测试

### 1. Schema 验证

```bash
uv run python scripts/convert_rules.py --validate --file p0/rule_r<nn>_<name>.yaml
```

**预期输出**：
```
✅ Validation passed
```

### 2. 红线验证

```bash
uv run python scripts/register_rules.py --validate-only
```

**预期输出**：
```
✅ rule_r<nn>_<name>: All red lines passed
```

### 3. 注册测试

```bash
# 使用临时数据库测试
uv run python scripts/register_rules.py --db /tmp/test_rules.db
```

**预期输出**：
```
✅ Registered: rule_r<nn>_<name> v0.9.0
```

---

## 🚫 常见错误

### 错误 1: when/then 用字符串

```yaml
# ❌ 错误
rule:
  when: "if risk is high"
  then: "deny it"
```

**正确做法**：
```yaml
# ✅ 正确
rule:
  when:
    risk_level_high: true
  then:
    decision: deny
    reason: "High risk not allowed"
```

---

### 错误 2: evidence_required 为空

```yaml
# ❌ 错误
rule:
  evidence_required: []
```

**正确做法**：
```yaml
# ✅ 正确
rule:
  evidence_required:
    - "content_source_yaml"
```

---

### 错误 3: scope 全部为空

```yaml
# ❌ 错误
rule:
  scope:
    applies_to_types: []
    applies_to_risk: []
    applies_to_phases: []
```

**正确做法**：
```yaml
# ✅ 正确
rule:
  scope:
    applies_to_types: ["command"]
    # 至少一个非空即可
```

---

### 错误 4: 包含执行字段

```yaml
# ❌ 错误
rule:
  when: { ... }
  then:
    execute: "rm -rf /tmp"  # 违反 RL1
```

**正确做法**：
```yaml
# ✅ 正确
rule:
  when: { ... }
  then:
    decision: deny  # 只能是 gate decision
    reason: "..."
```

---

### 错误 5: 文件名与 ID 不匹配

```yaml
# ❌ 错误
# 文件: rule_r13_wrong_name.yaml
id: rule_r13_rollback_required
```

**正确做法**：
```yaml
# ✅ 正确
# 文件: rule_r13_rollback_required.yaml
id: rule_r13_rollback_required
```

---

## 📖 最佳实践

### 1. 清晰命名

- **好**: `rule_r01_no_execution`
- **差**: `rule_r01_rule1`

### 2. 具体描述

- **好**: "Commands with write effects must enter requires_review state"
- **差**: "Write commands need review"

### 3. 结构化条件

- **好**: `{ effect_kind_is_write: true }`
- **差**: `"if effect is write"`

### 4. 合理 severity

- `block`: 红线级别（如 R01 禁止执行）
- `error`: 必须遵守（如 R03 引用必须在 registry）
- `warn`: 最佳实践（如 R09 建议引用证据）
- `info`: 提示信息（罕用）

### 5. 明确 scope

不要用 `applies_to_types: ["workflow", "agent", "command", "policy", "memory", "fact", "rule"]`（太宽泛）

**建议**: 只列出真正适用的类型

---

## 🔄 演化规则

### 创建新版本

如果需要修改现有规则：

```yaml
id: rule_r01_no_execution_v2  # 新 ID
type: rule
title: "..."
version: "0.10.0"  # 新版本
status: active

lineage:
  introduced_in: "v0.10"
  derived_from: "rule_r01_no_execution"  # 指向父版本
  supersedes: ["rule_r01_no_execution"]  # 替代旧版本

# ... 修改后的规则逻辑
```

---

## 📚 参考资料

- **Schema**: `agentos/schemas/content/rule.schema.json`
- **示例**: `docs/content/rules/p0/rule_r01_no_execution.yaml`（标准模板）
- **Validator**: `agentos/core/gates/validate_rule_redlines.py`
- **README**: `docs/content/rules/README.md`
- **Catalog**: `docs/content/rules/catalog.md`

---

## 💬 贡献流程

1. Fork 仓库
2. 创建新 rule YAML 文件
3. 运行本地测试（schema + 红线）
4. 提交 PR，标题：`feat(rules): add R<nn> <short_title>`
5. 等待 CI 通过（6 个 gates）
6. 等待 Code Review 批准

---

**版本**: v0.9.0  
**维护**: AgentOS Team  
**最后更新**: 2026-01-25
