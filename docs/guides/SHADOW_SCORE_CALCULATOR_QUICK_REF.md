# Shadow Score Calculator - 快速参考

**用途**: 计算 Reality Alignment Score，评估决策与用户需求的对齐程度

---

## 快速开始

### 1. 评估单个决策集

```python
from agentos.core.chat.shadow_evaluator import evaluate_decision_set

# 评估并记录到审计日志
scores = await evaluate_decision_set("ds-abc123", log_to_audit=True)

# 查看结果
print(f"Active: {scores['active'].score:.2f}")
for key, score in scores.items():
    if key.startswith("shadow-"):
        print(f"{key}: {score.score:.2f}")
```

### 2. 批量评估

```python
from agentos.core.chat.shadow_evaluator import evaluate_decision_set_batch

batch_scores = await evaluate_decision_set_batch(
    ["ds-001", "ds-002", "ds-003"],
    log_to_audit=True
)
```

### 3. 查看详细解释

```python
from agentos.core.chat.shadow_evaluator import (
    ShadowScoreCalculator,
    format_score_explanation
)

calculator = ShadowScoreCalculator()
score = calculator.compute_score_for_message("msg-123", "active")
print(format_score_explanation(score))
```

---

## 信号权重表

| 信号类型 | 权重 | 含义 |
|---------|------|------|
| `phase_violation` | **-0.3** | Phase 约束违规 |
| `explicit_negative_feedback` | **-0.3** | 用户给予负面反馈 |
| `reask_same_question` | **-0.2** | 用户重新问同样问题 |
| `abandoned_response` | **-0.2** | 用户放弃未读响应 |
| `user_followup_override` | **-0.1** | 用户立即纠正决策 |
| `delayed_comm_request` | **-0.1** | 用户后来手动联网 |
| `smooth_completion` | **+0.1** | 顺畅完成 |
| `explicit_positive_feedback` | **+0.1** | 用户给予正面反馈 |

---

## 评分公式

```
base_score = 1.0
raw_score = base_score + Σ(signal_weight × signal_count)
final_score = clamp(raw_score, 0.0, 1.0)
```

---

## 核心 API

### `ShadowScoreCalculator`

```python
calculator = ShadowScoreCalculator()

# 为单个消息计算分数
score = calculator.compute_score_for_message("msg-123", "active")

# 为决策集计算所有分数（active + shadows）
scores = calculator.compute_scores_for_decision_set("ds-abc123")

# 批量计算
batch_scores = calculator.compute_scores_batch([
    "ds-001", "ds-002", "ds-003"
])
```

### `RealityAlignmentScore`

```python
score.score           # 最终分数 (0.0-1.0)
score.raw_score       # 原始分数（截断前）
score.signal_contributions  # 信号贡献列表
score.total_signals_count   # 信号总数
score.signals_by_category   # 按分类统计
```

### `SignalContribution`

```python
contrib.signal_type    # 信号类型
contrib.weight         # 权重
contrib.count          # 出现次数
contrib.contribution   # 总贡献 (weight × count)
contrib.description    # 描述
```

---

## 分数解读

| 分数范围 | 解读 |
|---------|------|
| **0.9 - 1.0** | 优秀对齐，决策完全匹配用户需求 |
| **0.7 - 0.9** | 良好对齐，有轻微摩擦 |
| **0.5 - 0.7** | 中等对齐，有明显摩擦 |
| **0.3 - 0.5** | 差对齐，有严重摩擦 |
| **0.0 - 0.3** | 严重不对齐，决策与用户需求相悖 |

---

## 常见模式

### 查询历史评估

```python
from agentos.core.audit import get_shadow_evaluations_for_decision_set

evaluations = get_shadow_evaluations_for_decision_set("ds-abc123")
for eval in evaluations:
    payload = eval["payload"]
    print(f"Active: {payload['active_score']}")
    print(f"Shadows: {payload['shadow_scores']}")
```

### 自定义权重

```python
custom_weights = {
    "smooth_completion": (0.2, "positive", "Double weight"),
    "phase_violation": (-0.5, "negative", "Heavier penalty"),
}
calculator = ShadowScoreCalculator(signal_weights=custom_weights)
```

---

## 文件位置

- **实现**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/shadow_evaluator.py`
- **单元测试**: `tests/unit/core/chat/test_shadow_evaluator.py`
- **集成测试**: `tests/integration/chat/test_shadow_evaluator_e2e.py`
- **验收报告**: `SHADOW_SCORE_CALCULATOR_ACCEPTANCE_REPORT.md`

---

## 性能指标

- **单次评估**: < 50ms
- **批量评估**: ~200 评估/秒
- **内存占用**: < 1KB per score

---

## 测试

```bash
# 运行单元测试
python3 -m pytest tests/unit/core/chat/test_shadow_evaluator.py -v

# 运行集成测试
python3 -m pytest tests/integration/chat/test_shadow_evaluator_e2e.py -v

# 运行所有测试
python3 -m pytest tests/unit/core/chat/test_shadow_evaluator.py tests/integration/chat/test_shadow_evaluator_e2e.py -v
```

---

**最后更新**: 2026-01-31
**版本**: 1.0
