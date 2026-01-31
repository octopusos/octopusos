# Mode System 100% 快速入门指南

## 5 分钟快速入门

### 什么是 Mode System？

Mode System 是 AgentOS 的权限管理框架，由三个核心组件构成:

1. **Mode Policy (策略引擎)** - 定义每个 mode 允许的操作（如 commit、diff）
2. **Mode Alerts (告警聚合器)** - 在违规操作时发送多渠道告警
3. **Mode Monitor (监控面板)** - 实时查看告警和统计信息

### 核心功能

- ✅ **可配置权限**: 通过 JSON 文件定义策略，无需修改代码
- ✅ **多渠道告警**: 支持控制台、文件、Webhook
- ✅ **实时监控**: Web 界面查看告警和统计
- ✅ **安全默认值**: 未知 mode 自动禁止危险操作

---

## 快速开始

### 1. 查看当前策略

```python
from agentos.core.mode.mode_policy import get_global_policy

# 获取全局策略
policy = get_global_policy()

# 查看所有已定义的 modes
print(policy.get_all_modes())
# 输出: {'implementation', 'design', 'chat', 'planning', 'debug', 'ops', 'test', 'release'}

# 检查权限
print(policy.check_permission("implementation", "commit"))  # True
print(policy.check_permission("design", "commit"))          # False
```

### 2. 加载自定义策略

**方法 A: 环境变量 (推荐生产环境)**

```bash
# 设置策略文件路径
export MODE_POLICY_PATH=/path/to/custom_policy.json

# 启动应用，策略自动加载
python -m agentos.cli.main
```

**方法 B: Python API (推荐开发环境)**

```python
from pathlib import Path
from agentos.core.mode.mode_policy import load_policy_from_file

# 加载开发模式策略
policy = load_policy_from_file(Path("configs/mode/dev_policy.json"))

# 或加载严格模式策略
policy = load_policy_from_file(Path("configs/mode/strict_policy.json"))
```

### 3. 发送告警

**快速发送违规告警**:

```python
from agentos.core.mode.mode_alerts import alert_mode_violation

# 发送 ERROR 级别告警
alert_mode_violation(
    mode_id="design",
    operation="apply_diff",
    message="Design mode attempted to apply diff",
    context={"file_path": "/path/to/file.py"}
)
```

**自定义严重级别**:

```python
from agentos.core.mode.mode_alerts import get_alert_aggregator, AlertSeverity

aggregator = get_alert_aggregator()

# INFO 级别
aggregator.alert(
    severity=AlertSeverity.INFO,
    mode_id="implementation",
    operation="commit",
    message="Code committed successfully"
)

# WARNING 级别
aggregator.alert(
    severity=AlertSeverity.WARNING,
    mode_id="test",
    operation="test_run",
    message="Test execution took longer than expected",
    context={"duration_seconds": 120}
)

# CRITICAL 级别
aggregator.alert(
    severity=AlertSeverity.CRITICAL,
    mode_id="ops",
    operation="system_restart",
    message="System restart initiated",
    context={"reason": "out_of_memory"}
)
```

### 4. 配置告警输出

**添加文件输出**:

```python
from pathlib import Path
from agentos.core.mode.mode_alerts import get_alert_aggregator, FileAlertOutput

aggregator = get_alert_aggregator()

# 添加 JSONL 文件输出
file_output = FileAlertOutput(Path("logs/mode_alerts.jsonl"))
aggregator.add_output(file_output)
```

**添加 Webhook 输出**:

```python
from agentos.core.mode.mode_alerts import WebhookAlertOutput

webhook_output = WebhookAlertOutput("https://example.com/webhook")
aggregator.add_output(webhook_output)
```

### 5. 访问监控面板

**启动 WebUI**:

```bash
# 启动 Web 服务器
python -m agentos.webui.app

# 默认端口: 5000
# 浏览器访问: http://localhost:5000
```

**访问监控页面**:

1. 打开浏览器: `http://localhost:5000`
2. 导航到 "Mode Monitor" 页面
3. 查看实时统计和告警列表
4. 页面每 10 秒自动刷新

**使用 REST API**:

```bash
# 获取告警列表
curl http://localhost:5000/api/mode/alerts

# 获取统计信息
curl http://localhost:5000/api/mode/stats

# 清空告警缓存
curl -X POST http://localhost:5000/api/mode/clear
```

---

## 常用命令

### 验证系统完整性

```bash
# 运行 100% 完成度验证脚本
./scripts/verify_mode_100_completion.sh

# 检查退出码
echo $?  # 0 = 成功, 1 = 失败
```

### 运行测试

```bash
# 运行所有 mode 单元测试
pytest tests/unit/mode/ -v

# 运行策略引擎测试
pytest tests/unit/mode/test_mode_policy.py -v

# 运行告警系统测试
pytest tests/unit/mode/test_mode_alerts.py -v

# 运行 E2E 测试
pytest tests/e2e/test_mode_pipeline_demo.py -v

# 查看代码覆盖率
pytest tests/unit/mode/ --cov=agentos.core.mode --cov-report=html
open htmlcov/index.html
```

### 运行 Gate 验证

```bash
# Gate GM3: 策略强制执行
python scripts/gates/gm3_mode_policy_enforcement.py

# Gate GM4: 告警集成
python scripts/gates/gm4_mode_alert_integration.py

# 其他 Mode Gates
python scripts/gates/gch1_mode_chat_no_diff.py
python scripts/gates/gdbg1_mode_debug_no_diff.py
python scripts/gates/gmd1_mode_design_no_diff.py
```

### 查看日志

```bash
# 查看告警日志 (JSONL 格式)
tail -f logs/mode_alerts.jsonl

# 查看 WebUI 日志
tail -f logs/webui.log | grep mode

# 查看应用日志
tail -f logs/agentos.log | grep "Policy\|Alert"
```

---

## 配置文件

### 策略文件位置

```
configs/mode/
├── default_policy.json   # 生产默认策略
├── strict_policy.json    # 严格模式（禁止所有 commit/diff）
├── dev_policy.json       # 开发模式（宽松权限）
└── alert_config.json     # 告警配置
```

### 策略文件格式

```json
{
  "version": "1.0",
  "description": "自定义策略描述",
  "modes": {
    "implementation": {
      "allows_commit": true,
      "allows_diff": true,
      "allowed_operations": ["read", "write", "execute", "commit", "diff"],
      "risk_level": "high"
    },
    "design": {
      "allows_commit": false,
      "allows_diff": false,
      "allowed_operations": ["read"],
      "risk_level": "low"
    }
  }
}
```

### 告警配置格式

```json
{
  "outputs": {
    "console": {
      "enabled": true,
      "use_color": true
    },
    "file": {
      "enabled": true,
      "path": "logs/mode_alerts.jsonl"
    },
    "webhook": {
      "enabled": false,
      "url": "https://example.com/alerts"
    }
  },
  "filters": {
    "min_severity": "warning"
  }
}
```

---

## 故障排查

### 问题 1: 策略文件未加载

**症状**:
```
WARNING: Unknown mode_id 'custom_mode', returning safe default permissions
```

**解决方案**:
```bash
# 1. 检查环境变量
echo $MODE_POLICY_PATH

# 2. 检查文件是否存在
ls -l $MODE_POLICY_PATH

# 3. 验证 JSON 格式
python -m json.tool < $MODE_POLICY_PATH

# 4. 查看加载日志
grep "Policy loaded" logs/agentos.log
```

### 问题 2: 告警未写入文件

**症状**: 控制台显示告警，但文件为空

**解决方案**:
```python
# 1. 检查是否添加了文件输出
from agentos.core.mode.mode_alerts import get_alert_aggregator

aggregator = get_alert_aggregator()
print(f"Outputs: {[type(o).__name__ for o in aggregator.outputs]}")
# 应该包含: ['ConsoleAlertOutput', 'FileAlertOutput']

# 2. 检查文件权限
import os
log_file = "logs/mode_alerts.jsonl"
if os.path.exists(log_file):
    print(f"File exists, size: {os.path.getsize(log_file)} bytes")
else:
    print("File does not exist, check parent directory permissions")

# 3. 手动测试文件写入
from pathlib import Path
from agentos.core.mode.mode_alerts import FileAlertOutput, alert_mode_violation

file_output = FileAlertOutput(Path("test_alerts.jsonl"))
aggregator.add_output(file_output)

alert_mode_violation("test", "test_op", "Test message")
# 检查 test_alerts.jsonl 是否创建
```

### 问题 3: 监控面板显示错误

**症状**: 浏览器显示 "Failed to load alerts"

**解决方案**:
```bash
# 1. 检查后端 API 是否响应
curl http://localhost:5000/api/mode/stats

# 2. 检查 WebUI 是否启动
ps aux | grep "agentos.webui.app"

# 3. 查看后端日志
tail -f logs/webui.log

# 4. 清空浏览器缓存
# Chrome: Ctrl+Shift+Delete
# Firefox: Ctrl+Shift+Delete
# Safari: Cmd+Option+E
```

### 问题 4: 权限检查总是返回 False

**症状**: 所有 mode 都禁止 commit/diff

**解决方案**:
```python
# 1. 检查是否加载了严格策略
from agentos.core.mode.mode_policy import get_global_policy

policy = get_global_policy()
print(f"Policy version: {policy.get_policy_version()}")

# 2. 检查 implementation mode 权限
perms = policy.get_permissions("implementation")
print(f"allows_commit: {perms.allows_commit}")
print(f"allows_diff: {perms.allows_diff}")

# 3. 如果权限错误，重新加载默认策略
from pathlib import Path
from agentos.core.mode.mode_policy import load_policy_from_file

load_policy_from_file(Path("configs/mode/default_policy.json"))
```

---

## 实用技巧

### 技巧 1: 临时禁用告警

```python
from agentos.core.mode.mode_alerts import get_alert_aggregator

aggregator = get_alert_aggregator()

# 保存当前输出
old_outputs = aggregator.outputs.copy()

# 清空输出（禁用告警）
aggregator.outputs.clear()

# 执行操作
# ... your code ...

# 恢复输出
aggregator.outputs = old_outputs
```

### 技巧 2: 查看最近告警

```python
from agentos.core.mode.mode_alerts import get_alert_aggregator

aggregator = get_alert_aggregator()

# 获取最近 10 条告警
recent_alerts = aggregator.get_recent_alerts(limit=10)

for alert in recent_alerts:
    print(f"[{alert.timestamp}] {alert.severity}: {alert.message}")
```

### 技巧 3: 统计告警

```python
from agentos.core.mode.mode_alerts import get_alert_aggregator

aggregator = get_alert_aggregator()

# 获取统计信息
stats = aggregator.get_stats()

print(f"Total alerts: {stats['total_alerts']}")
print(f"Errors: {stats['severity_breakdown']['error']}")
print(f"Warnings: {stats['severity_breakdown']['warning']}")
print(f"Info: {stats['severity_breakdown']['info']}")
```

### 技巧 4: 自定义策略模板

```bash
# 复制默认策略作为模板
cp configs/mode/default_policy.json configs/mode/my_policy.json

# 编辑文件
vim configs/mode/my_policy.json

# 加载自定义策略
export MODE_POLICY_PATH=configs/mode/my_policy.json
```

### 技巧 5: 批量查询权限

```python
from agentos.core.mode.mode_policy import get_global_policy

policy = get_global_policy()

# 查询所有 mode 的 commit 权限
modes = policy.get_all_modes()
for mode_id in modes:
    allows_commit = policy.check_permission(mode_id, "commit")
    symbol = "✅" if allows_commit else "❌"
    print(f"{symbol} {mode_id}: commit={allows_commit}")
```

---

## 进阶用法

### 1. 动态权限检查

```python
from agentos.core.mode.mode_policy import get_global_policy

def safe_operation(mode_id: str, operation: str):
    """安全的操作封装，自动检查权限"""
    policy = get_global_policy()

    if not policy.check_permission(mode_id, operation):
        from agentos.core.mode.mode_alerts import alert_mode_violation

        alert_mode_violation(
            mode_id=mode_id,
            operation=operation,
            message=f"Permission denied: {mode_id} cannot perform {operation}",
            context={"requested_operation": operation}
        )
        raise PermissionError(f"{mode_id} does not allow {operation}")

    # 执行操作
    print(f"Executing {operation} in {mode_id} mode...")

# 使用示例
try:
    safe_operation("design", "commit")
except PermissionError as e:
    print(f"Operation blocked: {e}")
```

### 2. 告警过滤

```python
from agentos.core.mode.mode_alerts import (
    get_alert_aggregator,
    AlertSeverity,
    AlertOutput,
    ModeAlert
)

class FilteredAlertOutput(AlertOutput):
    """仅输出 ERROR 和 CRITICAL 级别的告警"""

    def __init__(self, base_output: AlertOutput):
        self.base_output = base_output

    def send(self, alert: ModeAlert):
        # 仅转发高优先级告警
        if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            self.base_output.send(alert)

# 使用示例
from agentos.core.mode.mode_alerts import ConsoleAlertOutput

aggregator = get_alert_aggregator()
console_output = ConsoleAlertOutput()
filtered_output = FilteredAlertOutput(console_output)
aggregator.add_output(filtered_output)
```

### 3. 策略比较工具

```python
from pathlib import Path
from agentos.core.mode.mode_policy import ModePolicy

def compare_policies(path1: Path, path2: Path):
    """比较两个策略文件的差异"""
    policy1 = ModePolicy(path1)
    policy2 = ModePolicy(path2)

    all_modes = policy1.get_all_modes() | policy2.get_all_modes()

    print(f"Comparing {path1.name} vs {path2.name}")
    print("-" * 60)

    for mode_id in sorted(all_modes):
        perms1 = policy1.get_permissions(mode_id)
        perms2 = policy2.get_permissions(mode_id)

        if perms1.allows_commit != perms2.allows_commit:
            print(f"⚠️  {mode_id}.allows_commit: {perms1.allows_commit} → {perms2.allows_commit}")

        if perms1.allows_diff != perms2.allows_diff:
            print(f"⚠️  {mode_id}.allows_diff: {perms1.allows_diff} → {perms2.allows_diff}")

# 使用示例
compare_policies(
    Path("configs/mode/default_policy.json"),
    Path("configs/mode/strict_policy.json")
)
```

---

## 参考链接

### 核心文档
- [完成度报告](MODE_SYSTEM_100_COMPLETION_REPORT.md)
- [策略配置指南](agentos/core/mode/README_POLICY.md)
- [验证指南](TASK16_MODE_100_VERIFICATION_GUIDE.md)

### 实施报告
- [Mode Policy 实施报告](TASK1_MODE_POLICY_IMPLEMENTATION_REPORT.md)
- [Mode Alerts 实施报告](TASK7_MODE_ALERTS_COMPLETION_REPORT.md)
- [Mode Monitor 实施报告](TASK13_MODE_MONITOR_VIEW_COMPLETION_REPORT.md)

### API 文档
- [监控 API 指南](TASK12_MODE_MONITORING_API_GUIDE.md)
- [告警系统测试报告](TASK10_MODE_ALERTS_TESTING_REPORT.md)

### 源代码
- [mode_policy.py](agentos/core/mode/mode_policy.py)
- [mode_alerts.py](agentos/core/mode/mode_alerts.py)
- [ModeMonitorView.js](agentos/webui/static/js/views/ModeMonitorView.js)

---

## 版本信息

| 项目 | 值 |
|------|-----|
| **版本** | 1.0.0 |
| **发布日期** | 2026-01-30 |
| **状态** | 生产就绪 ✅ |
| **测试覆盖率** | 96% |
| **文档完整度** | 100% |

---

## 快速命令速查表

```bash
# === 验证 ===
./scripts/verify_mode_100_completion.sh              # 完整验证
python scripts/gates/gm3_mode_policy_enforcement.py  # Gate GM3
python scripts/gates/gm4_mode_alert_integration.py   # Gate GM4

# === 测试 ===
pytest tests/unit/mode/ -v                           # 单元测试
pytest tests/e2e/test_mode_pipeline_demo.py -v       # E2E 测试
pytest tests/unit/mode/ --cov=agentos.core.mode      # 覆盖率

# === WebUI ===
python -m agentos.webui.app                          # 启动 WebUI
curl http://localhost:5000/api/mode/alerts           # 获取告警
curl http://localhost:5000/api/mode/stats            # 获取统计

# === 日志 ===
tail -f logs/mode_alerts.jsonl                       # 告警日志
tail -f logs/webui.log | grep mode                   # WebUI 日志
grep "Policy loaded" logs/agentos.log                # 策略加载日志

# === 配置 ===
export MODE_POLICY_PATH=configs/mode/dev_policy.json # 设置策略
python -m json.tool < $MODE_POLICY_PATH              # 验证 JSON
```

---

**最后更新**: 2026-01-30
**维护者**: AgentOS Team
**问题反馈**: 请提交 Issue 到 GitHub
