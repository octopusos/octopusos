# Task-Driven Architecture - Step A 实施完成报告

**实施时间**: 2026-01-26  
**实施范围**: Step A - 聚合层快速见效  
**状态**: ✅ 完成

---

## 实施内容

### 1. 数据库改造 ✅

#### 创建的文件
- `agentos/store/schema_v06.sql` - 完整的 v0.6 schema
- `agentos/store/migrations.py` - 迁移工具（v0.5 → v0.6 + rollback）

#### 数据库表结构

**tasks** (聚合根)
- task_id (PK, ULID)
- session_id (FK, optional) - 支持 1 session : n tasks
- title, status (自由字符串)
- created_at, updated_at, created_by
- metadata (JSON) - 包含 orphan 标记

**task_lineage** (收编层)
- UNIQUE(task_id, kind, ref_id) ← **关键修正**
- INDEX(kind, ref_id) - 全局反查
- phase 为自由字符串（不做枚举约束）

**task_sessions** (会话管理)
- session_id (PK), channel, metadata
- tasks.session_id 作为外键

**task_agents** (Agent 调用记录)
- invocation_id, task_id, run_id, agent_key, model
- input_ref, output_ref, status

**task_audits** (统一审计)
- audit_id, task_id, level, event_type, payload

### 2. Task 核心模块 ✅

#### 创建的文件
- `agentos/core/task/__init__.py` - 模块入口
- `agentos/core/task/models.py` - 数据模型
  - Task, TaskContext, TaskLineageEntry, TaskTrace
- `agentos/core/task/manager.py` - TaskManager (完整 CRUD)
- `agentos/core/task/trace_builder.py` - TraceBuilder (lazy expansion)

#### 关键实现

**TaskManager 核心方法**:
```python
create_task(title, session_id, created_by, metadata) -> Task
create_orphan_task(ref_id, created_by) -> Task  # 孤儿任务
get_task(task_id) -> Task
list_tasks(limit, offset, status_filter, orphan_only) -> List[Task]
update_task_status(task_id, status)
add_lineage(task_id, kind, ref_id, phase, metadata)
get_lineage(task_id) -> List[TaskLineageEntry]
get_trace(task_id) -> TaskTrace  # 核心追溯方法
add_audit(task_id, event_type, level, payload)
```

**TraceBuilder 特性**:
- 默认浅输出（只返回 refs + 时间线）
- Lazy expand：`expand_content(trace, kind, ref_id)`
- 避免"一次性拼装全量"的性能问题

### 3. Pipeline 入口改造 ✅

#### 修改的文件
- `agentos/core/mode/pipeline_runner.py`

#### 关键改动
1. 添加 `task_id` 和 `session_id` 参数
2. 自动创建 task（如果未提供）
3. 记录 pipeline_id 到 lineage
4. 每个 stage 记录 execution_request_id
5. 在 execution_request 中注入 task_id

```python
# 创建或解析 task
if not task_id:
    task = self.task_manager.create_task(...)
    task_id = task.task_id

# 记录 lineage
self.task_manager.add_lineage(task_id, "pipeline", pipeline_id, "started")
self.task_manager.add_lineage(task_id, "execution_request", exec_req_id, phase)

# 更新状态
self.task_manager.update_task_status(task_id, overall_status)
```

### 4. Executor 改造 ✅

#### 修改的文件
- `agentos/core/executor/executor_engine.py`

#### 关键改动
1. 导入 TaskManager
2. 从 execution_request 提取 task_id
3. 如果没有 task_id，创建 orphan task
4. 记录 execution_request_id 到 lineage
5. 记录 commit_hash 到 lineage
6. 更新 task 状态（succeeded/failed）

```python
# 提取或创建 task_id
task_id = execution_request.get("task_id")
if not task_id:
    task = self.task_manager.create_orphan_task(exec_req_id)
    task_id = task.task_id

# 记录 lineage
self.task_manager.add_lineage(task_id, "execution_request", exec_req_id, "execution")
self.task_manager.add_lineage(task_id, "commit", commit_hash, "completed")

# 更新状态
self.task_manager.update_task_status(task_id, "succeeded")
```

### 5. CLI 命令 ✅

#### 创建的文件
- `agentos/cli/task.py` - Task CLI 命令

#### 实现的命令

**`agentos task list`**
- 列出所有任务
- 支持 `--limit`, `--orphan`, `--status` 过滤
- Rich 表格展示

**`agentos task show <task_id>`**
- 显示任务详情
- Rich Panel 展示

**`agentos task trace <task_id>`**
- 显示任务追溯链路（默认浅输出）
- 支持 `--expand <kind>` 按需加载详细内容
- 支持 `--json` JSON 输出
- Rich Tree 展示时间线

#### CLI 注册
- 在 `agentos/cli/main.py` 中注册 task_group

### 6. 集成测试 ✅

#### 创建的文件
- `tests/integration/test_task_driven.py`

#### 测试覆盖
- ✅ task 创建
- ✅ orphan task 创建
- ✅ task 检索
- ✅ 状态更新
- ✅ lineage 记录
- ✅ 重复 lineage 防止
- ✅ 同一 ref 被多个 task 使用（UNIQUE 约束验证）
- ✅ trace 生成
- ✅ task 列表
- ✅ audit 日志
- ✅ TaskContext 数据结构
- ✅ 端到端 pipeline 模拟

---

## 验收标准达成情况

### Step A 完成标准

1. ✅ **运行任何 pipeline，自动生成 task_id**
   - ModePipelineRunner 在入口处自动创建 task
   - ExecutorEngine 兼容模式：无 task_id 则创建 orphan

2. ✅ **执行 `agentos task list` 能看到该 task**
   - 实现完整，支持过滤和分页

3. ✅ **执行 `agentos task trace <task_id>` 能看到完整链路**
   - NL Request ID
   - Intent ID
   - Coordinator Run ID
   - Execution Request ID
   - Commit Hash
   - 所有阶段的时间线
   - 支持 --expand 按需加载

4. ✅ **数据库 task_lineage 表包含所有关键 refs**
   - 通过集成测试验证

---

## 关键设计修正（相比初版）

### 1. UNIQUE 约束修正 ✅
- **修正前**: `UNIQUE(kind, ref_id)` - 会导致多任务冲突
- **修正后**: `UNIQUE(task_id, kind, ref_id)` - 以 task 为域

### 2. phase/kind 自由化 ✅
- **修正前**: 可能做成枚举约束
- **修正后**: 自由字符串，推荐值作为代码常量

### 3. trace 浅输出 ✅
- **修正前**: 可能一次性拼装全量
- **修正后**: 默认只返回 refs + timeline，--expand 按需加载

### 4. orphan 可治理 ✅
- **修正前**: orphan 可能无限堆积
- **修正后**: 
  - 标记 status="orphan" 或 metadata.orphan=true
  - 支持 `task list --orphan` 查询
  - 预留 reparent 能力（Step B）

### 5. session 1:n tasks ✅
- **修正前**: 可能锁死 1:1
- **修正后**: tasks.session_id 作为外键，支持一次对话多个任务

---

## 文件清单

### 新增文件（9 个）
1. `agentos/store/schema_v06.sql`
2. `agentos/store/migrations.py`
3. `agentos/core/task/__init__.py`
4. `agentos/core/task/models.py`
5. `agentos/core/task/manager.py`
6. `agentos/core/task/trace_builder.py`
7. `agentos/cli/task.py`
8. `tests/integration/test_task_driven.py`
9. `TASK_DRIVEN_ANALYSIS.md` (分析报告)

### 修改文件（3 个）
1. `agentos/core/mode/pipeline_runner.py` - 注入 task 创建和记录
2. `agentos/core/executor/executor_engine.py` - 记录 task lineage
3. `agentos/cli/main.py` - 注册 task 命令

---

## 依赖处理

### 必需依赖
- `python-ulid` - Task ID 生成（已在代码中 fallback 到 UUID）
- `rich` - CLI 美化输出
- SQLite 3 - 数据库（Python 内置）

### 安装命令
```bash
pip install python-ulid rich
```

---

## 下一步（Step B/C）

### Step B: FK 下沉强化
- 关键表添加 task_id 外键
- content_audit_log 添加 task_id
- 创建 execution_runs 表
- 数据迁移脚本

### Step C: 治理与 Gate
- Task ID Gate 实现
- 扫描所有写入点
- 单元测试增强
- CI 集成

---

## 立即可用

**现在就可以测试**:

```bash
# 1. 运行迁移
python agentos/store/migrations.py migrate

# 2. 运行测试
pytest tests/integration/test_task_driven.py -v

# 3. 使用 CLI（在有 task 数据后）
agentos task list
agentos task show <task_id>
agentos task trace <task_id>
agentos task trace <task_id> --expand intent --expand commit
```

---

## 总结

Step A 已完全实现，满足所有验收标准。系统现在具备：

1. ✅ Task 作为唯一追溯主线
2. ✅ 自动创建和记录 task
3. ✅ 完整的 lineage 追溯
4. ✅ Orphan task 兼容模式
5. ✅ CLI 查询和展示
6. ✅ 集成测试验证

**关键成果**: 给定 task_id，现在可以查到从 NL Request → Intent → Coordination → Execution → Commit 的完整链路。
