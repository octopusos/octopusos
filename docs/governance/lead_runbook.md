# Lead Agent Runbook

## 概述

Lead Agent 是 AgentOS 的自动化风险检测和线索挖掘系统，通过定期扫描 Supervisor 决策历史，识别系统性风险、异常模式和潜在问题，并自动创建 follow-up tasks 供人工审查。

### 核心功能

- **自动风险检测**: 基于 6 条规则挖掘系统性问题
- **幂等去重**: 避免重复告警（基于 fingerprint）
- **自动任务创建**: 根据严重级别自动创建 DRAFT/APPROVED 任务
- **可观测性**: 提供详细的扫描日志和统计信息

### 扫描频率建议

- **24小时窗口**: 建议每天运行一次（用于快速发现新问题）
- **7天窗口**: 建议每周运行一次（用于发现趋势性问题）

---

## 运行方式

### 1. 命令行运行

Lead scan 作为独立的 Python 模块运行，支持多种参数：

```bash
# 基本用法
python -m agentos.jobs.lead_scan --window <24h|7d> [--dry-run] [--force]

# 示例：预览模式（不创建任务）
python -m agentos.jobs.lead_scan --window 24h --dry-run

# 示例：实际运行（创建任务）
python -m agentos.jobs.lead_scan --window 7d

# 示例：强制运行（跳过并发保护）
python -m agentos.jobs.lead_scan --window 24h --force

# 示例：指定数据库路径
python -m agentos.jobs.lead_scan --window 24h --db-path /path/to/store.db
```

### 2. 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--window` | 扫描窗口：`24h` 或 `7d` | `24h` |
| `--dry-run` | 预览模式，不创建任务 | `False` |
| `--force` | 强制运行，跳过并发检查 | `False` |
| `--db-path` | 数据库路径 | `~/.agentos/store.db` |

### 3. Dry-run vs 实际执行

**Dry-run 模式**（推荐用于测试）:
```bash
python -m agentos.jobs.lead_scan --window 24h --dry-run
```
- ✓ 执行规则检测
- ✓ 存储 findings 到 `lead_findings` 表
- ✗ 不创建 follow-up tasks
- 输出显示 "Would create N tasks"

**实际执行模式**:
```bash
python -m agentos.jobs.lead_scan --window 24h
```
- ✓ 执行规则检测
- ✓ 存储 findings
- ✓ 创建 follow-up tasks（根据严重级别）
- 输出显示 "Created N tasks"

---

## Cron 配置

### 推荐配置

在生产环境中，建议通过 cron 定期运行 Lead scan：

```bash
# 编辑 crontab
crontab -e
```

添加以下配置：

```cron
# Lead Agent 24h 扫描（每天凌晨 2:00）
0 2 * * * /usr/bin/python3 -m agentos.jobs.lead_scan --window 24h >> /var/log/agentos/lead_scan_24h.log 2>&1

# Lead Agent 7d 扫描（每周一凌晨 3:00）
0 3 * * 1 /usr/bin/python3 -m agentos.jobs.lead_scan --window 7d >> /var/log/agentos/lead_scan_7d.log 2>&1
```

### 日志目录配置

```bash
# 创建日志目录
sudo mkdir -p /var/log/agentos

# 设置权限
sudo chown $USER:$USER /var/log/agentos
```

### 日志轮转

为避免日志文件过大，建议配置 logrotate：

```bash
# /etc/logrotate.d/agentos
/var/log/agentos/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 user user
}
```

---

## 数据库 Migrations

### 安装与配置

Lead Agent 需要执行 2 个 database migrations：

1. **v16_lead_findings.sql** - 创建核心表（lead_findings）
2. **v21_audit_decision_fields.sql** - 性能优化（⚠️ 不可跳过）

**详细指南**: 见 `agentos/store/migrations/README.md`

### 快速执行

```bash
cd agentos/store/migrations

# 1. 执行 v16（核心表）
sqlite3 ~/.agentos/store.db < v16_lead_findings.sql

# 2. 执行 v21（性能优化）
sqlite3 ~/.agentos/store.db < v21_audit_decision_fields.sql
```

### 验证

```bash
# 检查 schema 版本
sqlite3 ~/.agentos/store.db "SELECT version FROM schema_metadata WHERE key='version';"
# 期望输出: 0.21.0

# 检查 lead_findings 表是否存在
sqlite3 ~/.agentos/store.db "SELECT name FROM sqlite_master WHERE type='table' AND name='lead_findings';"
# 期望输出: lead_findings

# 检查 v21 冗余列是否存在
sqlite3 ~/.agentos/store.db "PRAGMA table_info(task_audits);" | grep "source_event_ts"
# 期望有输出
```

### ⚠️ 重要说明

- **执行顺序**: 必须先执行 v16，再执行 v21（不可跳过或乱序）
- **v21 重要性**: 提供 10-100x 性能提升，禁止跳过
- **幂等性**: 所有 migrations 可安全重复执行
- **回滚**: 不建议回滚，请先备份数据库

完整迁移文档请参考 `agentos/store/migrations/README.md`。

---

## 监控与可观测性

### 1. 查看日志

扫描完成后，会在日志中输出详细的统计信息：

```bash
# 查看最近的扫描日志
tail -f /var/log/agentos/lead_scan_24h.log

# 搜索错误日志
grep "ERROR" /var/log/agentos/lead_scan_24h.log

# 查看最近 10 次扫描结果
grep "Lead scan result" /var/log/agentos/lead_scan_24h.log | tail -10
```

### 2. 关键指标

Lead scan 输出以下关键指标：

| 指标 | 说明 |
|------|------|
| `raw_findings` | 规则检测到的原始 findings 数 |
| `new_findings` | 去重后的新 findings 数 |
| `duplicate_findings` | 重复的 findings 数（已存在于数据库） |
| `tasks_created` | 创建的 follow-up tasks 数 |
| `tasks_skipped` | 跳过的任务数（已有 linked_task_id） |

### 3. 查看扫描结果

#### 方法 1: 查看 lead_findings 表

```sql
-- 查看最近的 findings
SELECT
    fingerprint,
    code,
    severity,
    title,
    window_kind,
    count,
    linked_task_id,
    last_seen_at
FROM lead_findings
ORDER BY last_seen_at DESC
LIMIT 20;

-- 统计各规则的发现数
SELECT
    code,
    COUNT(*) as total,
    SUM(count) as total_occurrences,
    COUNT(CASE WHEN linked_task_id IS NOT NULL THEN 1 END) as with_tasks
FROM lead_findings
GROUP BY code
ORDER BY total DESC;

-- 查看未处理的高风险 findings
SELECT *
FROM lead_findings
WHERE severity IN ('HIGH', 'CRITICAL')
  AND linked_task_id IS NULL
ORDER BY last_seen_at DESC;
```

#### 方法 2: 查看创建的 tasks

```sql
-- 查看 Lead Agent 创建的任务
SELECT
    task_id,
    title,
    status,
    created_at,
    JSON_EXTRACT(metadata, '$.lead_agent.severity') as severity,
    JSON_EXTRACT(metadata, '$.lead_agent.fingerprint') as fingerprint
FROM tasks
WHERE created_by = 'lead_agent'
ORDER BY created_at DESC
LIMIT 20;
```

### 4. 告警建议

建议监控以下异常情况并设置告警：

1. **扫描失败**: 连续多次扫描失败（检查日志中的 ERROR）
2. **高风险激增**: `CRITICAL` 或 `HIGH` findings 数突然增加
3. **扫描耗时过长**: 执行时间超过预期（正常应在 10 秒内完成）
4. **锁冲突**: 频繁出现 "另一个实例正在运行" 提示

---

## 故障排查

### 常见错误 1: 数据库不存在

**症状**:
```
sqlite3.OperationalError: unable to open database file
```

**解决方案**:
1. 检查数据库路径是否正确
2. 确保数据库文件已创建
3. 检查文件权限

```bash
# 检查数据库是否存在
ls -l ~/.agentos/store.db

# 如果不存在，需要先初始化数据库
# （通常由 AgentOS 启动时自动创建）
```

### 常见错误 2: lead_findings 表不存在

**症状**:
```
sqlite3.OperationalError: no such table: lead_findings
```

**解决方案**:
运行数据库迁移脚本：

```bash
# 查找迁移脚本
ls agentos/store/migrations/v14_supervisor.sql

# 手动执行迁移
sqlite3 ~/.agentos/store.db < agentos/store/migrations/v14_supervisor.sql
```

### 常见错误 3: 锁冲突（另一个实例正在运行）

**症状**:
```
另一个 lead_scan 实例正在运行，跳过本次执行
```

**原因**:
- 上一次扫描尚未完成
- 上一次扫描异常退出，锁未释放

**解决方案**:

1. **检查是否有其他实例运行**:
```bash
# 查看锁文件中的 PID
cat /tmp/agentos_lead_scan.lock

# 检查该进程是否存在
ps aux | grep <PID>
```

2. **如果进程不存在，删除锁文件**:
```bash
rm /tmp/agentos_lead_scan.lock
```

3. **或使用 --force 参数强制运行**:
```bash
python -m agentos.jobs.lead_scan --window 24h --force
```

### 常见错误 4: 规则检测失败

**症状**:
日志中出现 `Miner found 0 raw findings`，但预期应有 findings

**排查步骤**:

1. **检查扫描窗口是否有数据**:
```sql
-- 检查窗口内是否有 Supervisor 决策
SELECT COUNT(*)
FROM task_audits
WHERE event_type LIKE 'SUPERVISOR_%'
  AND created_at >= datetime('now', '-24 hours');
```

2. **检查规则阈值配置**:
可能阈值设置过高，导致没有满足条件的 findings。

3. **手动测试规则**:
```python
from agentos.core.lead.miner import RiskMiner, MinerConfig
from agentos.core.lead.adapters.storage import LeadStorage
from agentos.core.lead.models import ScanWindow, WindowKind
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 创建测试实例
storage = LeadStorage(db_path=Path.home() / ".agentos" / "store.db")
miner = RiskMiner(config=MinerConfig())

# 构建窗口
end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(hours=24)
window = ScanWindow(
    kind=WindowKind.HOUR_24,
    start_ts=start_time.isoformat(),
    end_ts=end_time.isoformat()
)

# 测试各规则
blocked_reasons = storage.get_blocked_reasons(window)
print(f"Blocked reasons: {len(blocked_reasons)}")
```

### 常见错误 5: Task 创建失败

**症状**:
```
Failed to create follow-up task for finding <fingerprint>: ...
```

**排查步骤**:

1. **检查 TaskService 是否正常**:
```python
from agentos.core.task.service import TaskService
from pathlib import Path

service = TaskService(db_path=Path.home() / ".agentos" / "store.db")
task = service.create_draft_task(
    title="Test task",
    created_by="test"
)
print(f"Task created: {task.task_id}")
```

2. **检查数据库表结构**:
```sql
-- 检查 tasks 表是否存在
.schema tasks

-- 检查 task_audits 表是否存在
.schema task_audits
```

---

## 手动运行指南

### 场景 1: 测试新规则

```bash
# 1. 先用 dry-run 预览
python -m agentos.jobs.lead_scan --window 24h --dry-run

# 2. 检查 findings 是否符合预期
sqlite3 ~/.agentos/store.db "SELECT * FROM lead_findings ORDER BY last_seen_at DESC LIMIT 10;"

# 3. 如果满意，实际运行
python -m agentos.jobs.lead_scan --window 24h
```

### 场景 2: 紧急风险扫描

```bash
# 立即运行 24h 窗口扫描
python -m agentos.jobs.lead_scan --window 24h --force

# 查看新创建的任务
sqlite3 ~/.agentos/store.db "SELECT task_id, title FROM tasks WHERE created_by='lead_agent' ORDER BY created_at DESC LIMIT 5;"
```

### 场景 3: 回顾历史趋势

```bash
# 运行 7d 窗口扫描（查看长期趋势）
python -m agentos.jobs.lead_scan --window 7d --dry-run

# 分析结果
sqlite3 ~/.agentos/store.db "SELECT code, COUNT(*) FROM lead_findings WHERE window_kind='7d' GROUP BY code;"
```

---

## 维护操作

### 1. 调整规则阈值

如果觉得告警太多或太少，可以调整规则阈值：

```python
# 创建自定义配置
from agentos.core.lead.miner import MinerConfig
from agentos.jobs.lead_scan import LeadScanJob

config = MinerConfig(
    spike_threshold=10,              # 提高 blocked_reason_spike 阈值
    pause_count_threshold=3,         # 提高 pause_block_churn 阈值
    decision_lag_p95_ms=8000.0,      # 提高延迟阈值
    redline_ratio_increase=0.15,     # 提高 redline 增幅阈值
)

# 运行扫描
job = LeadScanJob(config=config)
result = job.run_scan(window_kind="24h", dry_run=False)
```

### 2. 清理旧数据

定期清理过期的 findings：

```sql
-- 删除 30 天前的 findings（已处理的）
DELETE FROM lead_findings
WHERE last_seen_at < datetime('now', '-30 days')
  AND linked_task_id IS NOT NULL;

-- 删除 90 天前的所有 findings
DELETE FROM lead_findings
WHERE last_seen_at < datetime('now', '-90 days');
```

### 3. 查看规则执行统计

```sql
-- 统计各规则的命中率
SELECT
    code,
    COUNT(*) as total_findings,
    AVG(count) as avg_count,
    MAX(count) as max_count,
    COUNT(CASE WHEN linked_task_id IS NOT NULL THEN 1 END) as linked_tasks
FROM lead_findings
GROUP BY code
ORDER BY total_findings DESC;

-- 查看最活跃的 findings（重复出现最多的）
SELECT
    fingerprint,
    code,
    title,
    count,
    first_seen_at,
    last_seen_at,
    linked_task_id
FROM lead_findings
ORDER BY count DESC
LIMIT 20;
```

### 4. 重置 linked_task_id（重新创建任务）

如果需要为某个 finding 重新创建任务：

```sql
-- 清除 linked_task_id
UPDATE lead_findings
SET linked_task_id = NULL
WHERE fingerprint = '<fingerprint>';
```

然后重新运行扫描，会自动创建新任务。

---

## 进阶用法

### 集成到 CI/CD

可以在 CI 流程中运行 dry-run 扫描，检测潜在风险：

```yaml
# .github/workflows/lead-scan.yml
name: Lead Agent Scan

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Lead Scan
        run: |
          python -m agentos.jobs.lead_scan --window 24h --dry-run
      - name: Check for critical findings
        run: |
          critical_count=$(sqlite3 ~/.agentos/store.db "SELECT COUNT(*) FROM lead_findings WHERE severity='CRITICAL' AND last_seen_at >= datetime('now', '-1 day');")
          if [ $critical_count -gt 0 ]; then
            echo "⚠️ Found $critical_count CRITICAL findings"
            exit 1
          fi
```

### 自定义告警

将扫描结果发送到 Slack/Email：

```python
import json
from agentos.jobs.lead_scan import LeadScanJob

# 运行扫描
job = LeadScanJob()
result = job.run_scan(window_kind="24h", dry_run=False)

# 检查高风险 findings
if result["findings_count"] > 0:
    # 查询 CRITICAL findings
    critical_findings = job.finding_store.get_findings_by_severity("CRITICAL")

    if critical_findings:
        # 发送告警
        send_slack_alert(
            message=f"🚨 发现 {len(critical_findings)} 个 CRITICAL 风险",
            findings=critical_findings
        )
```

---

## 附录

### A. 规则列表

| 规则代码 | 说明 | 严重级别 | 阈值参数 |
|---------|------|----------|----------|
| `blocked_reason_spike` | 某错误码在窗口内激增 | HIGH | `spike_threshold=5` |
| `pause_block_churn` | 任务多次 PAUSE 后仍 BLOCK | MEDIUM | `pause_count_threshold=2` |
| `retry_recommended_but_fails` | RETRY 建议后仍失败 | MEDIUM | 无 |
| `decision_lag_anomaly` | 决策延迟 p95 过高 | LOW | `decision_lag_p95_ms=5000` |
| `redline_ratio_increase` | REDLINE 占比显著上升 | HIGH | `redline_ratio_increase=0.10` |
| `high_risk_allow` | 高风险问题仍被 ALLOW | CRITICAL | 无 |

### B. 数据库表结构

```sql
CREATE TABLE lead_findings (
    fingerprint TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    window_kind TEXT NOT NULL,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    count INTEGER DEFAULT 1,
    evidence_json TEXT,
    linked_task_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lead_findings_severity ON lead_findings(severity);
CREATE INDEX idx_lead_findings_last_seen ON lead_findings(last_seen_at);
CREATE INDEX idx_lead_findings_code ON lead_findings(code);
```

### C. 相关文档

- [Lead Agent 设计文档](../agentos/core/lead/README.md)
- [Supervisor 架构文档](./supervisor_architecture.md)
- [Task 状态机文档](../agentos/core/task/README.md)

---

**文档版本**: v1.0
**最后更新**: 2025-01-28
**维护者**: AgentOS Team
