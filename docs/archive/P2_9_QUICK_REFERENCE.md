# P2-9: Budget 推荐系统 快速参考

## 🎯 核心原则

> **只"建议"，不"决定"**

- ✅ 推荐永不自动应用
- ✅ 用户必须显式确认
- ✅ 基于统计（P95 + 20% buffer）
- ✅ 不涉及语义分析

---

## 📁 文件清单

```
agentos/core/chat/budget_recommender.py     # 核心引擎
agentos/webui/api/budget.py                 # API 端点（新增）
agentos/webui/static/js/views/ConfigView.js # WebUI 推荐功能
tests/unit/chat/test_budget_recommender.py  # 单元测试
tests/integration/chat/test_budget_recommendation_e2e.py  # 集成测试
```

---

## 🚀 快速开始

### 用户使用流程

1. 打开 WebUI → **Configuration**
2. 滚动到 **Token Budget Configuration**
3. 点击 **"Show Smart Recommendation"**
4. 查看推荐对比表
5. 选择 **Apply** 或 **Dismiss**

### API 使用

```bash
# 获取推荐
curl -X POST http://localhost:8080/api/budget/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_test",
    "model_id": "gpt-4o",
    "context_window": 128000,
    "last_n": 30
  }'

# 应用推荐
curl -X POST http://localhost:8080/api/budget/apply-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation": {
      "window_tokens": 3000,
      "rag_tokens": 1500,
      "memory_tokens": 750,
      "system_tokens": 750
    },
    "session_id": "session_test"
  }'
```

---

## 🧮 推荐算法

```python
# 核心算法（保守策略）
推荐值 = P95(历史使用) * 1.2  # 20% buffer

# 约束条件
总推荐值 <= 模型窗口 * 0.85

# 最小可行值
window_tokens >= 2000
rag_tokens >= 1000
memory_tokens >= 500
system_tokens >= 500
```

---

## 📊 数据来源（只读）

- **context_snapshots 表**：历史 token 使用
- **watermark 状态**：截断频率分析
- **模型信息**：context_window 限制

**不使用**：
- ❌ 用户 prompt 内容
- ❌ 语义分析
- ❌ 模型输出质量判断

---

## 🎨 UI 交互

```
┌─────────────────────────────────────┐
│ Token Budget Configuration          │
│                                     │
│ [Current Config Card]               │
│                                     │
│ [Show Smart Recommendation]  [Save] │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 💡 Smart Recommendation         │ │  ← 默认折叠
│ │ [对比表格]                       │ │
│ │ [Apply] [Dismiss]               │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## ✅ 验收检查

```bash
# 运行测试
python3 -m pytest tests/unit/chat/test_budget_recommender.py -v
python3 -m pytest tests/integration/chat/test_budget_recommendation_e2e.py -v

# 预期结果
✅ 12 passed (单元测试)
✅ 8 passed (集成测试)
✅ 守门员红线测试通过
```

---

## 🛡️ 守门员红线

### ❌ 绝对禁止

1. **Silent Adjust**
   - 推荐不会自动应用
   - 测试：`test_recommendation_never_auto_applies`

2. **Override 用户配置**
   - Apply 前必须二次确认
   - 测试：`test_apply_requires_explicit_call`

3. **系统擅自决策**
   - 记录为 `user_applied_recommendation`
   - 测试：`test_recommendation_marked_as_ai_source`

### ✅ 允许行为

- 提供建议（用户请求后）
- 数据分析（统计方法）
- 友好提示（数据不足）
- 用户确认（二次确认）

---

## 🔍 故障排查

### 推荐不可用

**症状**: `available: false`

**可能原因**:
1. **insufficient_data**: 少于 10 次对话
   - 解决：继续使用系统，积累数据

2. **no_improvement**: 当前配置已优化
   - 解决：无需操作，保持现状

3. **recommendation_failed**: 算法错误
   - 解决：检查日志，报告 bug

### Apply 失败

**症状**: API 返回 400/500 错误

**检查点**:
1. 推荐格式是否完整？
2. token 值是否为负？
3. 总和是否超过模型窗口？

---

## 📐 关键代码片段

### 推荐引擎

```python
from agentos.core.chat.budget_recommender import BudgetRecommender

recommender = BudgetRecommender()

# 获取推荐
result = recommender.get_recommendation(
    session_id='session_test',
    current_budget={'window_tokens': 4000, ...},
    model_info=ModelInfo(id='gpt-4o', context_window=128000),
    last_n=30
)

if result['available']:
    recommended = result['recommended']
    print(f"推荐: {recommended['window_tokens']} window tokens")
    print(f"置信度: {recommended['metadata']['confidence']}")
```

### 前端调用

```javascript
// 加载推荐
async loadBudgetRecommendation() {
    const response = await apiClient.post('/api/budget/recommend', {
        session_id: window.currentSessionId,
        model_id: this.currentModelInfo.name,
        context_window: this.currentModelInfo.context_window,
        last_n: 30
    });

    if (response.ok && response.data.available) {
        this.renderRecommendation(response.data);
    }
}

// 应用推荐
async applyRecommendation(recommended) {
    const confirmed = await Dialog.confirm('Apply this recommendation?');
    if (!confirmed) return;

    await apiClient.post('/api/budget/apply-recommendation', {
        recommendation: recommended,
        session_id: window.currentSessionId
    });
}
```

---

## 📈 置信度等级

| 等级 | 样本数 | 说明 |
|------|--------|------|
| **High** | ≥30 | 推荐可靠 |
| **Medium** | 20-29 | 推荐较可靠 |
| **Low** | 10-19 | 推荐仅供参考 |
| N/A | <10 | 数据不足，不提供推荐 |

---

## 🔄 推荐不可用的场景

### 场景 1: 数据不足

```json
{
    "available": false,
    "reason": "insufficient_data",
    "hint": "At least 10 conversations needed...",
    "min_samples": 10
}
```

**用户看到**:
> "Smart Recommendation Not Available
> At least 10 conversations needed for recommendation.
> Keep using the system and recommendations will become available."

### 场景 2: 无需改进

```json
{
    "available": false,
    "reason": "no_improvement",
    "hint": "Your current budget is already well-optimized..."
}
```

**用户看到**:
> "Your current budget is already well-optimized based on usage patterns."

---

## 🎯 使用场景

### 场景 A: 新用户过度配置

**问题**: 新用户使用默认 4000 window tokens，但实际只用 2000

**推荐**:
```
Window: 4000 → 3000 (▼ 25%)
Est. Savings: 25% token waste reduction
```

### 场景 B: 高截断率

**问题**: 用户 budget 太小，60% 的对话被截断

**推荐**:
```
Window: 2000 → 3000 (▲ 50%)
Truncation Rate: 60% → ~12% (expected)
```

### 场景 C: 已优化

**问题**: 用户配置已接近 P95 使用

**推荐**:
```
No recommendation available.
Your current budget is already well-optimized.
```

---

## 📚 相关文档

- **P1-7**: Budget Snapshot → Audit/TaskDB（数据来源）
- **P2-9 实施报告**: 完整技术文档
- **Budget API 文档**: `/api/budget/*` 端点说明

---

## 🆘 支持

**问题报告**: GitHub Issues
**讨论**: 项目讨论区
**测试**: `python3 -m pytest tests/unit/chat/test_budget_recommender.py -v`

---

**版本**: 1.0
**最后更新**: 2026-01-30
