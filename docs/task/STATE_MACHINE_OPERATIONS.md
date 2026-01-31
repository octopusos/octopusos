# Task 状态机运维手册

**版本**: v1.0
**最后更新**: 2026-01-30
**适用范围**: AgentOS Task System v0.4+

---

## 目录

1. [状态机概览](#1-状态机概览)
2. [常见操作](#2-常见操作)
3. [高级控制](#3-高级控制)
4. [监控和观测](#4-监控和观测)
5. [故障排查](#5-故障排查)
6. [性能优化](#6-性能优化)
7. [治理与合规](#7-治理与合规) 🆕

---

## 1. 状态机概览

### 1.1 状态定义

Task 状态机定义了任务从创建到完成的完整生命周期。所有状态转换都经过严格的验证和审计。

#### 状态分类

**INITIAL 状态组 (初始状态)**
- `DRAFT`: 草稿状态，任务正在起草，尚未准备好执行

**APPROVAL 状态组 (审批状态)**
- `APPROVED`: 已审批，任务已获准执行，等待入队

**EXECUTION 状态组 (执行状态)**
- `QUEUED`: 已入队，任务在等待执行队列中
- `RUNNING`: 运行中，任务正在执行

**VERIFICATION 状态组 (验证状态)**
- `VERIFYING`: 验证中，任务执行完成，正在进行结果验证
- `VERIFIED`: 已验证，任务通过验证

**TERMINAL 状态组 (终态)**
- `DONE`: 完成，任务成功完成
- `FAILED`: 失败，任务执行失败
- `CANCELED`: 取消，任务被用户或系统取消
- `BLOCKED`: 阻塞，任务执行被阻塞（例如在 AUTONOMOUS 模式下触发了需要审批的检查点）

#### 状态说明表

| 状态 | 类型 | 说明 | 是否可重试 | 是否终态 |
|------|------|------|-----------|---------|
| DRAFT | INITIAL | 任务草稿，等待审批 | N/A | 否 |
| APPROVED | APPROVAL | 已审批，可以入队 | N/A | 否 |
| QUEUED | EXECUTION | 在执行队列中等待 | N/A | 否 |
| RUNNING | EXECUTION | 正在执行 | N/A | 否 |
| VERIFYING | VERIFICATION | 执行完成，正在验证 | N/A | 否 |
| VERIFIED | VERIFICATION | 验证通过 | N/A | 否 |
| DONE | TERMINAL | 任务完成 | 否 | 是 |
| FAILED | TERMINAL | 任务失败 | **是** | 是 |
| CANCELED | TERMINAL | 任务取消 | 否 | 是 |
| BLOCKED | TERMINAL | 任务阻塞 | **是** | 是 |

### 1.2 转换规则

状态机通过转换表（Transition Table）定义所有允许的状态转换。

#### 完整转换表

```
FROM DRAFT:
  → APPROVED    ✓ 任务审批通过
  → CANCELED    ✓ 草稿阶段取消

FROM APPROVED:
  → QUEUED      ✓ 任务入队执行
  → CANCELED    ✓ 审批后取消

FROM QUEUED:
  → RUNNING     ✓ 开始执行
  → CANCELED    ✓ 队列中取消

FROM RUNNING:
  → VERIFYING   ✓ 执行完成，进入验证
  → FAILED      ✓ 执行失败
  → CANCELED    ✓ 执行中取消
  → BLOCKED     ✓ 执行被阻塞

FROM VERIFYING:
  → VERIFIED    ✓ 验证通过
  → FAILED      ✓ 验证失败
  → CANCELED    ✓ 验证中取消
  → QUEUED      ✓ 验证失败，重新入队（Gate 失败重试）

FROM VERIFIED:
  → DONE        ✓ 标记为完成

FROM FAILED:
  → QUEUED      ✓ 失败后重试（需检查 retry 策略）

FROM BLOCKED:
  → QUEUED      ✓ 解除阻塞，重新入队
  → CANCELED    ✓ 取消被阻塞的任务
```

#### 转换条件

每个状态转换都需要满足以下条件：

1. **源状态匹配**: 当前状态必须与转换规则的源状态匹配
2. **转换规则存在**: 转换必须在转换表中定义
3. **业务规则验证**: 例如 retry 时需要检查 `max_retries` 限制
4. **并发安全**: 通过 SQLiteWriter 序列化写操作，避免竞态条件

#### 状态流转图（文本描述）

```
                    ┌─────────┐
                    │  DRAFT  │ (起点)
                    └────┬────┘
                         │ approve_task()
                         ↓
                    ┌─────────┐
                    │APPROVED │
                    └────┬────┘
                         │ queue_task()
                         ↓
                    ┌─────────┐
                    │ QUEUED  │ ←─────────┐ (retry)
                    └────┬────┘           │
                         │ start_task()   │
                         ↓                │
                    ┌─────────┐           │
                    │ RUNNING │           │
                    └────┬────┘           │
                         │ complete_task_execution()
                         ↓                │
                    ┌──────────┐          │
                    │VERIFYING │          │
                    └────┬─────┘          │
                         │ verify_task()  │
                         ↓                │
                    ┌──────────┐          │
                    │ VERIFIED │          │
                    └────┬─────┘          │
                         │ mark_task_done()
                         ↓                │
                    ┌─────────┐           │
                    │  DONE   │           │
                    └─────────┘           │
                                          │
    ┌─────────┐         ┌─────────┐      │
    │CANCELED │         │ FAILED  │──────┘
    └─────────┘         └─────────┘
         ↑                   ↑
         │                   │
         └───────┬───────────┘
          任意非终态状态
```

### 1.3 终态处理

#### 终态含义

- **DONE**: 任务成功完成，所有目标达成，验证通过
- **FAILED**: 任务执行失败，可能是代码错误、超时、Gate 验证失败等
- **CANCELED**: 任务被用户或系统主动取消
- **BLOCKED**: 任务执行被阻塞，通常发生在 AUTONOMOUS 模式下触发了需要人工审批的检查点

#### 从终态恢复

终态任务通常不可修改，但某些终态支持恢复操作：

**FAILED → QUEUED (Retry)**

```python
from agentos.core.task.service import TaskService

service = TaskService()

# 重试失败的任务
task = service.retry_failed_task(
    task_id="01HQ7X...",
    actor="admin",
    reason="Retry after fixing configuration"
)

print(f"Task {task.task_id} retried, now in {task.status} state")
```

**注意事项**:
- 必须检查 `max_retries` 限制
- 系统会自动检测 retry 循环（相同失败原因重复 3 次）
- Retry 次数会记录在 `metadata.retry_state.retry_count` 中

**BLOCKED → QUEUED (Unblock)**

```python
# 解除阻塞的任务
task = service.state_machine.transition(
    task_id="01HQ7X...",
    to="queued",
    actor="admin",
    reason="Manual approval granted, unblocking task"
)
```

**其他终态恢复**

DONE 和 CANCELED 状态不支持恢复。如需重新执行：
1. 创建新任务（推荐）
2. 或通过数据库手动修改状态（**不推荐**，会破坏审计链）

---

## 2. 常见操作

### 2.1 创建任务

所有新任务必须从 DRAFT 状态开始创建。

#### 基础创建

```python
from agentos.core.task.service import TaskService

service = TaskService()

# 创建草稿任务
task = service.create_draft_task(
    title="Implement user authentication",
    session_id="session_abc123",
    project_id="proj_001",
    created_by="developer@example.com",
    metadata={
        "priority": "high",
        "assignee": "team-backend",
        "estimated_hours": 8
    }
)

print(f"Created task {task.task_id} in {task.status} state")
# 输出: Created task 01HQ7X... in draft state
```

#### 参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `title` | `str` | ✓ | 任务标题（描述任务目标） |
| `session_id` | `str` | ✗ | 会话 ID（用于关联多个任务），未提供时自动生成 |
| `project_id` | `str` | ✗ | 项目 ID（用于继承项目配置） |
| `created_by` | `str` | ✗ | 创建者标识（邮箱、用户名等） |
| `metadata` | `dict` | ✗ | 任务元数据（自定义字段） |
| `route_plan_json` | `str` | ✗ | 路由计划（JSON 序列化） |
| `requirements_json` | `str` | ✗ | 任务需求（JSON 序列化） |
| `selected_instance_id` | `str` | ✗ | 选定的 provider 实例 ID |
| `router_version` | `str` | ✗ | 路由器版本 |

#### 批量创建和立即执行

对于需要立即执行的任务，可以使用组合方法：

```python
# 创建 + 审批 + 入队 + 启动（一步到位）
task = service.create_approve_queue_and_start(
    title="Generate weekly report",
    project_id="proj_001",
    created_by="scheduler",
    actor="system",
    metadata={
        "scheduled": True,
        "cron": "0 9 * * MON"
    }
)

print(f"Task {task.task_id} is now {task.status}")
# 输出: Task 01HQ7X... is now queued
# 后台 Runner 将自动启动执行
```

**流程**:
1. 创建 DRAFT 任务
2. 自动审批（DRAFT → APPROVED）
3. 自动入队（APPROVED → QUEUED）
4. 启动后台 Runner（异步执行，将转换为 RUNNING）

### 2.2 批准任务

任务从 DRAFT 状态转换为 APPROVED 状态，表示已获准执行。

#### 基础审批

```python
task = service.approve_task(
    task_id="01HQ7X...",
    actor="manager@example.com",
    reason="Task reviewed and approved for execution"
)

print(f"Task approved: {task.status}")
# 输出: Task approved: approved
```

#### 何时批准

**需要批准的场景**:
- **人工审批工作流**: 任务需要经过管理员或团队 leader 审批
- **预算审批**: 任务涉及资源消耗（LLM API 调用、计算资源等）
- **风险控制**: 高风险任务（修改生产代码、数据库操作等）
- **合规要求**: 组织政策要求任务审批流程

**自动批准的场景**:
- **自动化任务**: 定时任务、触发器任务
- **测试任务**: 开发环境的测试任务
- **低风险任务**: 只读操作、数据查询等

#### 审批工作流示例

```python
from agentos.core.task.service import TaskService

def review_and_approve_task(task_id: str, reviewer: str) -> bool:
    """审批工作流示例"""
    service = TaskService()

    # 1. 加载任务
    task = service.get_task(task_id)
    if not task:
        print(f"Task {task_id} not found")
        return False

    # 2. 检查任务状态
    if task.status != "draft":
        print(f"Task {task_id} is not in draft state (current: {task.status})")
        return False

    # 3. 审批逻辑（示例：检查元数据）
    priority = task.metadata.get("priority", "normal")
    estimated_hours = task.metadata.get("estimated_hours", 0)

    if priority == "high" and estimated_hours > 40:
        # 高优先级且耗时长的任务需要额外审批
        print(f"Task {task_id} requires senior approval (high priority, {estimated_hours} hours)")
        return False

    # 4. 批准任务
    try:
        approved_task = service.approve_task(
            task_id=task_id,
            actor=reviewer,
            reason=f"Approved by {reviewer}: Priority={priority}, Hours={estimated_hours}"
        )
        print(f"Task {task_id} approved successfully")
        return True
    except Exception as e:
        print(f"Failed to approve task {task_id}: {e}")
        return False

# 使用示例
review_and_approve_task("01HQ7X...", "manager@example.com")
```

### 2.3 重试任务

当任务失败后，可以通过 retry 操作重新执行。

#### 基础重试

```python
task = service.retry_failed_task(
    task_id="01HQ7X...",
    actor="operator",
    reason="Retry after fixing network issue"
)

print(f"Task retry scheduled: {task.status}")
# 输出: Task retry scheduled: queued
```

#### 何时重试

**适合重试的场景**:
- **临时性错误**: 网络超时、API 限流、资源暂时不可用
- **环境修复后**: 修复了配置错误、依赖问题后
- **随机性失败**: 偶发性错误（如并发冲突）

**不适合重试的场景**:
- **逻辑错误**: 代码 bug、算法错误（重试不会成功）
- **输入错误**: 任务参数错误、数据格式错误
- **权限问题**: 缺少必要权限（需要先解决权限问题）
- **达到 max_retries**: 已经重试多次仍失败（需要人工介入）

#### Retry 策略配置

任务可以配置 retry 策略，控制重试行为：

```python
from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

# 创建任务时配置 retry 策略
task = service.create_draft_task(
    title="Fetch external API data",
    metadata={
        "retry_config": RetryConfig(
            max_retries=5,
            backoff_type=RetryBackoffType.EXPONENTIAL,
            base_delay_seconds=60,
            max_delay_seconds=3600
        ).to_dict()
    }
)
```

**Retry 配置参数**:
- `max_retries`: 最大重试次数（默认 3）
- `backoff_type`: 退避策略（none/fixed/linear/exponential）
- `base_delay_seconds`: 基础延迟时间（秒，默认 60）
- `max_delay_seconds`: 最大延迟时间（秒，默认 3600）

#### 检查 Retry 状态

```python
# 加载任务
task = service.get_task("01HQ7X...")

# 获取 retry 状态
retry_state = task.get_retry_state()

print(f"Retry count: {retry_state.retry_count}")
print(f"Last retry: {retry_state.last_retry_at}")
print(f"Next retry after: {retry_state.next_retry_after}")

# 获取 retry 历史
for attempt in retry_state.retry_history:
    print(f"Attempt {attempt['attempt']}: {attempt['reason']} at {attempt['timestamp']}")
```

#### Retry 限制和错误处理

```python
from agentos.core.task.errors import RetryNotAllowedError

try:
    task = service.retry_failed_task(
        task_id="01HQ7X...",
        actor="operator",
        reason="Retry after configuration fix"
    )
except RetryNotAllowedError as e:
    print(f"Retry not allowed: {e.reason}")
    # 输出: Retry not allowed: Max retries (3) exceeded

    # 或: Retry not allowed: Retry loop detected: same failure repeated 3 times
```

### 2.4 取消任务

任务可以在执行的不同阶段被取消。

#### Cancel Draft/Approved/Queued 任务

```python
# 取消非运行状态的任务
task = service.cancel_task(
    task_id="01HQ7X...",
    actor="user@example.com",
    reason="Requirements changed, task no longer needed"
)

print(f"Task canceled: {task.status}")
# 输出: Task canceled: canceled
```

**支持的源状态**:
- DRAFT → CANCELED
- APPROVED → CANCELED
- QUEUED → CANCELED
- RUNNING → CANCELED
- VERIFYING → CANCELED

#### Cancel Running 任务

正在运行的任务需要使用专门的方法，支持 graceful shutdown：

```python
# 取消正在运行的任务（会触发清理流程）
task = service.cancel_running_task(
    task_id="01HQ7X...",
    actor="admin",
    reason="Emergency cancellation: system maintenance"
)

print(f"Running task canceled: {task.status}")
# 输出: Running task canceled: canceled
```

**Cancel Running 流程**:

1. **设置 cancel 标记**: 在任务 metadata 中设置 `cancel_actor`、`cancel_reason`、`cancel_requested_at`
2. **Runner 检测**: TaskRunner 在主循环中检测到 cancel 信号
3. **执行清理**: Runner 调用 CancelHandler 执行清理操作
   - 刷新日志（flush_logs）
   - 释放资源（release_resources）
   - 保存部分结果（save_partial_results）
4. **状态转换**: Runner 将任务状态转换为 CANCELED
5. **审计记录**: 记录 cancel 事件和清理结果

#### 区别说明

| 方法 | 适用状态 | 是否立即生效 | 是否执行清理 | 使用场景 |
|------|---------|------------|-------------|---------|
| `cancel_task()` | DRAFT, APPROVED, QUEUED, RUNNING, VERIFYING | 立即 | 否 | 取消未执行或已完成的任务 |
| `cancel_running_task()` | RUNNING | 下一次循环 | **是** | 取消正在运行的任务（需要清理） |

**最佳实践**:
- 对于 RUNNING 状态的任务，**必须**使用 `cancel_running_task()`
- 对于其他状态，使用 `cancel_task()` 即可
- 取消时**必须**提供 `reason`，便于后续审计

#### 批量取消示例

```python
def cancel_stale_tasks(max_age_hours: int = 24):
    """取消超过指定时间未完成的任务"""
    from datetime import datetime, timezone, timedelta

    service = TaskService()

    # 查询所有 QUEUED 状态的任务
    tasks = service.list_tasks(status_filter="queued", limit=1000)

    now = datetime.now(timezone.utc)
    canceled_count = 0

    for task in tasks:
        # 计算任务年龄
        created_at = datetime.fromisoformat(task.created_at)
        age_hours = (now - created_at).total_seconds() / 3600

        if age_hours > max_age_hours:
            try:
                service.cancel_task(
                    task_id=task.task_id,
                    actor="system",
                    reason=f"Stale task cleanup: queued for {age_hours:.1f} hours"
                )
                canceled_count += 1
            except Exception as e:
                print(f"Failed to cancel task {task.task_id}: {e}")

    print(f"Canceled {canceled_count} stale tasks")
    return canceled_count

# 使用示例
cancel_stale_tasks(max_age_hours=48)
```

---

## 3. 高级控制

### 3.1 Retry 策略

Retry 策略控制任务失败后的重试行为，包括重试次数、延迟策略、循环检测等。

#### 配置 Retry 策略

**方式 1: 任务创建时配置**

```python
from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

task = service.create_draft_task(
    title="API data synchronization",
    metadata={
        "retry_config": {
            "max_retries": 5,
            "backoff_type": "exponential",
            "base_delay_seconds": 60,
            "max_delay_seconds": 3600
        }
    }
)
```

**方式 2: 使用 RetryConfig 对象**

```python
retry_config = RetryConfig(
    max_retries=5,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=60,
    max_delay_seconds=3600
)

task = service.create_draft_task(
    title="API data synchronization",
    metadata={
        "retry_config": retry_config.to_dict()
    }
)
```

#### max_retries 限制

`max_retries` 定义任务最多可以重试的次数。

**推荐值**:
- **临时性错误（网络、API 限流）**: 5-10 次
- **一般错误**: 3 次（默认）
- **高成本操作（LLM 调用）**: 1-2 次
- **幂等操作**: 可以设置更高的值（如 20 次）

**示例**:

```python
# 网络爬虫任务：允许多次重试
task = service.create_draft_task(
    title="Crawl product data from e-commerce site",
    metadata={
        "retry_config": {
            "max_retries": 10,  # 网络可能不稳定
            "backoff_type": "exponential"
        }
    }
)

# LLM 生成任务：限制重试次数（成本考虑）
task = service.create_draft_task(
    title="Generate marketing copy with GPT-4",
    metadata={
        "retry_config": {
            "max_retries": 2,  # 限制 API 调用次数
            "backoff_type": "fixed"
        }
    }
)
```

**检查 Retry 次数**:

```python
task = service.get_task("01HQ7X...")
retry_config = task.get_retry_config()
retry_state = task.get_retry_state()

print(f"Retries: {retry_state.retry_count}/{retry_config.max_retries}")

if retry_state.retry_count >= retry_config.max_retries:
    print("Max retries exceeded, manual intervention required")
```

#### 退避策略选择

退避策略（Backoff Strategy）控制重试之间的延迟时间。

**可用策略**:

| 策略 | 延迟计算 | 适用场景 |
|------|---------|---------|
| `NONE` | 0 秒 | 立即重试，适用于快速失败检测 |
| `FIXED` | `base_delay_seconds` | 固定延迟，适用于周期性任务 |
| `LINEAR` | `base_delay_seconds * (retry_count + 1)` | 线性增长，适用于资源竞争场景 |
| `EXPONENTIAL` | `base_delay_seconds * (2 ^ retry_count)` | 指数增长，适用于网络错误、API 限流 |

**延迟计算示例**:

```python
# EXPONENTIAL (base_delay=60s, max_delay=3600s)
# Retry 1: 60s  (60 * 2^0)
# Retry 2: 120s (60 * 2^1)
# Retry 3: 240s (60 * 2^2)
# Retry 4: 480s (60 * 2^3)
# Retry 5: 960s (60 * 2^4)
# Retry 6: 1920s (60 * 2^5)
# Retry 7: 3600s (60 * 2^6 = 3840s, capped at 3600s)

# LINEAR (base_delay=60s, max_delay=3600s)
# Retry 1: 60s  (60 * 1)
# Retry 2: 120s (60 * 2)
# Retry 3: 180s (60 * 3)
# Retry 4: 240s (60 * 4)
# ...
```

**策略选择建议**:

```python
# API 限流场景：使用指数退避
api_task_config = {
    "retry_config": {
        "max_retries": 5,
        "backoff_type": "exponential",
        "base_delay_seconds": 60,
        "max_delay_seconds": 1800
    }
}

# 数据库锁竞争：使用线性退避
db_task_config = {
    "retry_config": {
        "max_retries": 3,
        "backoff_type": "linear",
        "base_delay_seconds": 30,
        "max_delay_seconds": 180
    }
}

# 快速失败检测：无延迟
quick_check_config = {
    "retry_config": {
        "max_retries": 3,
        "backoff_type": "none",
        "base_delay_seconds": 0,
        "max_delay_seconds": 0
    }
}

# 定时轮询：固定延迟
polling_config = {
    "retry_config": {
        "max_retries": 100,
        "backoff_type": "fixed",
        "base_delay_seconds": 300,  # 每 5 分钟重试一次
        "max_delay_seconds": 300
    }
}
```

#### Retry 循环检测

系统自动检测 retry 循环，防止相同错误无限重试。

**检测规则**:
- 检查最近 3 次 retry 的失败原因
- 如果 3 次失败原因完全相同，判定为 retry 循环
- 自动阻止进一步 retry，即使未达到 `max_retries`

**示例**:

```python
# 假设任务因为 "gate_failed" 原因失败并重试了 3 次
retry_history = [
    {"attempt": 1, "reason": "gate_failed", "timestamp": "2026-01-30T10:00:00Z"},
    {"attempt": 2, "reason": "gate_failed", "timestamp": "2026-01-30T10:02:00Z"},
    {"attempt": 3, "reason": "gate_failed", "timestamp": "2026-01-30T10:05:00Z"},
]

# 第 4 次 retry 时会被阻止
try:
    task = service.retry_failed_task(
        task_id="01HQ7X...",
        actor="system",
        reason="gate_failed"
    )
except RetryNotAllowedError as e:
    print(e.reason)
    # 输出: Retry loop detected: same failure repeated 3 times
```

**避免 Retry 循环**:
1. 在 retry 前修复根本原因（配置错误、代码 bug 等）
2. 使用不同的 `reason` 描述每次 retry（表明采取了不同的修复措施）
3. 监控 retry 模式，识别系统性问题

#### 最佳实践

**1. 根据任务类型设置策略**

```python
def get_retry_config_for_task_type(task_type: str) -> dict:
    """根据任务类型返回推荐的 retry 配置"""
    configs = {
        "api_call": {
            "max_retries": 5,
            "backoff_type": "exponential",
            "base_delay_seconds": 60,
            "max_delay_seconds": 1800
        },
        "file_processing": {
            "max_retries": 3,
            "backoff_type": "fixed",
            "base_delay_seconds": 120,
            "max_delay_seconds": 120
        },
        "llm_generation": {
            "max_retries": 2,
            "backoff_type": "exponential",
            "base_delay_seconds": 30,
            "max_delay_seconds": 300
        },
        "database_operation": {
            "max_retries": 3,
            "backoff_type": "linear",
            "base_delay_seconds": 30,
            "max_delay_seconds": 180
        }
    }
    return configs.get(task_type, {
        "max_retries": 3,
        "backoff_type": "exponential",
        "base_delay_seconds": 60,
        "max_delay_seconds": 3600
    })
```

**2. 记录详细的 Retry Reason**

```python
# ❌ 不好：原因模糊
service.retry_failed_task(
    task_id="01HQ7X...",
    actor="operator",
    reason="retry"
)

# ✅ 好：原因明确
service.retry_failed_task(
    task_id="01HQ7X...",
    actor="operator",
    reason="Retry after fixing API endpoint configuration (changed from http to https)"
)
```

**3. 监控 Retry 指标**

```python
def get_retry_metrics(task_id: str):
    """获取任务的 retry 指标"""
    service = TaskService()
    task = service.get_task(task_id)

    retry_config = task.get_retry_config()
    retry_state = task.get_retry_state()

    return {
        "task_id": task_id,
        "retry_count": retry_state.retry_count,
        "max_retries": retry_config.max_retries,
        "retry_exhausted": retry_state.retry_count >= retry_config.max_retries,
        "retry_reasons": [h["reason"] for h in retry_state.retry_history],
        "next_retry_after": retry_state.next_retry_after
    }
```

### 3.2 Timeout 机制

Timeout 机制基于 wallclock 时间检测任务执行超时，支持配置超时时间、警告阈值、心跳机制。

#### 配置 Timeout

**创建任务时配置**:

```python
from agentos.core.task.timeout_manager import TimeoutConfig

task = service.create_draft_task(
    title="Long-running data analysis",
    metadata={
        "timeout_config": {
            "enabled": True,
            "timeout_seconds": 3600,      # 1 小时超时
            "warning_threshold": 0.8      # 80% 时警告
        }
    }
)
```

**TimeoutConfig 参数**:
- `enabled`: 是否启用 timeout（默认 True）
- `timeout_seconds`: 超时时间（秒，默认 3600 = 1 小时）
- `warning_threshold`: 警告阈值（0-1，默认 0.8 = 80%）

**推荐超时时间**:

| 任务类型 | 推荐超时时间 | 说明 |
|---------|------------|------|
| API 调用 | 300s (5分钟) | 网络请求通常应快速完成 |
| 文件处理 | 1800s (30分钟) | 取决于文件大小 |
| LLM 生成 | 600s (10分钟) | 长文本生成可能较慢 |
| 数据分析 | 7200s (2小时) | 大数据集分析耗时长 |
| 代码编译 | 1800s (30分钟) | 大项目编译耗时 |

#### 超时检测原理

TaskRunner 在主循环中检测超时：

```python
# TaskRunner 伪代码
while iteration < max_iterations:
    # 1. 检查 timeout
    timeout_config = task.get_timeout_config()
    timeout_state = task.get_timeout_state()

    is_timeout, warning_msg, timeout_msg = timeout_manager.check_timeout(
        timeout_config,
        timeout_state
    )

    if is_timeout:
        # 超时：标记任务为 FAILED
        task.exit_reason = "timeout"
        break

    if warning_msg:
        # 警告：记录审计日志
        logger.warning(warning_msg)

    # 2. 更新 heartbeat
    timeout_state = timeout_manager.update_heartbeat(timeout_state)
    task.update_timeout_state(timeout_state)

    # 3. 执行任务逻辑
    # ...
```

**检测流程**:
1. 计算 `elapsed_seconds = now - execution_start_time`
2. 检查是否超时：`elapsed_seconds >= timeout_seconds`
3. 检查是否达到警告阈值：`elapsed_seconds >= timeout_seconds * warning_threshold`
4. 更新 heartbeat 时间戳

#### 警告阈值

当执行时间达到 `timeout_seconds * warning_threshold` 时，系统发出警告。

**默认阈值**: 0.8 (80%)

**示例**:
```python
# timeout_seconds = 3600 (1小时)
# warning_threshold = 0.8 (80%)
#
# 警告时间 = 3600 * 0.8 = 2880s = 48分钟
#
# 时间线:
#   0s ----------- 2880s (警告) ----------- 3600s (超时)
#   │              │                        │
#   开始            Warning                  Timeout
```

**调整阈值**:

```python
# 高风险任务：提前警告（50% 时就警告）
high_risk_config = {
    "timeout_config": {
        "enabled": True,
        "timeout_seconds": 3600,
        "warning_threshold": 0.5  # 提前警告
    }
}

# 低风险任务：接近超时才警告（90% 时警告）
low_risk_config = {
    "timeout_config": {
        "enabled": True,
        "timeout_seconds": 7200,
        "warning_threshold": 0.9  # 接近超时才警告
    }
}
```

#### 心跳机制

心跳（Heartbeat）用于跟踪任务的活跃状态。

**更新频率**: 每次主循环迭代更新一次

**用途**:
- 检测任务是否仍在运行
- 区分超时和 runner crash
- 支持分布式任务监控

**查看心跳**:

```python
task = service.get_task("01HQ7X...")
timeout_state = task.get_timeout_state()

print(f"Last heartbeat: {timeout_state.last_heartbeat}")
# 输出: Last heartbeat: 2026-01-30T12:34:56.789Z

# 计算心跳间隔
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
last_heartbeat = datetime.fromisoformat(timeout_state.last_heartbeat)
heartbeat_gap = (now - last_heartbeat).total_seconds()

if heartbeat_gap > 300:  # 5 分钟无心跳
    print("Warning: Task may be stuck or runner crashed")
```

#### 最佳实践

**1. 根据任务特性设置超时**

```python
def create_task_with_timeout(title: str, task_type: str):
    """根据任务类型设置合理的超时时间"""
    timeout_configs = {
        "quick": {"timeout_seconds": 300, "warning_threshold": 0.7},
        "normal": {"timeout_seconds": 1800, "warning_threshold": 0.8},
        "long": {"timeout_seconds": 7200, "warning_threshold": 0.9}
    }

    config = timeout_configs.get(task_type, timeout_configs["normal"])

    return service.create_draft_task(
        title=title,
        metadata={"timeout_config": config}
    )

# 使用示例
quick_task = create_task_with_timeout("Fetch user profile", "quick")
normal_task = create_task_with_timeout("Generate report", "normal")
long_task = create_task_with_timeout("Train ML model", "long")
```

**2. 监控超时趋势**

```python
def get_timeout_statistics():
    """统计超时任务"""
    service = TaskService()

    # 查询所有 FAILED 任务
    failed_tasks = service.list_tasks(status_filter="failed", limit=1000)

    timeout_count = 0
    timeout_tasks = []

    for task in failed_tasks:
        if task.exit_reason == "timeout":
            timeout_count += 1
            timeout_tasks.append({
                "task_id": task.task_id,
                "title": task.title,
                "created_at": task.created_at
            })

    return {
        "total_failed": len(failed_tasks),
        "timeout_count": timeout_count,
        "timeout_rate": timeout_count / len(failed_tasks) if failed_tasks else 0,
        "timeout_tasks": timeout_tasks
    }

stats = get_timeout_statistics()
print(f"Timeout rate: {stats['timeout_rate']:.2%}")
```

**3. 动态调整超时时间**

```python
def adjust_timeout_based_on_history(task_title: str):
    """基于历史数据动态调整超时时间"""
    service = TaskService()

    # 查询相似任务的历史执行时间
    similar_tasks = service.list_tasks(limit=100)
    execution_times = []

    for task in similar_tasks:
        if task.title.startswith(task_title.split()[0]):  # 简单的相似度匹配
            # 从 metadata 中提取实际执行时间
            timeout_state = task.get_timeout_state()
            if timeout_state.execution_start_time:
                # 计算执行时间...
                pass

    if execution_times:
        # 使用 P95 + 20% 作为超时时间
        import statistics
        p95 = statistics.quantiles(execution_times, n=20)[18]  # 95th percentile
        recommended_timeout = int(p95 * 1.2)
    else:
        recommended_timeout = 3600  # 默认值

    return {
        "timeout_config": {
            "enabled": True,
            "timeout_seconds": recommended_timeout,
            "warning_threshold": 0.8
        }
    }
```

### 3.3 Cancel 处理

Cancel 处理支持优雅终止（Graceful Shutdown）和清理操作。

#### cancel_running_task 用法

```python
# 取消正在运行的任务
task = service.cancel_running_task(
    task_id="01HQ7X...",
    actor="admin",
    reason="Emergency maintenance: database migration in progress"
)

print(f"Task {task.task_id} canceled, status: {task.status}")
# 输出: Task 01HQ7X... canceled, status: canceled
```

**内部流程**:

1. **验证状态**: 检查任务是否在 RUNNING 状态
2. **设置标记**: 在 metadata 中设置 cancel 标记
   ```python
   task.metadata["cancel_actor"] = actor
   task.metadata["cancel_reason"] = reason
   task.metadata["cancel_requested_at"] = "2026-01-30T12:00:00Z"
   ```
3. **记录审计**: 记录 `TASK_CANCEL_REQUESTED` 事件
4. **状态转换**: 执行 `RUNNING → CANCELED` 转换
5. **Runner 检测**: TaskRunner 在下次循环检测到 cancel 信号
6. **执行清理**: Runner 调用 CancelHandler 执行清理操作
7. **退出循环**: Runner 设置 `exit_reason = "user_cancelled"` 并退出

#### Graceful Shutdown

Graceful Shutdown 确保任务在取消时正确清理资源。

**清理操作**:

```python
from agentos.core.task.cancel_handler import CancelHandler

cancel_handler = CancelHandler()

# 执行清理操作
cleanup_results = cancel_handler.perform_cleanup(
    task_id="01HQ7X...",
    cleanup_actions=["flush_logs", "release_resources", "save_partial_results"]
)

print(f"Cleanup performed: {cleanup_results['cleanup_performed']}")
# 输出: Cleanup performed: ['flush_logs', 'release_resources', 'save_partial_results']

print(f"Cleanup failed: {cleanup_results['cleanup_failed']}")
# 输出: Cleanup failed: []
```

**默认清理动作**:
1. **flush_logs**: 刷新未写入的日志
2. **release_resources**: 释放占用的资源（文件句柄、网络连接等）
3. **save_partial_results**: 保存部分执行结果（如果有）

**自定义清理动作**:

```python
# 在 TaskRunner 中集成自定义清理
should_cancel, cancel_reason = cancel_handler.should_cancel(task_id, task.status)

if should_cancel:
    # 自定义清理操作
    cleanup_results = cancel_handler.perform_cleanup(
        task_id=task_id,
        cleanup_actions=[
            "flush_logs",
            "release_resources",
            "save_partial_results",
            "rollback_transaction",  # 自定义：回滚数据库事务
            "cleanup_temp_files"     # 自定义：清理临时文件
        ]
    )

    # 记录清理结果
    cancel_handler.record_cancel_event(
        task_id=task_id,
        actor=task.metadata.get("cancel_actor", "unknown"),
        reason=cancel_reason,
        cleanup_results=cleanup_results
    )

    exit_reason = "user_cancelled"
    break
```

#### Cleanup 操作

Cleanup 操作确保任务取消后不会留下"脏"状态。

**设计清理策略**:

```python
def design_cleanup_strategy(task_type: str) -> list:
    """根据任务类型设计清理策略"""
    strategies = {
        "api_task": [
            "flush_logs",
            "release_resources",
            "cancel_pending_requests"
        ],
        "database_task": [
            "flush_logs",
            "rollback_transaction",
            "release_database_locks"
        ],
        "file_task": [
            "flush_logs",
            "close_file_handles",
            "cleanup_temp_files"
        ],
        "ml_task": [
            "flush_logs",
            "save_model_checkpoint",
            "release_gpu_memory"
        ]
    }

    return strategies.get(task_type, [
        "flush_logs",
        "release_resources"
    ])

# 使用示例
cleanup_actions = design_cleanup_strategy("database_task")
cleanup_results = cancel_handler.perform_cleanup(
    task_id="01HQ7X...",
    cleanup_actions=cleanup_actions
)
```

**处理清理失败**:

```python
cleanup_results = cancel_handler.perform_cleanup(
    task_id="01HQ7X...",
    cleanup_actions=["flush_logs", "release_resources", "save_partial_results"]
)

# 检查清理失败
if cleanup_results["cleanup_failed"]:
    print("⚠️ Some cleanup actions failed:")
    for failed in cleanup_results["cleanup_failed"]:
        print(f"  - {failed['action']}: {failed['error']}")

    # 记录告警
    service.add_audit(
        task_id="01HQ7X...",
        event_type="CLEANUP_PARTIAL_FAILURE",
        level="warn",
        payload=cleanup_results
    )
```

#### 最佳实践

**1. 总是提供详细的 Cancel Reason**

```python
# ❌ 不好：原因不明确
service.cancel_running_task(
    task_id="01HQ7X...",
    actor="admin",
    reason="cancel"
)

# ✅ 好：原因明确
service.cancel_running_task(
    task_id="01HQ7X...",
    actor="admin",
    reason="Canceling due to database maintenance window (scheduled 12:00-13:00 UTC)"
)
```

**2. 监控 Cancel 操作**

```python
def monitor_cancellations():
    """监控最近的 cancel 操作"""
    service = TaskService()

    # 查询所有 CANCELED 任务
    canceled_tasks = service.list_tasks(status_filter="canceled", limit=100)

    cancel_stats = {
        "total": len(canceled_tasks),
        "by_actor": {},
        "by_reason": {}
    }

    for task in canceled_tasks:
        # 统计按 actor 分组
        cancel_actor = task.metadata.get("cancel_actor", "unknown")
        cancel_stats["by_actor"][cancel_actor] = cancel_stats["by_actor"].get(cancel_actor, 0) + 1

        # 统计按 reason 分组
        cancel_reason = task.metadata.get("cancel_reason", "unknown")
        cancel_stats["by_reason"][cancel_reason] = cancel_stats["by_reason"].get(cancel_reason, 0) + 1

    return cancel_stats

stats = monitor_cancellations()
print(f"Total cancellations: {stats['total']}")
print(f"Top cancelers: {stats['by_actor']}")
```

**3. 实现 Cancel 超时**

```python
def cancel_with_timeout(task_id: str, timeout_seconds: int = 30):
    """取消任务，并等待 Runner 确认（带超时）"""
    import time
    from datetime import datetime, timezone

    service = TaskService()

    # 1. 发送 cancel 信号
    task = service.cancel_running_task(
        task_id=task_id,
        actor="admin",
        reason="Graceful cancellation with timeout"
    )

    print(f"Cancel signal sent to task {task_id}")

    # 2. 等待 Runner 确认（轮询任务状态）
    start_time = datetime.now(timezone.utc)

    while True:
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

        if elapsed > timeout_seconds:
            print(f"⚠️ Cancel timeout after {timeout_seconds}s, task may still be running")
            break

        # 检查任务状态
        task = service.get_task(task_id)

        # 检查 exit_reason
        if task.exit_reason == "user_cancelled":
            print(f"✓ Task {task_id} canceled successfully after {elapsed:.1f}s")
            break

        time.sleep(1)  # 每秒检查一次

    return task

# 使用示例
cancel_with_timeout("01HQ7X...", timeout_seconds=30)
```

---

## 4. 监控和观测

### 4.1 状态转换审计

每次状态转换都会记录审计日志，包括转换前后的状态、操作者、原因、元数据等。

#### 如何查看转换历史

```python
# 获取任务的完整转换历史
service = TaskService()
history = service.get_transition_history("01HQ7X...")

print(f"Total transitions: {len(history)}")

for entry in history:
    print(f"{entry['from_state']} → {entry['to_state']}")
    print(f"  Actor: {entry['actor']}")
    print(f"  Reason: {entry['reason']}")
    print(f"  Time: {entry['created_at']}")
    print()

# 输出示例:
# Total transitions: 5
#
# draft → approved
#   Actor: manager@example.com
#   Reason: Task reviewed and approved
#   Time: 2026-01-30T10:00:00Z
#
# approved → queued
#   Actor: system
#   Reason: Task queued for execution
#   Time: 2026-01-30T10:01:00Z
#
# queued → running
#   Actor: runner
#   Reason: Task execution started
#   Time: 2026-01-30T10:02:00Z
#
# running → verifying
#   Actor: runner
#   Reason: Task execution completed, starting verification
#   Time: 2026-01-30T10:15:00Z
#
# verifying → verified
#   Actor: verifier
#   Reason: Task verification completed
#   Time: 2026-01-30T10:16:00Z
```

#### Audit 日志格式

审计日志存储在 `task_audits` 表中。

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `audit_id` | INTEGER | 审计记录 ID |
| `task_id` | TEXT | 任务 ID |
| `level` | TEXT | 日志级别（info/warn/error） |
| `event_type` | TEXT | 事件类型（STATE_TRANSITION_*, TASK_RETRY_ATTEMPT 等） |
| `payload` | TEXT | 事件负载（JSON 格式） |
| `created_at` | TEXT | 创建时间（ISO 8601） |

**Payload 结构（状态转换）**:

```json
{
  "from_state": "running",
  "to_state": "verifying",
  "actor": "runner",
  "reason": "Task execution completed, starting verification",
  "transition_metadata": {
    "duration_seconds": 780,
    "work_items_completed": 15
  }
}
```

#### 常见审计事件

| Event Type | Level | 说明 |
|-----------|-------|------|
| `TASK_CREATED` | info | 任务创建 |
| `STATE_TRANSITION_APPROVED` | info | 状态转换为 APPROVED |
| `STATE_TRANSITION_QUEUED` | info | 状态转换为 QUEUED |
| `STATE_TRANSITION_RUNNING` | info | 状态转换为 RUNNING |
| `STATE_TRANSITION_VERIFYING` | info | 状态转换为 VERIFYING |
| `STATE_TRANSITION_VERIFIED` | info | 状态转换为 VERIFIED |
| `STATE_TRANSITION_DONE` | info | 状态转换为 DONE |
| `STATE_TRANSITION_FAILED` | error | 状态转换为 FAILED |
| `STATE_TRANSITION_CANCELED` | warn | 状态转换为 CANCELED |
| `TASK_RETRY_ATTEMPT` | info | Retry 尝试 |
| `TASK_CANCEL_REQUESTED` | warn | Cancel 请求 |
| `TASK_CANCELED_DURING_EXECUTION` | warn | 执行中取消 |
| `CLEANUP_PARTIAL_FAILURE` | warn | 清理操作部分失败 |

**查询特定事件**:

```python
import sqlite3
import json

conn = sqlite3.connect("agentos.db")
cursor = conn.cursor()

# 查询所有 retry 事件
cursor.execute("""
    SELECT task_id, payload, created_at
    FROM task_audits
    WHERE event_type = 'TASK_RETRY_ATTEMPT'
    ORDER BY created_at DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    payload = json.loads(row[1])
    print(f"Task: {row[0]}")
    print(f"  Retry: {payload['retry_count']}/{payload['max_retries']}")
    print(f"  Reason: {payload['reason']}")
    print(f"  Time: {row[2]}")
    print()
```

### 4.2 任务执行指标

#### retry_count 监控

监控任务的重试次数，识别频繁失败的任务。

```python
def get_high_retry_tasks(threshold: int = 3):
    """查找重试次数较多的任务"""
    service = TaskService()

    # 查询所有任务
    tasks = service.list_tasks(limit=1000)

    high_retry_tasks = []

    for task in tasks:
        retry_state = task.get_retry_state()

        if retry_state.retry_count >= threshold:
            high_retry_tasks.append({
                "task_id": task.task_id,
                "title": task.title,
                "retry_count": retry_state.retry_count,
                "status": task.status,
                "retry_reasons": [h["reason"] for h in retry_state.retry_history]
            })

    # 按 retry_count 降序排序
    high_retry_tasks.sort(key=lambda x: x["retry_count"], reverse=True)

    return high_retry_tasks

# 使用示例
tasks = get_high_retry_tasks(threshold=3)
print(f"Found {len(tasks)} tasks with ≥3 retries")

for task in tasks[:10]:  # 显示前 10 个
    print(f"{task['task_id']}: {task['retry_count']} retries")
    print(f"  Title: {task['title']}")
    print(f"  Status: {task['status']}")
    print(f"  Reasons: {', '.join(task['retry_reasons'])}")
    print()
```

#### elapsed_seconds 监控

监控任务执行时间，识别耗时过长的任务。

```python
def get_long_running_tasks(min_duration_seconds: int = 3600):
    """查找执行时间较长的任务"""
    from datetime import datetime, timezone

    service = TaskService()

    # 查询 RUNNING 状态的任务
    running_tasks = service.list_tasks(status_filter="running", limit=1000)

    long_running = []
    now = datetime.now(timezone.utc)

    for task in running_tasks:
        timeout_state = task.get_timeout_state()

        if timeout_state.execution_start_time:
            start_time = datetime.fromisoformat(timeout_state.execution_start_time)
            elapsed = (now - start_time).total_seconds()

            if elapsed >= min_duration_seconds:
                long_running.append({
                    "task_id": task.task_id,
                    "title": task.title,
                    "elapsed_seconds": int(elapsed),
                    "elapsed_hours": elapsed / 3600,
                    "start_time": timeout_state.execution_start_time
                })

    # 按 elapsed_seconds 降序排序
    long_running.sort(key=lambda x: x["elapsed_seconds"], reverse=True)

    return long_running

# 使用示例
tasks = get_long_running_tasks(min_duration_seconds=3600)
print(f"Found {len(tasks)} tasks running ≥1 hour")

for task in tasks[:10]:
    print(f"{task['task_id']}: {task['elapsed_hours']:.1f} hours")
    print(f"  Title: {task['title']}")
    print(f"  Started: {task['start_time']}")
    print()
```

#### exit_reason 统计

统计任务的退出原因，识别常见失败模式。

```python
def get_exit_reason_statistics():
    """统计任务退出原因"""
    service = TaskService()

    # 查询所有终态任务
    terminal_tasks = []
    for status in ["done", "failed", "canceled", "blocked"]:
        terminal_tasks.extend(service.list_tasks(status_filter=status, limit=1000))

    exit_reason_counts = {}

    for task in terminal_tasks:
        reason = task.exit_reason or "unknown"
        exit_reason_counts[reason] = exit_reason_counts.get(reason, 0) + 1

    # 计算百分比
    total = len(terminal_tasks)
    exit_reason_stats = []

    for reason, count in exit_reason_counts.items():
        exit_reason_stats.append({
            "reason": reason,
            "count": count,
            "percentage": (count / total * 100) if total > 0 else 0
        })

    # 按 count 降序排序
    exit_reason_stats.sort(key=lambda x: x["count"], reverse=True)

    return {
        "total_tasks": total,
        "exit_reasons": exit_reason_stats
    }

# 使用示例
stats = get_exit_reason_statistics()
print(f"Total terminal tasks: {stats['total_tasks']}")
print("\nExit reasons:")

for item in stats["exit_reasons"]:
    print(f"  {item['reason']}: {item['count']} ({item['percentage']:.1f}%)")

# 输出示例:
# Total terminal tasks: 1523
#
# Exit reasons:
#   done: 1245 (81.8%)
#   timeout: 142 (9.3%)
#   user_cancelled: 78 (5.1%)
#   max_iterations: 35 (2.3%)
#   fatal_error: 18 (1.2%)
#   blocked: 5 (0.3%)
```

#### 成功率计算

计算任务的成功率指标。

```python
def calculate_success_rate(time_window_hours: int = 24):
    """计算指定时间窗口内的任务成功率"""
    from datetime import datetime, timezone, timedelta

    service = TaskService()

    # 计算时间窗口
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=time_window_hours)

    # 查询所有终态任务
    terminal_tasks = []
    for status in ["done", "failed", "canceled", "blocked"]:
        terminal_tasks.extend(service.list_tasks(status_filter=status, limit=5000))

    # 过滤时间窗口内的任务
    window_tasks = []
    for task in terminal_tasks:
        created_at = datetime.fromisoformat(task.created_at)
        if created_at >= start_time:
            window_tasks.append(task)

    # 统计
    total = len(window_tasks)
    success = sum(1 for t in window_tasks if t.status == "done")
    failed = sum(1 for t in window_tasks if t.status == "failed")
    canceled = sum(1 for t in window_tasks if t.status == "canceled")
    blocked = sum(1 for t in window_tasks if t.status == "blocked")

    return {
        "time_window_hours": time_window_hours,
        "total_tasks": total,
        "success_count": success,
        "failed_count": failed,
        "canceled_count": canceled,
        "blocked_count": blocked,
        "success_rate": (success / total * 100) if total > 0 else 0,
        "failure_rate": (failed / total * 100) if total > 0 else 0
    }

# 使用示例
stats = calculate_success_rate(time_window_hours=24)
print(f"Success rate (last {stats['time_window_hours']} hours):")
print(f"  Total: {stats['total_tasks']}")
print(f"  Success: {stats['success_count']} ({stats['success_rate']:.1f}%)")
print(f"  Failed: {stats['failed_count']} ({stats['failure_rate']:.1f}%)")
print(f"  Canceled: {stats['canceled_count']}")
print(f"  Blocked: {stats['blocked_count']}")
```

### 4.3 失败模式分析

#### 常见失败模式

| 失败模式 | Exit Reason | 症状 | 解决方案 |
|---------|------------|------|---------|
| **Timeout** | `timeout` | 任务执行时间超过限制 | 增加 timeout_seconds 或优化任务逻辑 |
| **Max Iterations** | `max_iterations` | 状态机循环次数过多 | 检查状态转换逻辑，可能存在死循环 |
| **Fatal Error** | `fatal_error` | 任务执行过程中出现致命错误 | 检查任务日志，修复代码 bug |
| **Blocked** | `blocked` | 任务在 AUTONOMOUS 模式下被阻塞 | 人工审批或修改 run_mode |
| **User Cancelled** | `user_cancelled` | 用户主动取消任务 | 无需处理（正常取消） |

#### 如何分析 Retry Pattern

```python
def analyze_retry_pattern(task_id: str):
    """分析任务的 retry 模式"""
    service = TaskService()
    task = service.get_task(task_id)

    retry_state = task.get_retry_state()
    retry_history = retry_state.retry_history

    if not retry_history:
        return {"pattern": "no_retries"}

    # 提取 retry 原因
    reasons = [h["reason"] for h in retry_history]

    # 检测模式
    analysis = {
        "retry_count": len(retry_history),
        "reasons": reasons,
        "unique_reasons": len(set(reasons)),
        "pattern": None,
        "recommendation": None
    }

    # 模式 1: 相同原因重复（循环）
    if analysis["unique_reasons"] == 1:
        analysis["pattern"] = "retry_loop"
        analysis["recommendation"] = "检查根本原因，避免无效重试"

    # 模式 2: 多种原因（随机失败）
    elif analysis["unique_reasons"] == len(reasons):
        analysis["pattern"] = "random_failures"
        analysis["recommendation"] = "任务不稳定，考虑增加 max_retries 或修复不稳定因素"

    # 模式 3: 部分重复（渐进式改善）
    else:
        analysis["pattern"] = "progressive_improvement"
        analysis["recommendation"] = "任务在改善中，继续监控"

    return analysis

# 使用示例
analysis = analyze_retry_pattern("01HQ7X...")
print(f"Retry pattern: {analysis['pattern']}")
print(f"Recommendation: {analysis['recommendation']}")
print(f"Retry reasons: {analysis['reasons']}")
```

#### 如何优化配置

```python
def recommend_retry_config(task_history: list):
    """根据任务历史推荐 retry 配置"""
    from statistics import mean, stdev

    retry_counts = []
    success_with_retry = 0

    for task in task_history:
        retry_state = task.get_retry_state()
        retry_count = retry_state.retry_count

        retry_counts.append(retry_count)

        if task.status == "done" and retry_count > 0:
            success_with_retry += 1

    if not retry_counts:
        return {"max_retries": 3, "backoff_type": "exponential"}

    # 分析
    avg_retries = mean(retry_counts)
    max_retries_observed = max(retry_counts)
    success_with_retry_rate = success_with_retry / len(task_history)

    # 推荐配置
    if success_with_retry_rate > 0.8:
        # 高成功率：retry 有效
        recommended_max_retries = min(max_retries_observed + 2, 10)
        recommended_backoff = "exponential"
    elif success_with_retry_rate > 0.5:
        # 中等成功率：适度 retry
        recommended_max_retries = int(avg_retries * 1.5)
        recommended_backoff = "linear"
    else:
        # 低成功率：减少 retry
        recommended_max_retries = max(1, int(avg_retries))
        recommended_backoff = "fixed"

    return {
        "max_retries": recommended_max_retries,
        "backoff_type": recommended_backoff,
        "analysis": {
            "avg_retries": avg_retries,
            "max_retries_observed": max_retries_observed,
            "success_with_retry_rate": success_with_retry_rate
        }
    }

# 使用示例
# 假设有一组相似任务的历史数据
similar_tasks = service.list_tasks(limit=100)
config = recommend_retry_config(similar_tasks)

print(f"Recommended retry config:")
print(f"  max_retries: {config['max_retries']}")
print(f"  backoff_type: {config['backoff_type']}")
print(f"\nAnalysis:")
print(f"  Average retries: {config['analysis']['avg_retries']:.1f}")
print(f"  Max retries observed: {config['analysis']['max_retries_observed']}")
print(f"  Success with retry: {config['analysis']['success_with_retry_rate']:.1%}")
```

---

## 5. 故障排查

### 5.1 任务卡住

#### 症状识别

- 任务状态长时间停留在 QUEUED 或 RUNNING
- Heartbeat 长时间未更新（>5 分钟）
- 任务无法取消或重试

#### 常见原因

1. **Runner 进程 crash**: Runner 进程异常退出，任务状态未更新
2. **数据库锁**: SQLite 数据库被锁定，无法更新任务状态
3. **死循环**: 任务逻辑存在死循环，无法正常退出
4. **资源耗尽**: 系统资源（CPU、内存、磁盘）耗尽，Runner 无法继续执行
5. **网络阻塞**: 任务等待外部 API 响应，但网络连接已断开

#### 诊断步骤

**步骤 1: 检查任务状态和心跳**

```python
from datetime import datetime, timezone

def diagnose_stuck_task(task_id: str):
    """诊断卡住的任务"""
    service = TaskService()
    task = service.get_task(task_id)

    if not task:
        return {"error": "Task not found"}

    diagnosis = {
        "task_id": task_id,
        "status": task.status,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    }

    # 检查心跳
    timeout_state = task.get_timeout_state()

    if timeout_state.last_heartbeat:
        last_heartbeat = datetime.fromisoformat(timeout_state.last_heartbeat)
        now = datetime.now(timezone.utc)
        heartbeat_gap = (now - last_heartbeat).total_seconds()

        diagnosis["last_heartbeat"] = timeout_state.last_heartbeat
        diagnosis["heartbeat_gap_seconds"] = int(heartbeat_gap)
        diagnosis["heartbeat_status"] = "healthy" if heartbeat_gap < 300 else "stale"
    else:
        diagnosis["last_heartbeat"] = None
        diagnosis["heartbeat_status"] = "no_heartbeat"

    # 检查执行时间
    if timeout_state.execution_start_time:
        start_time = datetime.fromisoformat(timeout_state.execution_start_time)
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        diagnosis["elapsed_seconds"] = int(elapsed)

    # 检查 retry 状态
    retry_state = task.get_retry_state()
    diagnosis["retry_count"] = retry_state.retry_count

    return diagnosis

# 使用示例
result = diagnose_stuck_task("01HQ7X...")
print(f"Task {result['task_id']} diagnosis:")
print(f"  Status: {result['status']}")
print(f"  Heartbeat: {result.get('last_heartbeat', 'N/A')}")
print(f"  Heartbeat gap: {result.get('heartbeat_gap_seconds', 'N/A')}s")
print(f"  Heartbeat status: {result.get('heartbeat_status', 'N/A')}")
print(f"  Elapsed time: {result.get('elapsed_seconds', 'N/A')}s")
```

**步骤 2: 检查 Runner 进程**

```bash
# 查找 Runner 进程
ps aux | grep "task_runner"

# 检查进程状态
ps -p <PID> -o pid,ppid,state,etime,cmd

# 检查系统资源
top -p <PID>
```

**步骤 3: 检查审计日志**

```python
def check_audit_logs(task_id: str, limit: int = 20):
    """检查任务审计日志"""
    import sqlite3
    import json

    conn = sqlite3.connect("agentos.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT event_type, level, payload, created_at
        FROM task_audits
        WHERE task_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (task_id, limit))

    logs = []
    for row in cursor.fetchall():
        logs.append({
            "event_type": row[0],
            "level": row[1],
            "payload": json.loads(row[2]) if row[2] else {},
            "created_at": row[3]
        })

    conn.close()
    return logs

# 使用示例
logs = check_audit_logs("01HQ7X...", limit=10)
print("Recent audit logs:")
for log in logs:
    print(f"[{log['level']}] {log['event_type']} at {log['created_at']}")
    if log['payload']:
        print(f"  Payload: {log['payload']}")
```

#### 解决方案

**方案 1: 重启 Runner**

```bash
# 杀死卡住的 Runner 进程
kill -9 <PID>

# 重新启动 Runner（如果使用 Launcher）
agentos task run <task_id>
```

**方案 2: 手动修复任务状态**

```python
def recover_stuck_task(task_id: str, new_status: str = "failed"):
    """恢复卡住的任务（手动修复状态）"""
    import warnings

    warnings.warn(
        "Manually recovering stuck task. This bypasses state machine validation. "
        "Use only as a last resort.",
        UserWarning
    )

    service = TaskService()
    task = service.get_task(task_id)

    if not task:
        return None

    # 记录恢复操作
    service.add_audit(
        task_id=task_id,
        event_type="MANUAL_RECOVERY",
        level="warn",
        payload={
            "old_status": task.status,
            "new_status": new_status,
            "reason": "Task was stuck, manually recovered"
        }
    )

    # 使用 TaskManager 直接更新状态（绕过状态机）
    task.status = new_status
    task.exit_reason = "manual_recovery"
    service.task_manager.update_task(task)

    print(f"Task {task_id} recovered: {task.status} → {new_status}")
    return task

# 使用示例（谨慎使用！）
recover_stuck_task("01HQ7X...", new_status="failed")
```

**方案 3: 使用 Recovery System（推荐）**

如果启用了 Recovery System（Task #9），可以自动恢复：

```bash
# 运行恢复扫描
agentos recovery scan

# 查看恢复报告
agentos recovery report
```

### 5.2 状态不一致

#### 症状识别

- 任务状态与实际执行情况不符
- 数据库中的状态与 Runner 内存中的状态不同步
- 审计日志缺失或错误

#### 常见原因

1. **并发写入冲突**: 多个 Writer 同时更新任务状态
2. **数据库事务失败**: SQLite 事务回滚，部分更新丢失
3. **Runner crash**: Runner 在状态转换过程中 crash
4. **时钟漂移**: 不同机器的时钟不同步，导致时间戳错误

#### 如何修复

**方法 1: 使用 SQLiteWriter 确保串行化**

SQLiteWriter 已内置，确保所有状态更新都通过它执行：

```python
from agentos.store import get_writer

def safe_state_update(task_id: str, new_status: str):
    """安全的状态更新（通过 SQLiteWriter）"""
    from datetime import datetime, timezone

    def _update(conn):
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?",
            (new_status, now, task_id)
        )

    writer = get_writer()
    writer.submit(_update, timeout=10.0)

    print(f"Task {task_id} status updated to {new_status}")

# 使用示例
safe_state_update("01HQ7X...", "failed")
```

**方法 2: 检查和修复不一致**

```python
def check_state_consistency(task_id: str):
    """检查任务状态一致性"""
    service = TaskService()
    task = service.get_task(task_id)

    if not task:
        return {"error": "Task not found"}

    # 获取最近的状态转换
    history = service.get_transition_history(task_id)

    if not history:
        return {
            "task_id": task_id,
            "current_status": task.status,
            "consistent": True,
            "message": "No state transitions recorded"
        }

    # 检查最近的转换是否与当前状态一致
    latest_transition = history[0]
    expected_status = latest_transition["to_state"]
    actual_status = task.status

    consistent = (expected_status == actual_status)

    return {
        "task_id": task_id,
        "current_status": actual_status,
        "expected_status": expected_status,
        "consistent": consistent,
        "latest_transition": latest_transition
    }

# 使用示例
result = check_state_consistency("01HQ7X...")
if not result["consistent"]:
    print(f"⚠️ State inconsistency detected:")
    print(f"  Current: {result['current_status']}")
    print(f"  Expected: {result['expected_status']}")
    print(f"  Latest transition: {result['latest_transition']}")
```

**方法 3: 重建审计链**

如果审计日志丢失，可以尝试重建：

```python
def rebuild_audit_chain(task_id: str):
    """重建任务审计链（基于当前状态推断）"""
    service = TaskService()
    task = service.get_task(task_id)

    if not task:
        return None

    # 根据当前状态推断可能的转换路径
    state_path = infer_state_path(task.status)

    # 为每个推断的转换创建审计记录
    for i, (from_state, to_state) in enumerate(state_path):
        service.add_audit(
            task_id=task_id,
            event_type=f"STATE_TRANSITION_{to_state.upper()}",
            level="warn",
            payload={
                "from_state": from_state,
                "to_state": to_state,
                "actor": "system",
                "reason": f"Audit chain rebuilt (inferred transition {i+1})",
                "rebuilt": True
            }
        )

    print(f"Rebuilt audit chain for task {task_id}: {len(state_path)} transitions")

def infer_state_path(current_status: str) -> list:
    """推断到达当前状态的可能路径"""
    # 简化示例：根据终态推断路径
    paths = {
        "done": [
            ("draft", "approved"),
            ("approved", "queued"),
            ("queued", "running"),
            ("running", "verifying"),
            ("verifying", "verified"),
            ("verified", "done")
        ],
        "failed": [
            ("draft", "approved"),
            ("approved", "queued"),
            ("queued", "running"),
            ("running", "failed")
        ],
        "canceled": [
            ("draft", "approved"),
            ("approved", "queued"),
            ("queued", "canceled")
        ]
    }
    return paths.get(current_status, [])
```

### 5.3 转换失败

#### 症状识别

- 调用 `service.approve_task()` 等方法时抛出 `InvalidTransitionError`
- 日志中出现 "Transition not allowed" 错误
- 任务卡在中间状态无法继续

#### InvalidTransitionError 分析

```python
from agentos.core.task.errors import InvalidTransitionError

try:
    # 尝试非法转换（例如从 DONE 转换为 RUNNING）
    service.state_machine.transition(
        task_id="01HQ7X...",
        to="running",
        actor="admin",
        reason="Invalid transition attempt"
    )
except InvalidTransitionError as e:
    print(f"Transition failed:")
    print(f"  From: {e.from_state}")
    print(f"  To: {e.to_state}")
    print(f"  Reason: {e.reason}")

# 输出示例:
# Transition failed:
#   From: done
#   To: running
#   Reason: No transition rule defined
```

#### 如何避免

**方法 1: 检查有效转换**

在执行转换前，先检查是否允许：

```python
def safe_transition(task_id: str, to_state: str, actor: str, reason: str):
    """安全的状态转换（带预检查）"""
    service = TaskService()
    task = service.get_task(task_id)

    if not task:
        print(f"Task {task_id} not found")
        return None

    # 检查转换是否有效
    valid_transitions = service.state_machine.get_valid_transitions(task.status)

    if to_state not in valid_transitions:
        print(f"Invalid transition: {task.status} → {to_state}")
        print(f"Valid transitions from {task.status}: {valid_transitions}")
        return None

    # 执行转换
    try:
        updated_task = service.state_machine.transition(
            task_id=task_id,
            to=to_state,
            actor=actor,
            reason=reason
        )
        print(f"Transition successful: {task.status} → {to_state}")
        return updated_task
    except Exception as e:
        print(f"Transition failed: {e}")
        return None

# 使用示例
safe_transition("01HQ7X...", "running", "admin", "Manual start")
```

**方法 2: 使用高级服务方法**

使用 TaskService 提供的高级方法，而不是直接调用 state_machine.transition()：

```python
# ❌ 不推荐：直接使用状态机
service.state_machine.transition(task_id, to="approved", actor="user", reason="...")

# ✅ 推荐：使用业务方法
service.approve_task(task_id, actor="user", reason="...")
```

业务方法会自动验证状态并提供更好的错误信息。

**方法 3: 捕获和处理异常**

```python
def transition_with_error_handling(task_id: str, operation: str):
    """带错误处理的转换"""
    service = TaskService()

    operations = {
        "approve": lambda: service.approve_task(task_id, "admin", "Approved"),
        "queue": lambda: service.queue_task(task_id, "system", "Queued"),
        "start": lambda: service.start_task(task_id, "runner", "Started"),
        "cancel": lambda: service.cancel_task(task_id, "admin", "Canceled")
    }

    op_func = operations.get(operation)
    if not op_func:
        print(f"Unknown operation: {operation}")
        return None

    try:
        task = op_func()
        print(f"✓ {operation.capitalize()} successful: {task.status}")
        return task
    except InvalidTransitionError as e:
        print(f"✗ Cannot {operation}: {e.reason}")
        print(f"  Current state: {e.from_state}")
        return None
    except Exception as e:
        print(f"✗ {operation.capitalize()} failed: {str(e)}")
        return None

# 使用示例
transition_with_error_handling("01HQ7X...", "approve")
```

---

## 6. 性能优化

### 6.1 并发控制

#### 如何限制并发任务数

**方法 1: 使用队列长度限制**

```python
def get_queue_length():
    """获取当前队列长度"""
    service = TaskService()
    queued_tasks = service.list_tasks(status_filter="queued", limit=10000)
    return len(queued_tasks)

def should_accept_new_task(max_queue_length: int = 100) -> bool:
    """检查是否应该接受新任务"""
    current_queue_length = get_queue_length()

    if current_queue_length >= max_queue_length:
        print(f"Queue full ({current_queue_length}/{max_queue_length}), rejecting new task")
        return False

    return True

# 使用示例
if should_accept_new_task(max_queue_length=50):
    task = service.create_approve_queue_and_start(
        title="New task",
        actor="system"
    )
else:
    print("Queue full, please try again later")
```

**方法 2: 使用并发运行限制**

```python
def get_running_task_count():
    """获取当前运行任务数"""
    service = TaskService()
    running_tasks = service.list_tasks(status_filter="running", limit=10000)
    return len(running_tasks)

def can_start_new_task(max_concurrent: int = 10) -> bool:
    """检查是否可以启动新任务"""
    current_running = get_running_task_count()

    if current_running >= max_concurrent:
        print(f"Max concurrent tasks reached ({current_running}/{max_concurrent})")
        return False

    return True

# 使用示例（在任务调度器中使用）
def task_scheduler():
    """任务调度器（限制并发）"""
    service = TaskService()
    max_concurrent = 10

    while True:
        if can_start_new_task(max_concurrent):
            # 从队列中取出任务
            queued_tasks = service.list_tasks(status_filter="queued", limit=1)

            if queued_tasks:
                task = queued_tasks[0]
                # 启动任务（会触发 QUEUED → RUNNING 转换）
                from agentos.core.runner.launcher import launch_task_async
                launch_task_async(task.task_id, actor="scheduler")
                print(f"Started task {task.task_id}")

        time.sleep(5)  # 每 5 秒检查一次
```

#### Worker Pool 配置

AgentOS 使用 Worker Pool 管理任务执行。

**配置 Worker 数量**:

```python
# 在 agentos/core/worker_pool/__init__.py 中配置
WORKER_POOL_SIZE = 10  # 最大并发 Worker 数

# 或通过环境变量配置
import os
os.environ["AGENTOS_WORKER_POOL_SIZE"] = "10"
```

**Worker Pool 指标**:

```python
def get_worker_pool_metrics():
    """获取 Worker Pool 指标"""
    from agentos.core.worker_pool import LeaseManager
    import sqlite3

    conn = sqlite3.connect("agentos.db")
    cursor = conn.cursor()

    # 查询 worker_lease 表
    cursor.execute("""
        SELECT
            COUNT(*) as total_leases,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_leases,
            SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired_leases
        FROM worker_lease
    """)

    row = cursor.fetchone()
    conn.close()

    return {
        "total_leases": row[0],
        "active_leases": row[1],
        "expired_leases": row[2],
        "worker_pool_size": int(os.environ.get("AGENTOS_WORKER_POOL_SIZE", 10))
    }

# 使用示例
metrics = get_worker_pool_metrics()
print(f"Worker Pool metrics:")
print(f"  Pool size: {metrics['worker_pool_size']}")
print(f"  Active leases: {metrics['active_leases']}")
print(f"  Expired leases: {metrics['expired_leases']}")
```

### 6.2 资源限制

#### 内存限制

**监控任务内存使用**:

```python
import psutil
import os

def get_task_memory_usage(pid: int):
    """获取任务内存使用情况"""
    try:
        process = psutil.Process(pid)
        memory_info = process.memory_info()

        return {
            "pid": pid,
            "rss_mb": memory_info.rss / 1024 / 1024,  # 物理内存（MB）
            "vms_mb": memory_info.vms / 1024 / 1024,  # 虚拟内存（MB）
            "percent": process.memory_percent()
        }
    except psutil.NoSuchProcess:
        return {"error": "Process not found"}

# 使用示例
usage = get_task_memory_usage(12345)
print(f"Memory usage (PID {usage['pid']}):")
print(f"  RSS: {usage['rss_mb']:.1f} MB")
print(f"  VMS: {usage['vms_mb']:.1f} MB")
print(f"  Percent: {usage['percent']:.1f}%")
```

**设置内存限制（Linux）**:

```bash
# 使用 ulimit 限制进程内存
ulimit -v 2097152  # 限制为 2GB (2097152 KB)

# 启动 Runner
agentos task run <task_id>
```

#### CPU 限制

**监控 CPU 使用**:

```python
def get_task_cpu_usage(pid: int, interval: float = 1.0):
    """获取任务 CPU 使用情况"""
    try:
        process = psutil.Process(pid)
        cpu_percent = process.cpu_percent(interval=interval)

        return {
            "pid": pid,
            "cpu_percent": cpu_percent,
            "num_threads": process.num_threads()
        }
    except psutil.NoSuchProcess:
        return {"error": "Process not found"}

# 使用示例
usage = get_task_cpu_usage(12345)
print(f"CPU usage (PID {usage['pid']}):")
print(f"  CPU: {usage['cpu_percent']:.1f}%")
print(f"  Threads: {usage['num_threads']}")
```

**使用 CPU 亲和性（Linux）**:

```python
import os

def set_cpu_affinity(pid: int, cpus: list):
    """设置进程 CPU 亲和性"""
    try:
        process = psutil.Process(pid)
        process.cpu_affinity(cpus)
        print(f"Set CPU affinity for PID {pid} to cores: {cpus}")
    except Exception as e:
        print(f"Failed to set CPU affinity: {e}")

# 使用示例：限制任务只在 CPU 0 和 1 上运行
set_cpu_affinity(12345, [0, 1])
```

#### 超时配置

参见 [3.2 Timeout 机制](#32-timeout-机制)。

### 6.3 队列管理

#### 任务优先级

AgentOS 不直接支持任务优先级，但可以通过以下方式实现：

**方法 1: 使用多个队列**

```python
def queue_task_with_priority(task_id: str, priority: str):
    """将任务入队到指定优先级队列"""
    service = TaskService()
    task = service.get_task(task_id)

    if not task:
        return None

    # 在 metadata 中标记优先级
    task.metadata["priority"] = priority
    service.task_manager.update_task(task)

    # 入队
    service.queue_task(task_id, actor="scheduler", reason=f"Queued with {priority} priority")

    return task

# 使用示例
queue_task_with_priority("01HQ7X...", priority="high")
```

**方法 2: 优先级调度器**

```python
def priority_scheduler():
    """优先级任务调度器"""
    service = TaskService()

    while True:
        # 获取所有 QUEUED 任务
        queued_tasks = service.list_tasks(status_filter="queued", limit=1000)

        if not queued_tasks:
            time.sleep(5)
            continue

        # 按优先级排序
        priority_order = {"high": 0, "normal": 1, "low": 2}

        sorted_tasks = sorted(
            queued_tasks,
            key=lambda t: priority_order.get(t.metadata.get("priority", "normal"), 1)
        )

        # 启动最高优先级的任务
        if can_start_new_task(max_concurrent=10):
            task = sorted_tasks[0]
            from agentos.core.runner.launcher import launch_task_async
            launch_task_async(task.task_id, actor="scheduler")
            print(f"Started {task.metadata.get('priority', 'normal')} priority task {task.task_id}")

        time.sleep(5)
```

#### 队列长度监控

```python
def monitor_queue_length():
    """监控队列长度"""
    service = TaskService()

    metrics = {
        "queued": len(service.list_tasks(status_filter="queued", limit=10000)),
        "running": len(service.list_tasks(status_filter="running", limit=10000)),
        "verifying": len(service.list_tasks(status_filter="verifying", limit=10000))
    }

    metrics["total_active"] = metrics["queued"] + metrics["running"] + metrics["verifying"]

    return metrics

# 使用示例
metrics = monitor_queue_length()
print(f"Queue metrics:")
print(f"  Queued: {metrics['queued']}")
print(f"  Running: {metrics['running']}")
print(f"  Verifying: {metrics['verifying']}")
print(f"  Total active: {metrics['total_active']}")

# 设置告警阈值
if metrics["queued"] > 100:
    print("⚠️ Queue length exceeds threshold (100)")
```

**队列长度趋势分析**:

```python
def track_queue_length_trend(duration_minutes: int = 60):
    """跟踪队列长度趋势"""
    import time
    from datetime import datetime

    data_points = []
    interval_seconds = 60  # 每分钟采样一次

    for i in range(duration_minutes):
        metrics = monitor_queue_length()
        data_points.append({
            "timestamp": datetime.now().isoformat(),
            "queued": metrics["queued"],
            "running": metrics["running"]
        })

        print(f"[{i+1}/{duration_minutes}] Queued: {metrics['queued']}, Running: {metrics['running']}")
        time.sleep(interval_seconds)

    # 分析趋势
    avg_queued = sum(d["queued"] for d in data_points) / len(data_points)
    max_queued = max(d["queued"] for d in data_points)

    return {
        "data_points": data_points,
        "avg_queued": avg_queued,
        "max_queued": max_queued
    }

# 使用示例（在后台运行）
# trend = track_queue_length_trend(duration_minutes=60)
```

---

## 附录

### A. 快速参考

#### 常用状态转换

```python
# 创建任务
task = service.create_draft_task(title="...")

# 批准任务
task = service.approve_task(task_id, actor="...", reason="...")

# 入队任务
task = service.queue_task(task_id, actor="...", reason="...")

# 启动任务
task = service.start_task(task_id, actor="...", reason="...")

# 完成任务
task = service.complete_task_execution(task_id, actor="...", reason="...")

# 验证任务
task = service.verify_task(task_id, actor="...", reason="...")

# 标记完成
task = service.mark_task_done(task_id, actor="...", reason="...")

# 标记失败
task = service.fail_task(task_id, actor="...", reason="...")

# 取消任务
task = service.cancel_task(task_id, actor="...", reason="...")

# 重试失败的任务
task = service.retry_failed_task(task_id, actor="...", reason="...")
```

#### 配置示例

```python
# Retry 配置
retry_config = {
    "max_retries": 5,
    "backoff_type": "exponential",
    "base_delay_seconds": 60,
    "max_delay_seconds": 3600
}

# Timeout 配置
timeout_config = {
    "enabled": True,
    "timeout_seconds": 3600,
    "warning_threshold": 0.8
}

# 创建任务时应用配置
task = service.create_draft_task(
    title="...",
    metadata={
        "retry_config": retry_config,
        "timeout_config": timeout_config
    }
)
```

### B. 错误码参考

| 错误类型 | 说明 | 解决方案 |
|---------|------|---------|
| `TaskNotFoundError` | 任务不存在 | 检查 task_id 是否正确 |
| `InvalidTransitionError` | 非法状态转换 | 检查当前状态和目标状态 |
| `RetryNotAllowedError` | 不允许重试 | 检查 retry 配置和 retry 历史 |
| `TaskStateError` | 状态机错误 | 查看错误详情，可能需要手动修复 |

### C. 相关文档

- [Task API Reference](../api/TASK_API_REFERENCE.md)
- [Retry Strategy Guide](RETRY_STRATEGY_GUIDE.md)
- [Timeout Configuration](TIMEOUT_CONFIGURATION.md)
- [Cancel Operations](CANCEL_OPERATIONS.md)
- [V04 Quick Reference](../../docs/V04_QUICK_REFERENCE.md)

---

## 7. 治理与合规

### 7.1 治理概述

AgentOS 状态机集成了 v0.4/3.1 治理体系，确保每个状态迁移都有：

- ✅ **规则验证**：所有转换必须符合转换表规则
- ✅ **审计追踪**：每次转换都记录到 `task_audits` 表
- ✅ **Gate 检查**：关键状态有进入条件保证
- ✅ **可回放性**：完整生命周期可从审计日志重建
- ✅ **可验收性**：所有操作都有可计算的证据

### 7.2 State Entry Gates（状态进入门控）

#### 7.2.1 DONE State Gate

**目的**：确保任务在标记为 DONE 前有完整的审计追踪

**检查规则**：
```python
MIN_AUDIT_EVENTS_FOR_COMPLETION = 2  # 至少：创建 + 一次状态转换
```

**Gate 检查逻辑**：
```python
# 在进入 DONE 状态前检查
audit_count = count_audits(task_id)
if audit_count < MIN_AUDIT_EVENTS_FOR_COMPLETION:
    logger.warning(f"Task {task_id} has insufficient audit trail")
    # 当前只警告，可配置为强制拒绝
```

**如何查看审计日志**：
```python
from agentos.core.task.state_machine import TaskStateMachine

sm = TaskStateMachine()
history = sm.get_transition_history(task_id)

print(f"Total transitions: {len(history)}")
for entry in history:
    print(f"  {entry['from_state']} → {entry['to_state']}")
    print(f"  Actor: {entry['actor']}, Reason: {entry['reason']}")
```

#### 7.2.2 FAILED State Gate

**目的**：确保失败任务必须有明确的 `exit_reason`

**检查规则**：
```python
VALID_EXIT_REASONS = [
    "timeout",           # 任务超时
    "retry_exhausted",   # 重试次数用尽
    "canceled",          # 用户取消
    "exception",         # 未处理异常
    "gate_failed",       # Gate 检查失败
    "user_stopped",      # 用户主动停止
    "fatal_error",       # 致命错误
    "max_iterations",    # 超过最大迭代次数
    "blocked",           # 执行被阻塞
    "unknown",           # 未知原因（兜底）
]
```

**Gate 检查逻辑**：
```python
# 在进入 FAILED 状态前检查
exit_reason = task.metadata.get("exit_reason")
if not exit_reason:
    raise TaskStateError(
        f"Task {task_id} cannot fail without exit_reason"
    )
if exit_reason not in VALID_EXIT_REASONS:
    logger.warning(f"Unknown exit_reason: {exit_reason}")
```

**如何设置 exit_reason**：
```python
# 方法1：在 TaskRunner 中自动设置
task.metadata["exit_reason"] = "timeout"
task_manager.update_task(task)

# 方法2：通过 TaskService
service.fail_task(
    task_id=task_id,
    actor="system",
    reason="Task execution timed out",
    exit_reason="timeout"
)
```

#### 7.2.3 CANCELED State Gate

**目的**：确保取消任务有清理摘要（cleanup_summary）

**检查规则**：
```python
# cleanup_summary schema
{
    "cleanup_performed": [...],   # 已完成的清理操作
    "cleanup_failed": [...],      # 失败的清理操作
    "cleanup_skipped": [...],     # 跳过的清理操作
    "auto_generated": True/False  # 是否自动生成
}
```

**Gate 检查逻辑**：
```python
# 在进入 CANCELED 状态前检查
if "cleanup_summary" not in task.metadata:
    # Auto-create minimal cleanup_summary (permissive gate)
    task.metadata["cleanup_summary"] = {
        "cleanup_performed": [],
        "cleanup_failed": [],
        "cleanup_skipped": ["no cleanup required"],
        "auto_generated": True
    }
```

**如何添加 cleanup_summary**：
```python
# 在 cancel_handler 中
cleanup_summary = {
    "cleanup_performed": ["stopped runner process", "released lease"],
    "cleanup_failed": [],
    "cleanup_skipped": [],
    "auto_generated": False
}

service.cancel_task(
    task_id=task_id,
    actor="user",
    reason="User requested cancellation",
    cleanup_summary=cleanup_summary
)
```

### 7.3 审计日志查询

#### 7.3.1 查看任务的所有审计事件

```python
import sqlite3
import json

def get_all_audits(task_id: str):
    """获取任务的所有审计日志"""
    conn = sqlite3.connect("agentos.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT audit_id, event_type, level, payload, created_at
        FROM task_audits
        WHERE task_id = ?
        ORDER BY created_at ASC
    """, (task_id,))

    audits = []
    for row in cursor.fetchall():
        audits.append({
            "audit_id": row[0],
            "event_type": row[1],
            "level": row[2],
            "payload": json.loads(row[3]) if row[3] else {},
            "created_at": row[4]
        })

    conn.close()
    return audits

# 使用示例
audits = get_all_audits("01HQ7X...")
print(f"Total audit events: {len(audits)}")
for audit in audits:
    print(f"  [{audit['level']}] {audit['event_type']} at {audit['created_at']}")
```

#### 7.3.2 过滤特定类型的审计事件

```python
def get_audits_by_type(task_id: str, event_type: str):
    """获取特定类型的审计日志"""
    conn = sqlite3.connect("agentos.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT audit_id, event_type, level, payload, created_at
        FROM task_audits
        WHERE task_id = ? AND event_type LIKE ?
        ORDER BY created_at ASC
    """, (task_id, f"%{event_type}%"))

    audits = []
    for row in cursor.fetchall():
        audits.append({
            "audit_id": row[0],
            "event_type": row[1],
            "level": row[2],
            "payload": json.loads(row[3]) if row[3] else {},
            "created_at": row[4]
        })

    conn.close()
    return audits

# 使用示例：查看所有状态转换
transitions = get_audits_by_type("01HQ7X...", "STATE_TRANSITION")
print(f"Total state transitions: {len(transitions)}")
for t in transitions:
    payload = t['payload']
    print(f"  {payload['from_state']} → {payload['to_state']}")
    print(f"    Actor: {payload['actor']}, Reason: {payload['reason']}")
```

#### 7.3.3 统计审计日志

```python
def audit_statistics(task_id: str):
    """生成任务的审计统计报告"""
    conn = sqlite3.connect("agentos.db")
    cursor = conn.cursor()

    # 总事件数
    cursor.execute(
        "SELECT COUNT(*) FROM task_audits WHERE task_id = ?",
        (task_id,)
    )
    total_events = cursor.fetchone()[0]

    # 按类型统计
    cursor.execute("""
        SELECT event_type, COUNT(*) as count
        FROM task_audits
        WHERE task_id = ?
        GROUP BY event_type
        ORDER BY count DESC
    """, (task_id,))

    event_types = {}
    for row in cursor.fetchall():
        event_types[row[0]] = row[1]

    # 按级别统计
    cursor.execute("""
        SELECT level, COUNT(*) as count
        FROM task_audits
        WHERE task_id = ?
        GROUP BY level
    """, (task_id,))

    levels = {}
    for row in cursor.fetchall():
        levels[row[0]] = row[1]

    conn.close()

    return {
        "total_events": total_events,
        "by_type": event_types,
        "by_level": levels
    }

# 使用示例
stats = audit_statistics("01HQ7X...")
print(f"Total Events: {stats['total_events']}")
print(f"By Type: {stats['by_type']}")
print(f"By Level: {stats['by_level']}")
```

### 7.4 任务生命周期回放

使用 `replay_task_lifecycle.py` 工具回放任务的完整生命周期：

#### 7.4.1 基本用法

```bash
# 文本格式回放（默认）
python scripts/replay_task_lifecycle.py <task_id>

# JSON 格式输出
python scripts/replay_task_lifecycle.py <task_id> --format json

# 包含任务摘要
python scripts/replay_task_lifecycle.py <task_id> --summary
```

#### 7.4.2 输出示例

```
================================================================================
Task Lifecycle Replay: 01HQ7X...
================================================================================

Total Events: 12

[1] 2026-01-30T10:15:23.456Z
    Event: STATE_TRANSITION_APPROVED
    Level: info
    Transition: DRAFT → APPROVED
    Actor: user:alice
    Reason: Task approved for execution

[2] 2026-01-30T10:15:24.123Z
    Event: STATE_TRANSITION_QUEUED
    Level: info
    Transition: APPROVED → QUEUED
    Actor: system:runner
    Reason: Task queued for execution

[3] 2026-01-30T10:15:25.789Z
    Event: STATE_TRANSITION_RUNNING
    Level: info
    Transition: QUEUED → RUNNING
    Actor: system:runner
    Reason: Task execution started

...

[12] 2026-01-30T10:20:45.123Z
    Event: STATE_TRANSITION_DONE
    Level: info
    Transition: VERIFIED → DONE
    Actor: system:runner
    Reason: Task marked as done

================================================================================
```

#### 7.4.3 编程方式回放

```python
from scripts.replay_task_lifecycle import replay_task_lifecycle

# 获取时间线
timeline = replay_task_lifecycle("01HQ7X...")

# 分析时间线
state_transitions = [
    event for event in timeline
    if "STATE_TRANSITION" in event["event_type"]
]

print(f"Task went through {len(state_transitions)} state transitions")

# 计算生命周期时长
if timeline:
    start_time = timeline[0]["timestamp"]
    end_time = timeline[-1]["timestamp"]
    print(f"Lifecycle: {start_time} → {end_time}")
```

### 7.5 合规性验证

#### 7.5.1 验证任务是否符合治理规范

```python
def validate_task_compliance(task_id: str) -> Dict[str, Any]:
    """验证任务是否符合治理规范"""
    from agentos.core.task import TaskManager
    from agentos.core.task.state_machine import TaskStateMachine

    tm = TaskManager()
    sm = TaskStateMachine()

    task = tm.get_task(task_id)
    if not task:
        return {"compliant": False, "reason": "Task not found"}

    issues = []

    # 检查1：审计日志完整性
    history = sm.get_transition_history(task_id)
    if len(history) < 2:
        issues.append(f"Insufficient audit trail: {len(history)} events")

    # 检查2：终态任务必须有 exit_reason
    if task.status in ["failed", "canceled", "blocked"]:
        exit_reason = task.metadata.get("exit_reason")
        if not exit_reason:
            issues.append(f"Terminal state '{task.status}' missing exit_reason")

    # 检查3：CANCELED 任务必须有 cleanup_summary
    if task.status == "canceled":
        cleanup_summary = task.metadata.get("cleanup_summary")
        if not cleanup_summary:
            issues.append("CANCELED state missing cleanup_summary")

    # 检查4：状态转换是否合法（通过回放验证）
    for i in range(len(history) - 1):
        from_state = history[i]["to_state"]
        to_state = history[i+1]["to_state"]
        if not sm.can_transition(from_state, to_state):
            issues.append(f"Invalid transition detected: {from_state} → {to_state}")

    return {
        "compliant": len(issues) == 0,
        "issues": issues,
        "audit_events": len(history),
        "task_status": task.status
    }

# 使用示例
result = validate_task_compliance("01HQ7X...")
if result["compliant"]:
    print("✅ Task is compliant with governance rules")
else:
    print("❌ Task has compliance issues:")
    for issue in result["issues"]:
        print(f"  - {issue}")
```

#### 7.5.2 批量合规性扫描

```python
def scan_compliance(limit: int = 100) -> Dict[str, Any]:
    """批量扫描任务的合规性"""
    from agentos.core.task import TaskManager

    tm = TaskManager()
    tasks = tm.list_tasks(limit=limit)

    compliant_count = 0
    non_compliant_tasks = []

    for task in tasks:
        result = validate_task_compliance(task.task_id)
        if result["compliant"]:
            compliant_count += 1
        else:
            non_compliant_tasks.append({
                "task_id": task.task_id,
                "status": task.status,
                "issues": result["issues"]
            })

    return {
        "total_tasks": len(tasks),
        "compliant_count": compliant_count,
        "non_compliant_count": len(non_compliant_tasks),
        "compliance_rate": compliant_count / len(tasks) if tasks else 0,
        "non_compliant_tasks": non_compliant_tasks
    }

# 使用示例
report = scan_compliance(limit=50)
print(f"Compliance Rate: {report['compliance_rate']*100:.1f}%")
print(f"Non-compliant Tasks: {report['non_compliant_count']}")
```

### 7.6 治理最佳实践

#### 7.6.1 始终通过 TaskService 操作状态

```python
# ✅ 推荐：使用 TaskService（经过治理检查）
from agentos.core.task.service import TaskService

service = TaskService()
service.approve_task(task_id, actor="user:alice", reason="Ready to execute")
service.queue_task(task_id, actor="system", reason="Queued for execution")

# ❌ 不推荐：直接使用 TaskManager（绕过治理）
from agentos.core.task import TaskManager
tm = TaskManager()
tm.update_task_status(task_id, "approved")  # 这会触发 DeprecationWarning
```

#### 7.6.2 为关键操作添加审计日志

```python
# 在执行重要操作前后记录审计
service.add_audit(
    task_id=task_id,
    event_type="CRITICAL_OPERATION_START",
    level="info",
    payload={"operation": "data_export", "user": "alice"}
)

# ... 执行操作 ...

service.add_audit(
    task_id=task_id,
    event_type="CRITICAL_OPERATION_COMPLETE",
    level="info",
    payload={"operation": "data_export", "records_exported": 1000}
)
```

#### 7.6.3 失败任务必须设置 exit_reason

```python
# 在 TaskRunner 或 executor 中
try:
    # ... 执行任务 ...
except TimeoutError:
    task.metadata["exit_reason"] = "timeout"
    service.fail_task(task_id, actor="system", reason="Task execution timed out")
except Exception as e:
    task.metadata["exit_reason"] = "exception"
    task.metadata["exception_type"] = type(e).__name__
    service.fail_task(task_id, actor="system", reason=f"Unhandled exception: {e}")
```

#### 7.6.4 取消任务时提供 cleanup_summary

```python
# 在 cancel_handler 中
cleanup_summary = {
    "cleanup_performed": [
        "stopped runner process (PID 12345)",
        "released worker lease",
        "rolled back partial changes"
    ],
    "cleanup_failed": [],
    "cleanup_skipped": ["no temp files to clean"]
}

service.cancel_task(
    task_id=task_id,
    actor="user:alice",
    reason="User requested cancellation",
    cleanup_summary=cleanup_summary
)
```

### 7.7 治理指标

#### 7.7.1 关键指标

| 指标 | 说明 | 目标值 |
|-----|------|-------|
| 审计覆盖率 | 所有任务都有审计日志 | 100% |
| Gate 通过率 | 进入关键状态时 Gate 检查通过率 | > 95% |
| Exit Reason 覆盖率 | FAILED 任务有 exit_reason | 100% |
| Cleanup 覆盖率 | CANCELED 任务有 cleanup_summary | 100% |
| 合规率 | 通过合规性验证的任务比例 | > 98% |

#### 7.7.2 监控查询

```sql
-- 审计覆盖率
SELECT
    (SELECT COUNT(DISTINCT task_id) FROM task_audits) * 1.0 /
    (SELECT COUNT(*) FROM tasks) as audit_coverage_rate;

-- Exit Reason 覆盖率（FAILED 任务）
SELECT
    SUM(CASE WHEN json_extract(metadata, '$.exit_reason') IS NOT NULL THEN 1 ELSE 0 END) * 1.0 /
    COUNT(*) as exit_reason_coverage_rate
FROM tasks
WHERE status = 'failed';

-- Cleanup Summary 覆盖率（CANCELED 任务）
SELECT
    SUM(CASE WHEN json_extract(metadata, '$.cleanup_summary') IS NOT NULL THEN 1 ELSE 0 END) * 1.0 /
    COUNT(*) as cleanup_coverage_rate
FROM tasks
WHERE status = 'canceled';

-- 状态转换统计
SELECT
    event_type,
    COUNT(*) as transition_count
FROM task_audits
WHERE event_type LIKE 'STATE_TRANSITION_%'
GROUP BY event_type
ORDER BY transition_count DESC;
```

### 7.8 治理故障排查

#### 7.8.1 Gate 检查失败

**问题**：任务无法进入 FAILED 状态，报错"cannot fail without exit_reason"

**解决方案**：
```python
# 添加 exit_reason
task = tm.get_task(task_id)
task.metadata["exit_reason"] = "exception"  # 或其他有效原因
tm.update_task(task)

# 然后重试状态转换
service.fail_task(task_id, actor="system", reason="...")
```

#### 7.8.2 审计日志缺失

**问题**：任务没有审计日志或日志不完整

**诊断**：
```python
audits = get_all_audits(task_id)
print(f"Total audits: {len(audits)}")
if len(audits) == 0:
    print("⚠️ No audit logs found. Task may have been created before audit system.")
```

**解决方案**：
```python
# 补充审计日志（仅用于历史数据修复）
service.add_audit(
    task_id=task_id,
    event_type="AUDIT_BACKFILL",
    level="info",
    payload={"reason": "Historical audit backfill", "backfilled_at": "2026-01-30"}
)
```

#### 7.8.3 合规性扫描发现问题

**问题**：批量扫描发现大量任务不合规

**分析步骤**：
```python
report = scan_compliance(limit=100)
print(f"Non-compliant: {report['non_compliant_count']}")

# 按问题类型分组
issue_types = {}
for task_info in report['non_compliant_tasks']:
    for issue in task_info['issues']:
        issue_type = issue.split(':')[0]
        issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

print("Issue breakdown:")
for issue_type, count in sorted(issue_types.items(), key=lambda x: -x[1]):
    print(f"  {issue_type}: {count} tasks")
```

**批量修复**：
```python
def batch_fix_missing_exit_reason(task_ids: List[str]):
    """批量修复缺失的 exit_reason"""
    for task_id in task_ids:
        task = tm.get_task(task_id)
        if task and task.status == "failed" and not task.metadata.get("exit_reason"):
            task.metadata["exit_reason"] = "unknown"  # 兜底值
            tm.update_task(task)
            print(f"Fixed {task_id}: added exit_reason='unknown'")
```

---

## 附录

### A. 配置示例

```python
# Retry 配置
retry_config = {
    "max_retries": 5,
    "backoff_type": "exponential",
    "base_delay_seconds": 60,
    "max_delay_seconds": 3600
}

# Timeout 配置
timeout_config = {
    "enabled": True,
    "timeout_seconds": 3600,
    "warning_threshold": 0.8
}

# 创建任务时应用配置
task = service.create_draft_task(
    title="...",
    metadata={
        "retry_config": retry_config,
        "timeout_config": timeout_config
    }
)
```

### B. 错误码参考

| 错误类型 | 说明 | 解决方案 |
|---------|------|---------|
| `TaskNotFoundError` | 任务不存在 | 检查 task_id 是否正确 |
| `InvalidTransitionError` | 非法状态转换 | 检查当前状态和目标状态 |
| `RetryNotAllowedError` | 不允许重试 | 检查 retry 配置和 retry 历史 |
| `TaskStateError` | 状态机错误 | 查看错误详情，可能需要手动修复 |

### C. 相关文档

- [Task API Reference](../api/TASK_API_REFERENCE.md)
- [Retry Strategy Guide](RETRY_STRATEGY_GUIDE.md)
- [Timeout Configuration](TIMEOUT_CONFIGURATION.md)
- [Cancel Operations](CANCEL_OPERATIONS.md)
- [V04 Quick Reference](../../docs/V04_QUICK_REFERENCE.md)
- [Replay Task Lifecycle](../../scripts/replay_task_lifecycle.py) 🆕

---

**文档结束**

如有问题或建议，请联系开发团队或提交 Issue。
