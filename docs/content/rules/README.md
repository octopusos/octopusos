# AgentOS Rules Catalog

Rules 是 AgentOS 的内容治理系统。本目录包含 **12 条 P0 Rules**，用于约束和验证 Content Plane 中的所有内容（Workflows、Agents、Commands 等）。

---

## 🚨 五条红线（Red Lines）

Rules 自身必须遵守以下强制约束：

### RL1: Rule 不包含执行指令

**禁止字段**：
- `execute`, `run`, `shell`, `bash`, `python`, `powershell`
- `subprocess`, `command_line`, `script`, `exec`

**强制约束**：
- `constraints.execution` 必须为 `"forbidden"`

### RL2: Rule 必须可审计（evidence_required）

**必须字段**：
- `rule.evidence_required` (array)
- 不能为空数组

**用途**：
- 声明判定规则需要哪类证据（factpack、scan、metadata 等）

### RL3: Rule 必须可机器判定（predicate 结构化）

**必须字段**：
- `rule.when` (object) - 结构化条件
- `rule.then` (object) - 结构化决策
- `rule.severity` (enum: info|warn|error|block)

**用途**：
- 为未来的规则引擎提供可执行的判定逻辑

### RL4: Rule 必须声明适用范围（scope）

**必须字段**（至少一个非空）：
- `rule.scope.applies_to_types` (array)
- `rule.scope.applies_to_risk` (array)
- `rule.scope.applies_to_phases` (array)

**用途**：
- 明确规则适用于哪些内容类型、风险级别、工作流阶段

### RL5: Rule 必须有 lineage

**必须字段**：
- `lineage.introduced_in` (format: `v0.9`)
- `lineage.derived_from` (null 或 rule ID)
- `lineage.supersedes` (array)

**用途**：
- 追踪规则演化历史，与其他 content 保持一致

---

## 📋 12 条 P0 Rules 目录

### R01: No Execution（禁止执行）
- **ID**: `rule_r01_no_execution`
- **Severity**: `block`
- **Scope**: 所有 content types
- **用途**: 强制 Content Plane 只存储定义，不包含执行逻辑

### R02: Lineage Required（lineage 必需）
- **ID**: `rule_r02_lineage_required`
- **Severity**: `block`
- **Scope**: workflow, agent, command, policy, rule
- **用途**: 激活前必须有完整 lineage（v0.5 红线的 gate 表达）

### R03: Registry Only References（仅引用注册内容）
- **ID**: `rule_r03_registry_only_references`
- **Severity**: `error`
- **Scope**: workflow, agent, command (medium/high/critical risk)
- **用途**: 禁止编造 content ID，必须从 registry 引用

### R04: No Fabrication Paths Commands（禁止编造路径/命令）
- **ID**: `rule_r04_no_fabrication_paths_commands`
- **Severity**: `error`
- **Scope**: workflow, command (medium/high/critical risk)
- **用途**: 路径/命令必须来自 factpack/scan，禁止幻觉

### R05: Risk Escalation Cloud Model Required（高风险需云端模型）
- **ID**: `rule_r05_risk_escalation_cloud_model_required`
- **Severity**: `error`
- **Scope**: high/critical risk
- **用途**: 高风险决策必须用云端模型推理（安全兜底）

### R06: Question Budget Full Auto Zero（全自动模式无提问预算）
- **ID**: `rule_r06_question_budget_full_auto_zero`
- **Severity**: `block`
- **Scope**: workflow (full_auto mode)
- **用途**: 无人值守模式禁止提问

### R07: Change Budget Required（变更预算必需）
- **ID**: `rule_r07_change_budget_required`
- **Severity**: `error`
- **Scope**: workflow (medium/high/critical risk)
- **用途**: 声明 max_files 和 max_commits，防止失控

### R08: Write Effect Requires Review State（写操作需审查）
- **ID**: `rule_r08_write_effect_requires_review_state`
- **Severity**: `error`
- **Scope**: command (write effects)
- **用途**: 写操作必须进入 requires_review 状态（gate decision）

### R09: Evidence Refs Required for Key Decisions（关键决策需证据）
- **ID**: `rule_r09_evidence_refs_required_for_key_decisions`
- **Severity**: `warn`
- **Scope**: workflow, command (key decisions)
- **用途**: 重要决策必须引用 evidence_refs（可审计）

### R10: Lock Scope Required for File Targets（文件操作需锁范围）
- **ID**: `rule_r10_lock_scope_required_for_file_targets`
- **Severity**: `error`
- **Scope**: command (targets files)
- **用途**: 声明 lock_scope，支持并发冲突检测（WAIT+replan）

### R11: Audit Log Mandatory（审计日志必需）
- **ID**: `rule_r11_audit_log_mandatory`
- **Severity**: `error`
- **Scope**: rule (all evaluations)
- **用途**: 规则判定必须写入 run_tape/audit（合规）

### R12: Rollback Plan Required High Risk（高风险需回滚计划）
- **ID**: `rule_r12_rollback_plan_required_high_risk`
- **Severity**: `error`
- **Scope**: high/critical risk
- **用途**: 高风险操作必须有 rollback_plan（失败恢复）

---

## 📦 文件结构

```
docs/content/rules/
├── README.md                    # 本文件
├── catalog.md                   # 规则目录（详细版）
├── authoring-guide.md           # 编写指南
└── p0/                          # P0 规则 YAML 文件
    ├── rule_r01_no_execution.yaml
    ├── rule_r02_lineage_required.yaml
    ├── rule_r03_registry_only_references.yaml
    ├── rule_r04_no_fabrication_paths_commands.yaml
    ├── rule_r05_risk_escalation_cloud_model_required.yaml
    ├── rule_r06_question_budget_full_auto_zero.yaml
    ├── rule_r07_change_budget_required.yaml
    ├── rule_r08_write_effect_requires_review_state.yaml
    ├── rule_r09_evidence_refs_required_for_key_decisions.yaml
    ├── rule_r10_lock_scope_required_for_file_targets.yaml
    ├── rule_r11_audit_log_mandatory.yaml
    └── rule_r12_rollback_plan_required_high_risk.yaml
```

---

## 🛠️ 使用指南

### 验证 Rules Schema

```bash
# 验证所有 rule YAML 文件
uv run python scripts/convert_rules.py --validate
```

### 注册 Rules

```bash
# 注册所有 rules（自动激活）
uv run python scripts/register_rules.py --auto-activate
```

### 列出已注册的 Rules

```bash
# 列出所有 rules
uv run agentos content list --type rule

# 查看特定 rule
uv run agentos content explain rule_r01_no_execution
```

### 运行 Gates

```bash
# Gate A: 文件存在性（严格 12 条）
uv run python scripts/gates/v09_gate_a_rules_exist.py

# Gate B: Schema 验证
uv run python scripts/gates/v09_gate_b_schema_validation.py

# Gate C: 红线负向测试
uv run python scripts/gates/v09_gate_c_redline_fixtures.py

# Gate D: 静态扫描（禁止执行符号）
bash scripts/gates/v09_gate_d_no_execution_symbols.sh

# Gate E: DB 初始化
uv run python scripts/gates/v09_gate_e_db_init.py

# Gate F: Explain 稳定性
uv run python scripts/gates/v09_gate_f_explain_snapshot.py
```

---

## 🚫 反模式（Anti-patterns）

### ❌ 错误 1: Rule 包含执行代码

```yaml
# 错误示例
rule:
  when: { ... }
  then:
    execute: "rm -rf /tmp/cache"  # ❌ 违反 RL1
```

**正确做法**：`then` 只能包含 gate decision（allow/deny/warn/require_review）

### ❌ 错误 2: evidence_required 为空

```yaml
# 错误示例
rule:
  evidence_required: []  # ❌ 违反 RL2
```

**正确做法**：至少声明一种证据类型（如 `["content_source_yaml"]`）

### ❌ 错误 3: when/then 非结构化

```yaml
# 错误示例
rule:
  when: "if risk is high"  # ❌ 违反 RL3（字符串）
  then: "deny it"          # ❌ 违反 RL3（字符串）
```

**正确做法**：使用结构化对象

```yaml
rule:
  when:
    risk_level_high: true
  then:
    decision: deny
    reason: "..."
```

### ❌ 错误 4: scope 全部为空

```yaml
# 错误示例
rule:
  scope:
    applies_to_types: []
    applies_to_risk: []
    applies_to_phases: []  # ❌ 违反 RL4
```

**正确做法**：至少一个字段非空

---

## 📖 相关文档

- **Schema**: `agentos/schemas/content/rule.schema.json`
- **Validator**: `agentos/core/gates/validate_rule_redlines.py`
- **Catalog**: `docs/content/rules/catalog.md`（详细索引）
- **Authoring Guide**: `docs/content/rules/authoring-guide.md`（编写指南）
- **v0.9 完成报告**: `docs/V09_RULES_IMPLEMENTATION_COMPLETE.md`
- **v0.9 冻结报告**: `docs/V09_FREEZE_CHECKLIST_REPORT.md`

---

## 🔒 版本与状态

- **版本**: v0.9.0
- **状态**: ✅ ACTIVE（Production Ready）
- **规则数量**: 12 条（P0）
- **红线数量**: 5 条（RL1-RL5）
- **冻结日期**: 2026-01-25

---

**维护**: AgentOS Team  
**最后更新**: 2026-01-25
