# Open Plan 架构主权边界

**Version**: 1.0.0  
**Date**: 2026-01-26  
**Status**: 架构定义  
**Authority**: 架构所有者必读

---

## 核心铁律

### 铁律 1: Verifier 不得 import Executor

```python
# ❌ 绝对禁止
from ..executor.executor_engine import ExecutorEngine

# ✅ 允许
from ..schemas import OpenPlan
```

**原因**: Verifier只能检查plan的合法性,不能依赖executor的实现细节。

**通信方式**: 通过 capability descriptors 间接通信

```python
# Verifier检查action kind是否存在
AVAILABLE_KINDS = get_available_kinds()  # 从schema获取,不从executor
if action.kind not in AVAILABLE_KINDS:
    reject()
```

### 铁律 2: Executor 不得 import Verifier

```python
# ❌ 绝对禁止  
from ..executor.open_plan_verifier import OpenPlanVerifier

# ✅ 允许 (如果必须)
# 在execute()方法内动态导入,不在模块顶层
def execute(self, plan):
    from ..executor.open_plan_verifier import verify_open_plan
    verify_open_plan(plan)
```

**原因**: Executor不应该知道"如何验证",只应该"接收已验证的plan"。

### 铁律 3: 二者只能通过 Capability Descriptors 通信

```python
# capability_descriptors.py (中立的数据层)
ACTION_KINDS = ["command", "file", "api", "agent", "rule", "check", "note"]
MODE_CONSTRAINTS = {
    "planning": {"allows_diff": False},
    "implementation": {"allows_diff": True}
}

# Verifier使用
if plan.mode == "planning" and has_diff(plan):
    reject("BR001")

# Executor使用  
if action.kind not in ACTION_KINDS:
    raise UnsupportedAction(action.kind)
```

---

## 决策权矩阵

| 决策类型 | 归属 | 不归属 | 通信方式 |
|---------|------|--------|----------|
| **Action kinds定义** | Schema | ❌ Verifier, ❌ Executor | Schema导出 |
| **Mode约束** | Mode System | ❌ Verifier | Capability descriptor |
| **Plan验证规则** | Verifier | ❌ Executor | Validation report |
| **执行能力** | Executor | ❌ Verifier, ❌ Plan | Runtime |
| **理解意图** | LLM | ❌ Verifier, ❌ Executor | OpenPlan |

---

## 循环依赖禁止表

### 已发现的循环依赖 (需修复)

```
agentos.core.executor.executor_engine 
    → agentos.core.mode
    → agentos.core.mode.pipeline_runner
    → agentos.core.executor.executor_engine
```

**状态**: 现有问题,不由Open Plan引入

**处理**: 
1. 短期: 测试直接导入文件
2. 长期: 重构mode/executor消除循环

### Open Plan引入的依赖 (已防范)

```
✅ schemas → (独立,无依赖)
✅ mode_proposer → schemas (单向)
✅ open_plan_builder → schemas (单向)
✅ open_plan_verifier → schemas (单向)
```

**验证命令**:
```bash
# 检查是否有循环
python -c "
from agentos.core.schemas import OpenPlan
from agentos.core.mode.mode_proposer import ModeProposer
from agentos.core.executor_dry.open_plan_builder import OpenPlanBuilder
print('✓ No circular imports in Open Plan components')
"
```

---

## 模块职责边界

### Schema层

**职责**:
- 定义OpenPlan数据结构
- 定义action kinds枚举
- 提供结构校验

**禁止**:
- ❌ 实现业务逻辑
- ❌ 调用executor
- ❌ 调用LLM

### ModeProposer

**职责**:
- 理解自然语言
- 提议mode pipeline
- 输出confidence

**禁止**:
- ❌ 保证执行路径
- ❌ 绕过verifier
- ❌ 直接调用executor

### OpenPlanBuilder

**职责**:
- 生成execution plan
- 遵守mode constraints
- 输出结构化steps

**禁止**:
- ❌ 创造新的action kinds
- ❌ 生成executor不支持的操作
- ❌ 绕过structural validation

### OpenPlanVerifier

**职责**:
- 检查结构合法性
- 检查mode安全性
- 检查capability存在性

**禁止**:
- ❌ 判断语义合理性
- ❌ 依赖executor实现
- ❌ 做"智能理解"

### Executor

**职责**:
- 执行已验证的plan
- 遵守10条护城河
- 生成audit trail

**禁止**:
- ❌ 验证plan (已由verifier完成)
- ❌ 理解自然语言
- ❌ 修改plan内容

---

## 能力泄漏防范

### 防范1: Executor能力不得泄漏给Plan

```python
# ❌ 错误: Plan直接引用executor内部能力
{
  "proposed_actions": [{
    "kind": "file",
    "payload": {
      "path": "test.txt",
      "executor_method": "write_file"  # 🚫 泄漏了内部实现
    }
  }]
}

# ✅ 正确: Plan只用公开的interface
{
  "proposed_actions": [{
    "kind": "file",
    "payload": {
      "path": "test.txt",
      "operation": "create"  # ✓ 公开接口
    }
  }]
}
```

### 防范2: Verifier规则不得泄漏给LLM

```python
# ❌ 错误: 在prompt中列举所有verifier规则
system_prompt = """
You must follow these rules:
- BR001: No diff in planning
- BR002: Must have file ops
... (全部7条)
"""

# ✅ 正确: 只给高层约束,让verifier检查
system_prompt = """
Rules:
- planning phase: no diff/apply actions
- implementation phase: must produce diffs
"""
# 具体的BR001-BR007由verifier检查
```

---

## 架构演进规则

### 可以改变的 (需文档化)

- ✅ Action kinds的数量和类型
- ✅ Verifier的SOFT_POLICIES列表
- ✅ LLM的prompt策略
- ✅ Confidence threshold

**要求**: 每次改变必须:
1. 更新 capability descriptor
2. 运行所有gates
3. 更新文档

### 不可改变的 (架构约束)

- 🔒 Verifier ↔ Executor 不直接import
- 🔒 Plan是proposal,不是command
- 🔒 System保留最终执行权
- 🔒 所有操作可审计

**违反**: 必须经过架构review

---

## 收权清单 (已执行)

✅ **已收权项**:

1. ✅ 写了《Open Plan 非目标声明》
   - 明确: 不是workflow engine
   - 明确: 不是task schema  
   - 明确: 不是orchestration language

2. ✅ Action kinds标注为"runtime capability snapshot"
   - 不是稳定API
   - 未来可能变化

3. ✅ ModeProposer添加"非承诺声明"
   - Mode selection is a proposal, not a decision
   - System may override/split/abort

4. ✅ OpenPlanVerifier添加SOFT_POLICIES
   - BR006, BR007标记为soft
   - 允许override但记录audit

---

## 违反检测

### Gate检查

```bash
# 检查是否有非法import
rg "from.*executor.*import.*Executor" agentos/core/executor/open_plan_verifier.py
# 预期: 无结果

# 检查是否有非法import
rg "from.*verifier" agentos/core/executor/executor_engine.py | grep -v "# "
# 预期: 仅动态import或无结果
```

### 人工Review Checklist

在PR review时必须检查:

- [ ] 新的action kind是否更新了capability descriptor?
- [ ] Verifier是否在做"语义判断"?
- [ ] Plan是否试图"保证执行结果"?
- [ ] 是否有循环import?
- [ ] 文档是否同步更新?

---

**最后更新**: 2026-01-26  
**下次Review**: 功能扩展时  
**所有权**: 架构团队  
**违反报告**: 必须先提Issue讨论
