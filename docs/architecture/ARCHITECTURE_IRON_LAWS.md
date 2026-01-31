# AgentOS 架构演进铁律

**Version**: 1.0  
**Date**: 2026-01-26  
**Authority**: 架构所有者  
**Enforcement**: 强制执行 (违反需架构review)

---

## 三条铁律 (半年内必须遵守)

### 铁律 1: 任何新能力,必须先写 Non-Goals

#### 规则

```
新 capability / new agent / new executor
第一个文件不是 README
是 NON_GOALS.md
```

#### 为什么

**问题**: 能力会自然膨胀成系统职责

**现象**:
- "这个agent能做X" → "这个agent应该做X" → "这个agent必须做X"
- "我们可以支持Y" → "我们应该支持Y" → "用户期望我们支持Y"

**后果**: 6个月后系统变成"什么都想做,什么都做不好"

#### 执行标准

**新capability checklist**:
- [ ] NON_GOALS.md 已创建
- [ ] 明确列出: 不是workflow engine / 不是XX / 不是YY
- [ ] 明确定位: 是"XX载体" / 是"XX接口" / 是"XX边界"
- [ ] 架构owner review通过

**示例** (Open Plan):
```markdown
# Open Plan 非目标声明

## Open Plan 不是什么
- ❌ 不是 workflow engine
- ❌ 不是 task schema
- ❌ 不是 orchestration language

## Open Plan 是什么
- ✅ LLM → Executor 之间的可审计提议载体
```

#### Review Gate

**触发时机**: PR包含新的capability/agent/executor

**检查项**:
1. 是否有 `*_NON_GOALS.md` 文件?
2. 是否明确列出至少3个"不是什么"?
3. 是否有"是什么"的一句话定位?

**不通过**: PR被block,要求补充

---

### 铁律 2: Agent 不能"合并 PR 意图"

#### 规则

```
Agent 的产出是 proposal，不是 decision，也不是 merge-ready truth
```

#### 为什么

**问题**: Agent会自然把"原型"推成"定型"

**现象**:
- Agent A实现原型
- Agent A自然会"优化""完善""固化"
- Agent A会把experimental变成production
- Agent A会把7种kinds变成"永久契约"

**本质**: AI的收敛本能 - 它会在没有阻止时主动完成"架构设计权"

#### 执行标准

**AI协作原则**:

| AI的职责 | 不是AI的职责 |
|---------|-------------|
| ✅ 实现原型 | ❌ 决定这是"最终架构" |
| ✅ 提供多个方案 | ❌ 选择"最佳方案" |
| ✅ 指出风险 | ❌ 决定"可接受风险" |
| ✅ 生成文档 | ❌ 决定"这就是规范" |
| ✅ 运行测试 | ❌ 决定"测试通过=可发布" |

**人类的职责**:
- 从AI的proposals中选择
- 定义"什么是临时的,什么是永久的"
- 明确"什么可以变,什么不能变"
- 收回"架构设计权"

**哪怕你一个人开发,也要对自己保持这条纪律**

#### 实践指南

**错误模式** ❌:
```
You: 实现一个Open Plan原型
AI: [实现] 完成! 这是production-ready的实现
You: [merge] 直接使用
```

**正确模式** ✅:
```
You: 实现一个Open Plan原型
AI: [实现] 完成! 这是我的proposal
You: [review] 哪些是临时的? 哪些是permanent?
You: [收权] 写NON_GOALS / SOVEREIGNTY / 标注snapshot
You: [merge] 合并收权后的版本
```

#### Review Checklist

**每次Agent完成实现后必问**:
- [ ] Agent是否标注了哪些是"暂时的"?
- [ ] Agent是否标注了哪些是"可能变化的"?
- [ ] Agent是否主动"完成了架构决策"?
- [ ] 我是否需要写NON_GOALS来收权?

---

### 铁律 3: 任何"语义判断"都必须显式标注为 SOFT

#### 规则

```
不允许出现"看起来不合理""不像一个任务"这类判断

所有这种判断要么是:
  - 提示 (warn)
  - 建议 (note)
  - 或需要人确认 (BLOCKED)
```

#### 为什么

**问题**: Verifier会慢慢变成"隐式workflow engine"

**演进路径** (危险):
```
Month 1: 检查"planning mode不能有diff" (结构性)
Month 2: 检查"步骤顺序是否合理" (语义性)
Month 3: 检查"这像不像一个任务" (理解性)
Month 6: 变成了"第二个规则引擎"
```

**后果**: 你从"执行裁决者"滑回"理解裁判者"

#### 执行标准

**Verifier只能做3类事**:

1. **结构合法性** ✅
   ```python
   if not plan.steps:
       reject("Empty plan")  # HARD
   ```

2. **Mode/Gate安全性** ✅
   ```python
   if mode == "planning" and has_diff(plan):
       reject("BR001: Planning cannot have diff")  # HARD
   ```

3. **Executor capability存在性** ✅
   ```python
   if action.kind not in AVAILABLE_KINDS:
       reject(f"Unknown action kind: {action.kind}")  # HARD
   ```

**Verifier不能做** ❌:

```python
# ❌ 语义判断
if step_order_looks_wrong(plan):
    reject("Step order unreasonable")

# ❌ 理解判断  
if not looks_like_valid_task(plan):
    reject("This doesn't look like a task")

# ❌ 质量判断
if too_many_steps(plan):
    reject("Too complex")
```

**如果必须判断,改为SOFT**:

```python
# ✅ SOFT警告 (可override)
if len(plan.steps) > 10:
    warn("BR_SOFT_001: Plan has many steps, consider splitting", 
         severity="warning", 
         policy="soft")
```

#### SOFT_POLICIES注册表

**当前SOFT规则**:
```python
SOFT_POLICIES = {
    "BR006": "No circular agent delegation (warning)",
    "BR007": "Check operations feasibility (warning)"
}
```

**添加新SOFT规则流程**:
1. 确认是"语义/质量判断",不是"结构/安全检查"
2. 添加到SOFT_POLICIES
3. severity设为"warning",不是"error"
4. 允许在audit trail中override
5. 文档化override条件

#### Audit Trail要求

**SOFT规则被触发时必须记录**:

```json
{
  "rule_id": "BR006",
  "policy": "soft",
  "triggered": true,
  "overridden": false,
  "reason": "Plan has 3 agent delegations",
  "severity": "warning",
  "audit_note": "Reviewed and accepted by operator"
}
```

**SOFT规则被override时**:

```json
{
  "rule_id": "BR006",
  "policy": "soft",
  "triggered": true,
  "overridden": true,
  "override_reason": "Necessary for complex task decomposition",
  "approved_by": "human_operator",
  "timestamp": "..."
}
```

---

## 违反检测

### Gate 1: NON_GOALS文件存在性

```bash
#!/bin/bash
# scripts/gates/check_non_goals.sh

for dir in agentos/core/*/ ; do
    if [[ -f "$dir/README.md" ]] && [[ ! -f "$dir/NON_GOALS.md" ]]; then
        echo "❌ $dir has README but no NON_GOALS.md"
        exit 1
    fi
done
echo "✓ All capabilities have NON_GOALS"
```

### Gate 2: Verifier语义判断检测

```bash
# 检查verifier代码中的危险词
rg "(reasonable|make sense|looks like|seems|appears to be)" \
   agentos/core/executor/*verifier.py

# 预期: 无结果 (或仅在注释中)
```

### Gate 3: SOFT规则审计完整性

```python
# 检查所有SOFT规则是否记录了audit
for rule_id in SOFT_POLICIES:
    if triggered(rule_id) and not audited(rule_id):
        raise AuditIncomplete(rule_id)
```

---

## 制度化 (How to enforce)

### 1. PR Template

在 `.github/PULL_REQUEST_TEMPLATE.md` 添加:

```markdown
## 架构演进检查

如果本PR引入新capability/agent/executor:

- [ ] 已创建 NON_GOALS.md
- [ ] 已标注哪些是"临时的"
- [ ] 已标注哪些是"可能变化的"  
- [ ] 已通过架构owner review

如果本PR修改Verifier:

- [ ] 新增的规则是HARD (结构/安全) 还是SOFT (语义/质量)?
- [ ] SOFT规则已添加到SOFT_POLICIES
- [ ] Audit trail完整
```

### 2. 架构Review会议

**频率**: 每月一次

**Agenda**:
1. Review新增的capabilities - 是否有NON_GOALS?
2. Review Verifier规则 - 是否有语义判断?
3. Review Agent产出 - 是否有"自作主张"?
4. Review SOFT_POLICIES - 是否需要升级为HARD或删除?

### 3. 文档审计

**季度审计**:

```bash
# 1. 检查所有capability是否有NON_GOALS
find agentos/core -name "README.md" | while read f; do
    dir=$(dirname "$f")
    if [[ ! -f "$dir/NON_GOALS.md" ]]; then
        echo "Missing: $dir/NON_GOALS.md"
    fi
done

# 2. 检查verifier是否有语义词
rg -i "reasonable|make sense|looks like|valid task" agentos/core/**/verifier.py

# 3. 检查是否有未标注的SOFT规则
rg "BR\d+" agentos/core/**/verifier.py | grep -v SOFT_POLICIES
```

---

## 实践案例: Open Plan

### ✅ 符合铁律的实施

**铁律1**: 已创建 `OPEN_PLAN_NON_GOALS.md` ✓
- 明确: 不是workflow engine
- 明确: 不是task schema
- 明确: 不是orchestration language

**铁律2**: 已标注proposal性质 ✓
- ModeProposer: "is a PROPOSAL, not a DECISION"
- Action kinds: "runtime capability snapshot, not permanent contract"
- 收权文档: `OPEN_PLAN_SOVEREIGNTY_CORRECTION.md`

**铁律3**: 已标注SOFT规则 ✓
```python
SOFT_POLICIES = {
    "BR006": "No circular agent delegation (warning)",
    "BR007": "Check operations feasibility (warning)"
}
```

### ❌ 如果没有收权会怎样 (反例)

**6个月后的Open Plan** (没有铁律):
```python
# Agent会自然演进成:
ACTION_KINDS = [
    "command", "file", "api", "agent", 
    "workflow",  # 新增: 因为"用户需要"
    "condition",  # 新增: 因为"很常见"
    "loop",  # 新增: 因为"很方便"
]

# Verifier会自然演进成:
def verify(plan):
    if not looks_reasonable(plan):  # 语义判断
        reject("Plan unreasonable")
    if not proper_task_structure(plan):  # 理解判断
        reject("Invalid task")
```

**结果**: Open Plan变成了workflow engine,违反了设计初衷

---

## 给未来维护者的话

### 如果你想添加新能力

**STOP 并回答这3个问题**:

1. **我写NON_GOALS了吗?**
   - 如果没有 → 先写
   - 如果有 → 继续

2. **这是结构判断还是语义判断?**
   - 结构/安全 → HARD规则
   - 语义/质量 → SOFT规则或删除

3. **我是在"实现提议"还是"做架构决策"?**
   - 实现提议 → 标注为experimental/snapshot
   - 架构决策 → 需要architecture owner批准

### 如果你是AI Agent

**你的职责**:
- ✅ 实现我指定的功能
- ✅ 指出风险和trade-offs
- ✅ 提供多个方案供选择
- ✅ 生成清晰的文档

**不是你的职责**:
- ❌ 替我做架构决策
- ❌ 把"原型"推成"定型"
- ❌ 判断什么是"最佳实践"
- ❌ 决定什么是"permanent"

**一句话**: 你是 implementer,不是 architect

---

## 违反后果

### 轻微违反 (可修复)

- 忘记写NON_GOALS → 补充即可
- SOFT规则未标注 → 移入SOFT_POLICIES
- Agent越界但及时发现 → 收权文档

### 严重违反 (需回滚)

- Capability膨胀成职责 → 需要拆分/重构
- Verifier变成workflow engine → 需要大规模重构
- 循环依赖无法解开 → 可能需要重写

### 防范措施

**每月review时必须检查**:
1. 新增的capability是否有scope creep?
2. Verifier是否在做语义判断?
3. Agent是否在替我们做架构决策?

**一旦发现苗头,立即收权**

---

## 总结

### 为什么需要这三条铁律

因为AI和人类在"收敛点"上有天然差异:

| 维度 | AI的本能 | 人类需要的 |
|------|---------|-----------|
| **Scope** | 扩展到"能做的" | 限制在"该做的" |
| **Stability** | 固化成"定型" | 保留"演进空间" |
| **Judgment** | 判断"合理性" | 只检查"合法性" |

### 一句话

**"实现力"不等于"架构权"**

Agent可以快速实现,但需要人类明确:
- 哪些是临时的
- 哪些是可变的
- 哪些是提议而非决策

### 这不是限制AI

这是**保护系统的演进空间**

没有这三条铁律,6个月后你会发现:
- 系统被自己的"能力"锁死
- 想加新功能但"违反规范"
- Verifier变成了"规则迷宫"

**有了这三条铁律,系统可以持续演进**

---

**Status**: 🔒 强制执行  
**Review**: 每月  
**Owner**: 架构团队  
**违反报告**: 立即收权
