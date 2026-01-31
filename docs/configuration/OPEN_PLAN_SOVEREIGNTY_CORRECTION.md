# 架构收权记录

**Date**: 2026-01-26  
**Trigger**: 架构审视发现agent越界  
**Status**: ✅ 已收权

---

## 收权背景

原型实现完成后,架构审视发现三个关键问题:

1. **Agent在偷偷"完成架构设计权"**
   - 自行决定了7种action kinds
   - 自行定义了7条business rules
   - 自行确定了experimental_open_plan mode边界

2. **Verifier承担了"业务语义"判断**
   - "7条业务规则"暗示在做语义理解
   - 有滑向"理解裁判者"的风险

3. **循环依赖暴露结构性风险**
   - Verifier/Executor边界不够清晰
   - 存在能力泄漏风险

---

## 收权行动

### Action 1: 创建《非目标声明》

**文件**: `docs/OPEN_PLAN_NON_GOALS.md`

**核心内容**:
- ❌ Open Plan不是workflow engine
- ❌ Open Plan不是task schema
- ❌ Open Plan不是orchestration language
- ✅ Open Plan是LLM→Executor的可审计提议载体

**目的**: 防止scope creep,明确设计边界

### Action 2: Action Kinds标注为Snapshot

**位置**: `docs/OPEN_PLAN_README.md`

**修改**:
```markdown
### 1. 7种执行通道 (Runtime Capability Snapshot)

**重要**: 这些action kinds不是稳定API,而是当前executor的capability snapshot。

**⚠️ 这不是永久契约**:
- 未来executor能力变化时,kinds可能增加/删除/合并
- 不要依赖"永远是7种"
```

**目的**: 防止action kinds被当作"Open Plan语言规范"

### Action 3: ModeProposer添加非承诺声明

**位置**: `agentos/core/mode/mode_proposer.py`

**修改**:
```python
"""
IMPORTANT: Mode selection is a PROPOSAL, not a DECISION.
- The system may override the proposed mode
- The system may split the pipeline  
- The system may abort execution
- Final authority remains with Gate/Verifier, not the proposer
"""
```

**目的**: 防止LLM的建议被当作"必须执行"

### Action 4: Verifier添加SOFT_POLICIES

**位置**: `agentos/core/executor/open_plan_verifier.py`

**修改**:
```python
# Policy classification: which rules are "soft" (can be overridden with audit)
SOFT_POLICIES = {
    "BR006",  # Circular delegation warning, not error
    "BR007",  # Feasibility check, not blocking
}
```

**新增Docstring**:
```python
"""
IMPORTANT: This is NOT a "semantic reasoner"

Verifier MUST NOT:
- Judge if the plan "makes sense"
- Evaluate if steps are "in the right order"  
- Decide if this "looks like a valid task"
"""
```

**目的**: 明确verifier只做机械校验,不做语义判断

### Action 5: 创建《架构主权边界》

**文件**: `docs/OPEN_PLAN_SOVEREIGNTY.md`

**核心内容**:
- 铁律1: Verifier不得import Executor
- 铁律2: Executor不得import Verifier
- 铁律3: 二者只通过capability descriptors通信

**目的**: 防止循环依赖和能力泄漏

---

## 收权效果

### Before (越界状态)

```
❌ Action kinds = "Open Plan语言规范"
❌ Mode selection = "LLM决策"
❌ Business rules = "语义判断"
❌ Verifier ↔ Executor 边界模糊
```

### After (收权状态)

```
✅ Action kinds = "Runtime capability snapshot"
✅ Mode selection = "LLM提议 + System确认"
✅ Business rules = "机械校验 (SOFT可override)"
✅ Verifier ↔ Executor 明确不直接import
```

---

## 架构决策记录

### ADR-001: Open Plan是提议载体,不是DSL

**Decision**: Open Plan不是一门"计划描述语言",而是LLM理解的结构化表达。

**Rationale**:
- 防止变成workflow engine
- 防止用户手写Open Plan
- 保持"理解→验证→执行"单向流

**Consequences**:
- Action kinds可以变化
- Verifier规则可以调整
- Plan不能保证执行结果

### ADR-002: Verifier只做机械校验,不做语义判断

**Decision**: Verifier只检查结构/安全/capability,不判断"合理性"。

**Rationale**:
- 语义理解是LLM的职责
- Verifier做语义判断会变成"第二个LLM"
- 机械校验才能保证可复现

**Consequences**:
- "看起来不合理"的plan可能通过验证
- 需要在LLM prompt中加强约束
- Soft policies允许override

### ADR-003: Mode Selection是提议,System保留最终权

**Decision**: LLM提议mode,但system可以override/split/abort。

**Rationale**:
- LLM可能误判
- 安全约束可能在LLM训练后变化
- 最终执行权必须在system

**Consequences**:
- Confidence < 0.5 fallback到规则模式
- Mode可能被Gate拒绝
- 审计轨迹记录override原因

---

## 未来防范

### 禁止的演进方向

❌ **不要做**:
1. 在Open Plan中添加if/else逻辑
2. 定义"标准task templates"
3. 让Verifier判断plan是否"看起来合理"
4. 保证action kinds永不变化
5. 让用户手写Open Plan文件

### 允许的演进方向

✅ **可以做**:
1. 增加/删除action kinds (更新capability descriptor)
2. 调整Verifier的SOFT_POLICIES列表
3. 优化LLM prompt策略
4. 改进audit trail详细程度

### Review Trigger

以下情况必须重新review架构主权:

- [ ] 有人提议"在Open Plan加逻辑"
- [ ] Verifier代码中出现"reasonable/makes sense"等词
- [ ] Action kinds连续3个月未变化(可能僵化)
- [ ] 出现Verifier ↔ Executor循环import
- [ ] 有人建议"让用户写Open Plan"

---

## 总结

### 收权前的状态

原型**功能完整**,但**架构主权模糊**:
- Agent自行定义了系统能力边界
- Verifier有滑向"语义理解"的风险
- Action kinds有被当作"永久契约"的风险

### 收权后的状态

原型保持**功能完整**,**架构主权明确**:
- Open Plan定位清晰(提议载体,非DSL)
- Verifier职责明确(机械校验,非语义判断)
- Action kinds定位清晰(capability snapshot,非契约)
- 演进空间保留(soft policies, override机制)

### 关键收获

这次收权证明了一个重要原则:

**"实现力"不等于"架构权"**

Agent可以快速实现原型,但:
- 它会自然地"收敛"到一个具体形态
- 它不知道哪些是"可变的",哪些是"不可变的"
- 它需要人类明确"架构主权边界"

这不是Agent的问题,而是工程的必然阶段。

---

**Created**: 2026-01-26  
**Owner**: Architecture Team  
**Status**: Closed (收权完成)
