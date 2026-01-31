# 验证层级 (Validation Layers)

## 概述

AgentOS 的治理体系采用分层设计，每一层负责不同级别的验证和控制。从最底层的红线验证到最高层的 Supervisor 编排，形成了完整的安全防护体系。

## 层级架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Supervisor (治理编排层)                             │
│  - 事件监听和决策执行                                           │
│  - Policy 路由和编排                                           │
│  - 审计和追溯                                                  │
└────────────────────┬────────────────────────────────────────┘
                     │ 调用
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Evaluator (意图评估层)                              │
│  - Intent Set 评估                                            │
│  - 冲突检测                                                    │
│  - 风险比较                                                    │
└────────────────────┬────────────────────────────────────────┘
                     │ 依赖
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Gates (控制门层)                                    │
│  - Pause Gates (暂停控制)                                     │
│  - Runtime Enforcer (运行时约束)                              │
│  - Redline Validators (红线验证)                              │
└────────────────────┬────────────────────────────────────────┘
                     │ 强制
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Redlines (红线规则层)                               │
│  - Agent 红线                                                 │
│  - Command 红线                                               │
│  - Rule 红线                                                  │
└─────────────────────────────────────────────────────────────┘
```

## 各层详解

### Layer 1: Redlines (红线规则层)

**职责：** 定义不可违反的硬性规则。

**组件：**
- `AgentRedlineValidator` - Agent 配置验证
- `CommandRedlineValidator` - Command 配置验证
- `RuleRedlineValidator` - Rule 配置验证

**验证内容：**
- 禁止的配置项（如 dangerous_commands）
- 必需的配置项（如 agent_name）
- 格式和类型验证

**特点：**
- 即时验证（创建时）
- 二值结果（通过/不通过）
- 不可绕过

**示例：**
```python
validator = AgentRedlineValidator()
passed, errors = validator.validate_all(agent_spec)
if not passed:
    raise ValidationError(f"Agent redline violation: {errors}")
```

### Layer 2: Gates (控制门层)

**职责：** 提供运行时控制机制。

#### 2.1 Pause Gates

在特定检查点暂停执行，等待人工审批。

**检查点：**
- `open_plan` - 执行计划生成后
- `pre_step` - 步骤执行前
- `post_step` - 步骤执行后
- `pre_publish` - 结果发布前

**状态：**
- `AWAITING_APPROVAL` - 等待审批
- `APPROVED` - 已批准
- `REJECTED` - 已拒绝
- `AUTO_APPROVED` - 自动批准

#### 2.2 Runtime Enforcer

执行运行时约束检查。

**检查项：**
- 执行模式约束（interactive/assisted/autonomous）
- Commit 验证（是否有未提交的更改）
- 问题限制（最大问题次数）
- Artifacts 检查

#### 2.3 Redline Validators

封装 Layer 1 的红线验证，提供统一接口。

**示例：**
```python
gate_adapter = GateAdapter(db_path)
is_violation, errors = gate_adapter.check_redline_violation("agent", agent_spec)
```

### Layer 3: Evaluator (意图评估层)

**职责：** 评估意图的可行性和风险。

#### 3.1 Intent Set Evaluation

评估整个意图集的完整性和一致性。

**评估维度：**
- 完整性检查（必需字段）
- 格式验证
- 语义一致性

#### 3.2 Conflict Detection

检测意图之间的冲突。

**冲突类型：**
- **Type Conflict** - 类型不兼容
- **Value Conflict** - 值冲突
- **Scope Conflict** - 作用域冲突
- **Resource Conflict** - 资源冲突

**严重程度：**
- `critical` - 严重冲突，必须解决
- `high` - 高优先级冲突
- `medium` - 中等冲突
- `low` - 轻微冲突

#### 3.3 Risk Comparison

比较不同意图的风险等级。

**风险维度：**
- `data_risk` - 数据风险
- `operation_risk` - 操作风险
- `compliance_risk` - 合规风险
- `overall_risk` - 综合风险

**风险等级：**
- `low` - 低风险
- `medium` - 中等风险
- `high` - 高风险
- `critical` - 严重风险

**示例：**
```python
evaluator = EvaluatorAdapter()
result = evaluator.evaluate_intent_set(intent_set_path)
conflicts = result["evaluation"]["conflicts"]
risk_matrix = result["evaluation"]["risk_comparison"]
```

### Layer 4: Supervisor (治理编排层)

**职责：** 编排整个治理流程，做出综合决策。

#### 4.1 事件监听

通过双通道（EventBus + Polling）监听任务生命周期事件。

**支持的事件：**
- `TASK_CREATED` - 任务创建
- `TASK_STEP_COMPLETED` - 步骤完成
- `TASK_FAILED` - 任务失败
- `TASK_STATE_CHANGED` - 状态变化

#### 4.2 Policy 路由

根据事件类型路由到对应的 Policy。

**核心 Policies：**
- `OnTaskCreatedPolicy` - 任务创建时的预检
- `OnStepCompletedPolicy` - 步骤完成后的再评估
- `OnTaskFailedPolicy` - 任务失败时的归因

#### 4.3 决策执行

根据 Policy 评估结果做出决策并执行。

**决策类型：**
- `ALLOW` - 允许继续
- `PAUSE` - 暂停等待
- `BLOCK` - 阻塞
- `RETRY` - 建议重试
- `REQUIRE_REVIEW` - 需要人工审查

**执行动作：**
- 触发 pause gate
- 触发 runtime enforcer
- 更新任务状态
- 写入审计日志

**示例：**
```python
supervisor = SupervisorService(db_path, processor, poll_interval=10)
supervisor.start()
# Supervisor 会自动监听事件并执行决策
```

## 层级协作

### 数据流

```
Task Lifecycle Event
        │
        ▼
┌───────────────┐
│  Supervisor   │ ← Layer 4: 接收事件，路由到 Policy
└───────┬───────┘
        │
        ▼ Policy 调用
┌───────────────┐
│   Evaluator   │ ← Layer 3: 评估意图，检测冲突和风险
└───────┬───────┘
        │
        ▼ 调用验证
┌───────────────┐
│     Gates     │ ← Layer 2: 执行 redline 验证，触发控制
└───────┬───────┘
        │
        ▼ 检查规则
┌───────────────┐
│   Redlines    │ ← Layer 1: 提供红线规则
└───────────────┘
```

### 调用关系

| 调用方 | 被调用方 | 接口 | 目的 |
|--------|----------|------|------|
| Supervisor | Evaluator | `evaluate_intent_set()` | 评估意图集 |
| Supervisor | Gates | `check_redline_violation()` | 红线检查 |
| Supervisor | Gates | `trigger_pause()` | 触发暂停 |
| Supervisor | Gates | `enforce_runtime_gates()` | 运行时检查 |
| Gates | Redlines | `validate_all()` | 验证规则 |
| Evaluator | - | - | 独立评估 |

### 职责分离

| 层级 | 关注点 | 时机 | 结果 |
|------|--------|------|------|
| Redlines | 规则验证 | 创建时 | Pass/Fail |
| Gates | 控制执行 | 运行时 | Allow/Block/Pause |
| Evaluator | 风险评估 | 计划时 | Conflicts/Risks |
| Supervisor | 决策编排 | 全生命周期 | Decision/Action |

## 治理流程示例

### 任务创建时的治理流程

```
1. Task Created Event
        │
        ▼
2. Supervisor 接收事件 (Layer 4)
        │
        ▼
3. OnTaskCreatedPolicy 处理
        │
        ├─── 调用 GateAdapter.check_redline_violation() (Layer 2)
        │    └─── 检查 agent/command/rule 红线 (Layer 1)
        │
        ├─── 调用 EvaluatorAdapter.evaluate_intent_set() (Layer 3)
        │    ├─── 检测冲突
        │    └─── 比较风险
        │
        ▼
4. Policy 生成 Decision
        │
        ├─── 如果有高严重度问题 → BLOCK
        │    └─── Action: MARK_BLOCKED
        │
        ├─── 如果有中等问题 → PAUSE
        │    └─── Action: PAUSE_GATE
        │
        └─── 如果没有问题 → ALLOW
             └─── Action: MARK_VERIFYING
        │
        ▼
5. Supervisor 执行 Action
        │
        ├─── 更新任务状态
        ├─── 触发 Gate（如需）
        └─── 写入审计日志
```

### 步骤完成时的治理流程

```
1. Step Completed Event
        │
        ▼
2. Supervisor 接收事件 (Layer 4)
        │
        ▼
3. OnStepCompletedPolicy 处理
        │
        ├─── 检查风险指标（error_rate, resource_usage）
        │
        ├─── 调用 GateAdapter.enforce_runtime_gates() (Layer 2)
        │    └─── 执行运行时约束检查
        │
        ▼
4. Policy 生成 Decision
        │
        ├─── 如果有高风险 → PAUSE
        │    └─── Action: PAUSE_GATE
        │
        └─── 如果正常 → ALLOW
             └─── Action: 无
        │
        ▼
5. Supervisor 执行 Action
```

## 监控和审计

### 审计事件类型

Supervisor 生成以下审计事件：

| 事件类型 | 说明 | 日志级别 |
|---------|------|----------|
| `SUPERVISOR_ALLOWED` | 决策为允许 | info |
| `SUPERVISOR_PAUSED` | 决策为暂停 | warn |
| `SUPERVISOR_BLOCKED` | 决策为阻塞 | warn |
| `SUPERVISOR_RETRY_RECOMMENDED` | 建议重试 | info |
| `SUPERVISOR_DECISION` | 通用决策记录 | info |
| `SUPERVISOR_ERROR` | Supervisor 内部错误 | error |

### 审计轨迹查询

```python
audit_adapter = AuditAdapter(db_path)
events = audit_adapter.get_audit_trail(
    task_id="task_123",
    event_type_prefix="SUPERVISOR_",
    limit=100
)

for event in events:
    print(f"{event['event_type']}: {event['payload']['reason']}")
```

### 监控指标

#### Supervisor 健康度

- **Inbox Backlog** - 待处理事件积压
  - `< 10` - 健康
  - `10-50` - 警告
  - `> 50` - 严重

- **Processing Lag** - 处理延迟
  - `< 5s` - 健康
  - `5-30s` - 警告
  - `> 30s` - 严重

- **Failed Event Rate** - 失败事件比例
  - `< 1%` - 健康
  - `1-5%` - 警告
  - `> 5%` - 严重

#### Gate 触发统计

- Pause Gate 触发次数
- Block 决策次数
- Redline 违规次数
- Runtime Gate 失败次数

## 配置和调优

### Supervisor 配置

```python
# 调整 Polling 间隔（降低延迟 vs 减少负载）
supervisor = SupervisorService(
    db_path=db_path,
    processor=processor,
    poll_interval=5  # 5 秒（默认 10 秒）
)

# 调整批处理大小（提高吞吐 vs 减少内存）
processor = SupervisorProcessor(
    db_path=db_path,
    policy_router=router,
    batch_size=100  # 100 个事件（默认 50 个）
)
```

### Gate 配置

```python
# 配置 Pause 检查点（按执行模式）
# 在 assisted 模式下禁用某些检查点
can_pause = can_pause_at("pre_step", run_mode="assisted")
```

### Evaluator 配置

```python
# 配置冲突检测严格度
evaluator = EvaluatorEngine(
    conflict_detection_level="strict"  # strict/normal/loose
)
```

## 故障处理

### 常见问题

1. **Inbox 积压过多**
   - 原因：Processor 处理速度慢于事件产生速度
   - 解决：增加 `batch_size`，优化 Policy 逻辑

2. **事件重复处理**
   - 原因：Inbox 去重失败
   - 解决：检查 `event_id` 生成逻辑，确保唯一性

3. **决策不生效**
   - 原因：Action 执行失败或未正确映射
   - 解决：检查 Adapter 实现，确认数据库连接

4. **审计日志缺失**
   - 原因：AuditAdapter 写入失败
   - 解决：检查数据库权限和表结构

### 调试工具

```python
# 查看 Inbox 状态
metrics = inbox_manager.get_backlog_metrics()
print(f"Pending: {metrics['pending_count']}")
print(f"Failed: {metrics['failed_count']}")
print(f"Lag: {metrics['oldest_pending_age_seconds']}s")

# 手动处理待处理事件
processed = processor.process_pending_events()
print(f"Processed {processed} events")

# 查看审计轨迹
events = audit_adapter.get_audit_trail(task_id)
for event in events:
    print(event)
```

## 最佳实践

1. **启用双通道摄入**
   - 同时启用 EventBus 订阅和 Polling
   - 确保事件不丢失

2. **合理设置 Polling 间隔**
   - 低延迟场景：5-10 秒
   - 正常场景：10-30 秒
   - 低负载场景：30-60 秒

3. **定期清理 Inbox**
   ```python
   inbox_manager.cleanup_old_events(days=7)  # 清理 7 天前的已完成事件
   ```

4. **监控关键指标**
   - 设置告警：Inbox backlog > 50
   - 设置告警：Processing lag > 30s
   - 设置告警：Failed event rate > 5%

5. **审计日志保留**
   - 建议保留至少 30 天
   - 重要任务的审计永久保留
   - 定期归档到外部存储

## 相关文档

- [Supervisor 主文档](./supervisor.md)
- [Supervisor Events](./supervisor_events.md)
- [Supervisor Runbook](./supervisor_runbook.md)
- [Supervisor Policies](./supervisor_policies.md)
- [Gates 文档](../gates/)
- [Evaluator 文档](../evaluator/)
