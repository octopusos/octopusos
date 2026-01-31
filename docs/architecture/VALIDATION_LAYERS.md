# Validation Layers Architecture

## Overview

AgentOS 采用三层验证架构，每层有明确的职责边界。**这三层不对齐是设计选择，而非缺陷。**

```
┌─────────────────────────────────────────┐
│  Layer 1: Schema Validation             │  ← 结构层
│  "这是不是合法的 OpenPlan 形态？"          │
├─────────────────────────────────────────┤
│  Layer 2: Business Rule Validation      │  ← 业务语义层
│  "这个计划在业务上是否自洽？"              │
├─────────────────────────────────────────┤
│  Layer 3: Dry Executor RED LINE         │  ← 安全层
│  "这个计划在执行前是否安全、可审计？"       │
└─────────────────────────────────────────┘
```

⸻

## Layer 1: Schema Validation

### 职责
回答："这是不是一个合法的 JSON 结构？"

### 校验内容
- JSON Schema 合规性
- 必填字段存在性
- 类型正确性
- 基础约束（枚举、数组长度、字符串格式）

### 实现
- `agentos/core/verify/schema_validator_service.py`
- `agentos/schemas/**/*.schema.json`

### 不关心
- ❌ 业务语义（planning mode 能不能有 diff）
- ❌ 安全风险（路径有没有伪造）
- ❌ 审计完整性（有没有 evidence_refs）

### 错误输出
```python
SchemaError:
  - path: "steps[0].proposed_actions[1].payload.operation"
  - message: "Field is required"
```

⸻

## Layer 2: Business Rule Validation (BR)

### 职责
回答："这个计划在业务语义上是否自洽？"

### 校验内容（BR001-BR007）
- BR001: Planning mode 不能有文件修改操作
- BR002: Implementation mode 必须有文件操作
- BR003: Pipeline 转换合法性
- BR004: Command allowlist 检查
- BR005: 文件路径约束（allowed_paths）
- BR006: Agent 委托循环检测
- BR007: 操作可行性检查

### 实现
- `agentos/core/executor/open_plan_verifier.py`

### 天然不覆盖（by design）
- ❌ DE3: 路径伪造检测（这是安全问题，不是业务规则）
- ❌ DE4: evidence_refs 强制（这是审计要求，不是语义要求）
- ❌ DE5: 高风险 requires_review（这是安全策略，不是业务逻辑）
- ❌ DE6: checksum/lineage（这是冻结保证，不是语义约束）

### 错误输出
```python
BusinessRuleViolation:
  - rule_id: "BR001"
  - severity: "error"
  - message: "Planning phase step 'step_1' contains file create operation"
  - step_id: "step_1"
```

⸻

## Layer 3: Dry Executor RED LINE (DE)

### 职责
回答："这个计划在'执行前'是否安全、可冻结、可审计？"

### 校验内容（DE1-DE6）
- DE1: 禁止执行符号（subprocess/exec）
- DE2: 禁止写项目文件
- DE3: 禁止编造路径（必须来自 intent/evidence）
- DE4: 所有节点必须有 evidence_refs
- DE5: 高/致命风险必须 requires_review
- DE6: 必须有 checksum + lineage

### 实现
- `agentos/core/executor_dry/validator.py` (DryExecutorValidator)
- `agentos/core/executor_dry/utils.py` (enforce_red_lines)

### 为什么不在 BR 层？
因为这些是**执行前的安全防线**，而非业务规则：
- 路径伪造 → 信任边界问题，不是语义问题
- evidence_refs → 审计要求，不是业务要求
- requires_review → 风险治理，不是流程约束

### 错误输出
```python
DryExecutorViolation:
  - violation_id: "DE4"
  - severity: "critical"
  - message: "Node 'node_003' missing evidence_refs"
  - node_id: "node_003"
```

⸻

## 为什么三层不对齐是正确的？

### ❌ 错误理解
"BR 和 DE 应该一一对应，否则有遗漏"

### ✅ 正确理解
"BR 和 DE 关注点不同，强行对齐会导致层污染"

### 类比（帮助理解）
```
Schema    = TypeScript 编译器 → "语法合法吗？"
BR        = ESLint 规则       → "代码风格一致吗？"
DE        = Security Scanner  → "有安全漏洞吗？"
```

你不会期望 ESLint 去检测 SQL 注入，
也不会期望 Security Scanner 去检查变量命名。

**职责分离 = 架构清晰**

⸻

## 错误信息链路（Traceable, Not Unified）

### 目标
不是统一错误码，而是统一追溯路径。

### 实现
所有验证错误都携带：
- `trace_id`: 唯一追溯 ID
- `task_id`: 所属任务 ID
- `layer`: 验证层（schema/br/de）
- `source`: 错误来源（validator class）

### 示例错误输出
```json
{
  "trace_id": "trace_2026_001",
  "task_id": "task_abc123",
  "layer": "dry_executor",
  "violation": {
    "id": "DE5",
    "severity": "critical",
    "message": "high risk without requires_review"
  }
}
```

⸻

## Definition of Done (S-02)

✅ Task S-02 完成标准：

1. **文档化分层契约** → 本文档
2. **DryExecutorValidator 统一入口** → `validator.py`
3. **错误链路可追溯** → 所有错误携带 layer 标识

⸻

## 架构原则

### ✅ DO
- 每层只关心自己的职责
- 错误信息明确标注来源层
- 可以跨层组合验证，但不能混合职责

### ❌ DON'T
- 不要在 Schema 中加业务规则
- 不要在 BR 中加安全检查
- 不要期望三层"对齐"

⸻

## 引用
- Schema 实现：`agentos/core/verify/schema_validator_service.py`
- BR 实现：`agentos/core/executor/open_plan_verifier.py`
- DE 实现：`agentos/core/executor_dry/validator.py`
- RED LINE 文档：`docs/executor/RED_LINES.md`
