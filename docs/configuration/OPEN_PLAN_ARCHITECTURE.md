# Open Plan Architecture - 开放理解 + 收敛执行

**Version**: 1.0.0  
**Date**: 2026-01-26  
**Status**: Experimental Prototype

---

## Executive Summary

Open Plan是AgentOS的实验性扩展,实现"开放理解 + 收敛执行"的理念:

- **AI负责发散**: 从自然语言理解需求,概率匹配mode,自由拆解步骤
- **系统负责收敛**: 把方案收敛成可执行、可验证、可审计的动作

核心设计原则: **Don't constrain content, only constrain the interface.**

---

## Table of Contents

1. [核心理念](#核心理念)
2. [架构设计](#架构设计)
3. [数据结构](#数据结构)
4. [执行流程](#执行流程)
5. [验证层](#验证层)
6. [与现有系统的关系](#与现有系统的关系)
7. [使用示例](#使用示例)
8. [限制与权衡](#限制与权衡)
9. [实施指南](#实施指南)
10. [未来演进](#未来演进)

---

## 核心理念

### 问题

传统的AI执行系统面临两难:

- **过度约束**: 预定义固定的步骤类型、操作词表 → 限制AI能力
- **过度开放**: 完全自由生成 → 难以验证、审计、执行

### 解决方案

Open Plan通过"容器 + 通道"模型平衡自由度和可控性:

```
┌─────────────────────────────────────────┐
│          OpenPlan (容器)                │
│  - 固定结构: goal, mode_selection, steps│
│  - 开放内容: AI自由填充                  │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│      7种执行通道 (Action Kinds)          │
│  command | file | api | agent |         │
│  rule | check | note                    │
│  - 限定接口                              │
│  - 开放payload                           │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│         双重验证                         │
│  - 结构校验: JSON schema               │
│  - 业务规则: Mode constraints           │
└─────────────────────────────────────────┘
```

### 关键特性

1. **无限内容空间**: AI不受预定义步骤类型限制
2. **有边界接口**: 所有操作通过7种通道执行
3. **最小必填字段**: 每种通道只要求关键字段
4. **全程审计**: mode_proposal + plan + validation全记录

---

## 架构设计

### 组件架构

```
┌─────────────────────────────────────────────────────┐
│              User Input (自然语言)                   │
└────────────────────┬────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│  ModeProposer (LLM驱动)                            │
│  - 理解用户意图                                     │
│  - 提议mode pipeline                               │
│  - 输出: ModeSelection + confidence + reason       │
└────────────────────┬────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│  OpenPlanBuilder (LLM驱动)                         │
│  - 拆解任务为steps                                 │
│  - 为每个step提议actions                           │
│  - 输出: OpenPlan                                  │
└────────────────────┬────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│  StructuralValidator                               │
│  - JSON schema验证                                 │
│  - 检查必填字段                                     │
│  - 检查类型正确性                                   │
└────────────────────┬────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│  OpenPlanVerifier (业务规则)                       │
│  - Planning mode禁止diff                           │
│  - Implementation mode必须有diff                   │
│  - Pipeline transition规则                         │
│  - Allowlist/path constraints                      │
└────────────────────┬────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────┐
│  ExecutorEngine (执行)                             │
│  - 遍历steps                                       │
│  - 根据action kind分发执行                         │
│  - 记录审计轨迹                                     │
└─────────────────────────────────────────────────────┘
```

### 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| **OpenPlan Schema** | `agentos/core/schemas/open_plan.py` | 数据容器定义 |
| **Action Validators** | `agentos/core/schemas/action_validators.py` | 动态schema验证 |
| **Structural Validator** | `agentos/core/schemas/structural_validator.py` | 结构校验 |
| **ModeProposer** | `agentos/core/mode/mode_proposer.py` | LLM驱动mode选择 |
| **OpenPlanBuilder** | `agentos/core/executor_dry/open_plan_builder.py` | LLM驱动plan生成 |
| **OpenPlanVerifier** | `agentos/core/executor/open_plan_verifier.py` | 业务规则校验 |
| **GOPL Gate** | `scripts/gates/gopl_open_plan_gate.py` | CI gate |

---

## 数据结构

### OpenPlan

```json
{
  "goal": "创建一个landing page",
  "mode_selection": {
    "primary_mode": "planning",
    "pipeline": ["planning", "implementation"],
    "confidence": 0.92,
    "reason": "Creating new feature requires planning then implementation"
  },
  "steps": [
    {
      "id": "S1",
      "intent": "设计页面结构和布局",
      "proposed_actions": [
        {
          "kind": "file",
          "payload": {
            "path": "src/pages/landing.tsx",
            "operation": "declare",
            "intent": "React landing page component"
          }
        }
      ],
      "success_criteria": [
        "页面结构清晰",
        "响应式设计"
      ],
      "risks": [
        "设计可能不符合品牌标准"
      ]
    },
    {
      "id": "S2",
      "intent": "实现页面组件",
      "proposed_actions": [
        {
          "kind": "file",
          "payload": {
            "path": "src/pages/landing.tsx",
            "operation": "create",
            "content_hint": "React component with hero section"
          }
        },
        {
          "kind": "check",
          "payload": {
            "check_type": "build",
            "target": "src/pages/landing.tsx"
          }
        }
      ],
      "success_criteria": [
        "组件编译通过",
        "无linter错误"
      ],
      "risks": [
        "可能有性能问题"
      ]
    }
  ],
  "artifacts": [
    {
      "path": "src/pages/landing.tsx",
      "role": "output",
      "notes": "Main landing page component"
    }
  ],
  "metadata": {
    "plan_id": "openplan_20260126_143022",
    "generated_at": "2026-01-26T14:30:22",
    "model": "gpt-4o-mini",
    "builder_version": "1.0.0"
  }
}
```

### 7种Action Kinds

#### 1. command

执行shell命令

```json
{
  "kind": "command",
  "payload": {
    "cmd": "npm install react",
    "args": ["--save"],
    "working_dir": "/path/to/project",
    "timeout": 30000
  }
}
```

#### 2. file

文件操作

```json
{
  "kind": "file",
  "payload": {
    "path": "src/App.tsx",
    "operation": "create",  // create | update | delete | declare
    "intent": "Main application component",
    "content_hint": "React component with routing"
  }
}
```

**重要**: Planning mode只能用`operation: "declare"`,Implementation mode可以用`create/update/delete`

#### 3. api

API调用

```json
{
  "kind": "api",
  "payload": {
    "endpoint": "https://api.example.com/deploy",
    "method": "POST",
    "body": {"version": "1.0.0"},
    "headers": {"Authorization": "Bearer token"}
  }
}
```

#### 4. agent

委托给子agent

```json
{
  "kind": "agent",
  "payload": {
    "agent_type": "frontend-engineer",
    "task": "Implement user authentication UI",
    "context": {"tech_stack": ["React", "TypeScript"]},
    "mode": "implementation"
  }
}
```

#### 5. rule

执行约束

```json
{
  "kind": "rule",
  "payload": {
    "constraint": "不修改已有测试文件",
    "scope": "tests/",
    "enforcement": "hard"  // hard | soft | warn
  }
}
```

#### 6. check

验证操作

```json
{
  "kind": "check",
  "payload": {
    "check_type": "test",  // build | test | lint | run | exists | contains
    "target": "src/",
    "expected": "all tests pass"
  }
}
```

#### 7. note

人类可读注释

```json
{
  "kind": "note",
  "payload": {
    "message": "这一步可能需要人工review",
    "level": "warning"  // info | warning | error | debug
  }
}
```

---

## 执行流程

### 完整流程图

```
User Request
    ↓
ModeProposer
    ↓ (ModeSelection)
OpenPlanBuilder
    ↓ (OpenPlan)
StructuralValidator
    ↓ (pass)
OpenPlanVerifier
    ↓ (pass)
ExecutorEngine
    ↓ (iterate steps)
For each step:
    ├─ For each action:
    │   ├─ kind == "command" → execute shell
    │   ├─ kind == "file" → write/update file
    │   ├─ kind == "agent" → delegate to sub-agent
    │   ├─ kind == "check" → run verification
    │   ├─ kind == "rule" → enforce constraint
    │   └─ kind == "note" → log to audit
    └─ Record to audit log
    ↓
Generate ReviewPack
```

### 审计轨迹

每次执行保存为`runs/<id>/open_plan.json`:

```json
{
  "run_id": "run_20260126_143022",
  "mode_proposal": {
    "nl_input": "创建一个landing page",
    "proposed": {
      "primary_mode": "planning",
      "pipeline": ["planning", "implementation"],
      "confidence": 0.92,
      "reason": "..."
    },
    "timestamp": "2026-01-26T14:30:22Z"
  },
  "open_plan": { /* OpenPlan JSON */ },
  "validation": {
    "structure": {"passed": true, "errors": []},
    "business_rules": {"passed": true, "violations": []}
  },
  "execution": {
    "status": "success",
    "steps_completed": 5,
    "operations_executed": 12
  }
}
```

---

## 验证层

### 双重验证

#### 1. 结构校验 (LLM生成后)

**时机**: `OpenPlanBuilder.build()` → `StructuralValidator.validate()`

**检查项**:
- ✅ Required fields存在
- ✅ Types正确
- ✅ `kind` 在7种之内
- ✅ `confidence` 在[0.0, 1.0]
- ✅ No duplicate step IDs
- ✅ Action payloads有必填字段

**实现**: `StructuralValidator` + `action_validators`

#### 2. 业务规则校验 (execution前)

**时机**: `ExecutorEngine.execute()` 入口处

**检查项**:
- ✅ Planning mode禁止file create/update/delete
- ✅ Implementation mode必须至少有一个file操作
- ✅ Pipeline transitions合法
- ✅ Commands在allowlist中
- ✅ File paths在allowed_paths中

**实现**: `OpenPlanVerifier`

### 业务规则清单

| Rule ID | Description | Severity |
|---------|-------------|----------|
| BR001 | Planning mode步骤不能包含file create/update/delete | error |
| BR002 | Implementation mode必须有至少一个file操作 | error |
| BR003 | Pipeline transitions必须合法 | error |
| BR004 | Commands必须在allowlist中 | error |
| BR005 | File操作必须respect allowed_paths | error |
| BR006 | 避免循环agent delegation | warning |
| BR007 | Check操作必须可行 | warning |

---

## 与现有系统的关系

### 清晰边界

| 维度 | 现有系统 (规则驱动) | Open Plan (理解驱动) |
|------|---------------------|----------------------|
| **Mode选择** | ModeSelector (关键词规则) | ModeProposer (LLM理解) |
| **Plan生成** | DryExecutor (固定结构) | OpenPlanBuilder (开放步骤) |
| **校验** | Schema validation | 结构校验 + 业务规则校验 |
| **执行** | ExecutorEngine (不变) | 相同 (最终都调用ExecutorEngine) |
| **Gate** | 现有gate (不变) | 新增 GOPL gate |
| **10条护城河** | 完全遵守 | 完全遵守 (无例外) |

### 兼容性保证

1. **Mode system不变**: `experimental_open_plan` 是新增mode,不影响现有mode
2. **Executor不变**: 最终都通过`ExecutorEngine.execute()`执行
3. **Gate system不变**: GOPL gate是新增,不替换现有gate
4. **审计不变**: 遵守相同的ReviewPack规范

### 用户选择

用户可以选择使用:
- **规则模式**: `ModeSelector` + `DryExecutor` (确定性,快速)
- **理解模式**: `ModeProposer` + `OpenPlanBuilder` (灵活,智能)
- **混合模式**: Mode用规则,Plan用Open Plan

---

## 使用示例

### 示例1: 创建Landing Page

**输入**:

```python
from agentos.core.mode import ModeProposer
from agentos.core.executor_dry import OpenPlanBuilder
from agentos.core.schemas import validate_open_plan_structure
from agentos.core.executor import verify_open_plan

# Step 1: Propose mode
proposer = ModeProposer()
mode_selection = proposer.propose_mode("创建一个landing page")

print(f"Pipeline: {mode_selection.pipeline}")
# Output: ['planning', 'implementation']
print(f"Confidence: {mode_selection.confidence}")
# Output: 0.92

# Step 2: Build plan
builder = OpenPlanBuilder()
plan = builder.build(
    goal="创建一个landing page",
    mode_selection=mode_selection,
    context={"tech_stack": ["React", "TypeScript"]}
)

print(f"Steps: {len(plan.steps)}")
# Output: 5

# Step 3: Structural validation
structural_report = validate_open_plan_structure(plan)
assert structural_report.valid

# Step 4: Business rules validation
business_report = verify_open_plan(plan)
assert business_report.valid

# Step 5: Execute (假设在ExecutorEngine中)
# executor.execute(plan)
```

**生成的Plan** (简化):

```json
{
  "goal": "创建一个landing page",
  "mode_selection": {...},
  "steps": [
    {
      "id": "S1",
      "intent": "设计页面结构",
      "proposed_actions": [
        {"kind": "file", "payload": {"path": "src/pages/landing.tsx", "operation": "declare"}}
      ]
    },
    {
      "id": "S2",
      "intent": "实现React组件",
      "proposed_actions": [
        {"kind": "file", "payload": {"path": "src/pages/landing.tsx", "operation": "create"}},
        {"kind": "check", "payload": {"check_type": "build", "target": "src/"}}
      ]
    },
    {
      "id": "S3",
      "intent": "添加样式",
      "proposed_actions": [
        {"kind": "file", "payload": {"path": "src/pages/landing.module.css", "operation": "create"}},
        {"kind": "check", "payload": {"check_type": "lint", "target": "src/"}}
      ]
    }
  ]
}
```

### 示例2: 修复Bug

**输入**:

```python
mode_selection = proposer.propose_mode(
    "修复登录页面无法提交的bug",
    additional_context="用户反馈点击登录按钮没有反应"
)

print(f"Pipeline: {mode_selection.pipeline}")
# Output: ['debug', 'implementation']

plan = builder.build(
    goal="修复登录页面无法提交的bug",
    mode_selection=mode_selection,
    context={"bug_report": "Login button not responding"}
)
```

**生成的Plan** (简化):

```json
{
  "steps": [
    {
      "id": "S1",
      "intent": "诊断问题",
      "proposed_actions": [
        {"kind": "check", "payload": {"check_type": "exists", "target": "src/pages/login.tsx"}},
        {"kind": "note", "payload": {"message": "检查事件处理器绑定"}}
      ]
    },
    {
      "id": "S2",
      "intent": "修复事件处理器",
      "proposed_actions": [
        {"kind": "file", "payload": {"path": "src/pages/login.tsx", "operation": "update"}},
        {"kind": "check", "payload": {"check_type": "test", "target": "tests/login.test.ts"}}
      ]
    }
  ]
}
```

### 示例3: 只读分析

**输入**:

```python
mode_selection = proposer.propose_mode("分析代码质量并给出建议")

print(f"Pipeline: {mode_selection.pipeline}")
# Output: ['chat']
```

**生成的Plan** (简化):

```json
{
  "steps": [
    {
      "id": "S1",
      "intent": "扫描代码库",
      "proposed_actions": [
        {"kind": "check", "payload": {"check_type": "lint", "target": "src/"}},
        {"kind": "check", "payload": {"check_type": "test", "target": "tests/"}}
      ]
    },
    {
      "id": "S2",
      "intent": "生成报告",
      "proposed_actions": [
        {"kind": "note", "payload": {"message": "代码质量良好,覆盖率85%", "level": "info"}}
      ]
    }
  ]
}
```

---

## 限制与权衡

### 适合使用Open Plan的场景

✅ **复杂任务** - 需要多步骤拆解  
✅ **创造性任务** - 没有固定模式  
✅ **探索性任务** - 需求不完全明确  
✅ **跨领域任务** - 涉及多种操作类型

### 不适合使用Open Plan的场景

❌ **简单任务** - 1-2步就能完成  
❌ **高确定性任务** - 有明确SOP  
❌ **实时任务** - 需要极快响应  
❌ **资源敏感任务** - Token成本敏感

### 权衡对比

| 维度 | 规则模式 (ModeSelector) | 理解模式 (Open Plan) |
|------|------------------------|---------------------|
| **速度** | 快 (毫秒级) | 慢 (秒级,需LLM调用) |
| **成本** | 低 (无LLM调用) | 中 (2次LLM调用) |
| **确定性** | 高 (规则固定) | 中 (LLM有随机性) |
| **灵活性** | 低 (关键词匹配) | 高 (真正理解) |
| **可解释性** | 高 (规则透明) | 中 (需审计reason) |
| **适用范围** | 已知模式 | 开放域 |

### Confidence Fallback策略

建议根据confidence决定是否使用Open Plan:

```python
mode_selection = proposer.propose_mode(nl_input)

if mode_selection.confidence < 0.5:
    # 低confidence: fallback到规则模式
    selector = ModeSelector()
    mode_selection = selector.select_mode(nl_input)
    use_open_plan = False
else:
    # 高confidence: 使用Open Plan
    use_open_plan = True
```

---

## 实施指南

### 集成到现有项目

#### 1. 使用ModeProposer (替代ModeSelector)

```python
# 旧代码
from agentos.core.mode import ModeSelector
selector = ModeSelector()
selection = selector.select_mode(nl_input)

# 新代码
from agentos.core.mode import ModeProposer
proposer = ModeProposer()
selection = proposer.propose_mode(nl_input)
```

#### 2. 使用OpenPlanBuilder (替代DryExecutor)

```python
# 旧代码
from agentos.core.executor_dry import DryExecutor
executor = DryExecutor()
result = executor.run(intent)

# 新代码
from agentos.core.executor_dry import OpenPlanBuilder
builder = OpenPlanBuilder()
plan = builder.build(goal, mode_selection, context)
```

#### 3. 添加验证

```python
from agentos.core.schemas import validate_open_plan_structure
from agentos.core.executor import verify_open_plan

# 结构验证
structural_report = validate_open_plan_structure(plan)
if not structural_report.valid:
    raise ValueError(f"Structural validation failed: {structural_report.errors}")

# 业务规则验证
business_report = verify_open_plan(
    plan,
    allowlist_commands=["npm", "git", "pnpm"],
    allowed_paths=["src/**", "tests/**"]
)
if not business_report.valid:
    raise ValueError(f"Business validation failed: {business_report.violations}")
```

### CI/CD集成

在CI pipeline中添加GOPL gate:

```yaml
# .github/workflows/ci.yml
- name: Run GOPL Gate
  run: |
    python scripts/gates/gopl_open_plan_gate.py runs/ tests/fixtures/
```

### 环境变量

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"  # 可选,默认gpt-4o-mini
```

---

## 未来演进

### v1.1 (Near Term)

- **Context增强**: 自动从FactPack/MemoryPack提取context
- **Confidence调优**: 基于历史数据优化confidence阈值
- **Action扩展**: 新增`docker`, `k8s`等action kinds
- **Replay功能**: 重放历史plan用于测试

### v1.2 (Mid Term)

- **多模型支持**: 支持Claude, Gemini等其他模型
- **Plan优化**: LLM自我review并优化plan
- **Dynamic adjustment**: 执行中根据结果动态调整plan
- **Cost optimization**: 缓存常见pattern减少LLM调用

### v2.0 (Long Term)

- **Multi-agent协作**: 多个OpenPlan并行执行
- **Plan templates**: 从历史成功plan学习patterns
- **RL优化**: 用强化学习优化mode selection和plan generation
- **Visual editor**: 图形化编辑OpenPlan

---

## 附录

### A. 完整API参考

#### ModeProposer

```python
class ModeProposer:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini")
    
    def propose_mode(
        self,
        nl_input: str,
        available_modes: Optional[List[str]] = None,
        additional_context: Optional[str] = None
    ) -> ModeSelection
```

#### OpenPlanBuilder

```python
class OpenPlanBuilder:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini")
    
    def build(
        self,
        goal: str,
        mode_selection: ModeSelection,
        context: Optional[Dict[str, Any]] = None
    ) -> OpenPlan
```

#### StructuralValidator

```python
class StructuralValidator:
    def __init__(self, strict: bool = False)
    
    def validate(self, plan: OpenPlan) -> StructuralValidationReport
```

#### OpenPlanVerifier

```python
class OpenPlanVerifier:
    def __init__(
        self,
        allowlist_commands: Optional[List[str]] = None,
        allowed_paths: Optional[List[str]] = None,
        forbidden_paths: Optional[List[str]] = None
    )
    
    def verify(self, plan: OpenPlan) -> BusinessValidationReport
```

### B. 常见问题

**Q: Open Plan与现有mode system冲突吗?**  
A: 不冲突。Open Plan是可选的扩展,用户可以继续使用规则模式。

**Q: Open Plan的成本如何?**  
A: 2次LLM调用 (ModeProposer + OpenPlanBuilder),约$0.001-0.01 per request (gpt-4o-mini)

**Q: 如何确保Open Plan不会生成危险操作?**  
A: 通过双重验证 + 10条护城河 + gate强制执行

**Q: Open Plan可以离线运行吗?**  
A: 需要LLM API,但可以缓存常见patterns或使用本地模型

**Q: 如何调试Open Plan失败?**  
A: 查看审计轨迹 `runs/<id>/open_plan.json`,包含完整validation报告

### C. 相关文档

- [AgentOS Whitepaper](WHITEPAPER_FULL_EN.md)
- [Mode System](../agentos/core/mode/README.md)
- [10条护城河](V12_HARD_EVIDENCE_REPORT.md)
- [Executor Red Lines](executor/RED_LINES.md)

---

**Created**: 2026-01-26  
**Last Updated**: 2026-01-26  
**Version**: 1.0.0  
**Status**: 🟡 Experimental Prototype  
**Maintainers**: AgentOS Team
