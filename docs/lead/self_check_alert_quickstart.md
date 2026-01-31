# Self-Check Alert 快速上手指南

## 什么是 Self-Check Alert?

Self-Check Alert 是 Lead Agent 的自检告警机制，用于检测"有数据但检测不到风险"的 silent failure。

**核心思想**: 如果 Storage 返回了数据，但 Miner 输出 0 个 findings，这通常意味着系统出了问题。

## 快速开始

### 1. 运行扫描

```bash
# 预览模式（推荐先用这个）
python -m agentos.jobs.lead_scan --window 24h --dry-run

# 实际运行
python -m agentos.jobs.lead_scan --window 24h
```

### 2. 查看告警

如果触发告警，你会看到：

```
🚨 ALERT: POTENTIAL SILENT FAILURE
High-priority signals detected (high_risk_allow=1, blocked=5) but Miner produced 0 findings. This is abnormal.
```

### 3. 运行测试

```bash
source .venv/bin/activate
python tests/unit/lead/run_self_check_tests.py
```

## 告警类型

### 高优先级告警（严重）

触发条件：
- high_risk_allow >= 1（默认阈值）
- 或 blocked >= 5（默认阈值）
- 且 findings = 0

示例：
```
High-priority signals detected (high_risk_allow=1, blocked=0) but Miner produced 0 findings.
```

### 通用告警

触发条件：
- 有任何 storage 数据（blocked, pause_block, retry_fail, high_risk_allow）
- 且 findings = 0

示例：
```
Storage returned 5 items (blocked=5, pause_block=0, retry_fail=0, high_risk_allow=0) but Miner produced 0 findings.
```

### INFO 提示

触发条件：
- 24h 窗口
- 完全没有数据

示例：
```
ℹ️  INFO: 24h scan found no data. This is normal if system is healthy.
```

## 配置阈值

### 使用默认阈值

```python
from agentos.jobs.lead_scan import LeadScanJob

job = LeadScanJob()
result = job.run_scan("24h", dry_run=False)
```

默认阈值：
- `min_blocked_for_alert`: 5
- `min_high_risk_for_alert`: 1

### 自定义阈值

```python
job = LeadScanJob(
    alert_thresholds={
        "min_blocked_for_alert": 10,    # 需要 10 个 blocked 才触发高优先级告警
        "min_high_risk_for_alert": 2    # 需要 2 个 high_risk_allow 才触发高优先级告警
    }
)
```

## 检查扫描结果

```python
result = job.run_scan("24h", dry_run=False)

# 查看自检结果
self_check = result["self_check"]

if self_check["alert_triggered"]:
    print(f"Alert triggered: {self_check['alert_reason']}")
    print(f"Storage items: {self_check['storage_items_count']}")
    print(f"Findings: {self_check['findings_count']}")
else:
    print("No alerts - system is healthy")
```

## 常见问题

### Q: 为什么会触发告警？

可能的原因：

1. **契约不匹配**: Storage 和 Miner 的版本不兼容
   - 检查 `result["contract_versions"]`
   - 确保 Storage 和 Miner 的 CONTRACT_VERSION 一致

2. **规则阈值过高**: Miner 配置的阈值太高，所有数据都被过滤了
   - 检查 MinerConfig 的阈值设置
   - 降低阈值重新测试

3. **转换层问题**: 数据转换逻辑有 bug
   - 检查 ContractMapper.convert_storage_to_miner()
   - 查看转换后的 miner_data 是否正确

4. **Miner 规则 bug**: 规则实现有问题
   - 查看 Miner 日志
   - 运行单元测试验证规则

### Q: 如何抑制告警？

如果你确认当前情况是正常的（例如，系统确实没有风险），可以：

1. **调整阈值**:
   ```python
   job = LeadScanJob(alert_thresholds={
       "min_blocked_for_alert": 100,  # 设置很高的阈值
       "min_high_risk_for_alert": 10
   })
   ```

2. **忽略告警**:
   ```python
   result = job.run_scan("24h", dry_run=False)
   if result["self_check"]["alert_triggered"]:
       # 记录但不采取行动
       logger.info("Self-check alert triggered, but ignoring")
   ```

### Q: 如何测试自检功能？

运行单元测试：

```bash
python tests/unit/lead/run_self_check_tests.py
```

或查看特定测试：

```python
from tests.unit.lead.test_self_check_alert import *

# 测试有数据但 findings=0
test_alert_when_storage_has_data_but_findings_zero()

# 测试高优先级告警
test_alert_when_high_risk_allow_but_findings_zero()
```

## 集成到监控系统

### 发送到 Slack

```python
import requests

result = job.run_scan("24h", dry_run=False)

if result["self_check"]["alert_triggered"]:
    slack_webhook = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    message = {
        "text": f"🚨 Lead Agent Alert: {result['self_check']['alert_reason']}"
    }
    requests.post(slack_webhook, json=message)
```

### 记录到数据库

```python
import sqlite3
from datetime import datetime, timezone

result = job.run_scan("24h", dry_run=False)

if result["self_check"]["alert_triggered"]:
    conn = sqlite3.connect("alerts.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lead_alerts (timestamp, reason, storage_items, findings)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        result["self_check"]["alert_reason"],
        result["self_check"]["storage_items_count"],
        result["self_check"]["findings_count"]
    ))
    conn.commit()
    conn.close()
```

## 最佳实践

1. **始终先用 dry-run 模式测试**
   ```bash
   python -m agentos.jobs.lead_scan --window 24h --dry-run
   ```

2. **定期审查告警历史**
   - 分析告警模式
   - 优化阈值配置

3. **告警响应流程**
   - 检查契约版本
   - 查看 Storage 数据和 Miner 输出
   - 运行单元测试验证
   - 必要时回滚或修复

4. **避免告警疲劳**
   - 设置合理的阈值
   - 添加告警抑制机制
   - 使用告警聚合

## 相关命令

```bash
# 运行扫描（预览）
python -m agentos.jobs.lead_scan --window 24h --dry-run

# 运行扫描（实际）
python -m agentos.jobs.lead_scan --window 24h

# 7天窗口
python -m agentos.jobs.lead_scan --window 7d

# 强制运行（跳过并发检查）
python -m agentos.jobs.lead_scan --window 24h --force

# 运行测试
python tests/unit/lead/run_self_check_tests.py
```

## 下一步

- 查看完整文档: [Self-Check Alert 实施报告](./self_check_alert_implementation.md)
- 了解规则: [Risk Miner 规则文档](./risk_miner_rules.md)
- 契约管理: [契约版本管理](./contract_version_management.md)
