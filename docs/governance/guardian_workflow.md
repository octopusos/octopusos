# Guardian Workflow

## Overview

Guardian Workflow 实现了 Supervisor→Guardian 验收闭环,确保所有任务变更都经过验证。

## 核心概念

### 角色职责

#### Supervisor
- **监听**任务状态变化
- **决策**是否需要 Guardian 验证
- **分配** Guardian 给任务
- **消费** Guardian verdict
- **更新**任务状态

#### Guardian
- **执行**验证逻辑(测试、检查、审计)
- **产出** Verdict (PASS/FAIL/NEEDS_CHANGES)
- **不直接修改**任务状态
- **幂等且可重试**

### 核心数据结构

#### GuardianAssignment
```python
@dataclass(frozen=True)
class GuardianAssignment:
    assignment_id: str
    task_id: str
    guardian_code: str
    created_at: str
    reason: dict[str, Any]
```

#### GuardianVerdictSnapshot
```python
@dataclass(frozen=True)
class GuardianVerdictSnapshot:
    verdict_id: str
    assignment_id: str
    task_id: str
    guardian_code: str
    status: VerdictStatus  # PASS | FAIL | NEEDS_CHANGES
    flags: list[dict[str, Any]]
    evidence: dict[str, Any]
    recommendations: list[str]
    created_at: str
```

## State Machine

### 状态定义

```
PLANNED → APPROVED → RUNNING → VERIFYING → GUARD_REVIEW → VERIFIED → DONE
                         ↓          ↓             ↓
                      BLOCKED    BLOCKED       BLOCKED
                         ↓          ↓             ↓
                      RUNNING    RUNNING       RUNNING
```

### 状态转换规则

| From State | To State | Trigger |
|------------|----------|---------|
| RUNNING | VERIFYING | Supervisor 分配 Guardian |
| VERIFYING | GUARD_REVIEW | Guardian 开始验证 |
| GUARD_REVIEW | VERIFIED | Verdict = PASS |
| GUARD_REVIEW | BLOCKED | Verdict = FAIL |
| GUARD_REVIEW | RUNNING | Verdict = NEEDS_CHANGES |
| VERIFIED | DONE | 完成流程 |
| BLOCKED | RUNNING | 恢复/重试 |

## 时序图

### Happy Path (PASS)

```
┌──────────┐     ┌────────────┐     ┌──────────┐     ┌──────────────┐
│  Task    │     │ Supervisor │     │ Guardian │     │ VerdictConsumer│
└────┬─────┘     └─────┬──────┘     └────┬─────┘     └──────┬────────┘
     │                 │                  │                  │
     │  RUNNING        │                  │                  │
     ├────────────────>│                  │                  │
     │                 │                  │                  │
     │                 │ 1. assign_guardian(findings)        │
     │                 ├─────────────────>│                  │
     │                 │                  │                  │
     │                 │ 2. GuardianAssignment              │
     │                 │<─────────────────┤                  │
     │                 │                  │                  │
     │  VERIFYING      │                  │                  │
     │<────────────────┤                  │                  │
     │                 │                  │                  │
     │                 │                  │ 3. verify(task_id, context)
     │                 │                  ├──────────┐       │
     │                 │                  │  执行测试   │       │
     │                 │                  │<─────────┘       │
     │                 │                  │                  │
     │  GUARD_REVIEW   │                  │                  │
     │<────────────────┼──────────────────┤                  │
     │                 │                  │                  │
     │                 │                  │ 4. GuardianVerdictSnapshot(PASS)
     │                 │                  ├─────────────────>│
     │                 │                  │                  │
     │                 │                  │                  │ 5. apply_verdict()
     │                 │                  │                  ├────────┐
     │                 │                  │                  │ 更新状态 │
     │  VERIFIED       │                  │                  │<───────┘
     │<────────────────┼──────────────────┼──────────────────┤
     │                 │                  │                  │
     │  DONE           │                  │                  │
     │<────────────────┤                  │                  │
     │                 │                  │                  │
```

### Failure Path (FAIL)

```
┌──────────┐     ┌────────────┐     ┌──────────┐     ┌──────────────┐
│  Task    │     │ Supervisor │     │ Guardian │     │ VerdictConsumer│
└────┬─────┘     └─────┬──────┘     └────┬─────┘     └──────┬────────┘
     │                 │                  │                  │
     │  GUARD_REVIEW   │                  │                  │
     │                 │                  │                  │
     │                 │                  │ verify(task_id, context)
     │                 │                  ├──────────┐       │
     │                 │                  │  测试失败   │       │
     │                 │                  │<─────────┘       │
     │                 │                  │                  │
     │                 │                  │ GuardianVerdictSnapshot(FAIL)
     │                 │                  ├─────────────────>│
     │                 │                  │                  │
     │                 │                  │                  │ apply_verdict()
     │                 │                  │                  ├────────┐
     │                 │                  │                  │ 更新为BLOCKED
     │  BLOCKED        │                  │                  │<───────┘
     │<────────────────┼──────────────────┼──────────────────┤
     │                 │                  │                  │
     │  (Manual intervention or auto-retry)                 │
     │                 │                  │                  │
```

### Needs Changes Path

```
┌──────────┐     ┌────────────┐     ┌──────────┐     ┌──────────────┐
│  Task    │     │ Supervisor │     │ Guardian │     │ VerdictConsumer│
└────┬─────┘     └─────┬──────┘     └────┬─────┘     └──────┬────────┘
     │                 │                  │                  │
     │  GUARD_REVIEW   │                  │                  │
     │                 │                  │                  │
     │                 │                  │ verify(task_id, context)
     │                 │                  ├──────────┐       │
     │                 │                  │  需要修改   │       │
     │                 │                  │<─────────┘       │
     │                 │                  │                  │
     │                 │                  │ GuardianVerdictSnapshot(NEEDS_CHANGES)
     │                 │                  ├─────────────────>│
     │                 │                  │                  │
     │                 │                  │                  │ apply_verdict()
     │                 │                  │                  ├────────┐
     │                 │                  │                  │ 更新为RUNNING
     │  RUNNING        │                  │                  │<───────┘
     │<────────────────┼──────────────────┼──────────────────┤
     │                 │                  │                  │
     │  (Agent makes changes, cycle repeats)                │
     │                 │                  │                  │
```

## 事件列表

### Supervisor Events
- `TASK_STATE_CHANGED` - 任务状态变更
- `TASK_READY_FOR_VERIFICATION` - 任务准备验证

### Guardian Events
- `GUARDIAN_ASSIGNED` - Guardian 已分配
- `GUARDIAN_VERIFICATION_STARTED` - 验证开始
- `GUARDIAN_VERDICT_RECORDED` - Verdict 已记录
- `GUARDIAN_VERDICT_APPLIED` - Verdict 已应用

## MVP Implementation

### SmokeTestGuardian

当前 MVP 实现的 Guardian:
- **代码**: `smoke_test`
- **职责**: 基础烟雾测试
- **验证内容**: 任务基本结构完整性
- **状态**: 目前为 stub 实现,总是返回 PASS

### Future Guardians
- `diff` - 检测文件变更冲突
- `security` - 安全扫描
- `performance` - 性能测试
- `compliance` - 合规性检查

## 数据库 Schema

### guardian_assignments
```sql
CREATE TABLE guardian_assignments (
    assignment_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    guardian_code TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    reason_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ASSIGNED'
);
```

### guardian_verdicts
```sql
CREATE TABLE guardian_verdicts (
    verdict_id TEXT PRIMARY KEY,
    assignment_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    guardian_code TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    verdict_json TEXT NOT NULL
);
```

### task_audits (增强)
```sql
ALTER TABLE task_audits ADD COLUMN verdict_id TEXT;
```

## API Endpoints

### Guardian Management
- `GET /api/guardians/tasks/{task_id}/assignments` - 查询任务的 assignments
- `GET /api/guardians/assignments/{assignment_id}` - 获取 assignment 详情
- `GET /api/guardians/tasks/{task_id}/verdicts` - 查询任务的 verdicts
- `GET /api/guardians/verdicts/{verdict_id}` - 获取 verdict 详情

## Best Practices

### Guardian Implementation
1. **幂等性**: 相同输入应产生相同输出
2. **超时控制**: 设置合理的超时时间
3. **错误处理**: 优雅处理异常,不应崩溃
4. **证据记录**: 详细记录验证过程和结果

### Verdict Creation
1. **完整性**: 提供完整的 flags 和 evidence
2. **可操作性**: recommendations 应具体可执行
3. **不可变性**: 一旦创建不可修改
4. **可追溯性**: 记录所有上下文信息

### State Management
1. **原子性**: 状态转换必须原子性完成
2. **验证**: 使用 `can_transition()` 验证转换合法性
3. **审计**: 所有转换都写入 audit log
4. **恢复**: 支持从 BLOCKED 状态恢复

## Troubleshooting

### Guardian 卡住
- 检查 guardian_assignments 表中的 status
- 查看 task_audits 中的错误信息
- 手动触发 Guardian 重试

### Verdict 未应用
- 检查 VerdictConsumer 是否运行
- 查看 Supervisor 日志
- 验证状态转换规则

### 状态转换失败
- 验证 from_state 和 to_state 组合
- 检查数据库约束
- 查看 can_transition() 返回值

## Related Documentation
- [Guardian Contract](./guardian_contract.md)
- [Verification Runbook](./verification_runbook.md)
- [Decision Replay API](./decision_replay.md)
