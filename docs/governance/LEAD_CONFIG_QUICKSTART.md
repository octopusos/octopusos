# Lead Agent 配置快速入门

## 概述

Lead Agent 支持通过 YAML 配置文件管理规则阈值，提供灵活的 override 机制，同时保持默认值冻结在代码仓库中。

## 快速开始

### 1. 使用默认配置

最简单的方式，直接运行：

```bash
python -m agentos.jobs.lead_scan --window 24h --dry-run
```

默认配置位于 `agentos/config/lead_rules.yaml`，包含生产验证的阈值。

### 2. 查看当前阈值

扫描开始时会自动打印阈值摘要：

```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ 规则               ┃ 阈值  ┃ 说明              ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ blocked_reason_... │ 5     │ 相同错误码激增    │
│ pause_block_churn  │ 2     │ PAUSE 次数阈值    │
│ retry_then_fail    │ 1     │ RETRY 后失败      │
│ decision_lag       │ 5000ms│ 决策延迟 p95      │
│ redline_ratio      │ 10%   │ 占比增幅阈值      │
│ high_risk_allow    │ 1     │ 高危放行          │
└────────────────────┴───────┴───────────────────┘
```

### 3. 自定义配置

#### 3.1 创建自定义配置文件

```bash
# 复制默认配置
cp agentos/config/lead_rules.yaml /path/to/my_config.yaml

# 编辑阈值
vim /path/to/my_config.yaml
```

示例配置：

```yaml
version: "1.0.0"

rules:
  blocked_reason_spike:
    threshold: 10  # 提高阈值（默认 5）

  pause_block_churn:
    pause_count_threshold: 3  # 提高阈值（默认 2）

  decision_lag:
    p95_threshold_ms: 8000  # 放宽延迟限制（默认 5000ms）

alert_thresholds:
  min_blocked_for_alert: 10  # 提高告警阈值（默认 5）

logging:
  print_threshold_summary: true  # 启用阈值摘要
  log_level: "INFO"
```

#### 3.2 使用自定义配置

**方式 1：命令行参数**

```bash
python -m agentos.jobs.lead_scan --window 24h --config /path/to/my_config.yaml
```

**方式 2：环境变量**

```bash
export LEAD_CONFIG=/path/to/my_config.yaml
python -m agentos.jobs.lead_scan --window 24h
```

环境变量优先级最高，适合生产环境部署。

### 4. 验证配置

使用 `--dry-run` 模式验证配置效果：

```bash
python -m agentos.jobs.lead_scan --window 24h --config /path/to/my_config.yaml --dry-run
```

观察阈值摘要表格，确认配置已生效。

## 配置优先级

从高到低：

1. **环境变量** `LEAD_CONFIG`
2. **命令行参数** `--config`
3. **默认配置文件** `agentos/config/lead_rules.yaml`
4. **硬编码默认值**（fallback，配置文件不存在时使用）

## 配置字段说明

### 规则阈值

| 规则 | 字段 | 默认值 | 说明 |
|-----|------|--------|------|
| blocked_reason_spike | threshold | 5 | 24h 内相同错误码出现次数阈值 |
| pause_block_churn | pause_count_threshold | 2 | 任务被 PAUSE 的次数阈值 |
| retry_then_fail | threshold | 1 | RETRY 后失败次数阈值 |
| decision_lag | p95_threshold_ms | 5000 | 决策延迟 p95 阈值（毫秒）|
| redline_ratio | increase_threshold | 0.10 | REDLINE 占比增幅阈值（10%）|
| redline_ratio | min_baseline | 0.05 | REDLINE 基准占比（5%）|
| high_risk_allow | threshold | 1 | 高危问题被放行次数阈值 |

### 告警阈值

| 字段 | 默认值 | 说明 |
|-----|--------|------|
| min_blocked_for_alert | 5 | blocked 数量超过此值且 findings=0 时触发告警 |
| min_high_risk_for_alert | 1 | high_risk_allow 数量超过此值且 findings=0 时触发告警 |

### 日志配置

| 字段 | 默认值 | 说明 |
|-----|--------|------|
| print_threshold_summary | true | 是否在扫描开始时打印阈值摘要 |
| log_level | "INFO" | 日志级别 |

## 最佳实践

### 1. 测试环境

使用宽松阈值，捕获更多潜在问题：

```yaml
rules:
  blocked_reason_spike:
    threshold: 3  # 降低阈值，更敏感
  pause_block_churn:
    pause_count_threshold: 1
```

### 2. 生产环境

使用严格阈值，减少噪音：

```yaml
rules:
  blocked_reason_spike:
    threshold: 10  # 提高阈值，只关注严重问题
  pause_block_churn:
    pause_count_threshold: 3
```

### 3. 配置版本管理

- **不要直接修改** `agentos/config/lead_rules.yaml`
- **创建环境特定配置**：`config/lead_rules.prod.yaml`, `config/lead_rules.test.yaml`
- **版本控制**：将自定义配置纳入 Git 管理
- **记录变更**：在 CHANGELOG 中记录阈值调整原因

### 4. 部署建议

**Docker 环境**：

```dockerfile
ENV LEAD_CONFIG=/app/config/lead_rules.prod.yaml
COPY config/lead_rules.prod.yaml /app/config/
```

**Kubernetes 环境**：

```yaml
env:
  - name: LEAD_CONFIG
    value: /config/lead_rules.yaml
volumeMounts:
  - name: config
    mountPath: /config
    readOnly: true
```

## 故障排查

### 配置未生效

1. **检查配置路径**：确保文件存在且可读
   ```bash
   ls -la /path/to/config.yaml
   ```

2. **验证 YAML 语法**：
   ```bash
   python -c "import yaml; yaml.safe_load(open('/path/to/config.yaml'))"
   ```

3. **检查优先级**：环境变量 `LEAD_CONFIG` 会 override 命令行参数
   ```bash
   echo $LEAD_CONFIG
   unset LEAD_CONFIG  # 清除环境变量
   ```

### 阈值摘要未显示

检查配置中的 `logging.print_threshold_summary`：

```yaml
logging:
  print_threshold_summary: true  # 确保为 true
```

### 部分配置缺失

配置文件可以只包含需要修改的字段，缺失字段会自动使用默认值：

```yaml
# 最小配置：只修改 spike_threshold
rules:
  blocked_reason_spike:
    threshold: 10
# 其他字段自动使用默认值
```

## 编程接口

### Python API

```python
from pathlib import Path
from agentos.config import load_lead_config
from agentos.jobs.lead_scan import LeadScanJob

# 加载配置
config = load_lead_config(Path("/path/to/config.yaml"))

# 查看配置
print(f"版本: {config.version}")
print(f"Spike 阈值: {config.rule_thresholds.spike_threshold}")

# 创建 job（配置会自动加载）
job = LeadScanJob(config_path=Path("/path/to/config.yaml"))
job.run_scan(window_kind="24h", dry_run=True)
```

### 向后兼容

旧代码仍然支持直接传递 `MinerConfig`：

```python
from agentos.core.lead.miner import MinerConfig

# 旧方式（仍然支持）
custom_config = MinerConfig(spike_threshold=10)
job = LeadScanJob(config=custom_config)
```

## 测试

运行配置管理测试：

```bash
# 单元测试
uv run pytest tests/unit/config/test_config_loader.py -v

# 集成测试
uv run pytest tests/unit/config/test_lead_scan_integration.py -v

# 所有配置测试
uv run pytest tests/unit/config/ -v
```

## 参考资料

- [Lead Agent 设计文档](./lead_agent.md#配置管理)
- [配置文件模板](../../agentos/config/lead_rules.yaml)
- [配置加载器源码](../../agentos/config/loader.py)

## 常见问题

**Q: 如何知道当前使用的是哪个配置文件？**

A: 查看扫描开始时的阈值摘要表格，表格标题会显示版本号。

**Q: 可以动态修改配置吗？**

A: 不可以。配置在 LeadScanJob 初始化时加载，后续修改不会生效。需要重启 job。

**Q: 配置文件可以使用 JSON 格式吗？**

A: 目前只支持 YAML。如需其他格式，请提交 issue。

**Q: 如何禁用阈值摘要？**

A: 在配置中设置 `logging.print_threshold_summary: false`

**Q: 配置文件支持环境变量替换吗？**

A: 目前不支持。如需动态配置，建议使用环境变量 `LEAD_CONFIG` 指向不同的配置文件。

## 变更历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2025-01-28 | 初始版本：YAML 配置文件支持 |
