# AgentOS v1.0: 完整技术白皮书

**从自然语言到可审计执行**

*AI 执行的操作系统级治理层*

---

**版本**: 1.0  
**日期**: 2026年1月25日  
**作者**: AgentOS 团队  
**许可证**: MIT

---

## 执行摘要

AgentOS 是一个执行操作系统，使 AI 智能体能够"把活干完"，而不会失控、越权或牺牲可审计性。与现有专注于让 AI "更聪明"的工具不同，AgentOS 专注于让 AI 执行**可靠、可控和负责任**。

**问题**：AI 可以写代码、生成方案、提供建议。但谁来确保 AI "执行"是安全、可控和负责任的？

**解决方案**：AgentOS 提供了一个操作系统级治理层，将规划与执行分离，执行机器可检查的约束，并维护完整的审计追踪。

**关键创新**：BLOCKED 作为一等状态 —— 当信息不足时，AgentOS 不会猜测或编造，而是生成 QuestionPack 并等待人类输入。

**目标用户**：构建生产 AI 系统的工程团队、自动化基础设施的 DevOps 团队，以及需要 AI 问责制的组织。

---

## 目录

1. [简介](#1-简介)
2. [执行鸿沟](#2-执行鸿沟)
3. [核心架构](#3-核心架构)
4. [设计原则](#4-设计原则)
5. [执行模式](#5-执行模式)
6. [记忆系统](#6-记忆系统)
7. [锁机制](#7-锁机制)
8. [审计追踪](#8-审计追踪)
9. [10条护城河](#9-10条护城河)
10. [实现细节](#10-实现细节)
11. [与现有方案的对比](#11-与现有方案的对比)
12. [使用案例](#12-使用案例)
13. [路线图](#13-路线图)
14. [结论](#14-结论)

---

## 1. 简介

### 1.1 AI 智能体的承诺与风险

过去一年，AI 智能体在代码生成、问题解决和任务自动化方面展现了卓越的能力。然而，一个关键鸿沟依然存在：**从"能生成"到"能安全执行"的转变**。

考虑这个场景：
- AI 智能体分析代码库
- 它识别出优化机会
- 它生成补丁
- **然后呢？**

大多数系统要么止步于此，要么在最小保护下继续执行。AgentOS 通过**工程级执行治理**弥合了这一鸿沟。

### 1.2 AgentOS 是什么（以及不是什么）

**AgentOS 是**：
- AI 执行的操作系统级治理层
- 一个将规划与执行分离的系统
- 一个执行机器可检查约束的框架
- 一个提供完整审计追踪的平台

**AgentOS 不是**：
- 语言模型或 AI 模型
- 代码补全工具（如 Copilot）
- 自动化脚本运行器
- 人类判断的替代品

### 1.3 核心理念

> "AI 将变得越来越强大，但执行不能仅仅依赖信任。AgentOS 让 AI 执行第一次表现得像真正的软件系统：有状态、有边界、有审计追踪和问责制。"

---

## 2. 执行鸿沟

### 2.1 为什么"能写" ≠ "能执行"

在现实世界中，执行意味着：

| 方面 | 代码生成 | 真实执行 |
|------|---------|---------|
| **影响** | 建议 | 改变生产系统 |
| **可逆性** | 容易丢弃 | 需要回滚 |
| **问责制** | 无需 | 需要完整审计追踪 |
| **风险** | 低 | 高 |
| **权限** | 咨询性 | 执行性 |

### 2.2 缺失的层次

传统软件栈有：
- **应用层**：业务逻辑
- **操作系统**：资源管理
- **硬件**：物理执行

AI 执行需要并行的栈：
- **AI 模型**：推理和生成
- **执行操作系统** ← **AgentOS 填补这一空白**
- **工具/基础设施**：实际执行

### 2.3 当前方案的不足

**问题1：没有规划/执行分离**
- 大多数智能体"一边想一边做"
- 意图和行动之间没有审查门禁

**问题2：编造风险**
- 智能体可能编造命令、路径或事实
- 没有来源追踪

**问题3：没有审计追踪**
- 执行发生在黑盒中
- 无法确定"改变了什么以及为什么"

**问题4：没有受控阻塞**
- 不确定时，智能体要么猜测要么失败
- 没有结构化的方式向人类询问输入

---

## 3. 核心架构

### 3.1 六阶段执行流水线

```
┌─────────────────────┐
│  自然语言请求        │  用户提供意图
└──────────┬──────────┘
           ↓
┌──────────────────────┐
│   意图分析            │  解析并结构化请求
│   (结构化)            │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   协调器              │  风险评估、策略选择
│  (决策制定)           │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   干运行执行器        │  规划阶段(无实际变更)
│   (仅规划)            │  生成执行计划
└──────────┬───────────┘
           ↓
      ┌────────┐
      │BLOCKED?│───是──→ QuestionPack → AnswerPack ──┐
      └────┬───┘                                       │
           │否                                         │
           ↓                                           ↓
┌──────────────────────┐                    ┌──────────────┐
│   执行器              │◄───────────────────┤   解除阻塞    │
│  (真实执行)           │                    └──────────────┘
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   审计系统            │  ReviewPack 生成
│  (可追溯性)           │  提交链接
└──────────────────────┘
```

### 3.2 关键组件

#### 3.2.1 意图解析器
- 将自然语言转换为结构化意图
- 提取：目标、约束、成功标准
- **无编造**：仅使用请求中的信息

#### 3.2.2 协调器
- 风险评估(低/中/高)
- 执行模式选择
- 资源分配
- 依赖解析

#### 3.2.3 干运行执行器
- **仅规划阶段** — 不做实际变更
- 生成：文件变更、命令序列、回滚计划
- 基于证据：参考 FactPack 和 MemoryPack

#### 3.2.4 问答系统
- **QuestionPack**：带证据的结构化问题
- **AnswerPack**：人类回应
- 类型：blocker、澄清、需要决策

#### 3.2.5 执行器
- **执行阶段** — 做出真实变更
- 沙箱环境
- 基于白名单的操作
- 获取锁

#### 3.2.6 审计系统
- **ReviewPack**：完整执行记录
- 带意图+差异哈希的补丁追踪
- 提交绑定
- 回滚指南

---

## 4. 设计原则

### 4.1 原则1：规划和执行完全分离

**传统方法**(❌)：
```
while (not done):
    think()
    act()  # 一边想一边做
```

**AgentOS 方法**(✅)：
```
# 阶段1：规划(干运行)
plan = dry_executor.plan(intent)

# 门禁
if not review_gate.approve(plan):
    raise ExecutionDenied

# 阶段2：执行
result = executor.execute(plan)
```

**为什么重要**：
- 计划可以在执行前审查
- 提前准备回滚策略
- 承诺前进行风险评估

### 4.2 原则2：BLOCKED 是一等状态

**传统方法**(❌)：
```python
if uncertain:
    guess()  # 或 fail()
```

**AgentOS 方法**(✅)：
```python
if insufficient_info:
    question_pack = generate_questions(evidence)
    state = BLOCKED
    await answer_pack  # 系统等待
    resume_with_answers()
```

**为什么重要**：
- 没有编造或幻觉
- 结构化的人机协作
- 基于证据的决策制定

### 4.3 原则3：执行必须受控

所有执行满足：

| 控制机制 | 目的 | 实现 |
|---------|------|------|
| **白名单** | 仅批准的操作 | 命令白名单 |
| **沙箱** | 隔离环境 | 文件系统隔离 |
| **锁** | 防止冲突 | 任务+文件锁 |
| **审查门禁** | 高风险人工批准 | 策略驱动 |
| **审计日志** | 完全可追溯性 | ReviewPack |
| **回滚** | 失败恢复 | Git + 快照 |

### 4.4 原则4：工具是承包商，不是大脑

AgentOS 可以将执行委托给外部工具：
- OpenCode
- Codex
- Claude CLI
- 任何未来的智能体

**合约**：
```
AgentOS → 工具:
  - TaskPack (做什么)
  - ExecutionPolicy (约束)

工具 → AgentOS:
  - ResultPack (做了什么)
  - Evidence (差异、日志)

最终权威: AgentOS
```

---

## 5. 执行模式

### 5.1 三种模式

AgentOS 支持三种执行模式，每种都有不同的风险/自主权衡：

#### 5.1.1 交互模式

**特点**：
- 自由提问(任何类型)
- 无问题预算
- 人类驱动执行

**使用场景**：
- 探索性任务
- 不确定的需求
- 学习阶段

**示例**：
```json
{
  "execution_mode": "interactive",
  "execution_policy": {
    "question_types_allowed": ["clarification", "blocker", "decision_needed"],
    "question_budget": null
  }
}
```

#### 5.1.2 半自动模式

**特点**：
- 仅允许阻塞问题
- 有限的问题预算(默认：3)
- 预算耗尽自动回退

**使用场景**：
- 大多数自动化任务
- 有边缘情况的已知工作流
- 监督自动化

**示例**：
```json
{
  "execution_mode": "semi_auto",
  "execution_policy": {
    "question_types_allowed": ["blocker"],
    "question_budget": 3,
    "require_evidence": true,
    "auto_fallback": true
  }
}
```

#### 5.1.3 全自动模式

**特点**：
- 零问题允许
- question_budget = 0
- 需要完整的 MemoryPack + FactPack

**使用场景**：
- 完全确定的任务
- CI/CD 流水线
- 计划任务

**示例**：
```json
{
  "execution_mode": "full_auto",
  "execution_policy": {
    "question_budget": 0,
    "require_memory_pack": true,
    "require_fact_pack": true
  }
}
```

### 5.2 模式选择策略

```
┌─────────────────────────────────────┐
│ 任务是否完全确定？                   │
└─────┬──────────────────────┬────────┘
      │是                    │否
      ↓                      ↓
  full_auto           ┌──────────────┐
                      │ 需要人类     │
                      │ 决策？       │
                      └─┬──────────┬─┘
                        │是        │否
                        ↓          ↓
                   interactive  semi_auto
```

---

## 6. 记忆系统

### 6.1 外部记忆服务

AgentOS 将"记忆"从执行中外置化：

**传统方法**(❌)：
- 在提示中嵌入所有上下文
- 每次执行都重新获取
- 没有结构化记忆

**AgentOS 方法**(✅)：
- 结构化 MemoryItems
- 全文搜索(FTS5)
- 上下文自动构建

### 6.2 记忆类型

| 类型 | 目的 | 示例 |
|------|------|------|
| **convention** | 编码标准 | "React组件使用PascalCase" |
| **constraint** | 硬性规则 | "永不删除用户数据除非有备份" |
| **decision** | 过去的决策 | "关系数据使用PostgreSQL" |
| **pattern** | 常见模式 | "API错误处理模式" |
| **contact** | 人类联系人 | "前端负责人: alice@example.com" |

### 6.3 MemoryPack 结构

```json
{
  "memory_pack_id": "mp-001",
  "project_id": "my-project",
  "agent_type": "frontend-engineer",
  "items": [
    {
      "id": "mem-001",
      "type": "convention",
      "scope": "project",
      "content": {
        "summary": "React组件使用PascalCase",
        "details": "所有React组件文件必须使用PascalCase命名..."
      },
      "sources": ["ev-001"],
      "confidence": 0.95,
      "tags": ["frontend", "react", "naming"]
    }
  ],
  "search_query": "React命名约定",
  "total_items": 1,
  "created_at": "2026-01-25T10:00:00Z"
}
```

---

## 7. 锁机制

### 7.1 为什么锁很重要

**问题**：多个智能体/任务同时修改相同文件

**后果**：
- 合并冲突
- 状态不一致
- 变更丢失

### 7.2 两级锁

#### 7.2.1 任务级锁
- 每个任务一个智能体
- 基于租约(默认：5分钟)
- 防止重复执行

#### 7.2.2 文件级锁
- 防止并发文件修改
- 冲突检测
- 解锁时自动rebase

### 7.3 冲突解决

```
任务A修改: [file1.ts, file2.ts]
任务B修改: [file2.ts, file3.ts]

→ file2.ts上冲突

解决方案:
1. 任务A首先获取锁 → 继续
2. 任务B进入WAITING_LOCK
3. 当任务A完成时:
   - 释放锁
   - 触发任务B rebase
4. 任务B用更新的file2.ts重新规划
```

---

## 8. 审计追踪

### 8.1 ReviewPack：完整执行记录

每次执行生成一个ReviewPack：

```json
{
  "task_id": "task-001",
  "run_id": 123,
  "execution_mode": "semi_auto",
  "start_time": "2026-01-25T10:00:00Z",
  "end_time": "2026-01-25T10:15:00Z",
  "plan_summary": {
    "intent": "添加用户认证API",
    "estimated_changes": 3,
    "risk_level": "medium"
  },
  "changed_files": [
    "src/auth/api.ts",
    "src/auth/middleware.ts",
    "tests/auth.test.ts"
  ],
  "patches": [
    {
      "patch_id": "p001",
      "intent": "创建JWT认证中间件",
      "files": ["src/auth/middleware.ts"],
      "diff_hash": "sha256:abc123...",
      "lines_added": 45,
      "lines_removed": 2
    }
  ],
  "commits": [
    {
      "hash": "abc123def",
      "message": "feat(auth): 添加JWT认证",
      "timestamp": "2026-01-25T10:14:00Z"
    }
  ],
  "questions_asked": 1,
  "questions_answered": 1,
  "rollback_guide": "git revert abc123def^..HEAD",
  "verification_status": "passed"
}
```

### 8.2 审计能力

有了ReviewPack，你可以回答：

1. **改变了什么？** → `changed_files`、`patches`
2. **为什么？** → 每个补丁中的`intent`
3. **谁决定的？** → `execution_mode`、`questions_answered`
4. **何时？** → `start_time`、`end_time`、提交`timestamp`
5. **如何撤销？** → `rollback_guide`

---

## 9. 10条护城河

AgentOS v1.0的质量通过10条机器可检查的约束(不是建议)来保证：

### 护城河1：无MemoryPack不允许执行
```python
if memory_pack is None:
    raise ExecutionDenied("需要MemoryPack")
```

### 护城河2：full_auto ⇒ question_budget = 0
```python
if mode == "full_auto" and question_budget != 0:
    raise InvalidPolicy("full_auto需要零问题")
```

### 护城河3：不允许编造命令/路径
```python
for command in plan.commands:
    if not provenance.verify(command):
        raise FabricationDetected(command)
```

### 护城河4：每次运行记录Plan/Apply/Verify
```python
required_steps = ["Plan", "Apply", "Verify"]
if not all(step in run_steps for step in required_steps):
    raise IncompleteRunSteps()
```

### 护城河5：每次运行都有ReviewPack
```python
if not review_pack.exists(run_id):
    raise MissingReviewPack(run_id)
```

### 护城河6：补丁追踪Intent + Diff Hash
```python
for patch in review_pack.patches:
    assert patch.intent is not None
    assert patch.diff_hash is not None
```

### 护城河7：提交必须可追溯
```python
for commit in review_pack.commits:
    assert commit.hash is not None
    assert git.verify_commit(commit.hash)
```

### 护城河8：文件锁冲突 ⇒ WAIT + Rebase
```python
if file_lock.conflict_detected():
    state = WAITING_LOCK
    schedule_rebase()
```

### 护城河9：并发执行需要锁
```python
if not task_lock.acquired():
    raise ConcurrentExecutionDenied()
```

### 护城河10：调度器规则必须可审计
```python
for trigger in scheduler.rules:
    assert trigger.is_deterministic()
    assert trigger.logged()
```

**这些由门禁强制执行，而不是代码审查。**

---

## 10. 实现细节

### 10.1 技术栈

- **语言**：Python 3.13+
- **数据库**：SQLite with FTS5
- **模式验证**：JSON Schema(严格模式)
- **AI集成**：OpenAI Structured Outputs
- **版本控制**：Git
- **打包**：uv(快速Python打包)

### 10.2 代码组织

```
agentos/
├── core/
│   ├── coordinator/     # 风险评估、决策制定
│   ├── executor/        # 干运行+真实执行
│   ├── answers/         # 问答系统
│   ├── memory/          # 记忆服务(FTS)
│   ├── locks/           # 任务+文件锁
│   ├── review/          # ReviewPack生成
│   └── scheduler/       # 多模式调度器
├── schemas/             # 40+个JSON模式
├── cli/                 # 命令行界面
├── adapters/            # 工具适配器
└── store/               # SQLite持久化
```

---

## 11. 与现有方案的对比

### 11.1 AgentOS vs. LangGraph

| 方面 | LangGraph | AgentOS |
|------|-----------|---------|
| **焦点** | 工作流编排 | 执行治理 |
| **规划/执行** | 混合 | 严格分离 |
| **BLOCKED状态** | 无 | 一等状态 |
| **审计** | 基础日志 | ReviewPack |

**关系**：AgentOS可以使用LangGraph作为执行工具，但在其上添加治理。

---

## 12. 使用案例

### 12.1 案例1：基础设施自动化

**场景**：自动化Kubernetes部署更新

**工作流**：
1. 用户："更新staging部署到v2.3.1"
2. 意图：结构化部署更新
3. 协调器：风险=中等(staging，非生产)
4. 干运行执行器：生成YAML变更
5. 问题："确认副本数：3？" → BLOCKED
6. 回答："是的，保持3个副本"
7. 执行器：应用YAML，回滚计划就绪
8. 审计：带提交+回滚指南的ReviewPack

---

## 13. 路线图

### 13.1 v1.x(近期)

**增强沙箱**：
- 基于Docker的隔离
- VM级沙箱
- 网络隔离

**审批工作流**：
- 多级审批
- 基于策略的路由
- Slack/Teams集成

---

## 14. 结论

### 14.1 范式转变

AgentOS代表了我们如何思考AI执行的根本转变：

**旧范式**：信任AI做正确的事  
**新范式**：像操作系统一样构造AI执行

就像操作系统提供：
- 进程隔离
- 资源管理
- 审计日志
- 安全边界

AgentOS为AI执行提供这些。

### 14.2 为什么重要

随着AI变得更强大，不受控制执行的风险也在增长。AgentOS确保增强的能力不会以安全为代价。

**目标不是让AI更大胆——而是让AI值得信赖。**

### 14.3 行动号召

AgentOS是开源的(MIT许可证)。我们邀请：

**开发者**：贡献核心、构建适配器  
**研究人员**：评估安全属性、提出改进  
**组织**：在生产中部署、分享反馈  
**工具构建者**：作为执行后端与AgentOS集成

### 14.4 最后的思考

AI的未来不仅仅关于更智能的模型。它关于**让AI执行可靠、可审计和安全的系统**。

AgentOS是我们对这一未来的贡献。

---

## 附录

### 附录A：安装和快速入门

```bash
# 克隆仓库
git clone https://github.com/yourusername/agentos.git
cd agentos

# 安装依赖
pip install uv
uv sync

# 初始化
uv run agentos init

# 注册项目
uv run agentos project add /path/to/project --id my-project

# 添加记忆
uv run agentos memory add \
  --type convention \
  --summary "React组件使用PascalCase"

# 创建任务
cat > queue/task.json <<EOF
{
  "task_id": "task-001",
  "project_id": "my-project",
  "execution_mode": "semi_auto"
}
EOF

# 执行
uv run agentos orchestrate
```

### 附录B：模式参考

参见`agentos/schemas/`以获取完整的模式定义。

### 附录C：API参考

参见`docs/API.md`以获取编程API文档。

### 附录D：贡献指南

参见`CONTRIBUTING.md`以获取贡献指南。

---

**AgentOS v1.0**  
*从自然语言到可审计执行*

**仓库**: 
**文档**: 
**社区**: 

**许可证**: MIT  
**版权**: 2026 AgentOS Team

---

*本白皮书是一份活文档。*
