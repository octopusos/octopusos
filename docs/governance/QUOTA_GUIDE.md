# Capability Quota System Guide

## 概述

Capability Quota System 是 AgentOS Governance 层的治理型配额系统。它在决策层控制能力调用的资源约束,而非执行层的简单限流。

## 核心概念

### 配额 vs 限流

| 维度 | 传统限流 (Rate Limit) | 治理型配额 (Governance Quota) |
|------|---------------------|------------------------------|
| **层级** | 执行层 (MCP/Extension) | 治理层 (AgentOS Governance) |
| **目的** | 防止资源耗尽 | 决策约束、可审计控制 |
| **粒度** | 单一工具 | 工具/能力/来源多级 |
| **审计** | 无 | 完整审计链 |
| **回放** | 不可回放 | 可回放、可冻结 |

### 配额范围 (Scope)

1. **Tool** - 单个工具级别
   - 例: `ext:tools.postman:get` 每分钟最多 10 次调用

2. **Capability** - 整个能力级别
   - 例: `tools.postman` 所有命令合计每分钟 20 次

3. **Source** - 整个来源级别
   - 例: 所有 Extension 合计并发不超过 5 个

## 配额限制类型

### 1. 调用次数限制 (calls_per_minute)

限制每分钟的调用次数:

```python
from agentos.core.capabilities.models.quota import CapabilityQuota, QuotaLimit

quota = CapabilityQuota(
    quota_id="tool:ext:tools.postman:get",
    scope="tool",
    target_id="ext:tools.postman:get",
    limit=QuotaLimit(calls_per_minute=10),
    window="sliding"  # 滑动窗口
)
```

### 2. 并发数限制 (max_concurrent)

限制同时运行的调用数:

```python
quota = CapabilityQuota(
    quota_id="source:extension",
    scope="source",
    target_id="extension",
    limit=QuotaLimit(max_concurrent=5)
)
```

### 3. 运行时间限制 (max_runtime_ms)

限制单次调用的最大运行时间:

```python
quota = CapabilityQuota(
    quota_id="tool:ext:tools.heavy:process",
    scope="tool",
    target_id="ext:tools.heavy:process",
    limit=QuotaLimit(max_runtime_ms=30000)  # 30秒
)
```

### 4. 成本限制 (max_cost_units)

限制计费能力的成本:

```python
quota = CapabilityQuota(
    quota_id="capability:ai.vision",
    scope="capability",
    target_id="ai.vision",
    limit=QuotaLimit(max_cost_units=100.0)  # 100 成本单位
)
```

## 窗口类型

### 滑动窗口 (Sliding Window)

- 默认类型
- 从当前时间向前追溯计算
- 适合平滑限流

```python
quota = CapabilityQuota(
    quota_id="test",
    scope="tool",
    target_id="test_tool",
    limit=QuotaLimit(calls_per_minute=10),
    window="sliding"
)
```

### 固定窗口 (Fixed Window)

- 按固定时间间隔重置
- 每分钟整点重置
- 适合周期性配额

```python
quota = CapabilityQuota(
    quota_id="test",
    scope="tool",
    target_id="test_tool",
    limit=QuotaLimit(calls_per_minute=10),
    window="fixed"
)
```

## 使用方法

### 1. 注册配额

```python
from agentos.core.capabilities.quota_manager import QuotaManager
from agentos.core.capabilities.models.quota import CapabilityQuota, QuotaLimit

# 创建配额管理器
quota_manager = QuotaManager()

# 注册配额
quota = CapabilityQuota(
    quota_id="tool:ext:tools.postman:get",
    scope="tool",
    target_id="ext:tools.postman:get",
    limit=QuotaLimit(
        calls_per_minute=10,
        max_concurrent=2
    )
)
quota_manager.register_quota(quota)
```

### 2. 检查配额

```python
# 检查配额是否允许
result = quota_manager.check_quota("tool:ext:tools.postman:get")

if not result.allowed:
    print(f"Quota exceeded: {result.reason}")
elif result.warning:
    print(f"Quota warning: approaching limit")
else:
    print("Quota OK")
```

### 3. 更新配额使用

```python
# 开始调用 - 增加并发计数
quota_manager.update_quota(
    "tool:ext:tools.postman:get",
    runtime_ms=0,
    increment_concurrent=1
)

# 执行工具调用...

# 结束调用 - 减少并发计数,记录运行时间
quota_manager.update_quota(
    "tool:ext:tools.postman:get",
    runtime_ms=150,  # 运行了 150ms
    cost_units=0.5,  # 消耗了 0.5 成本单位
    increment_concurrent=-1
)
```

### 4. 集成到 Router

ToolRouter 自动集成配额检查:

```python
from agentos.core.capabilities.router import ToolRouter
from agentos.core.capabilities.quota_manager import QuotaManager

quota_manager = QuotaManager()
# ... 注册配额 ...

router = ToolRouter(registry, quota_manager=quota_manager)

# 调用工具时自动检查配额
result = await router.invoke_tool(tool_id, invocation)
```

## 配额检查流程

配额检查是 7 层安全闸门的第 4 层:

```
1. Mode Gate          → 规划模式阻止副作用
2. Spec Frozen Gate   → 执行需要冻结规格
3. Project Binding    → 需要项目绑定
4. Quota Gate         → 配额检查 ⭐️
5. Policy Gate        → 风险和副作用策略
6. Admin Token Gate   → 高风险操作需要审批
7. Audit Gate         → 完整审计链
```

### 配额检查规则

1. **超限 (Exceeded)** → DENY
   - 拒绝调用
   - 触发 `quota_exceeded` 审计事件
   - 返回详细拒绝原因

2. **临界 (Warning)** → WARN + ALLOW
   - 允许调用但记录警告
   - 触发 `quota_warning` 审计事件
   - 默认阈值: 80%

3. **正常 (OK)** → ALLOW
   - 正常通过

## 审计集成

配额系统完全集成到审计链:

### 配额警告事件

```python
{
    "event_type": "quota_warning",
    "invocation_id": "inv_123",
    "tool_id": "ext:tools.postman:get",
    "tool_name": "Postman GET Request",
    "actor": "user@example.com",
    "quota_state": {
        "quota_id": "tool:ext:tools.postman:get",
        "used_calls": 8,
        "used_runtime_ms": 1200,
        "current_concurrent": 1,
        "window_start": "2026-01-30T10:00:00Z"
    }
}
```

### 配额超限事件

```python
{
    "event_type": "quota_exceeded",
    "invocation_id": "inv_124",
    "tool_id": "ext:tools.postman:get",
    "tool_name": "Postman GET Request",
    "actor": "user@example.com",
    "reason": "Calls per minute limit reached: 10/10"
}
```

## 使用场景

### 场景 1: 防止工具滥用

```python
# 限制单个工具的调用频率
quota = CapabilityQuota(
    quota_id="tool:ext:tools.postman:get",
    scope="tool",
    target_id="ext:tools.postman:get",
    limit=QuotaLimit(calls_per_minute=20)
)
```

### 场景 2: 控制并发资源

```python
# 限制整个 Extension 系统的并发数
quota = CapabilityQuota(
    quota_id="source:extension",
    scope="source",
    target_id="extension",
    limit=QuotaLimit(max_concurrent=10)
)
```

### 场景 3: 成本控制

```python
# 限制 AI 视觉能力的成本
quota = CapabilityQuota(
    quota_id="capability:ai.vision",
    scope="capability",
    target_id="ai.vision",
    limit=QuotaLimit(
        calls_per_minute=100,
        max_cost_units=500.0
    )
)
```

### 场景 4: 长时任务控制

```python
# 限制重型任务的运行时间
quota = CapabilityQuota(
    quota_id="tool:ext:tools.heavy:process",
    scope="tool",
    target_id="ext:tools.heavy:process",
    limit=QuotaLimit(
        max_runtime_ms=60000,  # 60秒
        max_concurrent=1  # 同时只能跑一个
    )
)
```

## API 参考

### QuotaManager

#### `__init__(db_path: Optional[Path] = None)`

创建配额管理器。

#### `register_quota(quota: CapabilityQuota)`

注册配额配置。

#### `check_quota(quota_id: str, estimated_runtime_ms: Optional[int] = None, estimated_cost: Optional[float] = None) -> QuotaCheckResult`

检查配额是否允许执行。

**返回值:**
- `allowed`: 是否允许
- `reason`: 拒绝原因(如果不允许)
- `state`: 当前配额状态
- `warning`: 是否接近限制

#### `update_quota(quota_id: str, runtime_ms: int, cost_units: float = 0.0, increment_concurrent: int = 0)`

更新配额使用状态。

**参数:**
- `runtime_ms`: 本次运行时间
- `cost_units`: 本次成本
- `increment_concurrent`: 并发数增量 (+1 开始, -1 结束)

### Models

#### `QuotaLimit`

配额限制定义:
- `calls_per_minute`: 每分钟最大调用次数
- `max_concurrent`: 最大并发调用数
- `max_runtime_ms`: 单次调用最大运行时间
- `max_cost_units`: 最大成本单位

#### `CapabilityQuota`

配额配置:
- `quota_id`: 配额 ID
- `scope`: 配额范围 (tool/capability/source)
- `target_id`: 目标 ID
- `limit`: 配额限制
- `window`: 窗口类型 (sliding/fixed)
- `enabled`: 是否启用

#### `QuotaState`

配额运行状态:
- `used_calls`: 已使用调用次数
- `used_runtime_ms`: 已使用运行时间
- `used_cost_units`: 已使用成本单位
- `current_concurrent`: 当前并发数
- `window_start`: 窗口开始时间
- `last_reset`: 上次重置时间

## 最佳实践

### 1. 分层配额

推荐从粗到细设置配额:

```python
# 1. 来源级别 - 全局控制
source_quota = CapabilityQuota(
    quota_id="source:extension",
    scope="source",
    target_id="extension",
    limit=QuotaLimit(max_concurrent=20)
)

# 2. 能力级别 - 能力组控制
capability_quota = CapabilityQuota(
    quota_id="capability:tools.postman",
    scope="capability",
    target_id="tools.postman",
    limit=QuotaLimit(calls_per_minute=50)
)

# 3. 工具级别 - 精细控制
tool_quota = CapabilityQuota(
    quota_id="tool:ext:tools.postman:get",
    scope="tool",
    target_id="ext:tools.postman:get",
    limit=QuotaLimit(calls_per_minute=20, max_concurrent=5)
)
```

### 2. 设置合理的警告阈值

默认警告阈值是 80%,可根据需要调整:

```python
result = quota_manager.check_quota("tool_id")
if result.warning:
    # 在达到 80% 时提前警告
    logger.warning(f"Approaching quota limit: {result.state.used_calls}")
```

### 3. 区分计划和执行

在规划阶段可以使用更宽松的配额:

```python
# 规划阶段配额
planning_quota = CapabilityQuota(
    quota_id="planning:tool_id",
    scope="tool",
    target_id="tool_id",
    limit=QuotaLimit(calls_per_minute=100)  # 更宽松
)

# 执行阶段配额
execution_quota = CapabilityQuota(
    quota_id="execution:tool_id",
    scope="tool",
    target_id="tool_id",
    limit=QuotaLimit(calls_per_minute=20)  # 更严格
)
```

### 4. 监控和调整

定期检查配额使用情况并调整:

```python
# 获取当前状态
state = quota_manager.states.get("tool_id")
if state:
    usage_rate = state.used_calls / quota.limit.calls_per_minute
    if usage_rate > 0.9:
        # 考虑增加配额或优化调用
        pass
```

## 故障处理

### 配额管理器不可用

如果配额管理器不可用,系统默认允许调用:

```python
if not quota_manager:
    # 默认允许,不阻塞业务
    return (True, None)
```

### 审计失败

配额审计失败不会阻塞调用,只记录警告:

```python
try:
    emit_quota_exceeded(invocation, tool, reason)
except Exception as e:
    logger.warning(f"Failed to emit quota audit: {e}")
    # 继续执行
```

### 数据库持久化失败

配额状态持久化失败不影响内存状态:

```python
def _persist_state(self, state: QuotaState):
    try:
        # 尝试持久化
        pass
    except Exception as e:
        logger.warning(f"Failed to persist quota state: {e}")
        # 继续使用内存状态
```

## 与其他 Governance 组件的关系

### Trust Tier

配额可以基于信任层级设置不同的限制:

```python
# T0 (本地 Extension) - 宽松配额
t0_quota = QuotaLimit(calls_per_minute=100)

# T3 (云端 MCP) - 严格配额
t3_quota = QuotaLimit(calls_per_minute=10, max_concurrent=2)
```

### Provenance

配额状态包含在溯源链中:

```python
{
    "provenance": {
        "quota_state": {
            "quota_id": "tool:xxx",
            "used_calls": 5,
            "used_runtime_ms": 500
        }
    }
}
```

### Policy Engine

配额是策略引擎的第 4 层闸门,与其他闸门协同工作。

## 未来扩展

1. **数据库持久化** - 配额状态持久化到数据库
2. **分布式配额** - 支持多实例配额共享
3. **动态配额** - 基于负载自动调整配额
4. **配额组** - 配额组合和继承
5. **配额预测** - 基于历史数据预测配额使用

## 总结

Capability Quota System 是 AgentOS Governance 的核心组件,提供:

- 治理层资源约束
- 多层级配额控制
- 完整审计集成
- 可回放和可冻结
- 优雅降级

通过合理配置和使用配额系统,可以有效控制能力调用的资源使用,防止滥用,保障系统稳定性。
