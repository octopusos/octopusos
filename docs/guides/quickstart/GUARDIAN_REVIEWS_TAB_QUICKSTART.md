# Guardian Reviews Tab - 快速参考指南

## 快速启动

### 1. 在浏览器中访问

```bash
# 启动 WebUI
python -m agentos.webui.app

# 访问 http://localhost:8080
# 导航到 Tasks 视图
# 点击任意 Task 打开详情
# 切换到 "Guardian Reviews" Tab
```

### 2. 测试组件（独立测试）

```bash
# 在浏览器中打开测试文件
open test_guardian_reviews_tab.html
```

---

## 文件结构

```
agentos/webui/
├── static/
│   ├── css/
│   │   └── guardian.css                  # Guardian 样式文件
│   └── js/
│       ├── components/
│       │   └── GuardianReviewPanel.js    # Guardian 组件
│       └── views/
│           └── TasksView.js              # Tasks 视图（已更新）
└── templates/
    └── index.html                        # 主页（已更新）
```

---

## 核心组件

### GuardianReviewPanel

**位置**: `agentos/webui/static/js/components/GuardianReviewPanel.js`

**用法**:
```javascript
const panel = new GuardianReviewPanel({
    container: document.getElementById('guardian-reviews-container'),
    verdictData: {
        target_type: "task",
        target_id: "task_123",
        total_reviews: 3,
        latest_verdict: "PASS",
        all_verdicts: ["PASS", "NEEDS_REVIEW", "PASS"]
    },
    reviews: [
        {
            review_id: "review_001",
            guardian_id: "guardian.ruleset.v1",
            review_type: "AUTO",
            verdict: "PASS",
            confidence: 0.95,
            evidence: { checks: ["ok"] },
            created_at: "2026-01-28T15:30:00Z"
        }
    ]
});
panel.render();
```

---

## API 端点

### 获取验收摘要

```bash
GET /api/guardian/targets/task/{task_id}/verdict
```

**响应**:
```json
{
    "target_type": "task",
    "target_id": "task_123",
    "total_reviews": 3,
    "latest_verdict": "PASS",
    "latest_review_id": "review_003",
    "latest_guardian_id": "guardian.ruleset.v3",
    "all_verdicts": ["PASS", "NEEDS_REVIEW", "PASS"]
}
```

### 获取完整审查列表

```bash
GET /api/guardian/reviews?target_type=task&target_id={task_id}
```

**响应**:
```json
{
    "reviews": [
        {
            "review_id": "review_003",
            "target_type": "task",
            "target_id": "task_123",
            "guardian_id": "guardian.ruleset.v3",
            "review_type": "AUTO",
            "verdict": "PASS",
            "confidence": 0.95,
            "rule_snapshot_id": "ruleset:v3@sha256:def456",
            "evidence": {
                "checks": ["state_machine_ok", "no_errors"],
                "metrics": { "coverage": 0.92 }
            },
            "created_at": "2026-01-28T15:30:00Z"
        }
    ],
    "total": 1
}
```

---

## 样式定制

### 修改 Verdict 颜色

编辑 `guardian.css`:

```css
.timeline-marker.pass {
    background: #28a745;  /* 修改 PASS 颜色 */
}

.timeline-marker.fail {
    background: #dc3545;  /* 修改 FAIL 颜色 */
}

.timeline-marker.needs_review {
    background: #ffc107;  /* 修改 NEEDS_REVIEW 颜色 */
}
```

### 修改 Confidence 进度条颜色

```css
.progress-fill {
    background: linear-gradient(90deg, #28a745, #20c997);  /* 修改渐变色 */
}
```

---

## 常见问题

### Q: Guardian Reviews Tab 不显示数据？

**A**: 检查以下几点：
1. API 端点是否正常返回数据
2. 浏览器控制台是否有错误
3. Task 是否有关联的 Guardian Reviews

**调试步骤**:
```javascript
// 在浏览器控制台执行
fetch('/api/guardian/targets/task/YOUR_TASK_ID/verdict')
    .then(r => r.json())
    .then(console.log);
```

### Q: Evidence 无法展开？

**A**: 检查 `GuardianReviewPanel.js` 中的 `attachEventListeners()` 方法是否被调用。

### Q: 样式不一致？

**A**: 确保 `guardian.css` 已正确引入到 `index.html` 中。

### Q: 如何添加新的 Verdict 类型？

**A**:
1. 在 `GuardianReviewPanel.js` 的 `renderVerdictBadge()` 方法中添加新类型
2. 在 `guardian.css` 中添加对应的样式

---

## 示例代码

### 创建一个 Guardian Review

```python
from agentos.core.guardian import GuardianService

service = GuardianService()
review = service.create_review(
    target_type="task",
    target_id="task_123",
    guardian_id="guardian.ruleset.v1",
    review_type="AUTO",
    verdict="PASS",
    confidence=0.95,
    evidence={
        "checks": ["state_machine_ok", "no_errors"],
        "metrics": {"coverage": 0.92}
    },
    rule_snapshot_id="ruleset:v1@sha256:abc123"
)
print(f"Created review: {review.review_id}")
```

### 查询 Task 的所有 Guardian Reviews

```python
from agentos.core.guardian import GuardianService

service = GuardianService()
reviews = service.get_reviews_by_target("task", "task_123")

for review in reviews:
    print(f"{review.created_at}: {review.verdict} (confidence: {review.confidence})")
```

---

## 扩展功能

### 添加过滤器

在 `TasksView.js` 的 Guardian Reviews Tab 中添加过滤器：

```javascript
// 添加过滤器 UI
const filtersHtml = `
    <div class="guardian-filters">
        <select id="guardian-filter-verdict">
            <option value="">All Verdicts</option>
            <option value="PASS">PASS</option>
            <option value="FAIL">FAIL</option>
            <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
        </select>
    </div>
`;

// 添加过滤逻辑
document.getElementById('guardian-filter-verdict').addEventListener('change', (e) => {
    const verdict = e.target.value;
    const filteredReviews = verdict
        ? reviews.filter(r => r.verdict === verdict)
        : reviews;
    this.renderGuardianReviewsPanel(container, verdictData, filteredReviews);
});
```

### 添加导出功能

```javascript
// 添加导出按钮
<button id="export-guardian-reviews">Export to JSON</button>

// 添加导出逻辑
document.getElementById('export-guardian-reviews').addEventListener('click', () => {
    const dataStr = JSON.stringify(reviews, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);

    const exportFileDefaultName = `guardian-reviews-${taskId}.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
});
```

---

## 性能优化

### 分页加载

对于 reviews 数量很多的情况，考虑分页加载：

```javascript
async loadGuardianReviews(taskId, limit = 10, offset = 0) {
    const reviewsResp = await apiClient.get(
        `/api/guardian/reviews?target_type=task&target_id=${taskId}&limit=${limit}&offset=${offset}`
    );

    if (reviewsResp.ok) {
        // 渲染 reviews
        // 添加 "Load More" 按钮
    }
}
```

### 虚拟滚动

对于超长列表，考虑使用虚拟滚动库（如 `virtual-scroller`）。

---

## 测试

### 单元测试

```javascript
// 测试 GuardianReviewPanel 渲染
describe('GuardianReviewPanel', () => {
    it('should render empty state when no reviews', () => {
        const container = document.createElement('div');
        const panel = new GuardianReviewPanel({
            container,
            verdictData: { total_reviews: 0 },
            reviews: []
        });
        panel.render();

        expect(container.querySelector('.empty-state')).toBeTruthy();
    });

    it('should render reviews timeline', () => {
        const container = document.createElement('div');
        const panel = new GuardianReviewPanel({
            container,
            verdictData: { total_reviews: 1, latest_verdict: 'PASS' },
            reviews: [{
                review_id: 'test',
                verdict: 'PASS',
                confidence: 0.95,
                created_at: '2026-01-28T15:30:00Z'
            }]
        });
        panel.render();

        expect(container.querySelector('.guardian-timeline')).toBeTruthy();
        expect(container.querySelectorAll('.timeline-item').length).toBe(1);
    });
});
```

---

## 相关文档

- [Task #3 交付报告](TASK_3_GUARDIAN_REVIEWS_TAB_DELIVERY.md)
- [Guardian Service 文档](agentos/core/guardian/README.md)
- [Guardian API 文档](agentos/webui/api/guardian.py)

---

**更新时间**: 2026-01-28
**版本**: v1.0
