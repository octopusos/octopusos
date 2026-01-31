# Supervisor 运维手册

## 概述

本文档提供 Supervisor 系统的运维指南，包括启动、监控、故障排查、日志分析等内容。

## 服务启动

### 基本启动

```python
from pathlib import Path
from agentos.core.supervisor.supervisor import (
    SupervisorService,
    SupervisorProcessor,
    PolicyRouter
)
from agentos.core.supervisor.subscriber import setup_supervisor_subscription
from agentos.core.supervisor.policies.on_task_created import OnTaskCreatedPolicy
from agentos.core.supervisor.policies.on_step_completed import OnStepCompletedPolicy
from agentos.core.supervisor.policies.on_task_failed import OnTaskFailedPolicy

# 1. 配置路径
db_path = Path("/path/to/agentos.db")

# 2. 创建 Policy Router 并注册 Policies
policy_router = PolicyRouter()
policy_router.register("TASK_CREATED", OnTaskCreatedPolicy(db_path))
policy_router.register("TASK_STEP_COMPLETED", OnStepCompletedPolicy(db_path))
policy_router.register("TASK_FAILED", OnTaskFailedPolicy(db_path))

# 3. 创建 Processor
processor = SupervisorProcessor(
    db_path=db_path,
    policy_router=policy_router,
    batch_size=50  # 批处理大小
)

# 4. 创建 Supervisor Service
supervisor = SupervisorService(
    db_path=db_path,
    processor=processor,
    poll_interval=10  # Polling 间隔（秒）
)

# 5. 启动服务
supervisor.start()

# 6. 设置 EventBus 订阅（可选）
subscriber = setup_supervisor_subscription(supervisor, db_path)

print("✅ Supervisor started successfully")
```

### Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -e .

CMD ["python", "-m", "agentos.core.supervisor.main"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  supervisor:
    build: .
    environment:
      - SUPERVISOR_POLL_INTERVAL=10
      - SUPERVISOR_BATCH_SIZE=50
      - AGENTOS_DB_PATH=/data/agentos.db
    volumes:
      - ./data:/data
    restart: unless-stopped
```

### 系统服务 (systemd)

```ini
# /etc/systemd/system/agentos-supervisor.service
[Unit]
Description=AgentOS Supervisor Service
After=network.target

[Service]
Type=simple
User=agentos
WorkingDirectory=/opt/agentos
ExecStart=/opt/agentos/.venv/bin/python -m agentos.core.supervisor.main
Restart=on-failure
RestartSec=10

Environment="SUPERVISOR_POLL_INTERVAL=10"
Environment="SUPERVISOR_BATCH_SIZE=50"
Environment="AGENTOS_DB_PATH=/var/lib/agentos/agentos.db"

[Install]
WantedBy=multi-user.target
```

启动命令：

```bash
sudo systemctl enable agentos-supervisor
sudo systemctl start agentos-supervisor
sudo systemctl status agentos-supervisor
```

### 优雅停止

```python
import signal
import sys

def signal_handler(sig, frame):
    print("Stopping Supervisor...")
    supervisor.stop()
    if subscriber:
        subscriber.unsubscribe()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# 保持运行
supervisor._thread.join()
```

## 监控指标

### 核心指标

#### 1. Inbox Backlog

待处理事件积压数量。

**查询方法：**

```python
from agentos.core.supervisor.inbox import InboxManager

inbox_manager = InboxManager(db_path)
metrics = inbox_manager.get_backlog_metrics()

print(f"Pending: {metrics['pending_count']}")
print(f"Processing: {metrics['processing_count']}")
print(f"Failed: {metrics['failed_count']}")
print(f"Completed: {metrics['completed_count']}")
```

**告警阈值：**

| 级别 | 阈值 | 说明 |
|------|------|------|
| 正常 | < 10 | 处理速度正常 |
| 警告 | 10-50 | 事件积压，需要关注 |
| 严重 | > 50 | 处理速度严重落后，需要立即介入 |

#### 2. Processing Lag

处理延迟，即最老待处理事件的年龄。

**查询方法：**

```python
metrics = inbox_manager.get_backlog_metrics()
lag_seconds = metrics.get('oldest_pending_age_seconds')

if lag_seconds:
    print(f"Processing lag: {lag_seconds:.1f}s")
```

**告警阈值：**

| 级别 | 阈值 | 说明 |
|------|------|------|
| 正常 | < 5s | 处理及时 |
| 警告 | 5-30s | 有延迟，需要监控 |
| 严重 | > 30s | 延迟过高，需要立即处理 |

#### 3. Event Throughput

事件处理吞吐量。

**查询方法：**

```python
import time

start_time = time.time()
processed_count = processor.process_pending_events()
elapsed = time.time() - start_time

throughput = processed_count / elapsed if elapsed > 0 else 0
print(f"Processed {processed_count} events in {elapsed:.2f}s ({throughput:.1f} events/s)")
```

#### 4. Failed Event Rate

失败事件比例。

**查询方法：**

```python
metrics = inbox_manager.get_backlog_metrics()
total = sum([
    metrics['pending_count'],
    metrics['processing_count'],
    metrics['failed_count'],
    metrics['completed_count']
])
failed_rate = metrics['failed_count'] / total if total > 0 else 0

print(f"Failed rate: {failed_rate:.2%}")
```

**告警阈值：**

| 级别 | 阈值 | 说明 |
|------|------|------|
| 正常 | < 1% | 失败率正常 |
| 警告 | 1-5% | 失败率偏高，需要检查 |
| 严重 | > 5% | 失败率异常，需要立即排查 |

### 监控脚本示例

```python
#!/usr/bin/env python3
"""
Supervisor 监控脚本

用法:
    python monitor_supervisor.py --db /path/to/agentos.db --interval 60
"""

import argparse
import time
from pathlib import Path
from agentos.core.supervisor.inbox import InboxManager


def monitor_loop(db_path: Path, interval: int):
    inbox_manager = InboxManager(db_path)

    while True:
        metrics = inbox_manager.get_backlog_metrics()

        # 计算告警级别
        pending = metrics['pending_count']
        lag = metrics.get('oldest_pending_age_seconds', 0)

        # 输出指标
        print(f"\n=== Supervisor Metrics ({time.strftime('%Y-%m-%d %H:%M:%S')}) ===")
        print(f"Pending:    {pending:>5}")
        print(f"Processing: {metrics['processing_count']:>5}")
        print(f"Failed:     {metrics['failed_count']:>5}")
        print(f"Completed:  {metrics['completed_count']:>5}")

        if lag:
            print(f"Lag:        {lag:>5.1f}s")

        # 告警检查
        alerts = []
        if pending > 50:
            alerts.append("CRITICAL: Inbox backlog > 50")
        elif pending > 10:
            alerts.append("WARNING: Inbox backlog > 10")

        if lag and lag > 30:
            alerts.append("CRITICAL: Processing lag > 30s")
        elif lag and lag > 5:
            alerts.append("WARNING: Processing lag > 5s")

        if alerts:
            print("\n⚠️  ALERTS:")
            for alert in alerts:
                print(f"  - {alert}")

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor Supervisor metrics")
    parser.add_argument("--db", required=True, help="Path to AgentOS database")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval (seconds)")

    args = parser.parse_args()
    monitor_loop(Path(args.db), args.interval)
```

### Prometheus 集成

```python
from prometheus_client import Gauge, Counter, start_http_server

# 定义指标
supervisor_inbox_pending = Gauge('supervisor_inbox_pending', 'Pending events in inbox')
supervisor_inbox_failed = Gauge('supervisor_inbox_failed', 'Failed events in inbox')
supervisor_processing_lag = Gauge('supervisor_processing_lag_seconds', 'Processing lag in seconds')
supervisor_events_processed = Counter('supervisor_events_processed_total', 'Total events processed')
supervisor_events_failed = Counter('supervisor_events_failed_total', 'Total events failed')

def update_metrics():
    """更新 Prometheus 指标"""
    metrics = inbox_manager.get_backlog_metrics()

    supervisor_inbox_pending.set(metrics['pending_count'])
    supervisor_inbox_failed.set(metrics['failed_count'])

    lag = metrics.get('oldest_pending_age_seconds', 0)
    if lag:
        supervisor_processing_lag.set(lag)

# 启动 Prometheus HTTP 服务
start_http_server(8000)

# 定期更新指标
while True:
    update_metrics()
    time.sleep(15)
```

## 日志分析

### 日志位置

Supervisor 使用 Python 标准 logging 模块，日志输出取决于配置。

**默认日志级别：**

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**推荐的生产配置：**

```python
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    '/var/log/agentos/supervisor.log',
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=10
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logger = logging.getLogger('agentos.core.supervisor')
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### 重要日志消息

#### 启动日志

```
✅ SupervisorService started
✅ Subscribed to EventBus
✅ Supervisor subscription setup complete
```

#### 处理日志

```
Processing 5 pending events
Processing event: TASK_CREATED for task task_abc123
TASK_CREATED decision: allow (findings=0)
✅ Processed 5/5 events
```

#### 错误日志

```
Error processing event evt_123: Database connection failed
Policy execution failed for TASK_CREATED: AttributeError: 'NoneType' object has no attribute 'evaluate'
Failed to insert event: UNIQUE constraint failed: supervisor_inbox.event_id
```

### 日志级别说明

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 详细调试信息 | `Event received from EventBus: TASK_CREATED (task=task_123)` |
| INFO | 正常运行信息 | `✅ Processed 10 events` |
| WARNING | 警告信息 | `Duplicate event from EventBus (deduped): evt_123` |
| ERROR | 错误信息 | `Error processing event evt_123: Database error` |

### 日志查询示例

**查找特定任务的处理日志：**

```bash
grep "task_abc123" /var/log/agentos/supervisor.log
```

**查找所有决策为 BLOCK 的日志：**

```bash
grep "decision: block" /var/log/agentos/supervisor.log
```

**查找最近的错误日志：**

```bash
tail -n 100 /var/log/agentos/supervisor.log | grep ERROR
```

**统计事件处理量：**

```bash
grep "Processed.*events" /var/log/agentos/supervisor.log | \
  awk '{sum+=$2} END {print "Total processed:", sum}'
```

## 故障排查

### 问题 1: Inbox 积压过多

**症状：**
- `pending_count` 持续增长
- `oldest_pending_age_seconds` 超过 30s

**可能原因：**
1. Processor 处理速度慢于事件产生速度
2. Policy 执行耗时过长
3. 数据库连接性能问题

**排查步骤：**

```python
# 1. 检查 Inbox 状态
metrics = inbox_manager.get_backlog_metrics()
print(metrics)

# 2. 检查是否有大量 processing 状态的事件（可能卡死）
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    SELECT COUNT(*), MIN(received_at)
    FROM supervisor_inbox
    WHERE status = 'processing'
""")
print(cursor.fetchone())

# 3. 手动触发处理
processed = processor.process_pending_events()
print(f"Processed {processed} events")
```

**解决方法：**

1. **增加批处理大小：**
   ```python
   processor = SupervisorProcessor(
       db_path=db_path,
       policy_router=policy_router,
       batch_size=100  # 从 50 增加到 100
   )
   ```

2. **优化 Policy 逻辑：**
   - 减少不必要的数据库查询
   - 使用缓存
   - 异步处理耗时操作

3. **重置卡死的事件：**
   ```sql
   UPDATE supervisor_inbox
   SET status = 'pending'
   WHERE status = 'processing'
     AND received_at < datetime('now', '-5 minutes');
   ```

### 问题 2: 事件重复处理

**症状：**
- 同一事件被处理多次
- 审计日志中有重复的决策记录

**可能原因：**
1. `event_id` 生成不唯一
2. Inbox 去重机制失效
3. 并发处理导致的竞态条件

**排查步骤：**

```python
# 检查是否有重复的 event_id
cursor.execute("""
    SELECT event_id, COUNT(*)
    FROM supervisor_inbox
    GROUP BY event_id
    HAVING COUNT(*) > 1
""")
duplicates = cursor.fetchall()
print(f"Duplicate event_ids: {len(duplicates)}")
```

**解决方法：**

1. **确保 event_id 唯一性：**
   - EventBus 事件使用 UUID
   - Polling 事件使用数据库唯一 ID

2. **检查数据库约束：**
   ```sql
   PRAGMA index_list(supervisor_inbox);
   -- 应该看到 event_id 的 UNIQUE 约束
   ```

3. **避免并发处理同一事件：**
   - 使用数据库事务
   - 在标记为 processing 前检查状态

### 问题 3: 决策不生效

**症状：**
- Policy 返回了 Decision，但动作未执行
- 任务状态未更新
- Pause gate 未触发

**可能原因：**
1. Adapter 执行失败
2. 数据库事务未提交
3. Gate/Task 系统配置错误

**排查步骤：**

```python
# 1. 查看审计日志
audit_adapter = AuditAdapter(db_path)
events = audit_adapter.get_audit_trail(task_id="task_abc")
for event in events:
    print(event)

# 2. 检查任务状态
cursor.execute("""
    SELECT task_id, status, metadata
    FROM tasks
    WHERE task_id = ?
""", (task_id,))
print(cursor.fetchone())

# 3. 检查 Gate 状态
cursor.execute("""
    SELECT gate_name, state, reason
    FROM task_gates
    WHERE task_id = ?
""", (task_id,))
print(cursor.fetchall())
```

**解决方法：**

1. **检查 Adapter 日志：**
   ```python
   logger.setLevel(logging.DEBUG)  # 开启详细日志
   ```

2. **确认数据库事务提交：**
   ```python
   # 在 Policy 中确保 cursor 是通过 conn.cursor() 创建的
   # 并且在 Processor 中正确 commit
   ```

3. **手动触发动作：**
   ```python
   # 手动触发 pause gate
   gate_adapter.trigger_pause(task_id, "open_plan", "Manual test", cursor)
   conn.commit()
   ```

### 问题 4: 审计日志缺失

**症状：**
- 没有 Supervisor 审计事件写入
- `get_audit_trail()` 返回空列表

**可能原因：**
1. AuditAdapter 写入失败
2. 数据库权限问题
3. `task_audits` 表结构错误

**排查步骤：**

```python
# 1. 检查表结构
cursor.execute("PRAGMA table_info(task_audits)")
print(cursor.fetchall())

# 2. 手动写入测试
audit_adapter.write_audit_event(
    task_id="test_task",
    event_type="TEST_EVENT",
    level="info",
    payload={"test": "data"},
    cursor=cursor
)
conn.commit()

# 3. 查询是否写入成功
cursor.execute("SELECT * FROM task_audits WHERE task_id = 'test_task'")
print(cursor.fetchone())
```

**解决方法：**

1. **检查数据库权限：**
   ```bash
   ls -la /path/to/agentos.db
   # 确保 Supervisor 进程有写权限
   ```

2. **重建表结构：**
   ```sql
   -- 如果表结构不正确，重建表
   DROP TABLE IF EXISTS task_audits;
   CREATE TABLE task_audits (
       audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
       task_id TEXT NOT NULL,
       level TEXT NOT NULL,
       event_type TEXT NOT NULL,
       payload TEXT,
       created_at TEXT NOT NULL
   );
   ```

### 问题 5: EventBus 订阅失效

**症状：**
- 只有 Polling 事件，没有 EventBus 事件
- `source` 字段全部为 `polling`

**可能原因：**
1. EventBus 订阅未正确设置
2. EventBus 服务未启动
3. 订阅回调异常

**排查步骤：**

```python
# 1. 检查订阅状态
from agentos.core.events.bus import get_event_bus

event_bus = get_event_bus()
print(f"Subscribers: {len(event_bus._subscribers)}")

# 2. 手动发布事件测试
from agentos.core.events.models import Event, EventType

test_event = Event(
    type=EventType.TASK_CREATED,
    entity=MockEntity(id="test_task"),
    ts="2025-01-28T10:00:00Z",
    payload={}
)
event_bus.publish(test_event)

# 3. 检查 inbox 是否收到
time.sleep(1)
cursor.execute("""
    SELECT * FROM supervisor_inbox
    WHERE task_id = 'test_task' AND source = 'eventbus'
""")
print(cursor.fetchone())
```

**解决方法：**

1. **重新设置订阅：**
   ```python
   subscriber = setup_supervisor_subscription(supervisor, db_path)
   ```

2. **检查 EventBus 配置：**
   ```python
   # 确保 EventBus 是全局单例
   event_bus = get_event_bus()
   ```

3. **捕获订阅回调异常：**
   - 订阅回调中的异常会被静默捕获
   - 查看 ERROR 级别日志

## 维护任务

### 日常维护

#### 1. 清理旧事件

```python
# 每天运行，清理 7 天前的已完成事件
deleted = inbox_manager.cleanup_old_events(days=7)
print(f"Cleaned up {deleted} old events")
```

**Cron 任务：**

```bash
# /etc/cron.daily/agentos-cleanup
#!/bin/bash
python3 << 'EOF'
from pathlib import Path
from agentos.core.supervisor.inbox import InboxManager

db_path = Path("/var/lib/agentos/agentos.db")
inbox_manager = InboxManager(db_path)
deleted = inbox_manager.cleanup_old_events(days=7)
print(f"Cleaned up {deleted} old events")
EOF
```

#### 2. 数据库备份

```bash
#!/bin/bash
# /usr/local/bin/agentos-backup.sh

DB_PATH="/var/lib/agentos/agentos.db"
BACKUP_DIR="/var/backups/agentos"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/agentos_$TIMESTAMP.db'"

# 保留最近 30 天的备份
find "$BACKUP_DIR" -name "agentos_*.db" -mtime +30 -delete

echo "Backup completed: agentos_$TIMESTAMP.db"
```

#### 3. 监控指标归档

```python
# 每小时记录一次指标到归档表
cursor.execute("""
    INSERT INTO supervisor_metrics_archive (
        timestamp, pending_count, failed_count, lag_seconds
    )
    SELECT
        datetime('now'),
        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END),
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END),
        julianday('now') - julianday(MIN(CASE WHEN status = 'pending' THEN received_at END))
    FROM supervisor_inbox
""")
conn.commit()
```

### 定期检查

#### 每周检查

1. **检查失败事件**
   ```sql
   SELECT event_id, task_id, event_type, error_message, received_at
   FROM supervisor_inbox
   WHERE status = 'failed'
   ORDER BY received_at DESC
   LIMIT 50;
   ```

2. **检查处理延迟趋势**
   ```sql
   SELECT DATE(timestamp) as date,
          AVG(lag_seconds) as avg_lag,
          MAX(lag_seconds) as max_lag
   FROM supervisor_metrics_archive
   WHERE timestamp > datetime('now', '-7 days')
   GROUP BY DATE(timestamp)
   ORDER BY date;
   ```

3. **检查决策分布**
   ```sql
   SELECT event_type,
          json_extract(payload, '$.decision_type') as decision,
          COUNT(*) as count
   FROM task_audits
   WHERE event_type LIKE 'SUPERVISOR_%'
     AND created_at > datetime('now', '-7 days')
   GROUP BY event_type, decision
   ORDER BY count DESC;
   ```

#### 每月检查

1. **数据库大小监控**
   ```bash
   du -h /var/lib/agentos/agentos.db
   ```

2. **索引性能检查**
   ```sql
   ANALYZE;
   PRAGMA integrity_check;
   ```

3. **审计日志统计**
   ```sql
   SELECT COUNT(*) as total_audits,
          COUNT(DISTINCT task_id) as unique_tasks
   FROM task_audits
   WHERE created_at > datetime('now', '-30 days');
   ```

## 性能调优

### 数据库优化

```sql
-- 创建索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_supervisor_inbox_status
    ON supervisor_inbox(status);

CREATE INDEX IF NOT EXISTS idx_supervisor_inbox_received_at
    ON supervisor_inbox(received_at);

CREATE INDEX IF NOT EXISTS idx_task_audits_task_id
    ON task_audits(task_id);

CREATE INDEX IF NOT EXISTS idx_task_audits_event_type
    ON task_audits(event_type);

-- 优化查询计划
ANALYZE;

-- 定期 VACUUM
VACUUM;
```

### Supervisor 配置调优

```python
# 高吞吐场景
supervisor = SupervisorService(
    db_path=db_path,
    processor=SupervisorProcessor(
        db_path=db_path,
        policy_router=policy_router,
        batch_size=200  # 增大批处理
    ),
    poll_interval=5  # 缩短 Polling 间隔
)

# 低延迟场景
supervisor = SupervisorService(
    db_path=db_path,
    processor=SupervisorProcessor(
        db_path=db_path,
        policy_router=policy_router,
        batch_size=20  # 小批量快速处理
    ),
    poll_interval=2  # 更频繁的 Polling
)

# 低负载场景
supervisor = SupervisorService(
    db_path=db_path,
    processor=SupervisorProcessor(
        db_path=db_path,
        policy_router=policy_router,
        batch_size=50  # 默认
    ),
    poll_interval=30  # 降低 Polling 频率
)
```

## 相关文档

- [Supervisor 主文档](./supervisor.md)
- [Supervisor Events](./supervisor_events.md)
- [Supervisor Policies](./supervisor_policies.md)
- [Validation Layers](./VALIDATION_LAYERS.md)
