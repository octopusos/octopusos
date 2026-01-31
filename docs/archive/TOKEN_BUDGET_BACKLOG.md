# Token Budget 系统 - 改进 Backlog

## 📋 概述

本文档记录 Token Budget 可配置化系统（v0.6.0）发布后的改进计划。

**当前状态**：✅ v0.6.0 已完成，可发布
**Backlog 创建时间**：2025-01-30
**守门员校验来源**：用户反馈

---

## 🎯 改进清单

### 任务 #7: Budget Snapshot 写入 Audit/TaskDB

**优先级**：P1（重要但不紧急）
**预计工作量**：2-3 天
**不阻塞发布**：✅ 当前功能完整，这是增强项

#### 背景

当前 Budget Snapshot 仅在以下场景中存在：
- ✅ Runtime 状态（内存）
- ✅ WebSocket 推送（前端显示）
- ⚠️ 未持久化到审计日志

#### 问题陈述

未来需要回答的问题：
- "这次任务执行时用的预算配置是什么？"（Replay）
- "上周的对话为什么被截断？"（Post-mortem）
- "合规检查：Token 使用是否在预算内？"（Compliance）

**关键证据缺失**：无法追溯历史 budget snapshot。

#### 解决方案

**1. 数据库层**

扩展现有 `context_snapshots` 表：
```sql
-- 已有字段（v0.6.0）
snapshot_id TEXT PRIMARY KEY
session_id TEXT
created_at INTEGER
budget_tokens INTEGER
total_tokens_est INTEGER
...

-- 需要确保包含
budget_source TEXT  -- 'auto-derived' | 'configured'
model_context_window INTEGER
allocation_json TEXT  -- 完整的分配配置
```

**2. Task 关联**

在 Task 执行时关联 budget snapshot：
```python
# agentos/core/task/service.py (假设未来集成)
def execute_task(task_id: str):
    # 构建上下文
    context_pack = builder.build(session_id, user_input)

    # 关联 snapshot 到 task
    task_service.update_task(
        task_id=task_id,
        metadata={
            "context_snapshot_id": context_pack.snapshot_id,
            "budget_tokens": context_pack.usage.budget_tokens,
        }
    )
```

**3. Audit API**

新增查询端点：
```python
# agentos/webui/api/audit.py
@router.get("/audit/budget/{session_id}")
async def get_budget_history(session_id: str):
    """获取会话的 budget 使用历史"""
    snapshots = db.query(
        "SELECT * FROM context_snapshots WHERE session_id = ?",
        session_id
    )
    return {
        "snapshots": snapshots,
        "summary": {
            "avg_usage_ratio": ...,
            "peak_usage": ...,
            "truncation_events": ...
        }
    }
```

**4. Replay 工具**

支持重现历史预算：
```python
# agentos/core/chat/replay.py
def replay_with_original_budget(snapshot_id: str):
    """使用原始预算配置重现对话"""
    snapshot = load_snapshot(snapshot_id)
    budget = ContextBudget.from_snapshot(snapshot)

    # 重建上下文
    builder = ContextBuilder(budget=budget)
    # ... replay logic
```

#### 改动文件清单

- [ ] `agentos/store/migrations/schema_vXX.sql` - 确保 budget 字段完整
- [ ] `agentos/core/chat/context_builder.py` - 扩展 snapshot 元数据
- [ ] `agentos/core/task/service.py` - Task 关联 snapshot
- [ ] `agentos/webui/api/audit.py` - Budget 历史查询 API
- [ ] `agentos/core/chat/replay.py` - Replay 工具（新增）

#### 验收标准

- [ ] 每次对话的 budget snapshot 持久化到数据库
- [ ] Task 可查询其使用的 budget 配置
- [ ] Audit API 返回 budget 使用历史
- [ ] Replay 工具可重现原始预算

---

### 任务 #8: Completion 截断时的 UX 文案

**优先级**：P1（用户体验重要改进）
**预计工作量**：0.5-1 天
**不阻塞发布**：✅ 当前可用，这是体验优化

#### 背景

当 Completion 被截断时，用户看到：
- ❌ 回答突然中断（看起来像是模型出错）
- ❌ 无任何提示（不知道为什么停止）
- ❌ 误解："是不是模型坏了？"

#### 问题案例

```
用户：请写一个完整的 React 组件

模型：
import React from 'react';

const MyComponent = () => {
  const [state, setState] = useState(0);

  return (
    <div>
      <h1>Hello</h1>
      <button onClick={() => setState(state + 1)}>
        Count: {state}
      </button>
    </div>
  );
};

export default MyComponent;

const AnotherComponent = () => {
  // 这里突然断掉了...
```

用户心理："WTF？模型挂了？"

#### 解决方案

**检测截断**：
```python
# agentos/core/chat/adapters.py
def generate(self, messages, max_tokens=2000):
    response = client.chat.completions.create(...)

    # 检测截断
    if response.choices[0].finish_reason == 'length':
        truncated = True
        tokens_used = response.usage.completion_tokens

    return response.choices[0].message.content, {
        "truncated": truncated,
        "reason": "max_tokens_reached",
        "tokens_used": tokens_used,
        "tokens_limit": max_tokens
    }
```

**友好提示**：
```python
# agentos/webui/websocket/chat.py
async def handle_send_message(self, session_id, user_input):
    content, metadata = adapter.generate(messages)

    # 如果截断，附加提示消息
    if metadata.get("truncated"):
        hint = (
            f"\n\n---\n"
            f"ℹ️ Response truncated at {metadata['tokens_used']} tokens "
            f"(limit: {metadata['tokens_limit']}). "
            f"You can increase the generation limit in Settings → Token Budget."
        )
        content += hint

    await self.send_json({
        "type": "message_chunk",
        "content": content,
        "metadata": metadata
    })
```

**前端显示**：
```javascript
// agentos/webui/static/js/main.js
function renderMessage(message, metadata) {
    const messageEl = document.createElement('div');
    messageEl.className = 'message assistant-message';
    messageEl.textContent = message;

    // 如果截断，添加视觉提示
    if (metadata.truncated) {
        messageEl.classList.add('truncated-message');

        const hintEl = document.createElement('div');
        hintEl.className = 'truncation-hint';
        hintEl.innerHTML = `
            ℹ️ <strong>Response truncated</strong> at ${metadata.tokens_used} tokens.
            <a href="#" onclick="openBudgetSettings()">Adjust limit</a>
        `;
        messageEl.appendChild(hintEl);
    }

    return messageEl;
}
```

**CSS 样式**：
```css
/* agentos/webui/static/css/chat.css */
.truncated-message {
    border-left: 3px solid #ffc107; /* 黄色警告 */
}

.truncation-hint {
    margin-top: 10px;
    padding: 8px 12px;
    background: #fff3cd;
    border-radius: 4px;
    font-size: 0.9em;
    color: #856404;
}

.truncation-hint a {
    color: #0066cc;
    text-decoration: underline;
}
```

#### 文案设计原则

✅ **克制**：不是报错，只是提示
✅ **非指责性**：说"limit"，不说"错误"
✅ **可操作**：告知在哪里调整
✅ **简洁**：1-2 行

**好的文案**：
```
ℹ️ Response truncated at 2000 tokens (configurable in Settings).
```

**不好的文案**：
```
❌ ERROR: Token limit exceeded! Your model failed to complete the response.
```

#### 改动文件清单

- [ ] `agentos/core/chat/adapters.py` - 检测 finish_reason
- [ ] `agentos/webui/websocket/chat.py` - 附加提示消息
- [ ] `agentos/webui/static/js/main.js` - 渲染提示
- [ ] `agentos/webui/static/css/chat.css` - 样式

#### 验收标准

- [ ] Completion 截断时自动检测
- [ ] 提示消息友好且克制
- [ ] 提供可操作的调整入口
- [ ] 视觉上有区分（淡黄色背景）
- [ ] 不影响正常消息显示

---

### 任务 #9: Budget 推荐系统（智能建议）

**优先级**：P2（锦上添花）
**预计工作量**：3-5 天
**不阻塞发布**：✅ 当前 auto-derive 已足够好

#### 背景

当前 v0.6.0 的 auto-derive 功能：
- ✅ 基于模型窗口自动推导
- ✅ 固定比例分配（12.5%/50%/25%/12.5%）
- ⚠️ 不考虑用户实际使用习惯

#### 问题案例

**用户 A（轻度对话用户）**：
- 实际使用：每次 5-10 轮对话，很少用 RAG
- 当前预算：Window 45.9k, RAG 22.9k
- 问题：RAG 预算浪费，Window 可能不够

**用户 B（重度知识检索用户）**：
- 实际使用：每次查询大量文档，对话轮数少
- 当前预算：Window 45.9k, RAG 22.9k
- 问题：RAG 预算不够，Window 浪费

#### 解决方案：智能推荐系统

**1. 数据收集**

分析用户最近 N 次对话的 usage pattern：
```python
# agentos/core/chat/budget_recommender.py
class BudgetRecommender:
    def analyze_usage_pattern(self, session_id: str, last_n: int = 30):
        """分析最近 N 次对话的使用模式"""
        snapshots = db.query(
            "SELECT * FROM context_snapshots "
            "WHERE session_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            session_id, last_n
        )

        # 统计实际使用
        stats = {
            "avg_window_usage": mean([s.tokens_window for s in snapshots]),
            "avg_rag_usage": mean([s.tokens_rag for s in snapshots]),
            "avg_memory_usage": mean([s.tokens_memory for s in snapshots]),
            "window_utilization": mean([s.tokens_window / s.window_budget for s in snapshots]),
            "rag_utilization": mean([s.tokens_rag / s.rag_budget for s in snapshots]),
            # ...
        }

        return stats
```

**2. 推荐算法**

基于实际使用 + 保守 buffer：
```python
def recommend_budget(self, stats: dict, model_info: ModelInfo) -> ContextBudget:
    """基于使用统计推荐预算"""

    # 策略：P95 使用量 + 20% buffer
    recommended_window = int(stats["p95_window_usage"] * 1.2)
    recommended_rag = int(stats["p95_rag_usage"] * 1.2)
    recommended_memory = int(stats["p95_memory_usage"] * 1.2)

    # 确保不超过模型窗口
    total = recommended_window + recommended_rag + recommended_memory + 1000
    if total > model_info.context_window * 0.85:
        # 按比例缩减
        scale = (model_info.context_window * 0.85) / total
        recommended_window = int(recommended_window * scale)
        # ...

    return ContextBudget(
        window_tokens=recommended_window,
        rag_tokens=recommended_rag,
        memory_tokens=recommended_memory,
        metadata={"source": "ai_recommended"}
    )
```

**3. WebUI 展示**

在 Settings → Budget 页面新增"智能推荐"段：
```
┌─────────────────────────────────────────────────────┐
│ 💡 Smart Recommendation                             │
│                                                      │
│ Based on your last 30 conversations:                │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Component   │ Current │ Recommended │ Change   │ │
│ ├─────────────┼─────────┼─────────────┼──────────┤ │
│ │ Window      │ 45,900  │ 20,000      │ -56% 💰 │ │
│ │ RAG         │ 22,950  │ 35,000      │ +52% 📈 │ │
│ │ Memory      │ 11,475  │  5,000      │ -56% 💰 │ │
│ │ System      │ 11,475  │ 11,475      │  0%     │ │
│ └─────────────┴─────────┴─────────────┴──────────┘ │
│                                                      │
│ Estimated savings: 25% token waste reduction        │
│                                                      │
│ [Apply Recommendation]  [Dismiss]                   │
└─────────────────────────────────────────────────────┘
```

**4. API 端点**

```python
# agentos/webui/api/budget.py
@router.get("/budget/recommend/{session_id}")
async def get_budget_recommendation(session_id: str):
    """获取智能推荐预算"""
    recommender = BudgetRecommender()

    # 分析使用模式
    stats = recommender.analyze_usage_pattern(session_id)

    # 生成推荐
    current = get_current_budget(session_id)
    recommended = recommender.recommend_budget(stats, model_info)

    return {
        "current": current.to_dict(),
        "recommended": recommended.to_dict(),
        "reasoning": {
            "avg_window_usage": stats["avg_window_usage"],
            "window_utilization": stats["window_utilization"],
            "savings_estimate": calculate_savings(current, recommended)
        }
    }

@router.post("/budget/apply_recommendation/{session_id}")
async def apply_recommendation(session_id: str):
    """应用推荐配置"""
    # ...
```

#### 推荐策略

**基础版（P2.1）**：
- 简单统计（均值、P95、利用率）
- 固定 buffer（20%）
- 人工规则（最小值、最大值）

**进阶版（P2.2，可选）**：
- 时间序列分析（趋势）
- 异常检测（去除异常值）
- 机器学习（回归预测）
- 场景识别（代码生成、知识检索、闲聊）

#### 改动文件清单

- [ ] `agentos/core/chat/budget_recommender.py` - 推荐引擎（新增）
- [ ] `agentos/webui/api/budget.py` - 推荐 API 端点
- [ ] `agentos/webui/static/js/views/ConfigView.js` - 推荐 UI
- [ ] `agentos/webui/static/css/budget-recommendation.css` - 样式
- [ ] `tests/unit/chat/test_budget_recommender.py` - 单元测试

#### 验收标准

- [ ] 可分析最近 N 次对话的 usage pattern
- [ ] 推荐预算基于实际使用 + 保守 buffer
- [ ] WebUI 显示当前 vs 推荐对比
- [ ] 一键应用推荐配置
- [ ] 显示预估节省百分比

---

## 📊 优先级总结

| 任务 | 优先级 | 工作量 | 价值 | 建议时间线 |
|------|--------|--------|------|----------|
| #7 Budget Snapshot → Audit | P1 | 2-3 天 | 审计追溯 | v0.6.1 (2-3 周后) |
| #8 Completion 截断提示 | P1 | 0.5-1 天 | 用户体验 | v0.6.1 (2-3 周后) |
| #9 智能推荐系统 | P2 | 3-5 天 | 锦上添花 | v0.7.0 (1-2 月后) |

---

## 🚀 实施路线图

### Phase 1: v0.6.1（预计 3 周后）

**目标**：完善审计和用户体验

- ✅ 任务 #7：Budget Snapshot 写入 Audit/TaskDB
- ✅ 任务 #8：Completion 截断时的 UX 文案

**交付物**：
- Budget 历史可追溯（Replay/Post-mortem）
- 截断提示友好（减少误解）

### Phase 2: v0.7.0（预计 2 月后）

**目标**：智能化增强

- ✅ 任务 #9：Budget 推荐系统（基础版）

**交付物**：
- 基于使用模式的智能推荐
- 一键优化预算配置

### Phase 3: v0.8.0+（探索）

**可能的方向**：
- 多会话预算共享池
- 成本追踪与预警
- 预算策略模板（代码生成、文档问答、闲聊等）
- A/B 测试框架（测试不同预算配置）

---

## 📝 备注

### 不阻塞发布的原因

**v0.6.0 已完成核心目标**：
1. ✅ 解决大模型上下文被截断问题（自动推导）
2. ✅ 提供用户配置能力（Settings 界面）
3. ✅ 实时可视化（状态栏 + Budget 标签页）
4. ✅ 完整测试（104 个测试，100% 通过）
5. ✅ 向后兼容（零破坏性）

**Backlog 属于增强项**：
- 任务 #7：提升审计能力（但现有功能完整）
- 任务 #8：改善用户体验（但不影响功能）
- 任务 #9：智能优化（但当前已够用）

### 守门员校验的价值

这三个改进点体现了深度思考：
1. **审计视角**：从合规、追溯、复现的角度考虑
2. **用户体验**：从认知负荷、误解预防的角度优化
3. **演进路径**：从"推荐"到"强制"的清晰边界

感谢这轮高质量的守门员校验！ 🙏

---

**文档维护者**：AgentOS Team
**最后更新**：2025-01-30
**版本**：v1.0
