# AgentOS Task-Driven 架构分析报告

**分析时间**: 2026-01-26  
**分析范围**: 全代码库扫描  
**结论**: ❌ **当前系统不是完全 task 驱动的架构**

---

## 📊 执行摘要

### 关键发现

1. **主要追溯线**: 系统目前以 `execution_request_id` / `run_id` 为主要追溯标识
2. **Task 概念存在但不是核心**: Task 主要用于调度系统，但不是全流程的追溯主线
3. **Session 概念缺失**: 代码中没有明确的 Session 概念和 session_id
4. **Agent 概念存在但未绑定 Task**: Agent 是内容注册表中的可选资源，不是每个执行的必须组件

---

## 🔍 详细分析

### 1. 当前的追溯体系

#### 1.1 主要 ID 体系

系统中存在多个并行的 ID 体系：

```
nl_request
    ↓
nl_request_id → intent_id → execution_request_id → run_id
                                    ↓
                            coordinator_run_id
                                    ↓
                            干执行 (dry_executor)
                                    ↓
                            question_pack_id / answer_pack_id
                                    ↓
                            执行 (executor)
                                    ↓
                            run_tape.jsonl + review_pack
```

**关键代码证据**:

```python
# agentos/core/intent_builder/builder.py:161
intent_id = f"intent_{uuid.uuid4().hex[:12]}"

# agentos/core/coordinator/engine.py:75
run_id = f"coord_run_{intent['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

# agentos/core/mode/pipeline_runner.py:221
exec_req_id = f"stage_{stage_idx}_{mode_id}_{uuid.uuid4().hex[:8]}"

# agentos/core/executor/executor_engine.py:89
exec_req_id = execution_request["execution_request_id"]
```

#### 1.2 数据库层的 Task 概念

**Task 出现的地方**:

1. **Scheduler 系统** (`agentos/core/scheduler/`)
   - `TaskNode`: 调度图中的任务节点
   - `TaskGraph`: 任务依赖图
   - `task_id`: 调度任务标识

2. **数据库表** (`agentos/store/schema_v02.sql`)
   - `task_runs`: 任务执行记录
   - `task_dependencies`: 任务依赖
   - `task_conflicts`: 任务冲突

**关键发现**: Task 主要用于**后台调度和并发控制**，但不是用户请求的主追溯线。

```sql
-- schema_v02.sql:28
CREATE TABLE IF NOT EXISTS task_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    agent_type TEXT,
    execution_mode TEXT NOT NULL,
    ...
);
```

#### 1.3 Session 概念的缺失

**扫描结果**: 
- ❌ 无 `session_id` 字段
- ❌ 无 `Session` 类定义
- ❌ 无会话管理机制
- ❌ 无多轮对话的会话绑定

**唯一相关的是 Answer Pack 的多轮机制**:

```python
# agentos/core/answers/multiround.py
class MultiRoundAnswerCollector:
    """Multi-round question-answer collection"""
    # 但这不是真正的 Session 管理
```

#### 1.4 Agent 概念的位置

**Agent 是内容注册表中的可选资源**:

```python
# agentos/core/content/registry.py
# Agent 作为 content_type 之一注册

# agentos/core/intent_builder/builder.py:74
agents = self.query_service.find_matching_agents(parsed_nl)
```

**关键发现**: Agent 不是每次执行的必须组件，而是根据需要从注册表选择的可选资源。

---

### 2. 真实的执行流程追溯链

#### 2.1 当前流程（以 execution_request_id 为主线）

```
用户输入 NL Request
    ↓
nl_request_id (唯一标识输入)
    ↓
Intent Builder → intent_id
    ↓
Coordinator → coordinator_run_id
    ↓
Dry Executor → dry_result_id
    ↓
(可选) Question/Answer → question_pack_id, answer_pack_id
    ↓
Executor → execution_request_id (核心追溯点)
    ↓
RunTape → run_tape.jsonl (审计日志)
    ↓
Git Commit → commit_hash (最终证据)
```

**证据**: ExecutorEngine.execute() 方法

```python
# agentos/core/executor/executor_engine.py:89-96
exec_req_id = execution_request["execution_request_id"]
run_dir = self.output_dir / exec_req_id
run_dir.mkdir(parents=True, exist_ok=True)

# P0-RT2: RunTape 必须从第一行开始写（最外层初始化）
audit_dir = run_dir / "audit"
audit_dir.mkdir(parents=True, exist_ok=True)
run_tape = RunTape(audit_dir)
```

#### 2.2 审计追溯能力

**当前能做到的**:

✅ 给定 `execution_request_id`，可以获取:
- 输入: execution_request.json
- 审计: run_tape.jsonl
- 快照: snapshots/*.json
- 结果: execution_result.json
- Commit: commit_hash (通过 review_pack)

✅ 给定 `intent_id`，可以获取:
- ExecutionIntent
- Coordinator 输出
- Dry Executor 结果

**当前做不到的**:

❌ 给定 `task_id`，无法获取:
- 从理解 (Intent) 到规划 (Coordinator) 的完整链路
- 该任务关联的所有 Agent 调用
- 该任务的会话历史

❌ 无法通过 `session_id` 追溯多轮对话的完整上下文

---

### 3. Task 驱动架构 vs 当前架构

#### 3.1 理想的 Task 驱动架构

```
用户发起请求 → 创建 Task (task_id)
    ↓
Task.session_id = session_001 (绑定会话)
    ↓
Task.agent_id = agent_planning (分配 Agent)
    ↓
Phase 1: Intent Analysis
    - Task.phase = "intent"
    - Task.intent_id = intent_xxx
    ↓
Phase 2: Coordination
    - Task.phase = "coordination"
    - Task.coordinator_run_id = coord_xxx
    ↓
Phase 3: Dry Execution
    - Task.phase = "dry_execution"
    - Task.dry_result_id = dry_xxx
    ↓
Phase 4: Real Execution
    - Task.phase = "execution"
    - Task.execution_request_id = exec_xxx
    - Task.commit_hash = abc123
    ↓
Task.status = "completed"
```

**核心特征**:
1. ✅ Task 是唯一的顶层追溯 ID
2. ✅ 所有 phase 的 ID 都记录在 Task 上
3. ✅ Session 和 Agent 都与 Task 绑定
4. ✅ 给定 task_id，可以获取全流程

#### 3.2 当前架构

```
用户发起请求 → nl_request_id
    ↓
Intent Builder → intent_id (独立生成)
    ↓
Coordinator → coordinator_run_id (独立生成)
    ↓
Dry Executor → dry_result_id (独立生成)
    ↓
Executor → execution_request_id (独立生成)
    ↓
Commit → commit_hash
```

**核心特征**:
1. ❌ 各个阶段的 ID 独立生成，没有统一的顶层 Task
2. ❌ 需要通过 JSON 文件的 lineage 字段来关联
3. ❌ 没有明确的 session_id
4. ❌ Agent 是可选的，不与执行强绑定

---

### 4. 数据库层的 Task 概念

#### 4.1 task_runs 表

```sql
CREATE TABLE IF NOT EXISTS task_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    agent_type TEXT,
    execution_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    lease_holder TEXT,
    lease_until TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    triggered_by TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

**用途**: 后台任务调度和管理，不是用户请求的主追溯线。

#### 4.2 Scheduler 的 Task 概念

```python
# agentos/core/scheduler/audit.py:11
@dataclass(frozen=True)
class TaskNode:
    """Task node for task graph."""
    task_id: str
    task_type: str = "default"
    policy_mode: str = "semi_auto"
    parallelism_group: Optional[str] = None
    priority: int = 0
    depends_on: list[str] = field(default_factory=list)
```

**用途**: 并行任务调度、依赖管理、锁冲突检测。

---

## 🎯 结论

### 主要问题

1. **追溯线不统一**: 
   - 当前以 `execution_request_id` / `run_id` 为主
   - Task 概念存在但边缘化
   - 需要通过 JSON lineage 字段手动串联

2. **Session 概念缺失**:
   - 无法追溯多轮对话
   - 无法关联同一会话的多个请求

3. **Agent 未与执行绑定**:
   - Agent 是可选的内容资源
   - 不是每次执行的必须组件

4. **数据库与执行流程脱节**:
   - `task_runs` 表主要用于后台调度
   - 用户请求的追溯数据主要在 JSON 文件中

---

## 💡 建议：如何改造为 Task 驱动架构

### 方案 1: 最小改造（兼容现有系统）

**核心思想**: 在现有基础上增加 Task 层，向下兼容

```python
# 新增 Task 模型
@dataclass
class Task:
    task_id: str  # 顶层唯一标识
    session_id: Optional[str]  # 会话 ID
    nl_request_id: str
    intent_id: Optional[str]
    coordinator_run_id: Optional[str]
    dry_result_id: Optional[str]
    execution_request_id: Optional[str]
    agent_ids: List[str]  # 参与的 Agent
    status: str  # created/planning/executing/completed/failed
    created_at: str
    updated_at: str
    commit_hash: Optional[str]
```

**实施步骤**:

1. 在 `IntentBuilder.build_intent()` 开始时创建 Task
2. 在各个阶段更新 Task 的相应字段
3. 保存 Task 到数据库（新表：`tasks`）
4. 现有 ID 体系不变，Task 作为聚合层

**优点**:
- ✅ 向下兼容
- ✅ 改动最小
- ✅ 可以逐步迁移

**缺点**:
- 🟡 Task 只是聚合层，不是真正的驱动核心

---

### 方案 2: 彻底重构（Task 优先）

**核心思想**: Task 成为所有操作的顶层入口

```python
# 用户请求首先创建 Task
task = TaskManager.create_task(
    nl_request=nl_request,
    session_id=session.id,
    policy="semi_auto"
)

# 所有后续操作都基于 task_id
intent = IntentBuilder.build(task_id=task.id, ...)
coord_result = Coordinator.coordinate(task_id=task.id, ...)
exec_result = Executor.execute(task_id=task.id, ...)
```

**数据库设计**:

```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    session_id TEXT,
    nl_request_id TEXT,
    intent_id TEXT,
    coordinator_run_id TEXT,
    execution_request_id TEXT,
    agent_ids TEXT,  -- JSON array
    status TEXT,
    phase TEXT,  -- intent/coordination/dry_execution/execution/completed
    commit_hash TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    project_id TEXT,
    created_at TIMESTAMP,
    last_activity TIMESTAMP
);

CREATE TABLE task_agents (
    task_id TEXT,
    agent_id TEXT,
    role TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
```

**优点**:
- ✅ 真正的 Task 驱动
- ✅ 追溯完整
- ✅ Session 管理清晰

**缺点**:
- ❌ 需要大量重构
- ❌ 破坏现有 API

---

### 方案 3: 混合方案（推荐）

**核心思想**: 
1. 保留现有 ID 体系（nl_request_id, intent_id, execution_request_id）
2. 增加 Task 作为顶层聚合和追溯入口
3. 增加 Session 管理层

**实施**:

```python
# Phase 1: 创建 Task（在 IntentBuilder 之前）
task = Task.create(
    nl_request_id=nl_request["id"],
    session_id=session_id,  # 从上下文获取
    policy="semi_auto"
)

# Phase 2: 各阶段记录到 Task
intent = IntentBuilder.build_intent(nl_request, policy)
task.update(intent_id=intent["id"], phase="coordination")

coord_result = Coordinator.coordinate(intent, policy, factpack)
task.update(coordinator_run_id=coord_result.run_id, phase="dry_execution")

# ... 以此类推

# Phase 3: 查询接口
task = Task.get(task_id)
# task.intent_id, task.coordinator_run_id, task.execution_request_id 都有值
```

**数据存储**:
- JSON 文件: 保留现有的 intent.json, execution_request.json 等
- SQLite: 新增 `tasks` 表作为索引
- 给定 task_id，先查数据库获取各阶段 ID，再读取 JSON 文件

**优点**:
- ✅ 兼容现有系统
- ✅ 增加顶层追溯能力
- ✅ 改动适中
- ✅ 可以逐步完善

---

## 📋 行动建议

### 立即可做（1-2 天）

1. **增加 Task 数据模型**
   - 定义 `Task` dataclass
   - 创建 `tasks` 表
   - 实现 `TaskManager` 基础 CRUD

2. **在 Pipeline 入口注入 Task**
   - `ModePipelineRunner.run_pipeline()` 创建 Task
   - 各阶段更新 Task 状态

3. **增加 Session 概念**
   - 创建 `sessions` 表
   - CLI 工具自动生成 session_id
   - 多轮对话绑定 session

### 中期完善（1-2 周）

1. **完善追溯 API**
   - `Task.get_full_trace()`: 返回从 NL 到 Commit 的完整链路
   - `Task.get_phase_artifacts()`: 获取各阶段的 JSON 文件
   - `Session.get_tasks()`: 获取会话的所有任务

2. **增强 Agent 绑定**
   - 记录每个 Task 使用的 Agent
   - 创建 `task_agents` 表

3. **重构 Scheduler 集成**
   - 调度器的 task_id 与追溯系统的 task_id 统一
   - `task_runs` 表与 `tasks` 表关联

### 长期优化（1 个月）

1. **可视化追溯界面**
   - Web UI: 输入 task_id，显示完整流程图
   - 每个节点可点击查看详情

2. **审计增强**
   - 所有日志包含 task_id
   - Git commit message 包含 task_id

3. **性能优化**
   - Task 数据缓存
   - 大规模任务的索引优化

---

## 🔚 总结

**当前状态**: ❌ 不是 Task 驱动架构

**主要问题**:
1. 追溯线以 execution_request_id 为主，不是 task_id
2. 缺少 Session 概念
3. Agent 未与执行流程强绑定

**推荐方案**: 混合方案（方案 3）
- 保留现有 ID 体系
- 增加 Task 作为顶层聚合
- 逐步完善追溯能力

**核心改造点**:
1. 增加 `Task` 模型和数据库表
2. 在 Pipeline 入口创建和更新 Task
3. 提供基于 task_id 的完整追溯 API

**预期效果**: 实现 "给定 task_id，获取从理解到规划到实施的全部环节" 的目标。
