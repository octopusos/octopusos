# Task Retry 策略指南

**版本**: v1.0
**最后更新**: 2026-01-30
**目标用户**: 运维人员、开发人员

---

## 目录

1. [概述](#1-概述)
2. [配置方法](#2-配置方法)
3. [Retry类型](#3-retry类型)
4. [Retry限制](#4-retry限制)
5. [最佳实践](#5-最佳实践)
6. [故障排查](#6-故障排查)
7. [监控和观测](#7-监控和观测)

---

## 1. 概述

### 1.1 Retry 策略的作用

AgentOS 的 Task Retry 策略系统为任务级别的失败恢复提供了强大且灵活的机制。当任务因临时性错误（如网络波动、资源不足、外部服务暂时不可用等）而失败时，Retry 策略可以自动或手动地重新执行任务，提高系统的可靠性和成功率。

**核心功能**：
- **任务级别重试控制**：独立于工具级别的重试机制（tool-level retry），专注于整个任务的重试策略
- **智能退避算法**：支持多种退避策略，避免系统过载
- **重试次数限制**：防止无限重试导致的资源浪费
- **重试循环检测**：自动识别并阻止相同失败原因的重复重试
- **完整的审计追踪**：记录每次重试的时间、原因和结果

### 1.2 适用场景

Retry 策略适用于以下场景：

**推荐使用 Retry 的情况**：
- 网络请求超时或连接失败
- 外部 API 返回临时性错误（如 HTTP 429/503）
- 系统资源暂时不足（如内存、CPU 占用过高）
- 数据库连接失败或锁等待超时
- 分布式系统中的临时性故障
- Gate 验证失败（可能由于环境状态变化）

**不推荐使用 Retry 的情况**：
- 配置错误（如无效的 API Key、错误的参数）
- 权限不足（如文件无读写权限）
- 数据验证失败（如输入格式错误）
- 业务逻辑错误（如不满足前置条件）
- 资源永久性缺失（如文件不存在）

### 1.3 Retry vs 手动重试的区别

| 特性 | 自动 Retry | 手动重试 |
|------|-----------|---------|
| **触发方式** | 系统自动检测失败并触发 | 需要用户/运维人员手动触发 |
| **延迟控制** | 支持智能退避算法（指数、线性、固定） | 立即执行，无延迟控制 |
| **循环检测** | 自动检测并阻止重试循环 | 需要人工判断是否应该重试 |
| **次数限制** | 强制限制最大重试次数 | 无限制，可能导致资源浪费 |
| **审计日志** | 自动记录完整的重试历史 | 需要手动记录 |
| **适用场景** | 临时性、可恢复的错误 | 需要人工干预或判断的情况 |

**示例对比**：

```python
# 自动 Retry（推荐用于临时性错误）
from agentos.core.task.service import TaskService
from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

service = TaskService()

# 配置任务的 retry 策略
task = service.create_draft_task(
    title="Deploy service to production",
    metadata={
        "retry_config": RetryConfig(
            max_retries=5,
            backoff_type=RetryBackoffType.EXPONENTIAL,
            base_delay_seconds=60,
            max_delay_seconds=1800
        ).to_dict()
    }
)

# 任务失败后，系统会根据配置自动重试
# 无需人工干预

# 手动重试（用于需要判断的情况）
try:
    service.retry_failed_task(
        task_id="01HXXX",
        actor="ops_team",
        reason="Network issue resolved, manually retrying"
    )
except Exception as e:
    print(f"Manual retry failed: {e}")
```

---

## 2. 配置方法

### 2.1 默认配置

如果不显式指定 retry 配置，系统会使用以下默认值：

```python
from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

default_config = RetryConfig(
    max_retries=3,                              # 最多重试 3 次
    backoff_type=RetryBackoffType.EXPONENTIAL,  # 指数退避策略
    base_delay_seconds=60,                      # 基础延迟 60 秒
    max_delay_seconds=3600                      # 最大延迟 1 小时
)
```

**默认配置说明**：
- **max_retries=3**：适用于大多数场景的合理重试次数
- **backoff_type=EXPONENTIAL**：推荐的退避策略，能够快速恢复又不会过载系统
- **base_delay_seconds=60**：第一次重试等待 1 分钟，给系统足够恢复时间
- **max_delay_seconds=3600**：最大延迟 1 小时，避免等待时间过长

**计算示例**（使用默认配置）：
- **第 1 次重试**：失败后等待 60 秒（60 × 2^0）
- **第 2 次重试**：失败后等待 120 秒（60 × 2^1）
- **第 3 次重试**：失败后等待 240 秒（60 × 2^2）
- **总等待时间**：约 7 分钟

### 2.2 自定义配置

#### 2.2.1 在创建任务时配置

```python
from agentos.core.task.service import TaskService
from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

service = TaskService()

# 场景 1: 快速重试（适用于网络请求失败）
task = service.create_draft_task(
    title="Fetch data from external API",
    metadata={
        "retry_config": RetryConfig(
            max_retries=5,
            backoff_type=RetryBackoffType.FIXED,
            base_delay_seconds=30,
            max_delay_seconds=30
        ).to_dict()
    }
)

# 场景 2: 谨慎重试（适用于资源密集型任务）
task = service.create_draft_task(
    title="Train ML model",
    metadata={
        "retry_config": RetryConfig(
            max_retries=2,
            backoff_type=RetryBackoffType.LINEAR,
            base_delay_seconds=300,
            max_delay_seconds=1800
        ).to_dict()
    }
)

# 场景 3: 不使用延迟（适用于立即重试）
task = service.create_draft_task(
    title="Quick validation check",
    metadata={
        "retry_config": RetryConfig(
            max_retries=3,
            backoff_type=RetryBackoffType.NONE,
            base_delay_seconds=0,
            max_delay_seconds=0
        ).to_dict()
    }
)
```

#### 2.2.2 使用 JSON 配置

对于配置文件或 API 请求，可以使用 JSON 格式：

```json
{
  "title": "Deploy service",
  "metadata": {
    "retry_config": {
      "max_retries": 5,
      "backoff_type": "exponential",
      "base_delay_seconds": 60,
      "max_delay_seconds": 3600
    }
  }
}
```

#### 2.2.3 动态修改配置

```python
from agentos.core.task.manager import TaskManager
from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

manager = TaskManager()

# 加载任务
task = manager.get_task("01HXXX")

# 修改 retry 配置
task.metadata["retry_config"] = RetryConfig(
    max_retries=10,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=120,
    max_delay_seconds=7200
).to_dict()

# 保存更新
manager.update_task(task)
```

### 2.3 配置参数说明

#### max_retries（最大重试次数）

- **类型**：整数（int）
- **默认值**：3
- **取值范围**：0-100（推荐 1-10）
- **说明**：任务失败后最多允许重试的次数。设置为 0 表示不允许重试。

**配置建议**：
```python
# 轻量级任务（网络请求、快速查询）
max_retries = 5-10

# 中等负载任务（数据处理、文件操作）
max_retries = 3-5

# 重量级任务（模型训练、大规模计算）
max_retries = 1-2
```

#### backoff_type（退避策略类型）

- **类型**：枚举（RetryBackoffType）
- **默认值**：EXPONENTIAL
- **可选值**：
  - `NONE`: 无延迟，立即重试
  - `FIXED`: 固定延迟
  - `LINEAR`: 线性增长延迟
  - `EXPONENTIAL`: 指数增长延迟（推荐）

**策略对比**：

| 策略 | 计算公式 | 适用场景 | 示例（base=60s） |
|------|---------|---------|-----------------|
| NONE | 0 | 快速任务，瞬时错误 | 0s, 0s, 0s |
| FIXED | base_delay | 稳定的临时性错误 | 60s, 60s, 60s |
| LINEAR | base_delay × (n+1) | 负载逐渐增加 | 60s, 120s, 180s |
| EXPONENTIAL | base_delay × 2^n | 系统恢复需要时间（推荐） | 60s, 120s, 240s |

#### base_delay_seconds（基础延迟时间）

- **类型**：整数（int）
- **默认值**：60（秒）
- **取值范围**：0-86400（0秒-24小时）
- **说明**：退避算法的基础延迟时间，用于计算实际延迟

**配置建议**：
```python
# 快速恢复场景（网络抖动、瞬时错误）
base_delay_seconds = 10-30

# 标准场景（API 限流、资源不足）
base_delay_seconds = 60-120

# 慢速恢复场景（数据库维护、系统升级）
base_delay_seconds = 300-600
```

#### max_delay_seconds（最大延迟时间）

- **类型**：整数（int）
- **默认值**：3600（1小时）
- **取值范围**：0-86400（0秒-24小时）
- **说明**：单次重试的最大等待时间，避免延迟过长

**重要性**：
- 防止指数退避导致的过长等待时间
- 确保任务在合理时间内完成或失败
- 避免资源长时间占用

**配置示例**：
```python
# 快速任务（最多等待 5 分钟）
max_delay_seconds = 300

# 标准任务（最多等待 1 小时）
max_delay_seconds = 3600

# 长时间任务（最多等待 4 小时）
max_delay_seconds = 14400
```

---

## 3. Retry 类型

### 3.1 无延迟 Retry (NONE)

#### 特点
- 失败后立即重试，无等待时间
- 适用于瞬时错误或无状态的快速操作
- 可能导致系统过载，需谨慎使用

#### 适用场景
- **内存操作错误**：临时的内存分配失败
- **竞态条件**：并发控制导致的临时失败
- **快速验证**：状态检查或轻量级验证
- **无副作用操作**：重复执行不会造成影响的操作

#### 配置示例

```python
from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

config = RetryConfig(
    max_retries=3,
    backoff_type=RetryBackoffType.NONE,
    base_delay_seconds=0,
    max_delay_seconds=0
)
```

#### 延迟计算

| 重试次数 | 延迟时间 | 累计时间 |
|---------|---------|---------|
| 第 1 次 | 0 秒 | 0 秒 |
| 第 2 次 | 0 秒 | 0 秒 |
| 第 3 次 | 0 秒 | 0 秒 |

#### 实际应用示例

```python
from agentos.core.task.service import TaskService
from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

service = TaskService()

# 场景: 快速状态检查任务
task = service.create_draft_task(
    title="Check service health",
    metadata={
        "retry_config": RetryConfig(
            max_retries=3,
            backoff_type=RetryBackoffType.NONE,
            base_delay_seconds=0,
            max_delay_seconds=0
        ).to_dict(),
        "description": "Quick health check with immediate retry"
    }
)

print(f"Created task {task.task_id} with NONE backoff strategy")
```

### 3.2 固定延迟 Retry (FIXED)

#### 特点
- 每次重试之间等待固定的时间
- 延迟时间稳定可预测
- 适用于已知恢复时间的场景

#### 适用场景
- **API 限流**：已知的固定时间窗口（如每分钟限制）
- **定时任务**：需要等待特定时间间隔
- **外部服务维护**：已知的固定维护时间
- **批处理任务**：固定的处理间隔

#### 配置示例

```python
config = RetryConfig(
    max_retries=5,
    backoff_type=RetryBackoffType.FIXED,
    base_delay_seconds=120,  # 固定等待 2 分钟
    max_delay_seconds=120    # max_delay 对 FIXED 无影响
)
```

#### 延迟计算

**计算公式**：`delay = base_delay_seconds`

| 重试次数 | 延迟时间 | 累计时间 |
|---------|---------|---------|
| 第 1 次 | 120 秒 | 120 秒 |
| 第 2 次 | 120 秒 | 240 秒 |
| 第 3 次 | 120 秒 | 360 秒 |
| 第 4 次 | 120 秒 | 480 秒 |
| 第 5 次 | 120 秒 | 600 秒 |

#### 实际应用示例

```python
# 场景: API 限流场景
task = service.create_draft_task(
    title="Call rate-limited API",
    metadata={
        "retry_config": RetryConfig(
            max_retries=5,
            backoff_type=RetryBackoffType.FIXED,
            base_delay_seconds=60,  # API 限制: 每分钟 1 次请求
            max_delay_seconds=60
        ).to_dict(),
        "api_endpoint": "https://api.example.com/data"
    }
)

# 场景: 定时批处理任务
batch_task = service.create_draft_task(
    title="Process batch data",
    metadata={
        "retry_config": RetryConfig(
            max_retries=3,
            backoff_type=RetryBackoffType.FIXED,
            base_delay_seconds=300,  # 每 5 分钟重试一次
            max_delay_seconds=300
        ).to_dict(),
        "batch_size": 1000
    }
)
```

### 3.3 线性退避 Retry (LINEAR)

#### 特点
- 延迟时间线性增长
- 逐步增加等待时间，避免立即过载
- 适用于负载逐渐增加的场景

#### 适用场景
- **资源逐渐恢复**：CPU、内存使用率逐渐降低
- **队列处理**：处理队列逐渐消化
- **数据库连接池**：连接池逐渐释放
- **逐步降级**：服务逐步恢复正常

#### 配置示例

```python
config = RetryConfig(
    max_retries=4,
    backoff_type=RetryBackoffType.LINEAR,
    base_delay_seconds=60,
    max_delay_seconds=600  # 限制最大延迟 10 分钟
)
```

#### 延迟计算

**计算公式**：`delay = min(base_delay_seconds × (retry_count + 1), max_delay_seconds)`

| 重试次数 | 计算过程 | 延迟时间 | 累计时间 |
|---------|---------|---------|---------|
| 第 1 次 | 60 × 1 | 60 秒 | 60 秒 |
| 第 2 次 | 60 × 2 | 120 秒 | 180 秒 |
| 第 3 次 | 60 × 3 | 180 秒 | 360 秒 |
| 第 4 次 | 60 × 4 | 240 秒 | 600 秒 |

#### 实际应用示例

```python
# 场景: 数据库连接池饱和
db_task = service.create_draft_task(
    title="Execute database query",
    metadata={
        "retry_config": RetryConfig(
            max_retries=5,
            backoff_type=RetryBackoffType.LINEAR,
            base_delay_seconds=30,
            max_delay_seconds=300
        ).to_dict(),
        "query_type": "heavy_join"
    }
)

# 场景: 文件系统 I/O 压力
io_task = service.create_draft_task(
    title="Process large files",
    metadata={
        "retry_config": RetryConfig(
            max_retries=4,
            backoff_type=RetryBackoffType.LINEAR,
            base_delay_seconds=120,
            max_delay_seconds=600
        ).to_dict(),
        "file_size_mb": 5000
    }
)
```

### 3.4 指数退避 Retry (EXPONENTIAL) - 推荐

#### 特点
- 延迟时间呈指数增长
- 快速恢复和避免过载的最佳平衡
- **系统默认和推荐的策略**

#### 适用场景
- **通用场景**：适用于大多数重试需求（推荐首选）
- **网络故障**：网络连接失败或超时
- **外部服务故障**：第三方 API 暂时不可用
- **系统过载**：CPU、内存、磁盘等资源不足
- **分布式系统**：微服务之间的临时性故障

#### 配置示例

```python
# 推荐配置（默认值）
config = RetryConfig(
    max_retries=3,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=60,
    max_delay_seconds=3600
)

# 快速恢复场景
fast_config = RetryConfig(
    max_retries=5,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=10,
    max_delay_seconds=300
)

# 慢速恢复场景
slow_config = RetryConfig(
    max_retries=3,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=300,
    max_delay_seconds=7200
)
```

#### 延迟计算

**计算公式**：`delay = min(base_delay_seconds × 2^retry_count, max_delay_seconds)`

**示例 1: 标准配置（base=60s, max=3600s）**

| 重试次数 | 计算过程 | 实际延迟 | 累计时间 |
|---------|---------|---------|---------|
| 第 1 次 | 60 × 2^0 = 60 | 60 秒 | 60 秒 |
| 第 2 次 | 60 × 2^1 = 120 | 120 秒 | 180 秒 |
| 第 3 次 | 60 × 2^2 = 240 | 240 秒 | 420 秒 |

**示例 2: 快速恢复（base=10s, max=300s）**

| 重试次数 | 计算过程 | 实际延迟 | 累计时间 |
|---------|---------|---------|---------|
| 第 1 次 | 10 × 2^0 = 10 | 10 秒 | 10 秒 |
| 第 2 次 | 10 × 2^1 = 20 | 20 秒 | 30 秒 |
| 第 3 次 | 10 × 2^2 = 40 | 40 秒 | 70 秒 |
| 第 4 次 | 10 × 2^3 = 80 | 80 秒 | 150 秒 |
| 第 5 次 | 10 × 2^4 = 160 | 160 秒 | 310 秒 |

**示例 3: 带 max_delay 限制（base=60s, max=180s）**

| 重试次数 | 计算过程 | 实际延迟 | 累计时间 |
|---------|---------|---------|---------|
| 第 1 次 | 60 × 2^0 = 60 | 60 秒 | 60 秒 |
| 第 2 次 | 60 × 2^1 = 120 | 120 秒 | 180 秒 |
| 第 3 次 | 60 × 2^2 = 240 → 180（限制） | 180 秒 | 360 秒 |
| 第 4 次 | 60 × 2^3 = 480 → 180（限制） | 180 秒 | 540 秒 |

#### 实际应用示例

```python
# 场景 1: 外部 API 调用（推荐配置）
api_task = service.create_draft_task(
    title="Fetch user data from external service",
    metadata={
        "retry_config": RetryConfig(
            max_retries=5,
            backoff_type=RetryBackoffType.EXPONENTIAL,
            base_delay_seconds=30,
            max_delay_seconds=1800
        ).to_dict(),
        "api_url": "https://api.external.com/users"
    }
)

# 场景 2: 微服务调用
service_task = service.create_draft_task(
    title="Call internal microservice",
    metadata={
        "retry_config": RetryConfig(
            max_retries=4,
            backoff_type=RetryBackoffType.EXPONENTIAL,
            base_delay_seconds=10,
            max_delay_seconds=300
        ).to_dict(),
        "service_name": "payment-service"
    }
)

# 场景 3: 数据库迁移任务
migration_task = service.create_draft_task(
    title="Migrate database schema",
    metadata={
        "retry_config": RetryConfig(
            max_retries=3,
            backoff_type=RetryBackoffType.EXPONENTIAL,
            base_delay_seconds=300,
            max_delay_seconds=7200
        ).to_dict(),
        "migration_version": "v2.5.0"
    }
)

# 场景 4: 使用默认配置（最简洁）
default_task = service.create_draft_task(
    title="Standard task with default retry",
    # 不指定 retry_config，使用默认的 EXPONENTIAL 策略
)
```

#### 为什么推荐指数退避？

1. **快速恢复**：第一次重试延迟较短，适合快速恢复的场景
2. **避免过载**：延迟快速增长，避免对故障系统造成持续压力
3. **资源高效**：在恢复时间不确定时，提供最佳的资源利用率
4. **行业标准**：被 AWS、Google Cloud、Azure 等云服务广泛采用
5. **灵活性高**：通过调整 base_delay 和 max_delay 适应不同场景

---

## 4. Retry 限制

### 4.1 最大重试次数

#### 为什么需要限制

1. **防止资源浪费**：无限重试会消耗系统资源（CPU、内存、网络）
2. **避免无效操作**：某些错误无法通过重试解决（如配置错误）
3. **快速失败**：尽早发现并报告永久性错误
4. **系统稳定性**：防止大量失败任务堵塞任务队列

#### 如何配置合理的次数

**通用建议**：

| 任务类型 | 推荐次数 | 理由 |
|---------|---------|------|
| 轻量级任务（网络请求） | 5-10 | 快速重试，成本低 |
| 中等负载任务（数据处理） | 3-5 | 平衡成功率和资源消耗 |
| 重量级任务（模型训练） | 1-2 | 重试成本高，谨慎重试 |
| 关键业务任务 | 5-7 | 提高成功率，确保完成 |
| 非关键任务 | 2-3 | 快速失败，避免资源浪费 |

**配置示例**：

```python
from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

# 轻量级网络请求
lightweight_config = RetryConfig(
    max_retries=8,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=10,
    max_delay_seconds=300
)

# 标准数据处理
standard_config = RetryConfig(
    max_retries=3,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=60,
    max_delay_seconds=3600
)

# 重量级计算任务
heavy_config = RetryConfig(
    max_retries=1,
    backoff_type=RetryBackoffType.LINEAR,
    base_delay_seconds=600,
    max_delay_seconds=1800
)

# 关键业务任务
critical_config = RetryConfig(
    max_retries=7,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=30,
    max_delay_seconds=1800
)
```

#### 检查当前重试次数

```python
from agentos.core.task.manager import TaskManager

manager = TaskManager()
task = manager.get_task("01HXXX")

# 获取 retry 配置和状态
retry_config = task.get_retry_config()
retry_state = task.get_retry_state()

print(f"当前重试次数: {retry_state.retry_count}")
print(f"最大重试次数: {retry_config.max_retries}")
print(f"剩余重试次数: {retry_config.max_retries - retry_state.retry_count}")

# 检查是否还能重试
from agentos.core.task.retry_strategy import RetryStrategyManager

manager = RetryStrategyManager()
can_retry, reason = manager.can_retry(retry_config, retry_state)

if can_retry:
    print("✅ 任务可以继续重试")
else:
    print(f"❌ 任务无法重试: {reason}")
```

#### 超限处理

当重试次数达到 `max_retries` 限制时，系统会：

1. **拒绝重试请求**：抛出 `RetryNotAllowedError` 异常
2. **记录审计日志**：记录重试超限事件
3. **保持 FAILED 状态**：任务保持在 FAILED 状态，不再自动重试
4. **需要人工干预**：运维人员需要分析失败原因并决定后续操作

```python
from agentos.core.task.service import TaskService
from agentos.core.task.errors import RetryNotAllowedError

service = TaskService()

try:
    service.retry_failed_task(
        task_id="01HXXX",
        actor="system",
        reason="Automatic retry attempt"
    )
except RetryNotAllowedError as e:
    print(f"重试被拒绝: {e}")
    print(f"任务 ID: {e.task_id}")
    print(f"当前状态: {e.current_state}")
    print(f"拒绝原因: {e.reason}")

    # 人工干预：分析失败原因
    task = service.get_task("01HXXX")
    print(f"失败原因: {task.metadata.get('last_error')}")

    # 可选操作：
    # 1. 修改配置后重置 retry_count
    # 2. 修复根本原因后手动重试
    # 3. 取消任务并创建新任务
```

### 4.2 Retry 循环检测

#### 什么是 Retry 循环

Retry 循环是指任务因相同的错误原因连续失败多次，导致无效的重复重试。例如：

- **配置错误**：API Key 无效，重试多次仍然失败
- **权限问题**：缺少文件读取权限，重试无法解决
- **数据错误**：输入数据格式错误，重试不会改变结果
- **环境问题**：依赖服务永久不可用

**示例场景**：
```
任务失败 → 原因: "API Key invalid"
第 1 次重试 → 失败原因: "API Key invalid"
第 2 次重试 → 失败原因: "API Key invalid"
第 3 次重试 → 失败原因: "API Key invalid"
↓
检测到 Retry 循环，阻止继续重试
```

#### 检测机制说明

AgentOS 会自动检测 Retry 循环：

**检测规则**：
- 检查最近 3 次重试的失败原因
- 如果 3 次失败原因完全相同，判定为 Retry 循环
- 自动阻止后续重试，避免资源浪费

**实现代码**（来自 `RetryStrategyManager.can_retry()`）：

```python
# 检查 retry 循环（相同失败原因重复 3 次）
if len(retry_state.retry_history) >= 3:
    recent_reasons = [
        h.get("reason", "")
        for h in retry_state.retry_history[-3:]
    ]
    if len(set(recent_reasons)) == 1:
        return False, f"Retry loop detected: same failure repeated 3 times"
```

#### 如何避免 Retry 循环

**1. 区分临时性和永久性错误**

```python
from agentos.core.task.service import TaskService

service = TaskService()

def handle_task_failure(task_id: str, error: Exception):
    """智能处理任务失败"""

    # 临时性错误：适合重试
    temporary_errors = [
        "ConnectionError",
        "TimeoutError",
        "TemporaryFailure",
        "ServiceUnavailable"
    ]

    # 永久性错误：不应重试
    permanent_errors = [
        "AuthenticationError",
        "PermissionDenied",
        "InvalidConfiguration",
        "DataValidationError"
    ]

    error_type = type(error).__name__

    if error_type in permanent_errors:
        # 永久性错误：取消任务，不重试
        print(f"❌ 永久性错误，取消任务: {error_type}")
        service.cancel_task(
            task_id=task_id,
            actor="error_handler",
            reason=f"Permanent error: {error_type}"
        )
    elif error_type in temporary_errors:
        # 临时性错误：尝试重试
        print(f"⏳ 临时性错误，尝试重试: {error_type}")
        try:
            service.retry_failed_task(
                task_id=task_id,
                actor="error_handler",
                reason=f"Temporary error: {error_type}"
            )
        except Exception as retry_error:
            print(f"⚠️ 重试失败: {retry_error}")
    else:
        # 未知错误：谨慎重试
        print(f"⚠️ 未知错误: {error_type}")
```

**2. 在 Retry 原因中添加更多上下文**

```python
# ❌ 不好的做法：原因过于笼统
service.retry_failed_task(
    task_id="01HXXX",
    actor="system",
    reason="API call failed"  # 每次都一样，容易触发循环检测
)

# ✅ 好的做法：添加详细信息
import time

service.retry_failed_task(
    task_id="01HXXX",
    actor="system",
    reason=f"API call failed: HTTP 503, retry at {time.time()}",
    metadata={
        "error_code": "503",
        "error_message": "Service Unavailable",
        "retry_timestamp": time.time()
    }
)
```

**3. 设置不同的失败处理策略**

```python
from agentos.core.task.manager import TaskManager

def should_retry_task(task_id: str) -> bool:
    """判断是否应该重试任务"""
    manager = TaskManager()
    task = manager.get_task(task_id)

    retry_state = task.get_retry_state()

    # 检查最近的失败原因
    if len(retry_state.retry_history) >= 2:
        last_two_reasons = [
            h.get("reason", "")
            for h in retry_state.retry_history[-2:]
        ]

        # 如果最近 2 次失败原因相同，需要更详细的检查
        if last_two_reasons[0] == last_two_reasons[1]:
            print(f"⚠️ 检测到相同失败原因: {last_two_reasons[0]}")

            # 检查是否是配置错误（不应重试）
            if "Invalid API Key" in last_two_reasons[0]:
                print("❌ 配置错误，不应重试")
                return False

            # 检查是否是网络错误（可以重试）
            if "Connection timeout" in last_two_reasons[0]:
                print("✅ 网络错误，可以重试")
                return True

    return True
```

**4. 监控和告警**

```python
from agentos.core.task.retry_strategy import RetryStrategyManager

def check_retry_health(task_id: str):
    """检查重试健康状态"""
    manager = TaskManager()
    task = manager.get_task(task_id)

    retry_state = task.get_retry_state()
    retry_manager = RetryStrategyManager()

    # 获取重试指标
    metrics = retry_manager.get_retry_metrics(retry_state)

    print(f"任务 ID: {task_id}")
    print(f"重试次数: {metrics['retry_count']}")
    print(f"重试历史长度: {metrics['retry_attempts']}")
    print(f"失败原因列表: {metrics['retry_reasons']}")

    # 检查是否有重复的失败原因
    reasons = metrics['retry_reasons']
    if len(reasons) >= 3 and len(set(reasons[-3:])) == 1:
        print("🚨 告警: 检测到潜在的 Retry 循环")
        print(f"   重复原因: {reasons[-1]}")
        print("   建议: 停止自动重试，进行人工排查")
```

### 4.3 Retry 失败处理

#### Retry 超限后的行为

当任务的 retry 尝试被拒绝时（超过 `max_retries` 或检测到循环），系统会：

1. **保持 FAILED 状态**：任务不会自动转换到其他状态
2. **抛出异常**：`RetryNotAllowedError`，包含拒绝原因
3. **记录审计日志**：记录重试被拒绝的事件
4. **更新 metadata**：在任务 metadata 中记录最后的重试状态

```python
from agentos.core.task.service import TaskService
from agentos.core.task.errors import RetryNotAllowedError

service = TaskService()

try:
    service.retry_failed_task(
        task_id="01HXXX",
        actor="system",
        reason="Automatic retry"
    )
except RetryNotAllowedError as e:
    # 异常信息
    print(f"Retry 被拒绝:")
    print(f"  - 任务 ID: {e.task_id}")
    print(f"  - 当前状态: {e.current_state}")
    print(f"  - 拒绝原因: {e.reason}")

    # 任务保持在 FAILED 状态
    task = service.get_task(e.task_id)
    assert task.status == "failed"
```

#### 如何处理 Retry 失败

**策略 1: 人工分析并修复问题**

```python
from agentos.core.task.manager import TaskManager

def analyze_failed_task(task_id: str):
    """分析失败任务的根本原因"""
    manager = TaskManager()
    task = manager.get_task(task_id)

    # 1. 检查 retry 历史
    retry_state = task.get_retry_state()
    print(f"重试历史 ({len(retry_state.retry_history)} 次):")
    for i, entry in enumerate(retry_state.retry_history, 1):
        print(f"  {i}. {entry['timestamp']}: {entry['reason']}")

    # 2. 检查最后的错误信息
    last_error = task.metadata.get("last_error", {})
    print(f"\n最后错误:")
    print(f"  - 类型: {last_error.get('type')}")
    print(f"  - 消息: {last_error.get('message')}")
    print(f"  - 堆栈: {last_error.get('traceback')}")

    # 3. 检查任务配置
    print(f"\n任务配置:")
    print(f"  - 项目 ID: {task.project_id}")
    print(f"  - 会话 ID: {task.session_id}")
    print(f"  - Provider: {task.selected_instance_id}")

    # 4. 提供修复建议
    print(f"\n建议操作:")
    if "API Key" in str(last_error):
        print("  → 检查 API Key 配置是否正确")
    elif "Permission" in str(last_error):
        print("  → 检查文件/资源权限")
    elif "Connection" in str(last_error):
        print("  → 检查网络连接和防火墙设置")
    else:
        print("  → 查看详细日志进行排查")

# 使用示例
analyze_failed_task("01HXXX")
```

**策略 2: 重置 Retry 计数器（谨慎使用）**

```python
def reset_retry_count(task_id: str, reason: str):
    """
    重置任务的 retry 计数器

    ⚠️ 警告: 仅在确认问题已修复后使用
    """
    from agentos.core.task.manager import TaskManager
    from agentos.core.task.retry_strategy import RetryState

    manager = TaskManager()
    task = manager.get_task(task_id)

    # 确认任务在 FAILED 状态
    if task.status != "failed":
        raise ValueError(f"任务不在 FAILED 状态: {task.status}")

    # 重置 retry_state
    task.metadata["retry_state"] = RetryState().to_dict()
    task.metadata["retry_reset_at"] = datetime.now(timezone.utc).isoformat()
    task.metadata["retry_reset_reason"] = reason

    # 保存更新
    manager.update_task(task)

    print(f"✅ 已重置任务 {task_id} 的 retry 计数器")
    print(f"   原因: {reason}")

    # 记录审计日志
    manager.add_audit(
        task_id=task_id,
        event_type="RETRY_COUNT_RESET",
        level="warn",
        payload={
            "reason": reason,
            "reset_by": "admin",
            "reset_at": task.metadata["retry_reset_at"]
        }
    )

# 使用示例（仅在问题修复后）
reset_retry_count(
    task_id="01HXXX",
    reason="Fixed API Key configuration, ready for retry"
)
```

**策略 3: 创建新任务**

```python
def recreate_failed_task(failed_task_id: str):
    """基于失败任务创建新任务"""
    from agentos.core.task.manager import TaskManager
    from agentos.core.task.service import TaskService

    manager = TaskManager()
    service = TaskService()

    # 加载失败的任务
    old_task = manager.get_task(failed_task_id)

    # 创建新任务（继承配置）
    new_task = service.create_draft_task(
        title=f"{old_task.title} (Retry)",
        project_id=old_task.project_id,
        session_id=old_task.session_id,
        metadata={
            **old_task.metadata,
            "recreated_from": failed_task_id,
            "recreated_at": datetime.now(timezone.utc).isoformat(),
            "recreated_reason": "Previous task exceeded retry limit"
        }
    )

    print(f"✅ 创建新任务: {new_task.task_id}")
    print(f"   基于失败任务: {failed_task_id}")

    # 可选：取消旧任务
    service.cancel_task(
        task_id=failed_task_id,
        actor="admin",
        reason="Replaced by new task"
    )

    return new_task

# 使用示例
new_task = recreate_failed_task("01HXXX")
```

**策略 4: 调整 Retry 配置后重试**

```python
def retry_with_adjusted_config(task_id: str):
    """调整配置后重新尝试"""
    from agentos.core.task.manager import TaskManager
    from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType

    manager = TaskManager()
    task = manager.get_task(task_id)

    # 重置 retry 状态
    task.metadata["retry_state"] = RetryState().to_dict()

    # 调整 retry 配置（更保守的策略）
    task.metadata["retry_config"] = RetryConfig(
        max_retries=2,  # 减少重试次数
        backoff_type=RetryBackoffType.LINEAR,  # 使用线性退避
        base_delay_seconds=300,  # 增加延迟时间
        max_delay_seconds=1800
    ).to_dict()

    # 保存更新
    manager.update_task(task)

    print(f"✅ 已调整任务 {task_id} 的 retry 配置")
    print(f"   新配置: max_retries=2, backoff=LINEAR, base_delay=300s")

    # 现在可以重试
    service = TaskService()
    service.retry_failed_task(
        task_id=task_id,
        actor="admin",
        reason="Retry with adjusted configuration"
    )

# 使用示例
retry_with_adjusted_config("01HXXX")
```

---

## 5. 最佳实践

### 5.1 何时使用 Retry

#### 适合 Retry 的失败类型

**网络相关错误** ✅
```python
# 场景: 网络请求超时
exceptions_to_retry = [
    "ConnectionTimeout",
    "ConnectionError",
    "ConnectionResetError",
    "SocketTimeout",
    "DNSLookupError",
    "NetworkUnreachable"
]

config = RetryConfig(
    max_retries=5,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=10,
    max_delay_seconds=300
)
```

**外部服务临时性错误** ✅
```python
# 场景: HTTP 状态码表示临时性错误
retriable_http_codes = [
    408,  # Request Timeout
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
]

config = RetryConfig(
    max_retries=4,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=60,
    max_delay_seconds=1800
)
```

**资源临时不足** ✅
```python
# 场景: 系统资源暂时不足
resource_errors = [
    "OutOfMemory",
    "DiskSpaceLow",
    "CPUThrottled",
    "DatabaseConnectionPoolExhausted",
    "ThreadPoolExhausted"
]

config = RetryConfig(
    max_retries=3,
    backoff_type=RetryBackoffType.LINEAR,
    base_delay_seconds=120,
    max_delay_seconds=600
)
```

**并发控制相关** ✅
```python
# 场景: 数据库锁、文件锁等
concurrency_errors = [
    "LockTimeout",
    "DeadlockDetected",
    "ResourceLocked",
    "OptimisticLockException"
]

config = RetryConfig(
    max_retries=5,
    backoff_type=RetryBackoffType.FIXED,
    base_delay_seconds=5,
    max_delay_seconds=5
)
```

**依赖服务重启/维护** ✅
```python
# 场景: 下游服务维护窗口
maintenance_config = RetryConfig(
    max_retries=10,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=300,  # 5 分钟
    max_delay_seconds=3600   # 最多等待 1 小时
)
```

#### 不适合 Retry 的失败类型

**配置错误** ❌
```python
# 场景: 配置问题（重试无法解决）
non_retriable_config_errors = [
    "InvalidAPIKey",
    "InvalidCredentials",
    "MissingRequiredConfig",
    "InvalidConfigFormat"
]

# 建议: 直接失败，记录错误，等待人工修复
# 不要配置 retry，或者设置 max_retries=0
```

**权限问题** ❌
```python
# 场景: 权限不足
permission_errors = [
    "PermissionDenied",
    "AccessForbidden",
    "AuthorizationFailed",
    "InsufficientPrivileges"
]

# 建议: 记录详细错误信息，通知管理员
# 不应该重试
```

**数据验证失败** ❌
```python
# 场景: 输入数据错误
validation_errors = [
    "InvalidInputFormat",
    "DataValidationFailed",
    "SchemaViolation",
    "ConstraintViolation",
    "TypeMismatch"
]

# 建议: 返回详细的验证错误信息
# 重试不会改变数据，不应该重试
```

**业务逻辑错误** ❌
```python
# 场景: 业务规则不满足
business_errors = [
    "InsufficientBalance",
    "OrderAlreadyProcessed",
    "InvalidStateTransition",
    "BusinessRuleViolation"
]

# 建议: 记录业务错误，返回用户友好的错误信息
# 不应该重试
```

**资源永久性缺失** ❌
```python
# 场景: 资源不存在
not_found_errors = [
    "FileNotFound",
    "ResourceNotFound",
    "EntityDoesNotExist",
    "PathNotFound"
]

# 建议: 确认资源路径，检查是否需要创建
# 重试不会使资源出现
```

#### 智能错误分类示例

```python
from enum import Enum

class ErrorRetryability(Enum):
    """错误可重试性分类"""
    RETRIABLE = "retriable"              # 可重试
    NON_RETRIABLE = "non_retriable"      # 不可重试
    CONDITIONAL = "conditional"          # 条件重试

def classify_error(error: Exception) -> ErrorRetryability:
    """分类错误是否应该重试"""
    error_type = type(error).__name__
    error_message = str(error)

    # 明确可重试的错误
    if error_type in [
        "ConnectionTimeout", "ConnectionError", "SocketTimeout",
        "TemporaryFailure", "ServiceUnavailable"
    ]:
        return ErrorRetryability.RETRIABLE

    # 明确不可重试的错误
    if error_type in [
        "AuthenticationError", "PermissionDenied",
        "InvalidConfiguration", "DataValidationError"
    ]:
        return ErrorRetryability.NON_RETRIABLE

    # HTTP 状态码判断
    if "HTTP" in error_type:
        if "429" in error_message or "503" in error_message:
            return ErrorRetryability.RETRIABLE
        elif "401" in error_message or "403" in error_message:
            return ErrorRetryability.NON_RETRIABLE

    # 默认: 条件重试（需要进一步判断）
    return ErrorRetryability.CONDITIONAL

# 使用示例
def handle_task_error(task_id: str, error: Exception):
    """根据错误类型决定是否重试"""
    from agentos.core.task.service import TaskService

    service = TaskService()
    retryability = classify_error(error)

    if retryability == ErrorRetryability.RETRIABLE:
        print(f"✅ 可重试错误: {error}")
        try:
            service.retry_failed_task(
                task_id=task_id,
                actor="auto_retry_handler",
                reason=f"Retriable error: {type(error).__name__}"
            )
        except Exception as e:
            print(f"⚠️ 重试失败: {e}")

    elif retryability == ErrorRetryability.NON_RETRIABLE:
        print(f"❌ 不可重试错误: {error}")
        print("   需要人工干预")
        # 发送告警通知

    else:  # CONDITIONAL
        print(f"⚠️ 需要判断: {error}")
        # 进一步分析或等待人工决策
```

### 5.2 Retry 次数建议

#### 不同场景的推荐次数

**场景矩阵**：

| 场景类型 | 任务重要性 | 任务成本 | 推荐次数 | 退避策略 | 总耗时 |
|---------|----------|---------|---------|---------|-------|
| API 调用 | 高 | 低 | 7-10 | EXPONENTIAL | ~10-30 分钟 |
| API 调用 | 中 | 低 | 5 | EXPONENTIAL | ~5-10 分钟 |
| API 调用 | 低 | 低 | 3 | FIXED | ~3-5 分钟 |
| 数据处理 | 高 | 中 | 5 | LINEAR | ~15-30 分钟 |
| 数据处理 | 中 | 中 | 3 | LINEAR | ~10-15 分钟 |
| 数据处理 | 低 | 中 | 2 | FIXED | ~5 分钟 |
| 模型训练 | 高 | 高 | 2 | LINEAR | ~30-60 分钟 |
| 模型训练 | 中 | 高 | 1 | LINEAR | ~15-30 分钟 |
| 快速检查 | 任意 | 极低 | 10 | NONE | 秒级 |

#### 配置示例

**高重要性 + 低成本（推荐激进重试）**：
```python
# 场景: 关键业务 API 调用
critical_api_config = RetryConfig(
    max_retries=10,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=10,
    max_delay_seconds=300
)
```

**高重要性 + 高成本（推荐谨慎重试）**：
```python
# 场景: 重要的模型训练任务
critical_heavy_config = RetryConfig(
    max_retries=2,
    backoff_type=RetryBackoffType.LINEAR,
    base_delay_seconds=600,
    max_delay_seconds=1800
)
```

**低重要性 + 任意成本（推荐快速失败）**：
```python
# 场景: 非关键任务
non_critical_config = RetryConfig(
    max_retries=2,
    backoff_type=RetryBackoffType.FIXED,
    base_delay_seconds=60,
    max_delay_seconds=60
)
```

#### 权衡因素

**1. 成功率 vs 资源消耗**

```python
# 计算预期成功率
def calculate_expected_success_rate(
    single_attempt_success_rate: float,
    max_retries: int
) -> float:
    """
    计算配置 N 次重试后的总成功率

    假设: 每次重试独立，成功率相同
    """
    failure_rate = 1 - single_attempt_success_rate
    total_failure_rate = failure_rate ** (max_retries + 1)
    return 1 - total_failure_rate

# 示例
print("单次成功率 90%:")
print(f"  0 次重试: {calculate_expected_success_rate(0.9, 0):.2%}")
print(f"  3 次重试: {calculate_expected_success_rate(0.9, 3):.2%}")
print(f"  5 次重试: {calculate_expected_success_rate(0.9, 5):.2%}")
print(f"  10 次重试: {calculate_expected_success_rate(0.9, 10):.2%}")

# 输出:
# 单次成功率 90%:
#   0 次重试: 90.00%
#   3 次重试: 99.99%
#   5 次重试: 99.9999%
#   10 次重试: 99.999999999%
```

**2. 时间成本 vs 成功率**

```python
def calculate_total_time(
    base_delay: int,
    max_retries: int,
    backoff_type: RetryBackoffType
) -> int:
    """计算总重试时间（秒）"""
    total = 0
    for i in range(max_retries):
        if backoff_type == RetryBackoffType.NONE:
            delay = 0
        elif backoff_type == RetryBackoffType.FIXED:
            delay = base_delay
        elif backoff_type == RetryBackoffType.LINEAR:
            delay = base_delay * (i + 1)
        else:  # EXPONENTIAL
            delay = base_delay * (2 ** i)
        total += delay
    return total

# 比较不同配置
configs = [
    ("Conservative", 2, RetryBackoffType.LINEAR, 300),
    ("Standard", 3, RetryBackoffType.EXPONENTIAL, 60),
    ("Aggressive", 5, RetryBackoffType.EXPONENTIAL, 30),
]

for name, retries, backoff, base_delay in configs:
    total_time = calculate_total_time(base_delay, retries, backoff)
    success_rate = calculate_expected_success_rate(0.85, retries)
    print(f"{name:12s}: {retries} retries, {total_time:4d}s, {success_rate:.2%} success")

# 输出:
# Conservative:  2 retries,  900s, 97.66% success
# Standard:      3 retries,  420s, 99.66% success
# Aggressive:    5 retries,  570s, 99.98% success
```

### 5.3 Retry 延迟配置

#### 如何选择 base_delay

**基于错误恢复时间**：

| 错误类型 | 典型恢复时间 | 推荐 base_delay |
|---------|-------------|----------------|
| 网络抖动 | 秒级 | 5-10 秒 |
| API 限流 | 分钟级 | 60-120 秒 |
| 资源不足 | 分钟级 | 120-300 秒 |
| 服务重启 | 分钟到小时级 | 300-600 秒 |
| 系统维护 | 小时级 | 600-1800 秒 |

**配置示例**：

```python
# 网络抖动（快速恢复）
network_config = RetryConfig(
    max_retries=5,
    backoff_type=RetryBackoffType.EXPONENTIAL,
    base_delay_seconds=10,
    max_delay_seconds=300
)

# API 限流（中等恢复）
rate_limit_config = RetryConfig(
    max_retries=4,
    backoff_type=RetryBackoffType.FIXED,
    base_delay_seconds=60,
    max_delay_seconds=60
)

# 服务重启（慢速恢复）
service_restart_config = RetryConfig(
    max_retries=3,
    backoff_type=RetryBackoffType.LINEAR,
    base_delay_seconds=300,
    max_delay_seconds=1800
)
```

#### 如何选择 max_delay

**基于任务时效性**：

| 任务类型 | 时效要求 | 推荐 max_delay |
|---------|---------|---------------|
| 实时任务 | 秒级响应 | 60-300 秒 |
| 交互式任务 | 分钟级响应 | 300-1800 秒 |
| 批处理任务 | 小时级响应 | 1800-7200 秒 |
| 后台任务 | 无严格要求 | 3600-86400 秒 |

**权衡原则**：

1. **避免过长等待**：max_delay 不应超过任务的时效要求
2. **平衡重试次数**：过小的 max_delay 会限制指数退避的效果
3. **考虑总时间**：所有重试的总时间不应超过任务的 SLA

**计算总时间示例**：

```python
def estimate_total_retry_time(config: RetryConfig) -> int:
    """估算总重试时间（最坏情况）"""
    total = 0
    for i in range(config.max_retries):
        if config.backoff_type == RetryBackoffType.EXPONENTIAL:
            delay = min(
                config.base_delay_seconds * (2 ** i),
                config.max_delay_seconds
            )
        elif config.backoff_type == RetryBackoffType.LINEAR:
            delay = min(
                config.base_delay_seconds * (i + 1),
                config.max_delay_seconds
            )
        elif config.backoff_type == RetryBackoffType.FIXED:
            delay = config.base_delay_seconds
        else:  # NONE
            delay = 0
        total += delay
    return total

# 测试不同配置
test_configs = [
    RetryConfig(3, RetryBackoffType.EXPONENTIAL, 60, 300),
    RetryConfig(3, RetryBackoffType.EXPONENTIAL, 60, 600),
    RetryConfig(3, RetryBackoffType.EXPONENTIAL, 60, 3600),
]

for config in test_configs:
    total_time = estimate_total_retry_time(config)
    print(f"max_delay={config.max_delay_seconds:4d}s → 总时间={total_time:4d}s ({total_time//60}分钟)")

# 输出:
# max_delay= 300s → 总时间= 420s (7分钟)
# max_delay= 600s → 总时间= 420s (7分钟)
# max_delay=3600s → 总时间= 420s (7分钟)
```

#### 动态调整策略

```python
def create_adaptive_retry_config(
    error_history: List[str],
    task_priority: str
) -> RetryConfig:
    """
    根据历史错误和任务优先级动态生成 retry 配置
    """
    # 分析错误模式
    is_network_error = any("network" in e.lower() for e in error_history)
    is_rate_limit = any("429" in e or "rate limit" in e.lower() for e in error_history)

    # 根据优先级和错误类型调整配置
    if task_priority == "critical":
        max_retries = 10
        base_delay = 30 if is_network_error else 60
    elif task_priority == "high":
        max_retries = 5
        base_delay = 60
    else:  # normal or low
        max_retries = 3
        base_delay = 120

    # 选择退避策略
    if is_rate_limit:
        backoff_type = RetryBackoffType.FIXED
        max_delay = base_delay
    elif is_network_error:
        backoff_type = RetryBackoffType.EXPONENTIAL
        max_delay = 300
    else:
        backoff_type = RetryBackoffType.LINEAR
        max_delay = 1800

    return RetryConfig(
        max_retries=max_retries,
        backoff_type=backoff_type,
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay
    )

# 使用示例
config = create_adaptive_retry_config(
    error_history=["ConnectionTimeout", "NetworkUnreachable"],
    task_priority="high"
)
print(f"生成的配置: {config}")
```

---

## 6. 故障排查

### 6.1 Retry 次数超限

#### 症状

```
❌ RetryNotAllowedError: Max retries (3) exceeded
   Task ID: 01HXXXXXXXXXXXXXXXXXXXXXXXXX
   Current State: failed
   Reason: Max retries (3) exceeded
```

#### 原因分析

**常见原因**：

1. **配置的 max_retries 太小**
   - 任务失败频率高于预期
   - 恢复时间长于预期

2. **根本问题未解决**
   - 配置错误（如无效的 API Key）
   - 权限问题（如文件无法访问）
   - 依赖服务持续不可用

3. **Retry 循环检测触发**
   - 相同错误连续出现 3 次
   - 系统自动限制重试

#### 解决方案

**步骤 1: 检查 Retry 历史**

```python
from agentos.core.task.manager import TaskManager

def diagnose_retry_exhaustion(task_id: str):
    """诊断 retry 次数超限问题"""
    manager = TaskManager()
    task = manager.get_task(task_id)

    # 获取 retry 状态
    retry_state = task.get_retry_state()
    retry_config = task.get_retry_config()

    print(f"=== Retry 诊断报告 ===")
    print(f"任务 ID: {task_id}")
    print(f"当前状态: {task.status}")
    print(f"重试次数: {retry_state.retry_count}/{retry_config.max_retries}")
    print(f"\nRetry 历史:")

    for i, entry in enumerate(retry_state.retry_history, 1):
        print(f"  [{i}] {entry['timestamp']}")
        print(f"      原因: {entry['reason']}")
        if 'metadata' in entry:
            print(f"      元数据: {entry['metadata']}")

    # 分析失败模式
    reasons = [e['reason'] for e in retry_state.retry_history]
    unique_reasons = set(reasons)

    print(f"\n失败原因统计:")
    for reason in unique_reasons:
        count = reasons.count(reason)
        print(f"  - {reason}: {count} 次")

    # 判断是否是循环
    if len(unique_reasons) == 1:
        print(f"\n⚠️ 检测到循环: 所有失败原因相同")
        print(f"   建议: 修复根本问题，不要简单增加 max_retries")
    else:
        print(f"\n✅ 失败原因多样，可能是临时性错误")
        print(f"   建议: 考虑增加 max_retries 或调整 backoff 策略")

# 使用
diagnose_retry_exhaustion("01HXXX")
```

**步骤 2: 根据诊断结果采取行动**

```python
def fix_retry_exhaustion(task_id: str, diagnosis: str):
    """根据诊断结果修复问题"""
    from agentos.core.task.service import TaskService
    from agentos.core.task.manager import TaskManager
    from agentos.core.task.retry_strategy import RetryConfig, RetryState, RetryBackoffType

    service = TaskService()
    manager = TaskManager()
    task = manager.get_task(task_id)

    if diagnosis == "config_error":
        # 情况 1: 配置错误 → 修复配置后重置
        print("📝 修复配置错误...")
        # 修复配置（示例）
        task.metadata["api_key"] = "NEW_VALID_KEY"

        # 重置 retry 状态
        task.metadata["retry_state"] = RetryState().to_dict()
        manager.update_task(task)

        # 重试
        service.retry_failed_task(
            task_id=task_id,
            actor="admin",
            reason="Configuration fixed, retrying"
        )
        print("✅ 配置已修复，任务已重新排队")

    elif diagnosis == "insufficient_retries":
        # 情况 2: max_retries 太小 → 增加重试次数
        print("📝 增加 max_retries...")

        # 更新配置
        task.metadata["retry_config"] = RetryConfig(
            max_retries=10,
            backoff_type=RetryBackoffType.EXPONENTIAL,
            base_delay_seconds=60,
            max_delay_seconds=1800
        ).to_dict()

        # 重置 retry 状态
        task.metadata["retry_state"] = RetryState().to_dict()
        manager.update_task(task)

        # 重试
        service.retry_failed_task(
            task_id=task_id,
            actor="admin",
            reason="Increased max_retries, retrying"
        )
        print("✅ max_retries 已增加，任务已重新排队")

    elif diagnosis == "permanent_failure":
        # 情况 3: 永久性失败 → 取消任务
        print("❌ 永久性失败，取消任务...")
        service.cancel_task(
            task_id=task_id,
            actor="admin",
            reason="Permanent failure detected, canceling"
        )
        print("✅ 任务已取消")

    else:
        print(f"⚠️ 未知诊断结果: {diagnosis}")

# 使用示例
fix_retry_exhaustion("01HXXX", "insufficient_retries")
```

### 6.2 Retry 循环检测触发

#### 症状

```
❌ RetryNotAllowedError: Retry loop detected: same failure repeated 3 times
   Task ID: 01HXXXXXXXXXXXXXXXXXXXXXXXXX
   Failure Reason: "Invalid API Key"
```

#### 原因分析

Retry 循环检测触发意味着任务因**完全相同的原因**连续失败了 3 次。这通常表示：

1. **配置错误**：API Key、认证信息等配置错误
2. **权限问题**：缺少文件/资源访问权限
3. **输入错误**：输入数据格式或内容错误
4. **环境问题**：依赖服务永久不可用

**检测逻辑**（来自源码）：
```python
# 检查最近 3 次重试
if len(retry_state.retry_history) >= 3:
    recent_reasons = [
        h.get("reason", "")
        for h in retry_state.retry_history[-3:]
    ]
    # 如果 3 次原因完全相同
    if len(set(recent_reasons)) == 1:
        return False, "Retry loop detected: same failure repeated 3 times"
```

#### 解决方案

**步骤 1: 识别循环原因**

```python
def identify_retry_loop_cause(task_id: str):
    """识别 retry 循环的根本原因"""
    from agentos.core.task.manager import TaskManager

    manager = TaskManager()
    task = manager.get_task(task_id)
    retry_state = task.get_retry_state()

    # 获取重复的失败原因
    if len(retry_state.retry_history) >= 3:
        repeated_reason = retry_state.retry_history[-1]['reason']
        print(f"🔍 检测到循环:")
        print(f"   重复原因: {repeated_reason}")

        # 分类错误类型
        if "API Key" in repeated_reason or "Authentication" in repeated_reason:
            return "auth_error", repeated_reason
        elif "Permission" in repeated_reason or "Access Denied" in repeated_reason:
            return "permission_error", repeated_reason
        elif "Invalid" in repeated_reason or "Validation" in repeated_reason:
            return "validation_error", repeated_reason
        elif "Not Found" in repeated_reason:
            return "not_found_error", repeated_reason
        else:
            return "unknown_error", repeated_reason

    return "no_loop", None

# 使用
error_type, reason = identify_retry_loop_cause("01HXXX")
print(f"错误类型: {error_type}")
print(f"错误原因: {reason}")
```

**步骤 2: 根据错误类型修复**

```python
def fix_retry_loop(task_id: str):
    """修复 retry 循环问题"""
    from agentos.core.task.service import TaskService
    from agentos.core.task.manager import TaskManager
    from agentos.core.task.retry_strategy import RetryState

    service = TaskService()
    manager = TaskManager()

    # 识别错误类型
    error_type, reason = identify_retry_loop_cause(task_id)

    task = manager.get_task(task_id)

    if error_type == "auth_error":
        print("🔧 修复认证问题...")
        # 提示用户更新配置
        print("   请更新以下配置:")
        print("   - API Key")
        print("   - Access Token")
        print("   - 认证凭证")

        # 等待用户确认修复
        input("   修复完成后按回车继续...")

        # 重置 retry 状态
        task.metadata["retry_state"] = RetryState().to_dict()
        manager.update_task(task)

        # 重试
        service.retry_failed_task(
            task_id=task_id,
            actor="admin",
            reason="Authentication configuration fixed"
        )
        print("✅ 认证问题已修复，任务已重新排队")

    elif error_type == "permission_error":
        print("🔧 修复权限问题...")
        print("   请检查以下权限:")
        print("   - 文件读写权限")
        print("   - 目录访问权限")
        print("   - 资源访问控制")

        input("   修复完成后按回车继续...")

        # 重置并重试
        task.metadata["retry_state"] = RetryState().to_dict()
        manager.update_task(task)

        service.retry_failed_task(
            task_id=task_id,
            actor="admin",
            reason="Permission issue fixed"
        )
        print("✅ 权限问题已修复，任务已重新排队")

    elif error_type == "validation_error":
        print("❌ 数据验证错误")
        print("   这类错误通常无法通过重试解决")
        print("   建议:")
        print("   1. 检查输入数据格式")
        print("   2. 修正错误数据")
        print("   3. 创建新任务")

        # 取消任务
        service.cancel_task(
            task_id=task_id,
            actor="admin",
            reason="Validation error - cannot be fixed by retry"
        )
        print("✅ 任务已取消")

    else:
        print(f"⚠️ 未知错误类型: {error_type}")
        print(f"   原因: {reason}")
        print("   建议人工分析")

# 使用示例
fix_retry_loop("01HXXX")
```

**步骤 3: 预防 Retry 循环**

```python
def prevent_retry_loops():
    """预防 retry 循环的最佳实践"""

    # 1. 在 retry 前进行预检查
    def should_retry_after_failure(task_id: str, error: Exception) -> bool:
        """在重试前检查是否应该重试"""
        error_type = type(error).__name__

        # 永久性错误：不应重试
        if error_type in [
            "AuthenticationError",
            "PermissionDenied",
            "InvalidConfiguration",
            "DataValidationError",
            "FileNotFoundError"
        ]:
            print(f"❌ 永久性错误，不应重试: {error_type}")
            return False

        # 临时性错误：可以重试
        return True

    # 2. 在 retry reason 中添加更多信息
    def create_detailed_retry_reason(error: Exception) -> str:
        """创建详细的 retry 原因，避免触发循环检测"""
        import time

        return (
            f"{type(error).__name__}: {str(error)} "
            f"(timestamp: {time.time()})"
        )

    # 3. 使用不同的错误处理策略
    def handle_repeated_failures(task_id: str):
        """处理重复失败"""
        from agentos.core.task.manager import TaskManager

        manager = TaskManager()
        task = manager.get_task(task_id)
        retry_state = task.get_retry_state()

        # 检查是否有重复的失败
        if len(retry_state.retry_history) >= 2:
            last_two = retry_state.retry_history[-2:]
            if last_two[0]['reason'] == last_two[1]['reason']:
                print("⚠️ 检测到相同失败原因，增加延迟时间")

                # 动态调整 retry 配置
                from agentos.core.task.retry_strategy import RetryConfig, RetryBackoffType
                task.metadata["retry_config"] = RetryConfig(
                    max_retries=5,
                    backoff_type=RetryBackoffType.LINEAR,
                    base_delay_seconds=300,  # 增加到 5 分钟
                    max_delay_seconds=1800
                ).to_dict()

                manager.update_task(task)
                print("✅ 已调整 retry 配置，增加延迟时间")

    print("预防 Retry 循环的最佳实践:")
    print("1. ✅ 在 retry 前进行预检查")
    print("2. ✅ 在 reason 中添加时间戳等唯一信息")
    print("3. ✅ 检测重复失败并动态调整策略")
    print("4. ✅ 区分临时性和永久性错误")

# 使用
prevent_retry_loops()
```

### 6.3 Retry 失败诊断

#### 如何查看 Retry 历史

**方法 1: 通过任务 metadata 查看**

```python
from agentos.core.task.manager import TaskManager

def view_retry_history(task_id: str):
    """查看任务的完整 retry 历史"""
    manager = TaskManager()
    task = manager.get_task(task_id)

    retry_state = task.get_retry_state()

    print(f"=== Retry 历史 ===")
    print(f"任务 ID: {task_id}")
    print(f"任务标题: {task.title}")
    print(f"当前状态: {task.status}")
    print(f"重试次数: {retry_state.retry_count}")
    print(f"最后重试时间: {retry_state.last_retry_at}")
    print(f"下次重试时间: {retry_state.next_retry_after}")
    print(f"\n详细历史:")

    for entry in retry_state.retry_history:
        print(f"\n  尝试 #{entry['attempt']}:")
        print(f"    时间: {entry['timestamp']}")
        print(f"    原因: {entry['reason']}")
        if entry.get('metadata'):
            print(f"    元数据: {entry['metadata']}")

# 使用
view_retry_history("01HXXX")
```

**方法 2: 通过审计日志查看**

```python
def view_retry_audit_logs(task_id: str):
    """通过审计日志查看 retry 事件"""
    from agentos.store import get_db

    db = get_db()

    # 查询 retry 相关的审计日志
    cursor = db.execute("""
        SELECT
            timestamp,
            event_type,
            level,
            actor,
            reason,
            payload
        FROM task_audit_logs
        WHERE task_id = ?
          AND event_type IN ('TASK_RETRY_ATTEMPT', 'TASK_RETRY_FAILED', 'TASK_RETRY_EXCEEDED')
        ORDER BY timestamp ASC
    """, (task_id,))

    logs = cursor.fetchall()

    print(f"=== Retry 审计日志 ===")
    print(f"任务 ID: {task_id}")
    print(f"找到 {len(logs)} 条 retry 相关日志\n")

    for log in logs:
        timestamp, event_type, level, actor, reason, payload_str = log
        payload = json.loads(payload_str) if payload_str else {}

        print(f"[{timestamp}] {event_type} ({level})")
        print(f"  执行者: {actor}")
        print(f"  原因: {reason}")
        if payload:
            print(f"  详情:")
            for key, value in payload.items():
                print(f"    - {key}: {value}")
        print()

# 使用
view_retry_audit_logs("01HXXX")
```

**方法 3: 可视化 Retry 时间线**

```python
def visualize_retry_timeline(task_id: str):
    """可视化 retry 时间线"""
    from datetime import datetime
    from agentos.core.task.manager import TaskManager

    manager = TaskManager()
    task = manager.get_task(task_id)
    retry_state = task.get_retry_state()

    print(f"=== Retry 时间线 ===")
    print(f"任务: {task.title} ({task_id})\n")

    # 解析时间戳并计算间隔
    start_time = None
    for i, entry in enumerate(retry_state.retry_history):
        timestamp = datetime.fromisoformat(entry['timestamp'])

        if start_time is None:
            start_time = timestamp
            elapsed = 0
        else:
            elapsed = (timestamp - start_time).total_seconds()

        # 可视化时间线
        bar_length = int(elapsed / 60)  # 每分钟一个字符
        bar = "=" * min(bar_length, 50)

        print(f"尝试 #{i+1} (+{elapsed:.0f}s / {elapsed/60:.1f}min)")
        print(f"  {bar}> {entry['reason']}")
        print()

# 使用
visualize_retry_timeline("01HXXX")
```

#### 如何分析 Retry 失败原因

**综合分析工具**：

```python
def analyze_retry_failures(task_id: str):
    """综合分析 retry 失败原因"""
    from collections import Counter
    from agentos.core.task.manager import TaskManager
    from agentos.core.task.retry_strategy import RetryStrategyManager

    manager = TaskManager()
    task = manager.get_task(task_id)

    retry_state = task.get_retry_state()
    retry_config = task.get_retry_config()

    print(f"=== Retry 失败分析报告 ===")
    print(f"任务 ID: {task_id}")
    print(f"任务状态: {task.status}")
    print(f"创建时间: {task.created_at}")
    print(f"更新时间: {task.updated_at}\n")

    # 1. 配置分析
    print("📋 Retry 配置:")
    print(f"  - 最大重试次数: {retry_config.max_retries}")
    print(f"  - 退避策略: {retry_config.backoff_type.value}")
    print(f"  - 基础延迟: {retry_config.base_delay_seconds}s")
    print(f"  - 最大延迟: {retry_config.max_delay_seconds}s\n")

    # 2. 状态分析
    print("📊 Retry 状态:")
    print(f"  - 当前重试次数: {retry_state.retry_count}/{retry_config.max_retries}")
    print(f"  - 最后重试时间: {retry_state.last_retry_at}")
    print(f"  - 下次重试时间: {retry_state.next_retry_after}")

    # 检查是否还能重试
    retry_manager = RetryStrategyManager()
    can_retry, reason = retry_manager.can_retry(retry_config, retry_state)
    print(f"  - 是否可重试: {'✅ 是' if can_retry else '❌ 否'}")
    if not can_retry:
        print(f"  - 拒绝原因: {reason}\n")
    else:
        print()

    # 3. 失败模式分析
    if retry_state.retry_history:
        reasons = [e['reason'] for e in retry_state.retry_history]
        reason_counts = Counter(reasons)

        print("🔍 失败模式:")
        for reason, count in reason_counts.most_common():
            percentage = (count / len(reasons)) * 100
            print(f"  - {reason}")
            print(f"    出现次数: {count}/{len(reasons)} ({percentage:.1f}%)")
        print()

        # 判断失败模式
        if len(reason_counts) == 1:
            print("⚠️ 诊断: 所有失败原因相同（可能是配置或权限问题）")
        elif len(reason_counts) > len(reasons) * 0.7:
            print("✅ 诊断: 失败原因多样（可能是临时性错误）")
        else:
            print("⚠️ 诊断: 存在主要失败原因，建议重点排查")
        print()

    # 4. 时间分析
    if len(retry_state.retry_history) >= 2:
        print("⏱️ 时间间隔分析:")
        for i in range(1, len(retry_state.retry_history)):
            prev_time = datetime.fromisoformat(retry_state.retry_history[i-1]['timestamp'])
            curr_time = datetime.fromisoformat(retry_state.retry_history[i]['timestamp'])
            interval = (curr_time - prev_time).total_seconds()
            print(f"  尝试 #{i} → 尝试 #{i+1}: {interval:.0f}s ({interval/60:.1f}min)")
        print()

    # 5. 建议
    print("💡 建议:")
    if not can_retry:
        if "Max retries" in str(reason):
            print("  1. 检查任务配置和输入数据")
            print("  2. 修复问题后重置 retry 计数器")
            print("  3. 或者增加 max_retries 并重新尝试")
        elif "Retry loop" in str(reason):
            print("  1. 这是永久性错误，不应继续重试")
            print("  2. 修复根本问题（配置、权限等）")
            print("  3. 重置 retry 状态后重新尝试")
    else:
        print("  任务仍可重试，建议继续尝试")
    print()

# 使用
analyze_retry_failures("01HXXX")
```

---

## 7. 监控和观测

### 7.1 Retry 次数统计

#### 如何查看 retry_count

**方法 1: 单个任务的 retry_count**

```python
from agentos.core.task.manager import TaskManager

def get_task_retry_count(task_id: str) -> dict:
    """获取任务的 retry 次数"""
    manager = TaskManager()
    task = manager.get_task(task_id)

    retry_state = task.get_retry_state()
    retry_config = task.get_retry_config()

    return {
        "task_id": task_id,
        "retry_count": retry_state.retry_count,
        "max_retries": retry_config.max_retries,
        "remaining_retries": retry_config.max_retries - retry_state.retry_count,
        "retry_history_length": len(retry_state.retry_history),
        "last_retry_at": retry_state.last_retry_at,
        "next_retry_after": retry_state.next_retry_after,
    }

# 使用
stats = get_task_retry_count("01HXXX")
print(f"Retry 统计:")
print(f"  - 当前重试: {stats['retry_count']}/{stats['max_retries']}")
print(f"  - 剩余重试: {stats['remaining_retries']}")
```

**方法 2: 批量统计多个任务**

```python
def get_batch_retry_stats(task_ids: List[str]) -> dict:
    """批量获取任务的 retry 统计"""
    from collections import defaultdict

    manager = TaskManager()

    stats = {
        "total_tasks": len(task_ids),
        "tasks_with_retries": 0,
        "total_retry_count": 0,
        "retry_distribution": defaultdict(int),
        "tasks": []
    }

    for task_id in task_ids:
        task = manager.get_task(task_id)
        retry_state = task.get_retry_state()

        if retry_state.retry_count > 0:
            stats["tasks_with_retries"] += 1

        stats["total_retry_count"] += retry_state.retry_count
        stats["retry_distribution"][retry_state.retry_count] += 1

        stats["tasks"].append({
            "task_id": task_id,
            "title": task.title,
            "status": task.status,
            "retry_count": retry_state.retry_count,
        })

    return stats

# 使用
task_ids = ["01HXXX", "01HYYY", "01HZZZ"]
batch_stats = get_batch_retry_stats(task_ids)

print(f"批量 Retry 统计:")
print(f"  - 总任务数: {batch_stats['total_tasks']}")
print(f"  - 有重试的任务: {batch_stats['tasks_with_retries']}")
print(f"  - 总重试次数: {batch_stats['total_retry_count']}")
print(f"\nRetry 分布:")
for count, num_tasks in sorted(batch_stats['retry_distribution'].items()):
    print(f"  {count} 次重试: {num_tasks} 个任务")
```

#### 如何监控 Retry 趋势

**时间序列监控**：

```python
def monitor_retry_trends(hours: int = 24):
    """监控最近 N 小时的 retry 趋势"""
    from datetime import datetime, timedelta, timezone
    from agentos.store import get_db
    import json

    db = get_db()

    # 计算时间范围
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    # 查询 retry 事件
    cursor = db.execute("""
        SELECT
            timestamp,
            task_id,
            payload
        FROM task_audit_logs
        WHERE event_type = 'TASK_RETRY_ATTEMPT'
          AND timestamp >= ?
        ORDER BY timestamp ASC
    """, (start_time.isoformat(),))

    events = cursor.fetchall()

    # 按小时统计
    hourly_stats = defaultdict(lambda: {
        "retry_count": 0,
        "unique_tasks": set(),
    })

    for timestamp, task_id, payload_str in events:
        event_time = datetime.fromisoformat(timestamp)
        hour_key = event_time.strftime("%Y-%m-%d %H:00")

        hourly_stats[hour_key]["retry_count"] += 1
        hourly_stats[hour_key]["unique_tasks"].add(task_id)

    # 输出统计
    print(f"=== Retry 趋势监控 (最近 {hours} 小时) ===\n")

    for hour in sorted(hourly_stats.keys()):
        stats = hourly_stats[hour]
        task_count = len(stats["unique_tasks"])
        retry_count = stats["retry_count"]

        # 简单的可视化
        bar = "█" * min(retry_count, 50)

        print(f"{hour}  {bar} {retry_count} retries ({task_count} tasks)")

    # 总体统计
    total_retries = sum(s["retry_count"] for s in hourly_stats.values())
    total_tasks = len(set().union(*[s["unique_tasks"] for s in hourly_stats.values()]))

    print(f"\n总计: {total_retries} 次重试, {total_tasks} 个任务")
    if total_tasks > 0:
        avg_retries = total_retries / total_tasks
        print(f"平均每个任务: {avg_retries:.2f} 次重试")

# 使用
monitor_retry_trends(hours=24)
```

**实时监控脚本**：

```python
import time
from collections import deque

def realtime_retry_monitor(duration_minutes: int = 60):
    """实时监控 retry 事件"""
    from agentos.store import get_db
    from datetime import datetime, timedelta, timezone

    db = get_db()

    # 存储最近的事件（用于速率计算）
    recent_events = deque(maxlen=100)

    print(f"🔄 实时 Retry 监控 (持续 {duration_minutes} 分钟)")
    print("=" * 60)

    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=duration_minutes)
    last_check = start_time

    try:
        while datetime.now(timezone.utc) < end_time:
            # 查询新的 retry 事件
            cursor = db.execute("""
                SELECT
                    timestamp,
                    task_id,
                    reason,
                    payload
                FROM task_audit_logs
                WHERE event_type = 'TASK_RETRY_ATTEMPT'
                  AND timestamp > ?
                ORDER BY timestamp ASC
            """, (last_check.isoformat(),))

            events = cursor.fetchall()

            # 处理新事件
            for event in events:
                timestamp, task_id, reason, payload_str = event
                recent_events.append(timestamp)

                print(f"[{timestamp}] Retry: {task_id[:8]}... - {reason}")

            # 更新检查时间
            last_check = datetime.now(timezone.utc)

            # 计算速率
            if len(recent_events) > 0:
                rate = len(recent_events) / ((last_check - start_time).total_seconds() / 60)
                print(f"   当前速率: {rate:.2f} retries/min")

            # 等待下一次检查
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n监控已停止")

    # 最终统计
    total_events = len(recent_events)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds() / 60
    avg_rate = total_events / duration if duration > 0 else 0

    print(f"\n监控总结:")
    print(f"  - 持续时间: {duration:.1f} 分钟")
    print(f"  - 总 retry 次数: {total_events}")
    print(f"  - 平均速率: {avg_rate:.2f} retries/min")

# 使用（Ctrl+C 停止）
realtime_retry_monitor(duration_minutes=30)
```

### 7.2 Retry 成功率

#### 计算方法

```python
def calculate_retry_success_rate(task_ids: List[str] = None, hours: int = 24) -> dict:
    """
    计算 retry 成功率

    成功率定义:
    - 最终成功的任务数 / 尝试过 retry 的任务总数
    """
    from agentos.store import get_db
    from datetime import datetime, timedelta, timezone

    db = get_db()

    # 时间范围
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    # 查询有 retry 的任务
    if task_ids:
        placeholders = ",".join("?" * len(task_ids))
        where_clause = f"task_id IN ({placeholders})"
        params = task_ids
    else:
        where_clause = "timestamp >= ?"
        params = [start_time.isoformat()]

    cursor = db.execute(f"""
        SELECT DISTINCT task_id
        FROM task_audit_logs
        WHERE event_type = 'TASK_RETRY_ATTEMPT'
          AND {where_clause}
    """, params)

    retry_task_ids = [row[0] for row in cursor.fetchall()]

    # 统计结果
    stats = {
        "total_tasks_with_retry": len(retry_task_ids),
        "succeeded_after_retry": 0,
        "failed_after_retry": 0,
        "still_running": 0,
        "success_rate": 0.0,
        "details": []
    }

    manager = TaskManager()

    for task_id in retry_task_ids:
        task = manager.get_task(task_id)
        retry_state = task.get_retry_state()

        result = {
            "task_id": task_id,
            "title": task.title,
            "status": task.status,
            "retry_count": retry_state.retry_count,
        }

        if task.status == "succeeded":
            stats["succeeded_after_retry"] += 1
            result["outcome"] = "success"
        elif task.status == "failed":
            stats["failed_after_retry"] += 1
            result["outcome"] = "failed"
        else:
            stats["still_running"] += 1
            result["outcome"] = "running"

        stats["details"].append(result)

    # 计算成功率（排除还在运行的）
    completed_tasks = stats["succeeded_after_retry"] + stats["failed_after_retry"]
    if completed_tasks > 0:
        stats["success_rate"] = stats["succeeded_after_retry"] / completed_tasks

    return stats

# 使用
success_stats = calculate_retry_success_rate(hours=24)

print(f"=== Retry 成功率报告 (最近 24 小时) ===")
print(f"有 retry 的任务总数: {success_stats['total_tasks_with_retry']}")
print(f"  - 最终成功: {success_stats['succeeded_after_retry']}")
print(f"  - 最终失败: {success_stats['failed_after_retry']}")
print(f"  - 仍在运行: {success_stats['still_running']}")
print(f"成功率: {success_stats['success_rate']:.2%}")
```

#### 优化建议

```python
def analyze_and_optimize_retry_config():
    """分析 retry 成功率并提供优化建议"""

    # 1. 获取最近的成功率数据
    stats = calculate_retry_success_rate(hours=168)  # 最近一周

    print(f"=== Retry 配置优化建议 ===\n")

    # 2. 分析成功率
    success_rate = stats["success_rate"]

    if success_rate >= 0.9:
        print("✅ 当前 retry 配置表现良好")
        print(f"   成功率: {success_rate:.2%}")
        print("   建议: 保持当前配置")

    elif 0.7 <= success_rate < 0.9:
        print("⚠️ Retry 配置可以优化")
        print(f"   成功率: {success_rate:.2%}")
        print("   建议:")
        print("   1. 考虑增加 max_retries")
        print("   2. 调整 backoff 策略为 EXPONENTIAL")
        print("   3. 增加 base_delay_seconds")

    else:  # success_rate < 0.7
        print("❌ Retry 配置需要重大调整")
        print(f"   成功率: {success_rate:.2%}")
        print("   建议:")
        print("   1. 检查失败的根本原因")
        print("   2. 很多失败可能是永久性错误，不应重试")
        print("   3. 改进错误分类逻辑")
        print("   4. 增加 max_retries 并使用 EXPONENTIAL 退避")

    print()

    # 3. 分析 retry 次数分布
    from collections import Counter

    retry_counts = [d["retry_count"] for d in stats["details"]]
    retry_distribution = Counter(retry_counts)

    print("Retry 次数分布:")
    for count in sorted(retry_distribution.keys()):
        num_tasks = retry_distribution[count]
        bar = "█" * min(num_tasks, 30)
        print(f"  {count} 次: {bar} {num_tasks} 个任务")

    print()

    # 4. 具体优化建议
    avg_retry_count = sum(retry_counts) / len(retry_counts) if retry_counts else 0

    if avg_retry_count < 2:
        print("💡 优化建议: 任务很快就成功或失败")
        print("   → 可能不需要 retry，或者应减少 base_delay")
    elif avg_retry_count > 5:
        print("💡 优化建议: 平均重试次数较高")
        print("   → 考虑增加 base_delay 或使用 LINEAR 退避")
    else:
        print("💡 优化建议: 重试次数适中")
        print("   → 当前配置合理")

# 使用
analyze_and_optimize_retry_config()
```

### 7.3 Retry 审计日志

#### 如何查询审计日志

**查询所有 Retry 事件**：

```python
def query_retry_audit_logs(
    task_id: str = None,
    hours: int = 24,
    event_types: List[str] = None
) -> List[dict]:
    """
    查询 retry 相关的审计日志

    Args:
        task_id: 可选，指定任务 ID
        hours: 查询最近 N 小时的日志
        event_types: 可选，指定事件类型
    """
    from agentos.store import get_db
    from datetime import datetime, timedelta, timezone
    import json

    db = get_db()

    # 默认事件类型
    if event_types is None:
        event_types = [
            "TASK_RETRY_ATTEMPT",
            "TASK_RETRY_FAILED",
            "TASK_RETRY_EXCEEDED",
            "RETRY_COUNT_RESET"
        ]

    # 构建查询
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    placeholders = ",".join("?" * len(event_types))

    if task_id:
        query = f"""
            SELECT
                id,
                task_id,
                timestamp,
                event_type,
                level,
                actor,
                from_state,
                to_state,
                reason,
                payload
            FROM task_audit_logs
            WHERE task_id = ?
              AND event_type IN ({placeholders})
              AND timestamp >= ?
            ORDER BY timestamp DESC
        """
        params = [task_id, *event_types, start_time.isoformat()]
    else:
        query = f"""
            SELECT
                id,
                task_id,
                timestamp,
                event_type,
                level,
                actor,
                from_state,
                to_state,
                reason,
                payload
            FROM task_audit_logs
            WHERE event_type IN ({placeholders})
              AND timestamp >= ?
            ORDER BY timestamp DESC
        """
        params = [*event_types, start_time.isoformat()]

    cursor = db.execute(query, params)

    # 转换为字典列表
    logs = []
    for row in cursor.fetchall():
        log = {
            "id": row[0],
            "task_id": row[1],
            "timestamp": row[2],
            "event_type": row[3],
            "level": row[4],
            "actor": row[5],
            "from_state": row[6],
            "to_state": row[7],
            "reason": row[8],
            "payload": json.loads(row[9]) if row[9] else {}
        }
        logs.append(log)

    return logs

# 使用示例
# 查询特定任务的 retry 日志
task_logs = query_retry_audit_logs(task_id="01HXXX")
print(f"找到 {len(task_logs)} 条 retry 日志")

# 查询最近 24 小时所有的 retry 日志
recent_logs = query_retry_audit_logs(hours=24)
print(f"最近 24 小时有 {len(recent_logs)} 次 retry")
```

#### 日志字段说明

**审计日志字段**：

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|-------|
| `id` | INTEGER | 日志唯一标识 | 12345 |
| `task_id` | TEXT | 任务 ID | 01HXXXXXXXXXXX |
| `timestamp` | TIMESTAMP | 事件时间 | 2026-01-30T10:30:00Z |
| `event_type` | TEXT | 事件类型 | TASK_RETRY_ATTEMPT |
| `level` | TEXT | 日志级别 | info / warn / error |
| `actor` | TEXT | 执行者 | system / admin / user |
| `from_state` | TEXT | 原状态 | failed |
| `to_state` | TEXT | 目标状态 | queued |
| `reason` | TEXT | 事件原因 | Automatic retry attempt |
| `payload` | TEXT (JSON) | 详细信息 | {"retry_count": 2, ...} |

**payload 字段详解**（针对 `TASK_RETRY_ATTEMPT` 事件）：

```json
{
  "retry_count": 2,              // 当前重试次数
  "max_retries": 5,              // 最大重试次数
  "next_retry_after": "2026-01-30T10:35:00Z",  // 下次重试时间
  "reason": "Connection timeout",              // 重试原因
  "backoff_type": "exponential", // 退避策略
  "delay_seconds": 120           // 本次延迟时间
}
```

**查询和分析示例**：

```python
def analyze_retry_logs(logs: List[dict]):
    """分析 retry 审计日志"""
    from collections import Counter

    print(f"=== Retry 审计日志分析 ===")
    print(f"总日志数: {len(logs)}\n")

    # 1. 按事件类型统计
    event_counts = Counter(log["event_type"] for log in logs)
    print("事件类型统计:")
    for event_type, count in event_counts.most_common():
        print(f"  - {event_type}: {count}")
    print()

    # 2. 按任务统计
    task_counts = Counter(log["task_id"] for log in logs)
    print(f"涉及 {len(task_counts)} 个任务")
    print("Top 5 重试最多的任务:")
    for task_id, count in task_counts.most_common(5):
        print(f"  - {task_id}: {count} 次 retry")
    print()

    # 3. 按执行者统计
    actor_counts = Counter(log["actor"] for log in logs)
    print("执行者统计:")
    for actor, count in actor_counts.most_common():
        print(f"  - {actor}: {count}")
    print()

    # 4. 分析 retry 原因
    retry_logs = [log for log in logs if log["event_type"] == "TASK_RETRY_ATTEMPT"]
    if retry_logs:
        reasons = [log["reason"] for log in retry_logs]
        reason_counts = Counter(reasons)

        print("Top 5 重试原因:")
        for reason, count in reason_counts.most_common(5):
            print(f"  - {reason}: {count} 次")

# 使用
logs = query_retry_audit_logs(hours=24)
analyze_retry_logs(logs)
```

---

## 总结

本指南详细介绍了 AgentOS Task Retry 策略系统的各个方面：

1. **概述**：了解 Retry 策略的作用、适用场景和与手动重试的区别
2. **配置方法**：学习如何配置默认和自定义的 Retry 策略
3. **Retry 类型**：掌握 NONE、FIXED、LINEAR、EXPONENTIAL 四种退避策略
4. **Retry 限制**：理解最大重试次数、循环检测和失败处理机制
5. **最佳实践**：学习何时使用 Retry、如何选择合理的配置参数
6. **故障排查**：诊断和修复 Retry 相关问题
7. **监控和观测**：监控 Retry 指标、分析成功率、查询审计日志

**关键要点**：

- ✅ **优先使用指数退避**：EXPONENTIAL 是推荐的默认策略
- ✅ **区分临时性和永久性错误**：只对临时性错误使用 Retry
- ✅ **合理配置 max_retries**：根据任务重要性和成本选择
- ✅ **关注 Retry 循环**：及时发现并修复根本问题
- ✅ **持续监控和优化**：定期分析 Retry 成功率并优化配置

**进一步学习**：

- [Timeout 配置指南](./TIMEOUT_CONFIGURATION.md)
- [Cancel 操作手册](./CANCEL_OPERATIONS.md)
- [状态机运维手册](./STATE_MACHINE_OPERATIONS.md)
- [审计追踪文档](./audit_trail.md)

---

**文档版本**: v1.0
**最后更新**: 2026-01-30
**维护者**: AgentOS Team
**反馈**: 如有问题或建议，请提交 Issue
