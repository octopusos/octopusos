# Open Plan 非目标声明

**Version**: 1.0.0  
**Date**: 2026-01-26  
**Status**: 架构边界定义  
**Purpose**: 明确Open Plan的设计边界,防止scope creep

---

## Open Plan 不是什么

### ❌ Open Plan 不是 Workflow Engine

Open Plan **不是**用来定义复杂工作流的DSL。

**不要用它做**:
- 分支条件 (`if/else`)
- 循环迭代 (`for/while`)
- 异常处理 (`try/catch`)
- 状态机 (state transitions)
- 并发控制 (parallel/sequential)

**原因**: 这些是workflow engine的职责,引入它们会让Open Plan变成"又一个工作流语言"。

**正确做法**: 如果需要复杂工作流,应该:
1. 在OpenPlan中声明 `agent` action
2. 委托给专门的workflow engine
3. Open Plan只记录"发生了什么",不定义"怎么控制流程"

---

### ❌ Open Plan 不是 Task Schema

Open Plan **不是**用来标准化任务类型的schema。

**不要期望**:
- "创建landing page"有固定的steps模板
- "修复bug"有标准的action序列
- 不同项目的"部署"长得一样

**原因**: 一旦我们定义"标准task schema",就回到了预定义模板的老路。

**正确理解**: 
- 每个OpenPlan都是LLM根据具体context生成的
- 两次"创建landing page"可以完全不同
- Open Plan是"理解结果",不是"执行模板"

---

### ❌ Open Plan 不是 Agent Orchestration Language

Open Plan **不是**用来编排多agent协作的语言。

**不要用它做**:
- Agent之间的消息传递
- Agent dependency graph
- Agent resource allocation
- Agent failure recovery

**原因**: Agent orchestration是更高层的系统问题,不应该在plan层解决。

**正确做法**: 
- Open Plan只能声明"需要某个agent"
- 具体的agent调度/通信由orchestrator负责
- Open Plan记录"哪些agent参与了",不定义"agent怎么协作"

---

## Open Plan 是什么

### ✅ LLM → Executor 之间的可审计提议载体

Open Plan的唯一职责:

**把LLM的理解翻译成Executor能验证和执行的结构**

```
LLM理解 → OpenPlan (结构化) → Verifier (检查) → Executor (执行)
  ↑                                                        ↓
  |                                                        |
  +------------------ Audit Trail (可复现) ----------------+
```

### 核心特征

1. **Proposal, not Command**
   - Open Plan是"提议",不是"命令"
   - System可以reject/modify/split plan
   - 最终执行权在Executor,不在Plan

2. **Audit Trail, not Workflow**
   - Open Plan主要价值是"记录AI做了什么决策"
   - 可复现 > 可扩展
   - 可审计 > 可编程

3. **Boundary, not Language**
   - 7种action kinds是当前Executor的capability
   - 不是一门"plan描述语言"
   - 未来capability变化,kinds也会变化

---

## 架构红线

### 红线 1: Open Plan不能绕过Gate

```python
# ❌ 错误: Plan直接指定"不检查"
{
  "steps": [{
    "proposed_actions": [{
      "kind": "command",
      "payload": {"cmd": "rm -rf /", "bypass_gate": true}  # 🚫
    }]
  }]
}

# ✅ 正确: Plan只提议,Gate决定
{
  "steps": [{
    "proposed_actions": [{
      "kind": "command",
      "payload": {"cmd": "npm install"}
    }]
  }]
}
# Gate在执行前检查allowlist
```

### 红线 2: Open Plan不能定义新的Executor能力

```python
# ❌ 错误: Plan创造新的action kind
{
  "proposed_actions": [{
    "kind": "kubernetes_deploy",  # 🚫 Executor不认识
    "payload": {...}
  }]
}

# ✅ 正确: 通过现有kinds组合
{
  "proposed_actions": [
    {"kind": "command", "payload": {"cmd": "kubectl apply -f deploy.yaml"}},
    {"kind": "check", "payload": {"check_type": "run", "target": "kubectl get pods"}}
  ]
}
```

### 红线 3: Open Plan不能承诺执行结果

```python
# ❌ 错误: Plan保证"会成功"
{
  "steps": [{
    "intent": "部署到生产环境",
    "guaranteed_success": true  # 🚫
  }]
}

# ✅ 正确: Plan只描述意图和风险
{
  "steps": [{
    "intent": "部署到生产环境",
    "success_criteria": ["pods running", "health check pass"],
    "risks": ["may timeout", "rollback needed"]
  }]
}
```

---

## 演进原则

### 可以变化的 (Flexible)

- ✅ Action kinds数量和类型
- ✅ Verifier的具体规则
- ✅ LLM的prompt策略
- ✅ 审计信息的详细程度

### 不能变化的 (Invariant)

- 🔒 Open Plan是proposal,不是command
- 🔒 System保留最终执行权
- 🔒 所有操作必须可审计
- 🔒 Plan不能绕过Gate

---

## 反模式 (Anti-Patterns)

### 反模式 1: 把Open Plan当作配置文件

❌ **错误思维**: "让用户手写Open Plan来配置任务"

✅ **正确思维**: "Open Plan是LLM的输出,不是人类的输入"

### 反模式 2: 期望Open Plan "足够表达一切"

❌ **错误思维**: "我们需要添加更多kinds来覆盖所有场景"

✅ **正确思维**: "7种kinds是当前capability,不够用就组合/委托"

### 反模式 3: 用Open Plan做版本控制

❌ **错误思维**: "把Open Plan提交到git作为'任务定义'"

✅ **正确思维**: "Open Plan是执行轨迹,审计用,不是源代码"

### 反模式 4: 把Verifier当作"智能审查"

❌ **错误思维**: "Verifier应该判断plan是否'合理'"

✅ **正确思维**: "Verifier只检查结构/安全/capability,不做语义判断"

---

## 决策权分配

| 决策 | 归属 | 原因 |
|------|------|------|
| **Mode selection** | LLM提议 + System确认 | LLM理解意图,System检查约束 |
| **Steps拆解** | LLM | 这是理解能力,系统不干预 |
| **Action kinds** | System定义 | 这是执行能力,LLM不创造 |
| **Payload内容** | LLM + Schema校验 | 开放内容,最小约束 |
| **执行 or 拒绝** | System (Gate/Verifier) | 最终执行权在系统 |
| **审计记录** | System强制 | 不可协商 |

---

## 给未来维护者的提醒

如果你发现自己在考虑以下任何一件事,**请先阅读本文档**:

- [ ] "我们需要在Open Plan里加入if/else逻辑"
- [ ] "我们应该定义标准的task templates"
- [ ] "我们需要让Open Plan支持agent间通信"
- [ ] "我们应该让用户手写Open Plan文件"
- [ ] "我们需要让Verifier判断plan是否'合理'"
- [ ] "我们应该保证action kinds的稳定性"

这些都是**违反设计哲学**的信号。

正确的问题是:
- [ ] "当前Executor的capability是什么?"
- [ ] "如何让LLM更好地理解这些capability?"
- [ ] "如何让审计轨迹更清晰?"
- [ ] "如何让Plan结构更简单?"

---

## 一句话总结

**Open Plan是LLM理解的结构化表达,不是系统能力的描述语言。**

它的价值在于:
- 让AI的决策可审计
- 让执行过程可复现
- 让系统边界可验证

它**不是**:
- 工作流引擎
- 任务模板
- 编排语言
- 配置文件

---

**Created**: 2026-01-26  
**Authority**: Architecture Owner  
**Enforcement**: This is a design constraint, not a suggestion  
**Violation**: Report to architecture team before proceeding
