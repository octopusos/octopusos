# Findings=0 自检告警机制实施报告

## 概述

实现了 Lead Agent 的自检告警机制，将"有数据但检测不到风险"的 silent failure 转换为 loud failure，防止系统长期失明。

## 实施内容

### 1. 核心功能

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/jobs/lead_scan.py`

#### 新增方法: `_self_check_findings()`

```python
def _self_check_findings(
    self,
    storage_data: dict,
    miner_data: dict,
    findings: list,
    window_kind: str
) -> dict
```

**功能**:
- 统计输入数据量（blocked_reasons, pause_block_churn, retry_then_fail, high_risk_allow）
- 比对 storage 数据量 vs miner 输出的 findings 数量
- 触发告警条件（按优先级排序）：
  1. 高优先级信号（high_risk_allow >= 1 或 blocked >= 5）但 findings=0
  2. 有任何 storage 数据但 findings=0
  3. 24h 窗口无数据（INFO 级别提示）

**返回值**:
```python
{
    "has_data": bool,                   # 是否有输入数据
    "findings_count": int,              # findings 数量
    "storage_items_count": int,         # storage 数据项数量
    "miner_findings_input_count": int,  # miner 输入 findings 数量
    "miner_decisions_input_count": int, # miner 输入 decisions 数量
    "alert_triggered": bool,            # 是否触发告警
    "alert_reason": str                 # 告警原因（如果触发）
}
```

#### 集成到 `run_scan()` 流程

在步骤 4.5（Miner 输出 findings 后）执行自检：

```python
# 4. 运行 Risk Miner 规则检测
raw_findings = self.miner.mine_risks(miner_data, scan_window)
console.print(f"✓ Miner found {len(raw_findings)} raw findings")

# 4.5 自检：如果有数据但 findings=0，触发告警
self_check_result = self._self_check_findings(
    storage_data=storage_data,
    miner_data=miner_data,
    findings=raw_findings,
    window_kind=window_kind
)
```

扫描结果包含自检信息：

```python
return {
    # ... 其他字段 ...
    "self_check": self_check_result
}
```

### 2. 可配置的告警阈值

在 `LeadScanJob.__init__()` 中添加：

```python
def __init__(
    self,
    db_path: Optional[Path] = None,
    config: Optional[MinerConfig] = None,
    alert_thresholds: Optional[dict] = None  # 新增参数
):
    # ...

    # 告警阈值配置
    self.alert_thresholds = alert_thresholds or {
        "min_blocked_for_alert": 5,       # blocked 数量超过此值且 findings=0 时告警
        "min_high_risk_for_alert": 1      # high_risk_allow 数量超过此值且 findings=0 时告警
    }
```

**使用示例**:

```python
# 默认阈值
job = LeadScanJob()

# 自定义阈值（更严格）
job = LeadScanJob(alert_thresholds={
    "min_blocked_for_alert": 10,
    "min_high_risk_for_alert": 2
})
```

### 3. 告警输出格式

#### 高优先级告警（红色 + emoji）

```
🚨 ALERT: POTENTIAL SILENT FAILURE
High-priority signals detected (high_risk_allow=1, blocked=0) but Miner produced 0 findings. This is abnormal.
```

#### 通用告警

```
🚨 ALERT: POTENTIAL SILENT FAILURE
Storage returned 5 items (blocked=5, pause_block=0, retry_fail=0, high_risk_allow=0) but Miner produced 0 findings. Possible causes: 1) Contract mismatch, 2) All rules filtered out, 3) Thresholds too high.
```

#### INFO 级别（无数据）

```
ℹ️  INFO: 24h scan found no data. This is normal if system is healthy, but verify if this is a new deployment.
```

同时记录到日志：

```python
logger.error(f"SILENT FAILURE ALERT: {alert_reason}")
```

## 测试验证

### 测试文件

- **单元测试**: `/Users/pangge/PycharmProjects/AgentOS/tests/unit/lead/test_self_check_alert.py`
- **测试运行器**: `/Users/pangge/PycharmProjects/AgentOS/tests/unit/lead/run_self_check_tests.py`

### 测试覆盖场景

| 测试场景 | 说明 | 预期结果 |
|---------|------|---------|
| 有 storage 数据但 findings=0 | 基本告警触发 | alert_triggered=True |
| 有 high_risk_allow 但 findings=0 | 高优先级告警 | "High-priority signals" |
| 有大量 blocked 但 findings=0 | 高优先级告警 | "High-priority signals" |
| 有数据且有 findings | 正常情况 | alert_triggered=False |
| 无数据且无 findings | 正常情况 | alert_triggered=False |
| 有 pause_block_churn 但 findings=0 | 基本告警触发 | alert_triggered=True |
| 有 retry_then_fail 但 findings=0 | 基本告警触发 | alert_triggered=True |
| 自定义告警阈值生效 | 阈值配置测试 | 按阈值触发 |
| 低于阈值时仍触发基本告警 | 降级告警测试 | "Storage returned" |

### 运行测试

```bash
cd /Users/pangge/PycharmProjects/AgentOS
source .venv/bin/activate
python tests/unit/lead/run_self_check_tests.py
```

**测试结果**: ✅ 9/9 passed

## 验收标准

| 标准 | 状态 |
|------|------|
| ✅ 有 storage 数据但 findings=0 时触发告警 | 已完成 |
| ✅ 有 high_risk_allow 但 findings=0 时触发告警 | 已完成 |
| ✅ 告警输出包含详细诊断信息（数据量 vs findings） | 已完成 |
| ✅ 告警使用显眼的格式（红色 + emoji） | 已完成 |
| ✅ 正常情况（有数据有 findings，或无数据无 findings）不触发告警 | 已完成 |
| ✅ 单元测试覆盖所有告警场景 | 已完成 |
| ✅ 扫描结果包含自检信息 | 已完成 |

## 使用示例

### 命令行运行

```bash
# 预览模式（dry-run）
python -m agentos.jobs.lead_scan --window 24h --dry-run

# 实际运行
python -m agentos.jobs.lead_scan --window 24h
```

### 代码集成

```python
from pathlib import Path
from agentos.jobs.lead_scan import LeadScanJob

# 创建作业（默认配置）
job = LeadScanJob()

# 运行扫描
result = job.run_scan(window_kind="24h", dry_run=False)

# 检查自检结果
if result["self_check"]["alert_triggered"]:
    print(f"Alert: {result['self_check']['alert_reason']}")
    # 触发告警通知（例如：发送到监控系统）
```

### 自定义阈值

```python
# 创建作业（自定义阈值）
job = LeadScanJob(
    alert_thresholds={
        "min_blocked_for_alert": 10,    # 更高的阈值
        "min_high_risk_for_alert": 2
    }
)

result = job.run_scan(window_kind="24h", dry_run=False)
```

## 告警响应流程

1. **检测到告警时**:
   - 告警会显示在控制台（红色 + emoji）
   - 同时记录到日志（ERROR 级别）
   - 扫描结果包含 `self_check` 字段供后续处理

2. **可能的原因**:
   - 契约不匹配（Storage vs Miner 版本不兼容）
   - 规则被全部过滤（阈值设置过高）
   - Miner 规则实现有 bug
   - 数据转换层有问题

3. **排查步骤**:
   1. 检查契约版本（`contract_versions` 字段）
   2. 查看 storage_data 和 miner_data 的内容
   3. 检查 Miner 配置的阈值
   4. 查看 Miner 日志是否有异常

## 后续改进建议

1. **集成到监控系统**:
   - 将告警发送到 Slack/Email/PagerDuty
   - 记录到专门的告警表（task_audits）

2. **告警降噪**:
   - 添加告警抑制机制（避免重复告警）
   - 设置告警冷却时间

3. **自动恢复**:
   - 检测到告警后自动回滚到上一个已知良好版本
   - 或触发人工审核流程

4. **统计分析**:
   - 记录告警历史，分析告警模式
   - 优化阈值配置

## 技术细节

### 告警优先级逻辑

```python
# 优先级 1: 高优先级信号（最严重）
if (high_risk_allow_count >= min_high_risk or blocked_count >= min_blocked) and findings_count == 0:
    # 触发高优先级告警

# 优先级 2: 通用数据但 findings=0
if not alert_triggered and total_storage_items > 0 and findings_count == 0:
    # 触发通用告警

# 优先级 3: 无数据（INFO 级别）
if window_kind == "24h" and not has_data:
    # 输出 INFO 信息（不是严重告警）
```

### 数据统计

```python
# 统计 storage 数据项
total_storage_items = (
    blocked_count +           # blocked_reasons 数量
    pause_block_count +       # pause_block_churn 数量
    retry_fail_count +        # retry_then_fail 数量
    high_risk_allow_count     # high_risk_allow 数量
)

# 统计 miner 输入数据
miner_findings_count = len(miner_data.get("findings", []))
miner_decisions_count = len(miner_data.get("decisions", []))

# 判断是否有数据
has_data = total_storage_items > 0 or miner_findings_count > 0 or miner_decisions_count > 0
```

## 相关文档

- [Lead Agent 架构设计](./lead_agent_architecture.md)
- [Risk Miner 规则文档](./risk_miner_rules.md)
- [契约版本管理](./contract_version_management.md)

## 变更历史

- **2025-01-28**: 初始实现，9个单元测试全部通过
