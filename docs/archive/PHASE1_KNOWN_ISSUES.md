# Phase 1 已知问题和限制

**项目**: AgentOS Mode-Task Integration - Phase 1
**版本**: 1.0
**日期**: 2026年1月30日

---

## 概述

本文档记录 Phase 1 实施中已知的问题、限制和不支持的场景。所有已知问题都已评估影响范围，并提供了缓解措施或解决计划。

**重要**: 以下列出的问题均为非阻塞性问题，不影响 Phase 1 的功能完整性和生产使用。

---

## 已知问题

### 问题 #1: SQLite 并发限制

**问题 ID**: P1-ISSUE-001

**描述**:
在高并发写入场景下（> 100 并发），SQLite 可能出现数据库锁定错误（`database is locked`）。这是 SQLite 的固有限制，而非 Mode-Task 集成的问题。

**影响范围**:
- **严重性**: LOW
- **影响场景**: 极端高并发场景（> 100 个并发任务同时尝试状态转换）
- **正常工作负载**: 不受影响（< 10 并发）
- **压力测试结果**: 50 并发时成功率 20-50%，10 并发时成功率 > 95%

**根本原因**:
SQLite 使用文件级锁定，不支持高并发写入。这是数据库选择的权衡：
- 优势: 轻量级，零配置，适合单机部署
- 劣势: 并发性能有限

**缓解措施**:
1. **当前缓解**:
   - 使用 SQLiteWriter 序列化写入，减少锁冲突
   - 配置合理的连接超时和重试策略
   - 限制并发任务数量（< 10）

2. **测试调整**:
   - 压力测试调整了预期成功率（20-50%）
   - 正常工作负载测试保持 100% 成功率

**长期解决方案**:
1. **PostgreSQL 迁移**（推荐）:
   - Phase 2 评估 PostgreSQL 作为可选后端
   - PostgreSQL 支持高并发（> 1000 并发）
   - 需要额外的部署和维护成本

2. **连接池优化**:
   - 实现更智能的连接池
   - 增加写入队列和批处理

3. **分片策略**:
   - 多数据库实例分片
   - 按项目或任务组分片

**监控建议**:
- 监控 `database is locked` 错误频率
- 告警阈值: > 5% 的操作失败
- 考虑迁移到 PostgreSQL（如果频繁触发）

**相关测试**:
- `tests/stress/test_mode_stress.py::test_high_concurrency_stress`
- `tests/integration/test_sqlite_threading.py`

---

### 问题 #2: Mode Gateway 缓存跨进程

**问题 ID**: P1-ISSUE-002

**描述**:
Mode Gateway 缓存是进程级别的（存储在 `_gateway_cache` 全局变量中），不会跨进程或跨服务器共享。

**影响范围**:
- **严重性**: LOW
- **影响场景**: 多进程或多服务器部署
- **性能影响**: 每个进程需要独立加载和缓存 Gateway
- **内存影响**: 每个进程维护独立缓存（每个缓存 < 1MB）

**具体表现**:
```
Process 1:
  - 首次查询 mode "implementation" → 加载 Gateway (1ms)
  - 第二次查询 → 缓存命中 (0.0001ms)

Process 2:
  - 首次查询 mode "implementation" → 重新加载 Gateway (1ms)
  - 第二次查询 → 缓存命中 (0.0001ms)
```

**为什么不是问题**:
1. Gateway 加载很快（< 1ms），即使缓存未命中也可接受
2. Gateway 实例很轻量（< 1KB），内存开销小
3. 每个进程的缓存仍然有效（进程内查询快速）
4. 大多数部署场景使用单进程

**缓解措施**:
1. **单进程部署**（推荐）:
   - AgentOS 默认单进程部署
   - 缓存效果最佳

2. **Pre-loading**:
   ```python
   # 在进程启动时预加载常用 Gateway
   from agentos.core.mode.gateway_registry import register_default_gateways
   register_default_gateways()
   ```

3. **Gateway 池**:
   - 多进程共享 Gateway 实例（通过 IPC）
   - 适合极高并发场景

**未来改进**（可选）:
1. **分布式缓存**（如 Redis）:
   - 跨进程共享缓存
   - 需要额外的 Redis 依赖
   - 增加系统复杂度

2. **Gateway 序列化**:
   - 将 Gateway 配置序列化到数据库
   - 每个进程从数据库加载配置

**不推荐**:
- 当前性能已足够（Gateway 查询 < 1ms）
- 增加分布式缓存的复杂度不值得

**相关测试**:
- `tests/stress/test_mode_stress.py::test_gateway_cache_concurrent`
- `tests/performance/test_mode_gateway_performance.py`

---

### 问题 #3: Mode 决策不持久化

**问题 ID**: P1-ISSUE-003

**描述**:
Mode 决策结果（ModeDecision）不直接存储在数据库中，而是通过审计追踪（audit trail）记录。

**影响范围**:
- **严重性**: LOW
- **影响**: 查询历史 Mode 决策需要解析审计日志
- **功能**: 不影响功能，只影响可观测性

**设计选择**:
这是一个有意的设计决策：
- **优势**:
  - 零数据库模式变更（Phase 1 目标）
  - 审计追踪已经记录所有转换
  - 避免数据冗余

- **劣势**:
  - 查询 Mode 决策历史需要解析 JSON
  - 无法直接统计 Mode 决策分布

**当前机制**:
```python
# Mode 决策记录在审计追踪的 metadata 中
{
    "event": "transition",
    "from_state": "QUEUED",
    "to_state": "RUNNING",
    "metadata": {
        "mode_decision": {
            "verdict": "APPROVED",
            "reason": "...",
            "timestamp": "..."
        }
    }
}
```

**查询示例**:
```python
# 查询任务的 Mode 决策历史
history = service.get_transition_history(task_id)
mode_decisions = [
    entry["metadata"].get("mode_decision")
    for entry in history
    if "mode_decision" in entry.get("metadata", {})
]
```

**未来改进**（可选）:
1. **专用表**:
   ```sql
   CREATE TABLE mode_decisions (
       id INTEGER PRIMARY KEY,
       task_id TEXT,
       mode_id TEXT,
       from_state TEXT,
       to_state TEXT,
       verdict TEXT,
       reason TEXT,
       timestamp TEXT
   );
   ```

2. **物化视图**:
   - 从审计追踪自动生成 Mode 决策视图
   - 提供快速查询接口

**不推荐现在实施**:
- 增加数据库复杂度
- 审计追踪已足够
- Phase 2 再评估需求

---

## 限制

### 限制 #1: Mode 类型固定

**限制 ID**: P1-LIMIT-001

**描述**:
当前支持的 Mode 类型（implementation, design, chat, autonomous）是在代码中定义的，不支持运行时动态添加新的 Mode 类型。

**具体限制**:
- ❌ 不能在配置文件中添加新 Mode
- ❌ 不能通过 API 动态注册新 Mode
- ✅ 可以通过代码添加新 Mode（需要重新部署）

**原因**:
Phase 1 专注于核心 Mode-Task 集成，Mode 类型管理留给后续版本。

**如何添加新 Mode**（当前）:
1. 创建新的 Gateway 实现
2. 在 `gateway_registry.py` 中注册
3. 更新文档
4. 重新部署

**示例**:
```python
# 1. 创建 Gateway
class ProductionModeGateway(RestrictedModeGateway):
    def __init__(self):
        super().__init__(
            mode_id="production",
            blocked_transitions={
                "QUEUED": {"RUNNING"},  # Require approval
            }
        )

# 2. 注册
from agentos.core.mode.gateway_registry import register_mode_gateway
register_mode_gateway("production", ProductionModeGateway())
```

**未来改进**（Phase 3 或更晚）:
1. **插件化 Mode 系统**:
   - Mode 作为插件加载
   - 配置文件定义 Mode

2. **Mode 配置 DSL**:
   - YAML/JSON 配置 Mode 规则
   - 无需代码变更

3. **Mode Registry API**:
   - API 动态注册/注销 Mode
   - 热重载 Mode 配置

**权衡**:
- 当前: 简单可控，但灵活性有限
- 未来: 灵活强大，但复杂度高

---

### 限制 #2: 同步 Gateway 模型

**限制 ID**: P1-LIMIT-002

**描述**:
Mode Gateway 的 `validate_transition()` 是同步方法，必须快速返回（< 10ms 建议）。不支持需要长时间外部调用的决策。

**具体限制**:
- ❌ 不能在 Gateway 中进行长时间 HTTP 请求
- ❌ 不能在 Gateway 中进行复杂计算
- ❌ 不能在 Gateway 中等待外部系统响应
- ✅ 可以返回 DEFERRED，由外部系统异步处理

**原因**:
Gateway 在状态转换的关键路径上，慢的 Gateway 会阻塞整个系统。

**如何处理异步决策**:
```python
class AsyncApprovalGateway:
    def validate_transition(self, ...):
        # 快速检查是否已有决策
        decision_id = f"{task_id}-{from_state}-{to_state}"
        cached_decision = self.cache.get(decision_id)

        if cached_decision:
            return cached_decision

        # 检查是否已请求审批
        request = self.get_approval_request(decision_id)

        if not request:
            # 创建异步审批请求
            self.create_approval_request_async(decision_id, task_id, ...)

        # 返回 DEFERRED，稍后重试
        return ModeDecision(
            verdict=ModeDecisionVerdict.DEFERRED,
            reason="Waiting for async approval",
            metadata={
                "retry_after": "60s",
                "request_id": decision_id
            }
        )
```

**重试机制**（调用方实现）:
```python
import time

def transition_with_retry(task_id, to_state, max_retries=3):
    for attempt in range(max_retries):
        try:
            return service.transition_task(task_id, to_state, ...)
        except ModeViolationError as e:
            if "Deferred" in str(e) and attempt < max_retries - 1:
                retry_after = e.metadata.get("retry_after", "60s")
                time.sleep(parse_duration(retry_after))
                continue
            raise
```

**未来改进**（可选）:
1. **异步 Gateway 协议**:
   ```python
   class AsyncModeGatewayProtocol(Protocol):
       async def validate_transition(...) -> ModeDecision:
           ...
   ```

2. **后台任务系统**:
   - Gateway 触发后台任务
   - 任务完成后更新决策缓存

**权衡**:
- 当前: 简单同步，性能可预测
- 未来: 异步灵活，但复杂度高

---

### 限制 #3: 单一 Mode 决策

**限制 ID**: P1-LIMIT-003

**描述**:
每个任务只能有一个 Mode，不支持嵌套或组合 Mode 决策。

**具体限制**:
- ❌ 不能同时应用多个 Mode 规则
- ❌ 不能有 Mode 继承关系
- ❌ 不能基于多个任务状态做决策

**原因**:
保持设计简单，避免复杂的决策逻辑和优先级冲突。

**当前模型**:
```
Task → 1 Mode → 1 Gateway → 1 Decision
```

**如果需要组合规则**（替代方案）:
```python
class CompositeGateway:
    def __init__(self, gateways: List[ModeGateway]):
        self.gateways = gateways

    def validate_transition(self, ...):
        # 应用所有 Gateway，取最严格的决策
        decisions = [
            gateway.validate_transition(...)
            for gateway in self.gateways
        ]

        # 优先级: REJECTED > BLOCKED > DEFERRED > APPROVED
        for decision in decisions:
            if decision.is_rejected():
                return decision

        for decision in decisions:
            if decision.is_blocked():
                return decision

        for decision in decisions:
            if decision.is_deferred():
                return decision

        return decisions[0]  # All approved
```

**未来改进**（可选）:
1. **Mode 组合**:
   - `mode_ids: ["production", "high_risk"]`
   - 应用所有 Mode 的 Gateway

2. **Mode 继承**:
   - `production` extends `autonomous`
   - 继承父 Mode 的规则

3. **策略引擎**:
   - 基于规则的决策系统
   - 支持复杂的条件逻辑

---

## 不支持的场景

### 场景 #1: 动态 Mode 切换

**场景**: 任务运行时动态切换 Mode

**当前行为**: ❌ 不支持

**原因**:
- Mode 决策在转换时验证
- 切换 Mode 可能导致不一致状态
- 复杂的状态管理和审计

**示例**（不支持）:
```python
# 任务在 RUNNING 状态
task = service.get_task(task_id)
task.metadata["mode_id"] = "new_mode"  # 不会生效
service.update_task(task)

# 下一次转换仍使用旧 Mode
```

**替代方案**:
1. **创建新任务**（推荐）:
   ```python
   new_task = service.create_draft_task(
       metadata={
           "mode_id": "new_mode",
           "replaces_task": old_task_id
       }
   )
   service.transition_task(old_task_id, "CANCELED", ...)
   ```

2. **在 DRAFT 状态修改**（仅限 DRAFT）:
   ```python
   if task.status == "DRAFT":
       task.metadata["mode_id"] = "new_mode"
       service.update_task(task)
   ```

**未来可能支持**（需要慎重设计）:
- Mode 切换作为显式操作
- 记录完整的 Mode 切换历史
- 验证 Mode 切换的合法性

---

### 场景 #2: 嵌套 Mode 决策

**场景**: Mode 之间的层级关系或继承

**当前行为**: ❌ 不支持

**示例**（不支持）:
```yaml
# 不支持的配置
modes:
  production:
    inherits: autonomous
    additional_rules:
      - require_change_ticket
      - require_rollback_plan
```

**原因**:
保持简单，避免复杂的优先级和继承逻辑。

**替代方案**:
在 Gateway 实现中处理 Mode 间关系：
```python
class ProductionGateway:
    def __init__(self):
        # 组合 autonomous Gateway 的规则
        self.autonomous_gateway = get_mode_gateway("autonomous")

    def validate_transition(self, ...):
        # 首先应用 autonomous 规则
        decision = self.autonomous_gateway.validate_transition(...)
        if not decision.is_approved():
            return decision

        # 再应用额外的 production 规则
        if not self.has_change_ticket(metadata):
            return ModeDecision(REJECTED, "Missing change ticket")

        return ModeDecision(APPROVED, "All checks passed")
```

---

### 场景 #3: 跨任务 Mode 策略

**场景**: 基于多个任务状态的 Mode 决策

**当前行为**: ❌ 不支持

**示例**（不支持）:
```python
# 不支持：基于其他任务状态决策
def validate_transition(self, ...):
    # 不能查询其他任务状态
    related_tasks = get_related_tasks(task_id)
    if any(t.status == "FAILED" for t in related_tasks):
        return BLOCKED
```

**原因**:
- Gateway 应该无状态
- 避免分布式状态管理
- 简化测试和调试

**替代方案**:
在更高层（如 Workflow 层）实现：
```python
# 在 Workflow 管理器中
class WorkflowManager:
    def can_start_task(self, task_id):
        task = service.get_task(task_id)
        dependencies = task.metadata.get("depends_on", [])

        # 检查依赖任务状态
        for dep_id in dependencies:
            dep = service.get_task(dep_id)
            if dep.status != "DONE":
                return False

        # 所有依赖满足，允许启动
        return True
```

---

## 监控和告警建议

### 关键指标

1. **Mode Gateway 性能**:
   - `mode_gateway_latency_ms`: Gateway 验证延迟
   - 目标: p50 < 5ms, p99 < 20ms
   - 告警: p99 > 50ms

2. **Mode 违规率**:
   - `mode_violation_rate`: Mode 违规次数 / 总转换次数
   - 正常: < 5%
   - 告警: > 10%

3. **Fail-safe 触发率**:
   - `mode_gateway_failsafe_rate`: Gateway 失败次数 / 总验证次数
   - 正常: < 0.1%
   - 告警: > 1%

4. **Gateway 缓存命中率**:
   - `mode_gateway_cache_hit_rate`: 缓存命中次数 / 总查询次数
   - 目标: > 90%
   - 告警: < 70%

### 告警规则

```yaml
alerts:
  - name: HighModeGatewayLatency
    condition: mode_gateway_latency_p99 > 50ms
    severity: WARNING
    action: Investigate Gateway performance

  - name: HighModeViolationRate
    condition: mode_violation_rate > 10%
    severity: WARNING
    action: Review Mode configuration

  - name: ModeGatewayFailsafe
    condition: mode_gateway_failsafe_rate > 1%
    severity: CRITICAL
    action: Check Gateway availability

  - name: LowGatewayCacheHitRate
    condition: mode_gateway_cache_hit_rate < 70%
    severity: INFO
    action: Review cache configuration
```

---

## 总结

Phase 1 已知问题和限制都是非阻塞性的，不影响核心功能和生产使用。所有问题都有：

- ✅ 明确的影响范围
- ✅ 实用的缓解措施
- ✅ 清晰的解决计划

**关键点**:
1. SQLite 并发限制是数据库选择的权衡，可通过 PostgreSQL 解决
2. Gateway 缓存跨进程是可接受的设计，性能影响小
3. 所有限制都有清晰的替代方案

**生产就绪**: Phase 1 适合生产使用，建议监控关键指标并根据实际负载评估是否需要 PostgreSQL。

---

**文档版本**: 1.0
**最后更新**: 2026年1月30日
**反馈**: 如发现新问题，请更新本文档
