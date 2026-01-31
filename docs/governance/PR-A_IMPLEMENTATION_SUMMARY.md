# PR-A: Capability Quota System Implementation Summary

## 实施完成状态: ✅ 完成

本文档总结了 PR-A: Capability Quota System (治理型配额) 的完整实施情况。

## 实施目标

实现治理型配额系统,在 AgentOS Governance 层控制能力调用的资源约束。

### 核心原则

- ❌ 不是简单的 rate limit
- ❌ 不在 MCP 层控制
- ✅ 在 AgentOS Governance 层完成
- ✅ 可审计、可回放、可冻结

## 实施清单

### Step 1: 配额数据模型 ✅

**文件位置:**
- `/agentos/core/capabilities/governance_models/quota.py`
- `/agentos/core/capabilities/governance_models/__init__.py`

**实现内容:**
1. `QuotaLimit` - 配额限制定义
   - `calls_per_minute`: 每分钟最大调用次数
   - `max_concurrent`: 最大并发调用数
   - `max_runtime_ms`: 单次调用最大运行时间
   - `max_cost_units`: 最大成本单位

2. `CapabilityQuota` - 配额配置(静态)
   - `quota_id`: 配额 ID
   - `scope`: 配额范围 (tool/capability/source)
   - `target_id`: 目标 ID
   - `limit`: 配额限制
   - `window`: 窗口类型 (sliding/fixed)
   - `enabled`: 是否启用

3. `QuotaState` - 配额使用状态(运行态)
   - `used_calls`: 已使用调用次数
   - `used_runtime_ms`: 已使用运行时间
   - `used_cost_units`: 已使用成本单位
   - `current_concurrent`: 当前并发数
   - `window_start`: 窗口开始时间
   - `last_reset`: 上次重置时间

4. `QuotaCheckResult` - 配额检查结果
   - `allowed`: 是否允许
   - `reason`: 拒绝原因
   - `state`: 当前状态
   - `warning`: 是否接近限制

### Step 2: 配额管理器 ✅

**文件位置:**
- `/agentos/core/capabilities/quota_manager.py`

**实现内容:**
1. `QuotaManager` 类
   - `register_quota()`: 注册配额配置
   - `check_quota()`: 检查配额是否允许执行
   - `update_quota()`: 更新配额使用状态
   - 滑动窗口和固定窗口支持
   - 自动重置机制
   - 并发数追踪

**核心功能:**
- ✅ 配额注册和启用/禁用
- ✅ 多维度配额检查(调用次数、并发、时间、成本)
- ✅ 警告阈值(80%)
- ✅ 窗口重置(固定窗口)
- ✅ 并发计数管理
- ✅ 优雅降级(无配额管理器时默认允许)

### Step 3: QuotaGate 集成 ✅

**文件位置:**
- `/agentos/core/capabilities/policy.py`

**实现内容:**
1. 在 `ToolPolicyEngine` 中添加 `quota_manager` 参数
2. 实现 `_check_quota_gate()` 方法
3. 将 QuotaGate 集成为第 4 层闸门

**7 层安全闸门系统:**
1. Mode Gate - 规划模式阻止副作用
2. Spec Frozen Gate - 执行需要冻结规格
3. Project Binding Gate - 需要项目绑定
4. **Quota Gate** - 配额检查 ⭐️ (本 PR 实现)
5. Policy Gate - 风险和副作用策略
6. Admin Token Gate - 高风险操作需要审批
7. Audit Gate - 完整审计链

**QuotaGate 行为:**
- 超限 → DENY (触发 `quota_exceeded` 审计事件)
- 临界(80%) → WARN + ALLOW (触发 `quota_warning` 审计事件)
- 正常 → ALLOW

### Step 4: Router 集成 ✅

**文件位置:**
- `/agentos/core/capabilities/router.py`

**实现内容:**
1. `ToolRouter.__init__()` 添加 `quota_manager` 参数
2. 在工具调用前增加并发计数
3. 在工具调用后更新配额状态(运行时间、成本)
4. 在工具调用后减少并发计数
5. 使用 try-finally 确保并发计数正确

**执行流程:**
```
1. Get tool descriptor
2. Policy check (包含 QuotaGate)
3. Emit audit start
4. Update quota (concurrent +1)
5. Execute tool
6. Update quota (runtime, concurrent -1) [finally block]
7. Add timing info
8. Emit audit end
```

### Step 5: 审计集成 ✅

**文件位置:**
- `/agentos/core/capabilities/audit.py`

**实现内容:**
1. `emit_quota_warning()` - 配额警告事件
2. `emit_quota_exceeded()` - 配额超限事件
3. 集成到 task_audits 表
4. 结构化日志记录

**审计事件:**
```json
// quota_warning
{
  "event_type": "quota_warning",
  "invocation_id": "inv_123",
  "tool_id": "ext:tools.postman:get",
  "quota_state": {
    "used_calls": 8,
    "current_concurrent": 1,
    ...
  }
}

// quota_exceeded
{
  "event_type": "quota_exceeded",
  "invocation_id": "inv_124",
  "tool_id": "ext:tools.postman:get",
  "reason": "Calls per minute limit reached: 10/10"
}
```

### Step 6: 测试 ✅

**文件位置:**
- `/tests/core/capabilities/test_quota.py` (10 个测试)
- `/tests/core/capabilities/test_quota_integration.py` (5 个测试)

**测试覆盖:**

#### 单元测试 (QuotaManager)
1. ✅ `test_quota_not_exceeded` - 未超限通过
2. ✅ `test_quota_warning` - 临界警告(80%)
3. ✅ `test_quota_exceeded` - 超限拒绝
4. ✅ `test_quota_window_reset` - 窗口重置
5. ✅ `test_quota_concurrent` - 并发限制
6. ✅ `test_quota_disabled` - 禁用配额
7. ✅ `test_quota_no_registration` - 未注册配额
8. ✅ `test_quota_runtime_limit` - 运行时间限制
9. ✅ `test_quota_cost_limit` - 成本限制
10. ✅ `test_quota_state_persistence` - 状态持久化

#### 集成测试 (Policy Engine + Router)
1. ✅ `test_policy_engine_with_quota_manager` - 策略引擎集成
2. ✅ `test_policy_engine_quota_warning` - 警告机制
3. ✅ `test_policy_engine_no_quota_manager` - 无配额管理器降级
4. ✅ `test_quota_gate_order` - 闸门顺序验证
5. ✅ `test_quota_vs_blacklist` - 配额与黑名单交互

**测试结果:**
```
======================== 15 passed, 2 warnings in 0.18s ========================
```

### Step 7: 文档 ✅

**文件位置:**
- `/docs/governance/QUOTA_GUIDE.md`

**文档内容:**
- 概念介绍(配额 vs 限流)
- 配额范围和类型
- 窗口类型说明
- 使用方法和示例
- API 参考
- 最佳实践
- 故障处理
- 与其他 Governance 组件的关系

## 技术亮点

### 1. 治理层控制

配额系统在 AgentOS Governance 层实现,不依赖 MCP 或 Extension 层:
- 统一的配额策略
- 完整的审计链
- 可回放和可冻结

### 2. 多维度配额

支持 4 种配额类型:
- 调用次数(calls_per_minute)
- 并发数(max_concurrent)
- 运行时间(max_runtime_ms)
- 成本(max_cost_units)

### 3. 三级配额范围

- Tool - 单个工具级别
- Capability - 整个能力级别
- Source - 整个来源级别

### 4. 警告机制

80% 阈值触发警告但允许执行,提前预警而不阻塞业务。

### 5. 优雅降级

- 无配额管理器时默认允许
- 审计失败不阻塞调用
- 并发计数异常保护

### 6. 完整审计

- `quota_warning` 事件
- `quota_exceeded` 事件
- 集成到 task_audits 表
- 结构化日志

## 架构图

```
┌─────────────────────────────────────────────────────┐
│                   ToolRouter                        │
│  ┌──────────────────────────────────────────────┐  │
│  │  1. Get Tool                                 │  │
│  │  2. Policy Check (7 Layers)                 │  │
│  │     ├─ Mode Gate                            │  │
│  │     ├─ Spec Frozen Gate                     │  │
│  │     ├─ Project Binding Gate                 │  │
│  │     ├─ Quota Gate ⭐                         │  │
│  │     │   └─> QuotaManager.check_quota()      │  │
│  │     ├─ Policy Gate                          │  │
│  │     ├─ Admin Token Gate                     │  │
│  │     └─ Audit Gate                           │  │
│  │  3. Emit Audit Start                        │  │
│  │  4. Update Quota (concurrent +1)            │  │
│  │  5. Execute Tool                            │  │
│  │  6. Update Quota (runtime, concurrent -1)   │  │
│  │  7. Emit Audit End                          │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
                ┌────────────────┐
                │ QuotaManager   │
                │  - Quotas      │
                │  - States      │
                │  - Windows     │
                └────────────────┘
```

## 配额检查流程

```
┌──────────────┐
│ Tool Call    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ QuotaGate    │
│ (Gate 4)     │
└──────┬───────┘
       │
       ▼
┌──────────────────────────┐
│ QuotaManager.check_quota │
└──────┬───────────────────┘
       │
       ├─> No quota registered → ALLOW
       │
       ├─> Quota disabled → ALLOW
       │
       ├─> Check limits:
       │   ├─ calls_per_minute
       │   ├─ max_concurrent
       │   ├─ max_runtime_ms
       │   └─ max_cost_units
       │
       ├─> Exceeded → DENY + emit_quota_exceeded
       │
       ├─> Warning (80%) → ALLOW + emit_quota_warning
       │
       └─> Normal → ALLOW
```

## 使用示例

### 基本用法

```python
from agentos.core.capabilities.quota_manager import QuotaManager
from agentos.core.capabilities.governance_models.quota import (
    CapabilityQuota,
    QuotaLimit
)

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

# 集成到 Router
router = ToolRouter(registry, quota_manager=quota_manager)

# 调用自动检查配额
result = await router.invoke_tool(tool_id, invocation)
```

### 与 Policy Engine 集成

```python
from agentos.core.capabilities.policy import ToolPolicyEngine

# 创建策略引擎(自动集成配额检查)
policy_engine = ToolPolicyEngine(quota_manager=quota_manager)

# 检查工具调用
allowed, reason, decision = policy_engine.check_allowed(
    tool, invocation, admin_token
)

if not allowed:
    print(f"Denied: {reason}")
```

## 验收标准

✅ 所有测试通过 (15/15)
✅ QuotaGate 正确拒绝超限调用
✅ 审计事件包含配额信息
✅ 不污染 MCP/Extension 实现
✅ 优雅降级机制完善
✅ 文档完整

## 未来扩展

配额系统已实现核心功能,未来可扩展:

1. **数据库持久化** - 配额状态持久化到数据库
2. **分布式配额** - 支持多实例配额共享
3. **动态配额** - 基于负载自动调整配额
4. **配额组** - 配额组合和继承
5. **配额预测** - 基于历史数据预测配额使用
6. **配额仪表板** - 可视化配额使用情况

## 总结

PR-A: Capability Quota System 已完整实施,提供:

- ✅ 治理层资源约束
- ✅ 多层级配额控制 (tool/capability/source)
- ✅ 完整审计集成
- ✅ 可回放和可冻结
- ✅ 优雅降级
- ✅ 15 个测试全部通过
- ✅ 完整文档

配额系统已经成为 AgentOS Governance 层的核心组件,为能力调用提供了强大的资源约束和审计能力。

**实施日期:** 2026-01-30
**状态:** ✅ 完成并通过验收
