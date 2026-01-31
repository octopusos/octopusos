# Task #7: Mode Alerts System - Quick Reference

## 🎯 快速开始

### 最简单的用法
```python
from agentos.core.mode.mode_alerts import alert_mode_violation

# 报告违规（自动使用 ERROR 级别）
alert_mode_violation(
    mode_id="autonomous_mode",
    operation="apply_diff",
    message="Attempted to delete protected file",
    context={"file": "config.py", "action": "blocked"}
)
```

### 自定义严重级别
```python
from agentos.core.mode.mode_alerts import get_alert_aggregator, AlertSeverity

aggregator = get_alert_aggregator()

aggregator.alert(
    severity=AlertSeverity.WARNING,
    mode_id="manual_mode",
    operation="commit",
    message="Commit took longer than expected",
    context={"duration": 45}
)
```

---

## 📊 严重级别

| 级别 | 值 | Emoji | 用途 |
|------|-----|-------|------|
| INFO | `"info"` | ℹ️ | 信息性消息 |
| WARNING | `"warning"` | ⚠️ | 潜在问题 |
| ERROR | `"error"` | ❌ | 操作失败 |
| CRITICAL | `"critical"` | 🚨 | 系统级故障 |

---

## 🔌 输出通道

### 1. 控制台输出（默认）
```python
from agentos.core.mode.mode_alerts import ConsoleAlertOutput

output = ConsoleAlertOutput(use_color=True)
aggregator.add_output(output)
```

### 2. 文件输出（JSONL）
```python
from agentos.core.mode.mode_alerts import FileAlertOutput
from pathlib import Path

output = FileAlertOutput(Path("/var/log/mode_alerts.jsonl"))
aggregator.add_output(output)
```

### 3. Webhook 输出
```python
from agentos.core.mode.mode_alerts import WebhookAlertOutput

output = WebhookAlertOutput("https://monitoring.example.com/alerts")
aggregator.add_output(output)
```

---

## 📈 统计信息

```python
# 获取统计
stats = aggregator.get_stats()

# 返回结构
{
    "total_alerts": 42,
    "recent_count": 42,
    "severity_breakdown": {
        "info": 20,
        "warning": 15,
        "error": 5,
        "critical": 2
    },
    "max_recent": 100,
    "output_count": 3
}
```

### 获取最近告警
```python
# 获取最近 10 条
recent = aggregator.get_recent_alerts(limit=10)

for alert in recent:
    print(f"{alert.severity}: {alert.message}")
```

---

## 🏗️ 核心 API

### AlertSeverity
```python
class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

### ModeAlert
```python
@dataclass
class ModeAlert:
    timestamp: str          # ISO 8601 UTC
    severity: AlertSeverity
    mode_id: str           # "autonomous_mode", "manual_mode"
    operation: str         # "apply_diff", "commit", "push"
    message: str           # Human-readable message
    context: Dict[str, Any] # Additional data

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization"""
```

### ModeAlertAggregator
```python
class ModeAlertAggregator:
    def add_output(self, output: AlertOutput):
        """Add an output channel"""

    def alert(
        self,
        severity: AlertSeverity,
        mode_id: str,
        operation: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Send an alert"""

    def get_stats(self) -> dict:
        """Get statistics"""

    def get_recent_alerts(self, limit: Optional[int] = None) -> List[ModeAlert]:
        """Get recent alerts"""

    def clear_recent(self):
        """Clear recent buffer"""
```

### 全局函数
```python
def get_alert_aggregator() -> ModeAlertAggregator:
    """Get global singleton (auto-initializes with console output)"""

def alert_mode_violation(
    mode_id: str,
    operation: str,
    message: str,
    context: Optional[Dict[str, Any]] = None
):
    """Quick helper for ERROR-level alerts"""

def reset_global_aggregator():
    """Reset global instance (for testing)"""
```

---

## 💡 使用场景

### 场景 1: Mode Policy 违规
```python
# mode_policy.py
from .mode_alerts import alert_mode_violation

if constraint.violated:
    alert_mode_violation(
        mode_id=self.mode_id,
        operation="apply_diff",
        message=f"Constraint violated: {constraint.name}",
        context={
            "constraint": constraint.to_dict(),
            "action": action.to_dict()
        }
    )
```

### 场景 2: Executor 操作监控
```python
# executor_engine.py
from agentos.core.mode.mode_alerts import get_alert_aggregator, AlertSeverity

aggregator = get_alert_aggregator()

# 操作开始
aggregator.alert(
    AlertSeverity.INFO,
    self.mode_id,
    "apply_diff",
    "Starting diff application",
    context={"changes": len(diff.hunks)}
)

# 检测到问题
if len(diff.changes) > 200:
    aggregator.alert(
        AlertSeverity.WARNING,
        self.mode_id,
        "apply_diff",
        "Large diff detected - may need review",
        context={"lines": len(diff.changes), "threshold": 200}
    )

# 操作完成
aggregator.alert(
    AlertSeverity.INFO,
    self.mode_id,
    "apply_diff",
    "Diff applied successfully",
    context={"files_modified": 5}
)
```

### 场景 3: WebUI 监控
```python
# webui/api/mode_monitoring.py
from fastapi import APIRouter
from agentos.core.mode.mode_alerts import get_alert_aggregator

router = APIRouter()

@router.get("/api/mode/alerts/stats")
def get_alert_stats():
    return get_alert_aggregator().get_stats()

@router.get("/api/mode/alerts/recent")
def get_recent_alerts(limit: int = 100):
    aggregator = get_alert_aggregator()
    alerts = aggregator.get_recent_alerts(limit)
    return [alert.to_dict() for alert in alerts]
```

---

## 🎨 输出示例

### 控制台输出
```
[2026-01-30T13:13:43.276107+00:00] ❌ ERROR [autonomous_mode] apply_diff: Attempted to delete protected file
  Context: {
  "file": "critical_config.py",
  "constraint": "no_delete_protected",
  "action": "blocked"
}
```

### JSONL 文件输出
```jsonl
{"timestamp": "2026-01-30T13:13:43.276107+00:00", "severity": "error", "mode_id": "autonomous_mode", "operation": "apply_diff", "message": "Attempted to delete protected file", "context": {"file": "critical_config.py", "constraint": "no_delete_protected", "action": "blocked"}}
```

### Webhook 输出（简化）
```
🌐 [Webhook] POST https://monitoring.example.com/alerts
  Payload: {
  "timestamp": "2026-01-30T13:13:43.276107+00:00",
  "severity": "error",
  "mode_id": "autonomous_mode",
  "operation": "apply_diff",
  "message": "Attempted to delete protected file",
  "context": {...}
}
```

---

## ✅ 测试验证

```bash
# 运行测试套件
python3 test_mode_alerts_standalone.py

# 预期输出
🎉 ALL TESTS PASSED!
Results: 10/10 tests passed (100%)
```

---

## 📂 文件位置

| 文件 | 路径 |
|------|------|
| 核心实现 | `/Users/pangge/PycharmProjects/AgentOS/agentos/core/mode/mode_alerts.py` |
| 测试套件 | `/Users/pangge/PycharmProjects/AgentOS/test_mode_alerts_standalone.py` |
| 使用示例 | `/Users/pangge/PycharmProjects/AgentOS/examples/mode_alerts_demo.py` |
| 完成报告 | `/Users/pangge/PycharmProjects/AgentOS/TASK7_MODE_ALERTS_COMPLETION_REPORT.md` |

---

## 🔗 相关文档

- [Mode Policy Engine 文档](./agentos/core/mode/README_POLICY.md)
- [Mode Policy 配置指南](./agentos/core/mode/mode_policy.json)
- [Task #7 完成报告](./TASK7_MODE_ALERTS_COMPLETION_REPORT.md)

---

## 🚀 下一步

1. **Task #8**: 集成告警到 `executor_engine.py`
2. **Task #10**: 编写告警系统单元测试（pytest）
3. **Task #11**: 创建 Gate GM4 告警集成验证

---

**创建时间**: 2026-01-30
**版本**: v1.0
**状态**: ✅ Ready for use
