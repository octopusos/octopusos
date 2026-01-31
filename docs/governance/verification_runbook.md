# Verification Runbook

## Overview

本文档提供 Guardian Workflow 运维指南,包括常见问题、排查步骤和恢复方案。

## System Health Check

### Quick Status Check

```bash
# 检查最近的 Guardian 活动
curl http://localhost:8080/api/governance/tasks/{task_id}/summary

# 检查 Supervisor 状态
curl http://localhost:8080/api/runtime/supervisor/status

# 查看最近的 verdicts
curl http://localhost:8080/api/guardians/tasks/{task_id}/verdicts
```

### Database Queries

```sql
-- 查看待处理的 assignments
SELECT *
FROM guardian_assignments
WHERE status = 'ASSIGNED'
ORDER BY created_at DESC
LIMIT 10;

-- 查看最近的 verdicts
SELECT verdict_id, task_id, guardian_code, status, created_at
FROM guardian_verdicts
ORDER BY created_at DESC
LIMIT 20;

-- 查看卡住的任务
SELECT t.task_id, t.status, t.updated_at,
       ga.assignment_id, ga.guardian_code, ga.status as assignment_status
FROM tasks t
LEFT JOIN guardian_assignments ga ON t.task_id = ga.task_id
WHERE t.status IN ('VERIFYING', 'GUARD_REVIEW')
  AND t.updated_at < datetime('now', '-1 hour');

-- 查看 verdict 应用记录
SELECT task_id, event_type, verdict_id, created_at, payload
FROM task_audits
WHERE event_type = 'GUARDIAN_VERDICT_APPLIED'
ORDER BY created_at DESC
LIMIT 10;
```

## Common Issues

### Issue 1: Task Stuck in VERIFYING

**症状:**
- Task 长时间停留在 VERIFYING 状态
- 没有 GuardianAssignment 记录

**原因:**
- Supervisor 未正确分配 Guardian
- GuardianAssigner 异常
- 数据库写入失败

**排查步骤:**

```bash
# 1. 检查 task 状态
curl http://localhost:8080/api/tasks/{task_id}

# 2. 检查是否有 assignment
curl http://localhost:8080/api/guardians/tasks/{task_id}/assignments

# 3. 检查 Supervisor 日志
tail -f logs/supervisor.log | grep {task_id}
```

**解决方案:**

```python
# 手动触发 Guardian 分配
from agentos.core.governance.orchestration.assigner import GuardianAssigner
from agentos.core.governance.guardian.registry import GuardianRegistry

registry = GuardianRegistry()
# ... register guardians ...

assigner = GuardianAssigner(registry)
assignment = assigner.assign_guardian(
    task_id="{task_id}",
    findings=[{"category": "RISK_RUNTIME"}],
    task_context={"task_id": "{task_id}"}
)

# 保存到数据库
# ... save assignment ...
```

### Issue 2: Task Stuck in GUARD_REVIEW

**症状:**
- Task 在 GUARD_REVIEW 状态超过预期时间
- 有 assignment 但没有 verdict

**原因:**
- Guardian 执行超时
- Guardian 抛出异常
- Guardian 进程崩溃

**排查步骤:**

```sql
-- 查找对应的 assignment
SELECT *
FROM guardian_assignments
WHERE task_id = '{task_id}'
ORDER BY created_at DESC
LIMIT 1;

-- 检查是否有 verdict
SELECT *
FROM guardian_verdicts
WHERE assignment_id = '{assignment_id}';

-- 查看 Guardian 执行日志
-- (查看 logs/guardian-{guardian_code}.log)
```

**解决方案:**

```python
# Option 1: 手动执行 Guardian
from agentos.core.governance.guardian.registry import GuardianRegistry

registry = GuardianRegistry()
# ... register guardians ...

guardian = registry.get("{guardian_code}")
verdict = guardian.verify(
    task_id="{task_id}",
    context={"assignment_id": "{assignment_id}"}
)

# 保存 verdict 到数据库
# ... save verdict ...
```

```python
# Option 2: 重新分配 Guardian
# 将 task 状态改回 RUNNING,让 Supervisor 重新分配
cursor.execute(
    "UPDATE tasks SET status = 'RUNNING' WHERE task_id = ?",
    ("{task_id}",)
)
```

### Issue 3: Verdict Not Applied

**症状:**
- Verdict 已记录,但 task 状态未更新
- guardian_verdicts 表有记录,但 task 状态不匹配

**原因:**
- VerdictConsumer 未运行
- 状态转换验证失败
- 数据库事务失败

**排查步骤:**

```sql
-- 检查 verdict 记录
SELECT *
FROM guardian_verdicts
WHERE task_id = '{task_id}'
ORDER BY created_at DESC
LIMIT 1;

-- 检查 task 当前状态
SELECT task_id, status, updated_at
FROM tasks
WHERE task_id = '{task_id}';

-- 检查是否有 audit 记录
SELECT *
FROM task_audits
WHERE task_id = '{task_id}'
  AND verdict_id = '{verdict_id}';
```

**解决方案:**

```python
# 手动应用 verdict
from agentos.core.governance.orchestration.consumer import VerdictConsumer
from pathlib import Path

db_path = Path("store/registry.sqlite")
consumer = VerdictConsumer(db_path)

# 从数据库加载 verdict
# ... load verdict from guardian_verdicts ...

consumer.apply_verdict(verdict)
```

### Issue 4: Invalid State Transition

**症状:**
- 错误: "Cannot transition from X to Y"
- Verdict 应用失败

**原因:**
- Task 状态与预期不符
- 状态转换规则不允许

**排查步骤:**

```python
from agentos.core.governance.states import can_transition, get_allowed_transitions

# 检查转换是否合法
current_state = "GUARD_REVIEW"
target_state = "VERIFIED"

allowed = can_transition(current_state, target_state)
print(f"Transition {current_state} -> {target_state}: {allowed}")

# 查看允许的转换
allowed_transitions = get_allowed_transitions(current_state)
print(f"Allowed from {current_state}: {allowed_transitions}")
```

**解决方案:**

```sql
-- 检查 task 实际状态
SELECT task_id, status FROM tasks WHERE task_id = '{task_id}';

-- 如果状态不正确,手动修正
-- (谨慎操作,记录原因)
UPDATE tasks
SET status = 'GUARD_REVIEW',
    updated_at = CURRENT_TIMESTAMP
WHERE task_id = '{task_id}';
```

### Issue 5: Verdict Backlog

**症状:**
- 大量 verdicts 未被处理
- Supervisor 处理延迟

**原因:**
- VerdictConsumer 性能瓶颈
- 数据库连接池耗尽
- 事件队列堆积

**排查步骤:**

```sql
-- 统计未处理的 verdicts
SELECT COUNT(*)
FROM guardian_verdicts gv
LEFT JOIN task_audits ta ON gv.verdict_id = ta.verdict_id
WHERE ta.verdict_id IS NULL;

-- 查看处理延迟
SELECT
    gv.verdict_id,
    gv.created_at as verdict_created,
    ta.created_at as audit_created,
    (julianday(ta.created_at) - julianday(gv.created_at)) * 86400 as delay_seconds
FROM guardian_verdicts gv
JOIN task_audits ta ON gv.verdict_id = ta.verdict_id
WHERE ta.event_type = 'GUARDIAN_VERDICT_APPLIED'
ORDER BY gv.created_at DESC
LIMIT 20;
```

**解决方案:**

```python
# 批量处理积压的 verdicts
import sqlite3
import json
from pathlib import Path
from agentos.core.governance.orchestration.consumer import VerdictConsumer
from agentos.core.governance.guardian.models import GuardianVerdictSnapshot

db_path = Path("store/registry.sqlite")
consumer = VerdictConsumer(db_path)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# 查找未处理的 verdicts
cursor.execute("""
    SELECT gv.verdict_id, gv.verdict_json
    FROM guardian_verdicts gv
    LEFT JOIN task_audits ta ON gv.verdict_id = ta.verdict_id
    WHERE ta.verdict_id IS NULL
    ORDER BY gv.created_at ASC
    LIMIT 100
""")

for row in cursor.fetchall():
    verdict_id, verdict_json = row
    verdict_dict = json.loads(verdict_json)
    verdict = GuardianVerdictSnapshot(**verdict_dict)

    try:
        consumer.apply_verdict(verdict)
        print(f"✅ Applied verdict {verdict_id}")
    except Exception as e:
        print(f"❌ Failed to apply verdict {verdict_id}: {e}")

conn.close()
```

## Recovery Procedures

### Procedure 1: Reset Task to RUNNING

适用场景: Guardian 卡住或失败,需要重新验证

```sql
-- 1. 记录当前状态(审计)
INSERT INTO task_audits (task_id, event_type, created_at, payload)
VALUES (
    '{task_id}',
    'MANUAL_STATE_RESET',
    CURRENT_TIMESTAMP,
    json_object(
        'from_state', (SELECT status FROM tasks WHERE task_id = '{task_id}'),
        'to_state', 'RUNNING',
        'reason', 'Manual recovery: Guardian stuck',
        'operator', '{operator_name}'
    )
);

-- 2. 重置 task 状态
UPDATE tasks
SET status = 'RUNNING',
    updated_at = CURRENT_TIMESTAMP
WHERE task_id = '{task_id}';

-- 3. (可选) 标记旧的 assignment 为 FAILED
UPDATE guardian_assignments
SET status = 'FAILED'
WHERE task_id = '{task_id}'
  AND status IN ('ASSIGNED', 'VERIFYING');
```

### Procedure 2: Force VERIFIED

适用场景: Guardian 失败但人工审查后确认可以通过

```sql
-- 1. 创建手动 verdict
INSERT INTO guardian_verdicts (
    verdict_id, assignment_id, task_id, guardian_code,
    status, created_at, verdict_json
)
VALUES (
    'verdict_manual_' || substr(hex(randomblob(6)), 1, 12),
    '{assignment_id}',
    '{task_id}',
    'manual_override',
    'PASS',
    CURRENT_TIMESTAMP,
    json_object(
        'verdict_id', 'verdict_manual_xxx',
        'assignment_id', '{assignment_id}',
        'task_id', '{task_id}',
        'guardian_code', 'manual_override',
        'status', 'PASS',
        'flags', json('[]'),
        'evidence', json_object(
            'note', 'Manual override by operator',
            'operator', '{operator_name}',
            'reason', '{reason}'
        ),
        'recommendations', json('[]'),
        'created_at', datetime('now')
    )
);

-- 2. 更新 task 状态
UPDATE tasks
SET status = 'VERIFIED',
    updated_at = CURRENT_TIMESTAMP
WHERE task_id = '{task_id}';

-- 3. 记录审计
INSERT INTO task_audits (task_id, event_type, created_at, verdict_id, payload)
VALUES (
    '{task_id}',
    'GUARDIAN_VERDICT_APPLIED',
    CURRENT_TIMESTAMP,
    'verdict_manual_xxx',
    json_object(
        'verdict_status', 'PASS',
        'note', 'Manual override',
        'operator', '{operator_name}'
    )
);
```

### Procedure 3: Clean Stale Assignments

适用场景: 清理过期的 assignments

```sql
-- 查找超过 24 小时的 ASSIGNED 状态
SELECT assignment_id, task_id, guardian_code, created_at
FROM guardian_assignments
WHERE status = 'ASSIGNED'
  AND created_at < datetime('now', '-24 hours');

-- 标记为 FAILED
UPDATE guardian_assignments
SET status = 'FAILED'
WHERE status = 'ASSIGNED'
  AND created_at < datetime('now', '-24 hours');
```

## Monitoring & Alerts

### Key Metrics

1. **Guardian Latency**
   - p50, p95, p99 执行时间
   - 告警阈值: p95 > 5 分钟

2. **Verdict Application Lag**
   - Verdict 创建到应用的时间差
   - 告警阈值: 超过 1 分钟

3. **Stuck Tasks**
   - VERIFYING/GUARD_REVIEW 状态超过 1 小时
   - 告警阈值: 超过 10 个

4. **Failure Rate**
   - FAIL verdicts 占比
   - 告警阈值: 超过 20%

### Prometheus Metrics (Future)

```python
# Example metrics to implement
guardian_execution_duration_seconds = Histogram(
    'guardian_execution_duration_seconds',
    'Guardian execution time',
    ['guardian_code']
)

guardian_verdict_total = Counter(
    'guardian_verdict_total',
    'Total verdicts produced',
    ['guardian_code', 'status']
)

verdict_application_lag_seconds = Histogram(
    'verdict_application_lag_seconds',
    'Time from verdict creation to application'
)

stuck_tasks_total = Gauge(
    'stuck_tasks_total',
    'Number of stuck tasks',
    ['state']
)
```

## Best Practices

### Operational Guidelines

1. **定期巡检**
   - 每天检查 stuck tasks
   - 每周审查 failure patterns

2. **日志保留**
   - Guardian 执行日志: 30 天
   - Verdict 记录: 永久
   - Audit 日志: 永久

3. **容量规划**
   - 监控 Guardian 并发数
   - 评估数据库存储增长

4. **变更管理**
   - Guardian 代码变更需要 review
   - 状态机变更需要 RFC
   - 数据库迁移需要测试

### Safety Checks

执行恢复操作前,务必:

1. **备份数据库**
```bash
cp store/registry.sqlite store/registry.sqlite.backup.$(date +%Y%m%d_%H%M%S)
```

2. **记录操作**
```sql
INSERT INTO task_audits (task_id, event_type, created_at, payload)
VALUES (...);
```

3. **验证结果**
```bash
# 检查 task 状态
curl http://localhost:8080/api/tasks/{task_id}

# 检查 verdicts
curl http://localhost:8080/api/guardians/tasks/{task_id}/verdicts
```

## Escalation

### When to Escalate

- Guardian 系统性失败(> 50% 失败率)
- 数据不一致无法自动恢复
- 状态机死锁
- 数据库损坏

### Escalation Path

1. **L1 Support** - 基础排查和恢复
2. **L2 Engineering** - 复杂问题和代码修复
3. **Architect Review** - 系统设计问题

### Contact Information

- Slack: `#agentos-guardian-support`
- PagerDuty: `Guardian Workflow Alerts`
- Docs: `https://docs.agentos.ai/governance/`

## Related Documentation
- [Guardian Workflow](./guardian_workflow.md)
- [Guardian Contract](./guardian_contract.md)
