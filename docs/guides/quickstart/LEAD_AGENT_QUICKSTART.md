# Lead Agent 快速开始指南

## 一分钟上手

Lead Agent 是 AgentOS 的自动化风险检测系统，通过分析 Supervisor 决策历史，识别系统性问题并自动创建任务。

### 立即运行

```bash
# 1. 预览扫描（不创建任务）
python -m agentos.jobs.lead_scan --window 24h --dry-run

# 2. 实际运行（创建任务）
python -m agentos.jobs.lead_scan --window 24h

# 3. 每周扫描
python -m agentos.jobs.lead_scan --window 7d
```

### 查看结果

```bash
# 查看发现的风险
sqlite3 ~/.agentos/store.db "SELECT * FROM lead_findings ORDER BY last_seen_at DESC LIMIT 10;"

# 查看创建的任务
sqlite3 ~/.agentos/store.db "SELECT task_id, title, status FROM tasks WHERE created_by='lead_agent' ORDER BY created_at DESC LIMIT 10;"
```

---

## 核心概念

### 1. 扫描窗口

- **24h**：查看过去 24 小时的决策，建议每天运行
- **7d**：查看过去 7 天的趋势，建议每周运行

### 2. 运行模式

- **Dry-run**（`--dry-run`）：预览模式，不创建任务
- **实际执行**：创建 follow-up tasks 供人工审查

### 3. 6 条规则

| 规则 | 检测内容 | 严重级别 |
|------|---------|---------|
| blocked_reason_spike | 某错误码激增 | HIGH |
| pause_block_churn | 任务多次暂停后阻塞 | MEDIUM |
| retry_recommended_but_fails | 重试建议后仍失败 | MEDIUM |
| decision_lag_anomaly | 决策延迟过高 | LOW |
| redline_ratio_increase | 红线违规占比上升 | HIGH |
| high_risk_allow | 高风险问题被放行 | CRITICAL |

---

## 设置 Cron 定时任务

### 方法 1: 系统 crontab

```bash
# 编辑 crontab
crontab -e

# 添加以下内容
0 2 * * * /usr/bin/python3 -m agentos.jobs.lead_scan --window 24h >> /var/log/agentos/lead_scan.log 2>&1
0 3 * * 1 /usr/bin/python3 -m agentos.jobs.lead_scan --window 7d >> /var/log/agentos/lead_scan_7d.log 2>&1
```

### 方法 2: systemd timer

创建 `/etc/systemd/system/lead-scan-24h.service`:

```ini
[Unit]
Description=Lead Agent 24h Scan

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -m agentos.jobs.lead_scan --window 24h
```

创建 `/etc/systemd/system/lead-scan-24h.timer`:

```ini
[Unit]
Description=Lead Agent 24h Scan Timer

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

启用 timer:

```bash
sudo systemctl enable lead-scan-24h.timer
sudo systemctl start lead-scan-24h.timer
```

---

## 常见场景

### 场景 1: 测试新规则

```bash
# 1. 先用 dry-run 查看会发现什么
python -m agentos.jobs.lead_scan --window 24h --dry-run

# 2. 检查结果
sqlite3 ~/.agentos/store.db "SELECT code, title, severity FROM lead_findings ORDER BY last_seen_at DESC LIMIT 5;"

# 3. 如果满意，实际运行
python -m agentos.jobs.lead_scan --window 24h
```

### 场景 2: 紧急风险扫描

```bash
# 立即运行（跳过并发检查）
python -m agentos.jobs.lead_scan --window 24h --force

# 查看高风险发现
sqlite3 ~/.agentos/store.db "SELECT * FROM lead_findings WHERE severity IN ('HIGH', 'CRITICAL') AND linked_task_id IS NULL;"
```

### 场景 3: 回顾历史趋势

```bash
# 运行 7 天窗口扫描
python -m agentos.jobs.lead_scan --window 7d --dry-run

# 统计规则命中情况
sqlite3 ~/.agentos/store.db "SELECT code, COUNT(*), AVG(count) FROM lead_findings WHERE window_kind='7d' GROUP BY code;"
```

---

## 故障排查

### 问题 1: 另一个实例正在运行

**症状**:
```
另一个 lead_scan 实例正在运行，跳过本次执行
```

**解决**:
```bash
# 方法 1: 删除锁文件
rm /tmp/agentos_lead_scan.lock

# 方法 2: 使用 --force 强制运行
python -m agentos.jobs.lead_scan --window 24h --force
```

### 问题 2: 表不存在

**症状**:
```
sqlite3.OperationalError: no such table: lead_findings
```

**解决**:
```bash
# 运行数据库迁移
sqlite3 ~/.agentos/store.db < agentos/store/migrations/v14_supervisor.sql
```

### 问题 3: 没有发现任何问题

**可能原因**:
1. 窗口内没有 Supervisor 决策数据
2. 规则阈值设置过高
3. 数据质量问题

**检查**:
```sql
-- 检查窗口内是否有决策数据
SELECT COUNT(*) FROM task_audits
WHERE event_type LIKE 'SUPERVISOR_%'
  AND created_at >= datetime('now', '-24 hours');
```

---

## 进阶用法

### 自定义规则阈值

```python
from agentos.core.lead.miner import MinerConfig
from agentos.jobs.lead_scan import LeadScanJob

# 自定义配置
config = MinerConfig(
    spike_threshold=10,              # 提高激增阈值
    pause_count_threshold=3,         # 提高暂停次数阈值
    decision_lag_p95_ms=8000.0,      # 提高延迟阈值
)

# 使用自定义配置运行
job = LeadScanJob(config=config)
result = job.run_scan(window_kind="24h", dry_run=False)
```

### 集成到 CI/CD

```yaml
# .github/workflows/lead-scan.yml
name: Lead Agent Scan

on:
  schedule:
    - cron: '0 2 * * *'

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Lead Scan
        run: python -m agentos.jobs.lead_scan --window 24h --dry-run
```

---

## 监控指标

### 关键指标

| 指标 | 说明 | 查询方法 |
|------|------|----------|
| findings_count | 新发现数 | 查看扫描输出 |
| tasks_created | 创建任务数 | 查看扫描输出 |
| duplicate_findings | 重复发现数 | 查看扫描输出 |
| execution_time | 执行耗时 | 查看扫描输出 |

### 告警建议

1. **CRITICAL findings > 0**: 立即处理
2. **连续 3 次扫描失败**: 检查系统状态
3. **执行耗时 > 10 秒**: 检查数据库性能

---

## 数据维护

### 清理旧数据

```sql
-- 删除 30 天前已处理的 findings
DELETE FROM lead_findings
WHERE last_seen_at < datetime('now', '-30 days')
  AND linked_task_id IS NOT NULL;
```

### 查看统计

```sql
-- 规则命中统计
SELECT
    code,
    COUNT(*) as total,
    AVG(count) as avg_count,
    COUNT(CASE WHEN linked_task_id IS NOT NULL THEN 1 END) as linked
FROM lead_findings
GROUP BY code;

-- 最活跃的 findings
SELECT fingerprint, code, title, count, last_seen_at
FROM lead_findings
ORDER BY count DESC
LIMIT 10;
```

---

## 完整文档

- **运维手册**: `docs/governance/lead_runbook.md`
- **交付文档**: `agentos/core/lead/JOBS_DELIVERY.md`
- **设计文档**: `agentos/core/lead/README.md`
- **测试**: `tests/integration/lead/test_lead_scan_job.py`

---

## 快速命令参考

```bash
# 帮助信息
python -m agentos.jobs.lead_scan --help

# Dry-run 扫描
python -m agentos.jobs.lead_scan --window 24h --dry-run

# 实际运行
python -m agentos.jobs.lead_scan --window 24h

# 每周扫描
python -m agentos.jobs.lead_scan --window 7d

# 强制运行
python -m agentos.jobs.lead_scan --window 24h --force

# 指定数据库
python -m agentos.jobs.lead_scan --window 24h --db-path /path/to/store.db

# 查看结果
sqlite3 ~/.agentos/store.db "SELECT * FROM lead_findings ORDER BY last_seen_at DESC LIMIT 10;"

# 查看任务
sqlite3 ~/.agentos/store.db "SELECT task_id, title FROM tasks WHERE created_by='lead_agent' ORDER BY created_at DESC LIMIT 10;"

# 清理锁文件
rm /tmp/agentos_lead_scan.lock

# 查看日志
tail -f /var/log/agentos/lead_scan.log
```

---

**版本**: v1.0
**最后更新**: 2025-01-28
