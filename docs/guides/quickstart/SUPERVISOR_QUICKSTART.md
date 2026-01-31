# Supervisor MVP 快速启动指南

**5 分钟快速上手 AgentOS Supervisor**

---

## 🚀 快速启动（3 步）

### 1. 应用数据库迁移

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python agentos/store/migrations.py migrate 0.14.0
```

**预期输出**:
```
╔══════════════════════════════════════════════════════════════════
║ 数据库迁移计划
╠══════════════════════════════════════════════════════════════════
║ 当前版本: v0.13.0
║ 目标版本: v0.14.0
║ 迁移步骤: 1 个
╠══════════════════════════════════════════════════════════════════
✅ Migration v0.13.0 → v0.14.0 completed
```

### 2. 验证安装

```bash
python3 -c "
from agentos.core.supervisor import SupervisorService
from agentos.core.supervisor.policies import OnTaskCreatedPolicy
print('✅ Supervisor installed successfully!')
"
```

### 3. 运行基础示例

```python
from pathlib import Path
from agentos.core.supervisor import SupervisorService
from agentos.core.supervisor.supervisor import SupervisorProcessor
from agentos.core.supervisor.router import PolicyRouter
from agentos.core.supervisor.policies import (
    OnTaskCreatedPolicy,
    OnStepCompletedPolicy,
    OnTaskFailedPolicy,
)

# 配置
db_path = Path("~/.agentos/store/registry.sqlite").expanduser()

# 创建 Policy Router
router = PolicyRouter()
router.register("TASK_CREATED", OnTaskCreatedPolicy(db_path))
router.register("TASK_STEP_COMPLETED", OnStepCompletedPolicy(db_path))
router.register("TASK_FAILED", OnTaskFailedPolicy(db_path))

# 创建 Processor 和 Service
processor = SupervisorProcessor(db_path, policy_router=router)
service = SupervisorService(db_path, processor, poll_interval=10)

# 启动
service.start()
print("✅ Supervisor is running!")

# ... 你的应用运行 ...

# 停止
service.stop()
print("✅ Supervisor stopped")
```

---

## 📊 验证 Supervisor 正在工作

### 检查 Inbox

```python
from pathlib import Path
from agentos.core.supervisor.inbox import InboxManager

db_path = Path("~/.agentos/store/registry.sqlite").expanduser()
inbox = InboxManager(db_path)

metrics = inbox.get_backlog_metrics()
print(f"Pending events: {metrics['pending_count']}")
print(f"Completed events: {metrics['completed_count']}")
print(f"Failed events: {metrics['failed_count']}")
```

### 查看审计事件

```python
from pathlib import Path
from agentos.core.supervisor.adapters import AuditAdapter

db_path = Path("~/.agentos/store/registry.sqlite").expanduser()
audit = AuditAdapter(db_path)

# 获取某个任务的 Supervisor 审计轨迹
events = audit.get_audit_trail(task_id="task_abc123")

for event in events:
    print(f"{event['created_at']}: {event['event_type']}")
    print(f"  Reason: {event['payload'].get('reason', 'N/A')}")
```

### 检查 Checkpoint

```python
from pathlib import Path
from agentos.core.supervisor.poller import EventPoller
from agentos.core.supervisor.inbox import InboxManager

db_path = Path("~/.agentos/store/registry.sqlite").expanduser()
inbox = InboxManager(db_path)
poller = EventPoller(db_path, inbox)

status = poller.get_checkpoint_status()
print(f"Source: {status['source_table']}")
print(f"Last seen ID: {status['last_seen_id']}")
print(f"Updated at: {status['updated_at']}")
```

---

## 🧪 运行测试

### 单元测试

```bash
# 安装依赖
pip install pytest pytest-cov

# 运行所有单元测试
pytest tests/unit/supervisor/ -v

# 运行特定测试
pytest tests/unit/supervisor/test_supervisor_models.py -v

# 带覆盖率报告
pytest tests/unit/supervisor/ --cov=agentos.core.supervisor --cov-report=html
```

### 集成测试

```bash
# 运行所有集成测试
pytest tests/integration/supervisor/ -v

# 运行特定测试
pytest tests/integration/supervisor/test_supervisor_drives_task_state_machine.py -v

# 使用测试运行器（推荐）
cd tests/integration/supervisor
./run_tests.sh
```

---

## 📚 深入学习

### 必读文档（按顺序）

1. **[Supervisor 主文档](./docs/governance/supervisor.md)** (15 分钟)
   - 架构概览
   - 核心概念
   - 数据流

2. **[运维手册](./docs/governance/supervisor_runbook.md)** (10 分钟)
   - 启动和配置
   - 监控指标
   - 故障排查

3. **[Policy 文档](./docs/governance/supervisor_policies.md)** (20 分钟)
   - 三个核心 Policy
   - 如何扩展
   - 最佳实践

### 可选文档

- **[事件契约](./docs/governance/supervisor_events.md)** - 事件格式详解
- **[验证层级](./docs/governance/VALIDATION_LAYERS.md)** - Supervisor 在治理体系中的位置
- **[实现报告](./docs/governance/SUPERVISOR_MVP_IMPLEMENTATION.md)** - 完整的实现细节

---

## 🔧 常见任务

### 添加新的 Policy

```python
from agentos.core.supervisor.policies.base import BasePolicy
from agentos.core.supervisor.models import SupervisorEvent, Decision, DecisionType

class MyCustomPolicy(BasePolicy):
    def evaluate(self, event: SupervisorEvent, cursor) -> Decision:
        # 你的决策逻辑
        return Decision(
            decision_type=DecisionType.ALLOW,
            reason="Custom policy evaluation passed",
            findings=[],
            actions=[]
        )

# 注册到 router
router.register("MY_CUSTOM_EVENT", MyCustomPolicy(db_path))
```

### 监控 Supervisor 健康

```python
from agentos.core.supervisor.inbox import InboxManager

def check_supervisor_health(db_path):
    inbox = InboxManager(db_path)
    metrics = inbox.get_backlog_metrics()

    # 检查积压
    if metrics['pending_count'] > 100:
        print("⚠️  WARNING: High backlog!")

    # 检查失败率
    total = metrics['completed_count'] + metrics['failed_count']
    if total > 0:
        failure_rate = metrics['failed_count'] / total
        if failure_rate > 0.05:
            print(f"⚠️  WARNING: High failure rate: {failure_rate:.1%}")

    # 检查延迟
    if metrics['oldest_pending_age_seconds']:
        if metrics['oldest_pending_age_seconds'] > 60:
            print(f"⚠️  WARNING: High lag: {metrics['oldest_pending_age_seconds']}s")

    print("✅ Supervisor health check passed")

check_supervisor_health(db_path)
```

### 手动触发 Polling

```python
from agentos.core.supervisor.poller import EventPoller
from agentos.core.supervisor.inbox import InboxManager

inbox = InboxManager(db_path)
poller = EventPoller(db_path, inbox)

# 扫描新事件
count = poller.scan()
print(f"Polled {count} new events")
```

---

## 🐛 故障排查

### 问题：事件没有被处理

**检查清单**:
1. Supervisor 服务是否启动？
2. EventBus 订阅是否成功？
3. Inbox 中有待处理事件吗？
4. Policy Router 是否正确注册了 policy？

```python
# 检查 Inbox
inbox = InboxManager(db_path)
print(f"Pending: {inbox.get_pending_count()}")

# 检查 Router
print(f"Registered policies: {router.list_registered_policies()}")
```

### 问题：处理失败率高

**检查清单**:
1. 查看失败事件的错误信息
2. 检查 policy 代码是否有 bug
3. 检查 evaluator/gate 依赖是否正常

```sql
-- 查看失败事件
SELECT event_id, event_type, error_message
FROM supervisor_inbox
WHERE status = 'failed'
ORDER BY received_at DESC
LIMIT 10;
```

### 问题：处理延迟高

**可能原因**:
1. Policy 执行时间过长
2. Evaluator 评估慢
3. 数据库锁竞争
4. poll_interval 设置过大

**解决方案**:
- 减小 poll_interval（默认 10s）
- 优化 policy 逻辑
- 增加批处理大小

---

## 📞 获取帮助

### 文档
- 主文档：`docs/governance/supervisor.md`
- 运维手册：`docs/governance/supervisor_runbook.md`
- Policy 文档：`docs/governance/supervisor_policies.md`

### 测试示例
- 单元测试：`tests/unit/supervisor/`
- 集成测试：`tests/integration/supervisor/`

### 问题反馈
- GitHub Issues: `github.com/agentos/issues`
- 查看日志：`~/.agentos/logs/supervisor.log`

---

## 🎉 完成！

你已经成功启动 Supervisor MVP！

**下一步**:
1. 阅读 [Supervisor 主文档](./docs/governance/supervisor.md)
2. 运行测试验证
3. 集成到你的应用
4. 监控运行指标

祝你使用愉快！🚀
