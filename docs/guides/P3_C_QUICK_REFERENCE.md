# P3-C Time 快速参考

**模块**: Cognitive Time（认知健康监控）
**核心**: "我的理解是在变好，还是在变坏？"

---

## 一、核心概念

### Time ≠ 历史回放

❌ **不是**:
- Git commit 时间线
- 文件修改历史
- 代码变更记录

✅ **而是**:
- 认知健康监控
- 理解质量趋势分析
- 认知债务预警

### 回答的问题

1. **覆盖率是上升还是下降？**
2. **盲区是增加还是减少？**
3. **证据来源是单一还是多元？**
4. **哪些区域长期被忽略？**
5. **哪些区域在退化？**

---

## 二、快速使用

### 2.1 查看健康报告

```bash
# 最近 30 天
curl "http://localhost:8000/api/brain/time/health?window_days=30"

# 最近 7 天
curl "http://localhost:8000/api/brain/time/health?window_days=7"
```

### 2.2 Python 方式

```python
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.cognitive_time import analyze_trends

# 连接数据库
store = SQLiteStore(".brainos/v0.1_mvp.db")
store.connect()

# 分析趋势
report = analyze_trends(store, window_days=30)

# 查看结果
print(f"Health Score: {report.current_health_score:.2f}")
print(f"Health Level: {report.current_health_level.value}")
print(f"Coverage Trend: {report.coverage_trend.direction.value}")

# 查看预警
for warning in report.warnings:
    print(f"⚠️ {warning}")

# 查看建议
for rec in report.recommendations:
    print(f"💡 {rec}")

store.close()
```

---

## 三、核心数据模型

### 3.1 HealthReport（健康报告）

```python
@dataclass
class HealthReport:
    # 时间窗口
    window_start: str
    window_end: str
    window_days: int

    # 当前状态
    current_health_level: HealthLevel  # EXCELLENT/GOOD/FAIR/POOR/CRITICAL
    current_health_score: float  # 0-100

    # 趋势线
    coverage_trend: TrendLine
    blind_spot_trend: TrendLine
    evidence_density_trend: TrendLine

    # 来源迁移
    source_migration: Dict[str, TrendDirection]

    # 认知债务
    cognitive_debts: List[CognitiveDebt]
    total_debt_count: int

    # 预警和建议
    warnings: List[str]
    recommendations: List[str]
```

### 3.2 TrendLine（趋势线）

```python
@dataclass
class TrendLine:
    metric_name: str
    direction: TrendDirection  # IMPROVING/DEGRADING/STABLE/INSUFFICIENT_DATA
    slope: float  # 斜率（正=上升，负=下降）
    avg_value: float
    max_value: float
    min_value: float
    predicted_next_value: Optional[float]
```

### 3.3 TrendDirection（趋势方向）

```python
class TrendDirection(Enum):
    IMPROVING = "IMPROVING"              # 改善 🟢
    DEGRADING = "DEGRADING"              # 退化 🔴
    STABLE = "STABLE"                    # 稳定 🟡
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # 数据不足 ⚪
```

### 3.4 HealthLevel（健康等级）

```python
class HealthLevel(Enum):
    EXCELLENT = "EXCELLENT"  # 优秀：>= 80
    GOOD = "GOOD"            # 良好：60-80
    FAIR = "FAIR"            # 一般：40-60
    POOR = "POOR"            # 较差：20-40
    CRITICAL = "CRITICAL"    # 危险：< 20
```

### 3.5 CognitiveDebt（认知债务）

```python
@dataclass
class CognitiveDebt:
    entity_id: str
    entity_type: str
    entity_name: str

    debt_type: str  # "UNCOVERED", "DEGRADING", "ORPHANED"
    duration_days: int
    severity: float  # 0-1

    description: str
    recommendation: str
```

---

## 四、健康评分计算

### 4.1 评分公式

```python
health_score = (
    0.4 * coverage_percentage * 100 +           # 40% 权重：覆盖率
    0.3 * min(evidence_density * 10, 100) +     # 30% 权重：证据密度
    0.3 * (100 - blind_spot_ratio * 100)        # 30% 权重：盲区反向
)
```

### 4.2 等级映射

| 评分范围 | 等级 | 描述 | 图标 |
|---------|------|------|------|
| >= 80 | EXCELLENT | 优秀 | 🟢 |
| 60-80 | GOOD | 良好 | 🟦 |
| 40-60 | FAIR | 一般 | 🟡 |
| 20-40 | POOR | 较差 | 🟠 |
| < 20 | CRITICAL | 危险 | 🔴 |

---

## 五、趋势检测算法

### 5.1 线性回归

使用最小二乘法计算趋势斜率：

```python
# 计算斜率
slope = Σ((x[i] - x̄) * (y[i] - ȳ)) / Σ((x[i] - x̄)²)

# 判断方向
if |slope| < 0.001:
    direction = STABLE
elif slope > 0:
    direction = IMPROVING (or DEGRADING for blind_spot_ratio)
else:
    direction = DEGRADING (or IMPROVING for blind_spot_ratio)
```

### 5.2 特殊处理

**盲区比例 (blind_spot_ratio)**:
- 斜率 > 0 → DEGRADING（盲区增加是退化）
- 斜率 < 0 → IMPROVING（盲区减少是改善）

**其他指标 (coverage_percentage, evidence_density)**:
- 斜率 > 0 → IMPROVING（增加是改善）
- 斜率 < 0 → DEGRADING（减少是退化）

---

## 六、认知债务识别

### 6.1 债务类型

| 类型 | 条件 | 严重度 | 建议 |
|-----|------|--------|------|
| UNCOVERED | 无证据 >= 14 天 | 1.0 | 添加文档或代码引用 |
| DEGRADING | 证据持续减少 >= 7 天 | 0.7 | 更新引用 |
| ORPHANED | 无边连接 >= 14 天 | 0.8 | 建立关系 |

### 6.2 识别逻辑

```python
# UNCOVERED: 无证据
if entity.evidence_count == 0:
    debt = CognitiveDebt(
        debt_type="UNCOVERED",
        severity=1.0,
        recommendation="Add documentation or code references"
    )

# ORPHANED: 无覆盖源
if len(entity.coverage_sources) == 0:
    debt = CognitiveDebt(
        debt_type="UNCOVERED",
        severity=0.7,
        recommendation="Link to Git commits, docs, or code"
    )
```

---

## 七、API 响应示例

### 7.1 成功响应

```json
{
  "ok": true,
  "data": {
    "current_health_level": "GOOD",
    "current_health_score": 72.5,

    "coverage_trend": {
      "direction": "IMPROVING",
      "slope": 0.005,
      "avg_value": 0.65
    },

    "warnings": [
      "⚠️ Blind spots are INCREASING (slope: 0.0030)"
    ],

    "recommendations": [
      "🔍 Review and resolve blind spots",
      "💳 Address top 5 cognitive debts"
    ],

    "cognitive_debts": [
      {
        "entity_name": "old_module.py",
        "debt_type": "UNCOVERED",
        "severity": 1.0,
        "recommendation": "Add documentation"
      }
    ]
  }
}
```

### 7.2 数据不足响应

```json
{
  "ok": true,
  "data": {
    "coverage_trend": {
      "direction": "INSUFFICIENT_DATA"
    },

    "warnings": [
      "⚠️ Insufficient data (need >= 2 snapshots)"
    ],

    "recommendations": [
      "📸 Create snapshots regularly to enable trend analysis"
    ]
  }
}
```

---

## 八、常见使用场景

### 8.1 定期健康检查

```bash
# 每周检查
curl "http://localhost:8000/api/brain/time/health?window_days=7"

# 关注：
# - current_health_score
# - warnings
# - recommendations
```

### 8.2 识别退化区域

```python
report = analyze_trends(store, window_days=30)

if report.coverage_trend.direction == TrendDirection.DEGRADING:
    print("⚠️ Coverage is degrading!")
    print(f"Slope: {report.coverage_trend.slope:.4f}")

    # 查看认知债务
    for debt in report.cognitive_debts[:5]:
        print(f"- {debt.entity_name}: {debt.recommendation}")
```

### 8.3 追踪改善进展

```python
# 1. 记录初始状态
initial_report = analyze_trends(store, window_days=7)
initial_score = initial_report.current_health_score

# 2. 执行改进措施
# ... 添加文档、更新代码 ...

# 3. 创建新快照
from agentos.core.brain.compare.snapshot import capture_snapshot
capture_snapshot(store, description="After improvements")

# 4. 再次检查
final_report = analyze_trends(store, window_days=7)
final_score = final_report.current_health_score

# 5. 对比
improvement = final_score - initial_score
print(f"Health score improved by: {improvement:.2f}")
```

---

## 九、预警和建议

### 9.1 预警类型

| 预警 | 条件 | 描述 |
|-----|------|------|
| Coverage DEGRADING | slope < 0 | 覆盖率下降 |
| Blind spots INCREASING | slope > 0 | 盲区增加 |
| High cognitive debt | count > 5 | 债务过多 |

### 9.2 建议类型

| 建议 | 触发条件 | 描述 |
|-----|----------|------|
| Rebuild index | Coverage degrading | 重建索引 |
| Add documentation | Coverage degrading | 添加文档 |
| Review blind spots | Blind spots increasing | 审查盲区 |
| Address debts | Debt count > 0 | 处理债务 |

---

## 十、性能基准

| 场景 | 快照数 | 实体数 | 执行时间 |
|------|-------|-------|---------|
| 空数据库 | 0 | 0 | < 0.01s |
| 单个实体 | 2 | 1 | < 0.05s |
| 多个快照 | 3 | 5 | < 0.10s |
| 标准场景 | 5 | 50 | < 0.20s |
| 大规模 | 10 | 500 | < 1.00s |

**目标**: < 2s
**实际**: < 0.2s（远超目标）

---

## 十一、故障排查

### 11.1 "Insufficient data" 错误

**原因**: 快照数量 < 2

**解决**:
```bash
# 创建快照
brain snapshot

# 等待一段时间后再创建第二个快照
brain snapshot
```

### 11.2 "Database not found" 错误

**原因**: BrainOS 数据库不存在

**解决**:
```bash
# 构建 BrainOS 索引
brain build
```

### 11.3 时区警告

**原因**: 快照时间戳时区不一致

**解决**: 自动处理，无需手动干预

---

## 十二、最佳实践

### 12.1 定期创建快照

```bash
# 建议频率：每天或每次重大变更后
brain snapshot --description "Daily snapshot"
```

### 12.2 关注长期趋势

```bash
# 使用 30 天窗口观察长期趋势
curl "http://localhost:8000/api/brain/time/health?window_days=30"
```

### 12.3 及时处理债务

```python
report = analyze_trends(store, window_days=7)

# 优先处理高严重度债务
high_severity_debts = [
    d for d in report.cognitive_debts
    if d.severity >= 0.8
]

for debt in high_severity_debts:
    print(f"HIGH: {debt.entity_name} - {debt.recommendation}")
```

### 12.4 监控预警

```python
if report.warnings:
    print("⚠️ WARNINGS:")
    for warning in report.warnings:
        print(f"  {warning}")

    # 发送通知（可选）
    # send_slack_notification(report.warnings)
```

---

## 十三、集成示例

### 13.1 CLI 工具

```python
#!/usr/bin/env python3
"""CLI tool for health monitoring"""

import sys
from agentos.core.brain.store import SQLiteStore
from agentos.core.brain.cognitive_time import analyze_trends

def main():
    store = SQLiteStore(".brainos/v0.1_mvp.db")
    store.connect()

    report = analyze_trends(store, window_days=30)

    print(f"Health Score: {report.current_health_score:.2f}")
    print(f"Level: {report.current_health_level.value}")

    if report.warnings:
        print("\n⚠️ Warnings:")
        for w in report.warnings:
            print(f"  {w}")

    if report.recommendations:
        print("\n💡 Recommendations:")
        for r in report.recommendations:
            print(f"  {r}")

    store.close()

    # Exit with non-zero if health is poor
    if report.current_health_level.value in ["POOR", "CRITICAL"]:
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 13.2 监控脚本

```bash
#!/bin/bash
# health_monitor.sh - 定期健康检查

# 运行健康检查
python3 health_check.py

# 检查退出码
if [ $? -ne 0 ]; then
    echo "⚠️ Health check FAILED!"
    # 发送通知
    # curl -X POST "https://slack.com/webhook" -d "Health check failed"
else
    echo "✅ Health check PASSED"
fi
```

---

## 十四、快速诊断

### 14.1 检查列表

- [ ] 是否有足够的快照？（>= 2）
- [ ] 健康评分是否 >= 60？
- [ ] 覆盖率趋势是否 IMPROVING 或 STABLE？
- [ ] 盲区趋势是否 IMPROVING 或 STABLE？
- [ ] 认知债务是否 <= 5？
- [ ] 是否有警告？
- [ ] 是否有紧急建议？

### 14.2 快速命令

```bash
# 1. 检查快照数量
curl -s "http://localhost:8000/api/brain/snapshots" | jq '.data | length'

# 2. 查看最新健康评分
curl -s "http://localhost:8000/api/brain/time/health?window_days=7" | jq '.data.current_health_score'

# 3. 查看预警
curl -s "http://localhost:8000/api/brain/time/health?window_days=7" | jq '.data.warnings[]'

# 4. 查看建议
curl -s "http://localhost:8000/api/brain/time/health?window_days=7" | jq '.data.recommendations[]'
```

---

## 十五、相关资源

- **完整实施报告**: `P3_C_TIME_IMPLEMENTATION.md`
- **验收报告**: `P3_C_ACCEPTANCE_REPORT.md`
- **源代码**: `agentos/core/brain/cognitive_time/`
- **测试**: `tests/unit/core/brain/cognitive_time/`, `tests/integration/brain/cognitive_time/`
- **API 文档**: `/api/docs` (FastAPI auto-generated)

---

**快速参考版本**: v1.0
**最后更新**: 2026-01-31
