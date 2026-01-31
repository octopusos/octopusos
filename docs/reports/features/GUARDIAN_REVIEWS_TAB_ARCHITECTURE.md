# Guardian Reviews Tab - 架构图

## 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         WebUI Frontend                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    TasksView.js                           │ │
│  │  (View Controller - 控制器层)                             │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  • setupTabSwitching()        - Tab 切换逻辑             │ │
│  │  • loadGuardianReviews()      - 数据加载                 │ │
│  │  • renderGuardianReviewsPanel() - 渲染调用               │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │ calls                                    │
│                      ↓                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              GuardianReviewPanel.js                       │ │
│  │  (Component - 组件层)                                     │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  • render()                   - 主渲染                    │ │
│  │  • renderOverallStatus()      - 整体状态                  │ │
│  │  • renderTimeline()           - 时间线                    │ │
│  │  • attachEventListeners()     - 事件绑定                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    guardian.css                           │ │
│  │  (Styles - 样式层)                                        │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  • .guardian-overall-status   - 整体状态样式              │ │
│  │  • .guardian-timeline         - 时间线样式                │ │
│  │  • .timeline-marker           - 标记点样式                │ │
│  │  • .badge                     - 徽章样式                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/REST API
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      WebUI Backend (FastAPI)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                 guardian.py (API Router)                  │ │
│  │  (API 端点层)                                             │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  GET  /api/guardian/reviews                               │ │
│  │  GET  /api/guardian/targets/task/{id}/verdict             │ │
│  │  POST /api/guardian/reviews                               │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │ calls                                    │
│                      ↓                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              GuardianService (service.py)                 │ │
│  │  (业务逻辑层)                                             │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  • create_review()            - 创建审查记录              │ │
│  │  • get_reviews_by_target()    - 按目标查询               │ │
│  │  • get_verdict_summary()      - 获取验收摘要              │ │
│  │  • get_statistics()           - 统计数据                  │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │ calls                                    │
│                      ↓                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              GuardianStorage (storage.py)                 │ │
│  │  (数据访问层)                                             │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  • save()                     - 保存记录                  │ │
│  │  • get_by_id()                - 按 ID 查询                │ │
│  │  • get_by_target()            - 按目标查询                │ │
│  │  • query()                    - 灵活查询                  │ │
│  └───────────────────┬───────────────────────────────────────┘ │
│                      │ SQL                                      │
│                      ↓                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       SQLite Database                           │
├─────────────────────────────────────────────────────────────────┤
│  Table: guardian_reviews                                        │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ review_id          TEXT PRIMARY KEY                       │ │
│  │ target_type        TEXT                                   │ │
│  │ target_id          TEXT                                   │ │
│  │ guardian_id        TEXT                                   │ │
│  │ review_type        TEXT (AUTO/MANUAL)                     │ │
│  │ verdict            TEXT (PASS/FAIL/NEEDS_REVIEW)          │ │
│  │ confidence         REAL                                   │ │
│  │ evidence           TEXT (JSON)                            │ │
│  │ rule_snapshot_id   TEXT                                   │ │
│  │ created_at         TEXT                                   │ │
│  │                                                           │ │
│  │ Indexes:                                                  │ │
│  │  - idx_guardian_target (target_type, target_id)          │ │
│  │  - idx_guardian_created (created_at DESC)                │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 数据流动图

### 1. 加载 Guardian Reviews

```
User Action: Click "Guardian Reviews" Tab
        ↓
TasksView.setupTabSwitching()
    [检查] guardianReviewsLoaded === false?
        ↓ YES
TasksView.loadGuardianReviews(taskId)
        ↓
    [并行 API 请求]
        ├─→ GET /api/guardian/targets/task/{taskId}/verdict
        │       ↓
        │   guardian.py: get_target_verdict_summary()
        │       ↓
        │   GuardianService.get_verdict_summary()
        │       ↓
        │   GuardianStorage.get_by_target()
        │       ↓
        │   SQLite: SELECT * FROM guardian_reviews
        │            WHERE target_type = 'task'
        │            AND target_id = ?
        │            ORDER BY created_at DESC
        │       ↓
        │   返回: { total_reviews, latest_verdict, all_verdicts }
        │
        └─→ GET /api/guardian/reviews?target_type=task&target_id={taskId}
                ↓
            guardian.py: list_guardian_reviews()
                ↓
            GuardianService.list_reviews()
                ↓
            GuardianStorage.query()
                ↓
            SQLite: SELECT * FROM guardian_reviews
                     WHERE target_type = ?
                     AND target_id = ?
                     ORDER BY created_at DESC
                ↓
            返回: { reviews: [...], total: N }
        ↓
    [合并数据]
    verdictData + reviews[]
        ↓
TasksView.renderGuardianReviewsPanel(container, verdictData, reviews)
        ↓
new GuardianReviewPanel({ container, verdictData, reviews })
        ↓
GuardianReviewPanel.render()
    ├─→ renderOverallStatus()
    │       └─→ 计算平均 confidence
    │           └─→ 渲染进度条和徽章
    │
    └─→ renderTimeline()
            └─→ 按时间排序 reviews
                └─→ renderTimelineItem() × N
                        └─→ 渲染标记点 + 内容卡片 + Evidence
        ↓
GuardianReviewPanel.attachEventListeners()
    └─→ 绑定 Evidence 展开/折叠事件
        ↓
    [渲染完成]
    显示在 UI 上
```

---

## 组件交互图

```
┌─────────────────────────────────────────────────────────────┐
│                     Task Detail Drawer                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Task Detail Tab Navigation               │    │
│  ├────────────────────────────────────────────────────┤    │
│  │ [Overview] [Repos] [Dependencies] [Decision Trace] │    │
│  │ [Guardian Reviews] [Audit] [History]               │    │
│  └────────────────────────────────────────────────────┘    │
│                         ↓ click                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Guardian Reviews Tab Content               │    │
│  ├────────────────────────────────────────────────────┤    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │      Overall Status Card                     │  │    │
│  │  ├──────────────────────────────────────────────┤  │    │
│  │  │  Overall Status  [PASS]  3 Guardians        │  │    │
│  │  │  Confidence: [▓▓▓▓▓▓▓▓▓▓▓▓░░░] 95%          │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │      Review Timeline                         │  │    │
│  │  ├──────────────────────────────────────────────┤  │    │
│  │  │                                               │  │    │
│  │  │  ●─┬─ 2026-01-28 15:30  [AUTO]  [PASS]      │  │    │
│  │  │  │ │  Guardian: guardian.ruleset.v3          │  │    │
│  │  │  │ │  Confidence: 95%                        │  │    │
│  │  │  │ │  [View Evidence ▼]                      │  │    │
│  │  │  │ └───────────────────────────────────────  │  │    │
│  │  │  │                                            │  │    │
│  │  │  ●─┬─ 2026-01-28 14:15  [MANUAL]  [NEEDS]   │  │    │
│  │  │  │ │  Guardian: guardian.manual.reviewer     │  │    │
│  │  │  │ │  Confidence: 65%                        │  │    │
│  │  │  │ │  [View Evidence ▼]                      │  │    │
│  │  │  │ └───────────────────────────────────────  │  │    │
│  │  │  │                                            │  │    │
│  │  │  ●─┬─ 2026-01-28 12:00  [AUTO]  [PASS]      │  │    │
│  │  │    │  Guardian: guardian.ruleset.v2          │  │    │
│  │  │    │  Confidence: 88%                        │  │    │
│  │  │    │  [View Evidence ▼]                      │  │    │
│  │  │    └───────────────────────────────────────  │  │    │
│  │  │                                               │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │                                                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 状态机图

```
┌──────────────────────────────────────────────────────────────┐
│         Guardian Reviews Tab 状态机                          │
└──────────────────────────────────────────────────────────────┘

                    [Tab Not Active]
                           │
                           │ User clicks "Guardian Reviews" Tab
                           ↓
                    [Loading State]
                    ┌──────────────┐
                    │ Show spinner │
                    │ "Loading..." │
                    └──────────────┘
                           │
                           │ API requests complete
                           ↓
                    ┌──────────────┐
                    │  Check data  │
                    └──────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
         reviews.length > 0?      reviews.length === 0
                │                     │
                ↓                     ↓
         [Rendered State]      [Empty State]
         ┌──────────────┐      ┌──────────────┐
         │ Show status  │      │ Show message │
         │ Show timeline│      │ "No reviews" │
         │              │      │ + emoji      │
         └──────────────┘      └──────────────┘
                │
                │ User clicks "View Evidence"
                ↓
         [Evidence Expanded]
         ┌──────────────┐
         │ Show JSON    │
         │ in <pre>     │
         └──────────────┘
                │
                │ User clicks "Hide Evidence"
                ↓
         [Evidence Collapsed]
         (back to Rendered State)


         [Error State]
         ┌──────────────┐
         │ API failed   │
         │ Show error   │
         │ message      │
         └──────────────┘
                ↑
                │ If API request fails
                │
         (from any state)
```

---

## CSS 样式层次结构

```
guardian.css
│
├─ .guardian-overall-status           (整体状态容器)
│  ├─ .status-header                  (标题栏)
│  │  ├─ h3                           (标题)
│  │  ├─ .badge                       (Verdict 徽章)
│  │  └─ .review-count                (审查数量)
│  │
│  └─ .confidence-bar                 (置信度进度条)
│     ├─ label                        (标签)
│     ├─ .progress-bar                (进度条容器)
│     │  └─ .progress-fill            (进度填充 + shimmer 动画)
│     └─ .confidence-value            (数值显示)
│
├─ .guardian-timeline                 (时间线容器)
│  ├─ h4                              (标题)
│  └─ .timeline-items                 (时间线列表)
│     ├─ ::before                     (垂直线)
│     └─ .timeline-item               (单个时间线条目)
│        ├─ .timeline-marker          (标记点 - PASS/FAIL/NEEDS_REVIEW)
│        └─ .timeline-content         (内容卡片)
│           ├─ .timeline-header       (头部)
│           │  ├─ .timestamp          (时间戳)
│           │  ├─ .review-type-badge  (类型徽章 - AUTO/MANUAL)
│           │  └─ .badge              (Verdict 徽章)
│           │
│           └─ .timeline-body         (主体)
│              ├─ .guardian-info      (Guardian 信息)
│              ├─ .confidence-info    (置信度信息)
│              ├─ .rule-snapshot      (规则快照)
│              ├─ .btn-expand-evidence (展开按钮)
│              └─ .evidence-detail    (Evidence 详情)
│                 └─ pre              (JSON 显示)
│
├─ .badge                             (徽章基类)
│  ├─ .badge-success                  (PASS - 绿色)
│  ├─ .badge-danger                   (FAIL - 红色)
│  ├─ .badge-warning                  (NEEDS_REVIEW - 黄色)
│  └─ .badge-secondary                (UNKNOWN - 灰色)
│
├─ .empty-state                       (空状态)
│  ├─ .empty-icon                     (图标)
│  ├─ h3                              (标题)
│  ├─ p                               (描述)
│  └─ .empty-hint                     (提示)
│
├─ .guardian-loading                  (加载状态)
│  ├─ .loading-spinner                (加载动画)
│  └─ span                            (提示文字)
│
└─ .error-message                     (错误状态)
   ├─ .error-icon                     (错误图标)
   └─ .error-text                     (错误文字)
```

---

## 安全架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Security Layers                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Frontend (JavaScript)                                  │
│     ├─ HTML Escaping                                       │
│     │  └─ GuardianReviewPanel.escapeHtml()                │
│     │     • Prevents XSS attacks                           │
│     │     • Escapes: & < > " '                             │
│     │                                                       │
│     └─ Content Security Policy                             │
│        └─ No inline scripts in Evidence display            │
│                                                             │
│  2. Backend (FastAPI)                                      │
│     ├─ Input Validation                                    │
│     │  └─ Pydantic models validate all inputs             │
│     │     • target_type: Enum validation                   │
│     │     • verdict: Enum validation                       │
│     │     • confidence: Range validation (0.0-1.0)         │
│     │                                                       │
│     ├─ SQL Injection Prevention                            │
│     │  └─ Parameterized queries only                      │
│     │     • No string concatenation in SQL                 │
│     │                                                       │
│     └─ Rate Limiting (Future)                              │
│        └─ Prevent API abuse                                │
│                                                             │
│  3. Database (SQLite)                                      │
│     ├─ Immutable Records                                   │
│     │  └─ Guardian reviews never modified/deleted         │
│     │                                                       │
│     └─ Audit Trail                                         │
│        └─ created_at timestamp for all records            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 性能优化策略

```
┌─────────────────────────────────────────────────────────────┐
│                  Performance Optimizations                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 并行 API 请求                                           │
│     • Verdict + Reviews 同时请求                            │
│     • 减少总等待时间                                        │
│                                                             │
│  2. Lazy Loading                                           │
│     • 仅在切换到 Tab 时加载                                 │
│     • guardianReviewsLoaded 标志防止重复加载                │
│                                                             │
│  3. DOM 优化                                                │
│     • 使用 innerHTML 批量更新 DOM                            │
│     • 避免频繁的 DOM 操作                                   │
│                                                             │
│  4. CSS 动画优化                                            │
│     • 使用 transform 和 opacity (GPU 加速)                  │
│     • 避免 layout thrashing                                │
│                                                             │
│  5. 数据库索引                                              │
│     • idx_guardian_target (target_type, target_id)         │
│     • idx_guardian_created (created_at DESC)               │
│                                                             │
│  6. 未来优化 (如需要)                                       │
│     • 分页加载 (limit + offset)                             │
│     • 虚拟滚动 (长列表)                                     │
│     • WebSocket 实时更新                                    │
│     • Service Worker 缓存                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 扩展点

```
┌─────────────────────────────────────────────────────────────┐
│                    Extension Points                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 新增 Verdict 类型                                       │
│     • GuardianReviewPanel.renderVerdictBadge()             │
│     • guardian.css: 添加新颜色样式                         │
│                                                             │
│  2. 新增过滤器                                              │
│     • TasksView.loadGuardianReviews() 添加参数             │
│     • 添加 UI 过滤器组件                                    │
│                                                             │
│  3. 导出功能                                                │
│     • 添加 Export 按钮                                      │
│     • 支持 JSON/CSV/PDF 导出                                │
│                                                             │
│  4. 实时更新                                                │
│     • WebSocket 连接                                       │
│     • 监听新 Guardian Review 事件                           │
│                                                             │
│  5. 图表可视化                                              │
│     • 添加 Chart.js/D3.js                                   │
│     • 渲染 verdict 分布图                                   │
│                                                             │
│  6. 与其他模块集成                                          │
│     • 与 Decision Trace 关联                                │
│     • 与 Task Audit 关联                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 总结

Guardian Reviews Tab 采用**分层架构**设计：
- **表现层**: GuardianReviewPanel 组件负责 UI 渲染
- **控制层**: TasksView 负责数据获取和组件调用
- **API 层**: guardian.py 提供 REST 端点
- **业务层**: GuardianService 处理业务逻辑
- **数据层**: GuardianStorage 处理数据访问

设计原则：
- ✅ **关注点分离**: 每层职责清晰
- ✅ **可测试性**: 组件独立可测试
- ✅ **可扩展性**: 提供多个扩展点
- ✅ **安全性**: 多层防御机制
- ✅ **性能**: 并行请求 + 懒加载

---

**文档版本**: v1.0
**更新时间**: 2026-01-28
