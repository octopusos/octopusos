# P4-C2 Decision Review UI - 快速参考卡片

## 🚀 快速启动

```bash
# 1. 验证集成
./verify_decision_review_ui.sh

# 2. 启动 WebUI
agentos webui

# 3. 访问
http://localhost:8000
→ Governance > Decision Review
```

## 📁 文件清单

### 新增文件 (6个)
```
agentos/webui/static/js/views/DecisionReviewView.js    (1095行)
agentos/webui/static/css/decision-review.css           (773行)
tests/integration/webui/test_decision_review_ui.py     (273行)
P4_C2_DECISION_REVIEW_UI_COMPLETION.md                 (350行)
verify_decision_review_ui.sh                           (100行)
DECISION_REVIEW_UI_MANUAL_TEST_GUIDE.md                (400行)
```

### 修改文件 (2个)
```
agentos/webui/static/js/main.js                        (+12行)
agentos/webui/templates/index.html                     (+9行)
```

## 🎨 UI 布局

```
┌─────────────────────────────────────────────────────┐
│ 🏛️ Decision Review                     [Refresh]    │
├─────────────────────────────────────────────────────┤
│ Type: [All Types ▼]  Status: [All Status ▼]       │
├─────────────────┬───────────────────────────────────┤
│ Timeline (400px)│ Detail Panel                      │
│                 │                                   │
│ ┌─────────────┐ │ ┌─────────────────────────────┐ │
│ │ NAVIGATION  │ │ │ NAVIGATION                  │ │
│ │ How to ...  │ │ │ ID: dec_xxx                 │ │
│ │ 5分钟前      │ │ │ ✅ Verified                 │ │
│ │ [APPROVED]  │ │ │                             │ │
│ └─────────────┘ │ │ 当时认知 │ 当前认知         │ │
│                 │ │ ─────────┼───────────        │ │
│ ┌─────────────┐ │ │ Result 1 │ Result 1         │ │
│ │ COMPARE     │ │ │ ...      │ ...              │ │
│ │ Compare ... │ │ │                             │ │
│ │ [SIGNED]    │ │ └─────────────────────────────┘ │
│ └─────────────┘ │                                   │
└─────────────────┴───────────────────────────────────┘
```

## 🎨 颜色编码

### 状态标签
- 🟡 **PENDING** - `#fff3cd` (黄色)
- 🟢 **APPROVED** - `#d4edda` (绿色)
- 🔴 **BLOCKED** - `#f8d7da` (红色)
- 🔵 **SIGNED** - `#d1ecf1` (蓝色)
- 🔴 **FAILED** - `#f8d7da` (红色)

### 治理动作标签
- 🟢 **ALLOW** - `#d4edda` (绿色)
- 🟡 **WARN** - `#fff3cd` (黄色)
- 🔴 **BLOCK** - `#f8d7da` (红色)
- 🟠 **REQUIRE_SIGNOFF** - `#ffeaa7` (橙色)

## 🔌 API 端点

```
GET  /api/brain/governance/decisions?limit=100&decision_type=NAVIGATION
     → 列出决策记录

GET  /api/brain/governance/decisions/{decision_id}
     → 获取详情

GET  /api/brain/governance/decisions/{decision_id}/replay
     → 重放对比

POST /api/brain/governance/decisions/{decision_id}/signoff
     Body: { "signed_by": "...", "note": "..." }
     → 签字决策
```

## 🧪 测试命令

```bash
# 快速验证
./verify_decision_review_ui.sh

# Python 测试
python3 tests/integration/webui/test_decision_review_ui.py

# Pytest 测试
pytest tests/integration/webui/test_decision_review_ui.py -v

# 查看测试指南
cat DECISION_REVIEW_UI_MANUAL_TEST_GUIDE.md
```

## 📊 功能清单

- ✅ 决策时间线列表
- ✅ 类型过滤（NAVIGATION/COMPARE/HEALTH）
- ✅ 状态过滤（PENDING/APPROVED/BLOCKED/SIGNED/FAILED）
- ✅ 决策详情展示
- ✅ 完整性验证显示（✅/❌）
- ✅ 触发规则显示
- ✅ 重放对比（当时 vs 现在）
- ✅ 签字功能（条件显示）
- ✅ 签字表单验证
- ✅ 审计追踪显示
- ✅ 刷新功能
- ✅ 响应式布局

## 🐛 常见问题

### Q: 页面显示 "DecisionReviewView not loaded"
**A**: 清除浏览器缓存（Ctrl+Shift+R）

### Q: API 返回 404
**A**: 运行 `agentos brain build` 构建数据库

### Q: 签字按钮不显示
**A**: 只在 status=PENDING && final_verdict=REQUIRE_SIGNOFF 时显示

### Q: 样式不正常
**A**: 检查 index.html 是否引用了 decision-review.css

## 📋 签字流程

```
1. 找到 REQUIRE_SIGNOFF 决策
   ↓
2. 点击 "Sign Off" 按钮
   ↓
3. 填写签字表单
   - 签字人: [必填]
   - 备注: [必填]
   ↓
4. 点击 "确认签字"
   ↓
5. 状态更新为 SIGNED
```

## 🎯 验收检查点

```
□ 页面正常加载
□ 导航切换正常
□ 列表显示正常
□ 过滤器工作正常
□ 详情展开正常
□ 完整性验证显示正确
□ 重放对比显示正常
□ 签字按钮条件正确
□ 签字流程正常
□ 无 JavaScript 错误
□ 响应式布局正常
```

## 📚 相关文档

- **实施报告**: `P4_C2_DECISION_REVIEW_UI_COMPLETION.md`
- **测试指南**: `DECISION_REVIEW_UI_MANUAL_TEST_GUIDE.md`
- **总结报告**: `P4_C2_FINAL_SUMMARY.md`
- **验证脚本**: `verify_decision_review_ui.sh`

## 💡 关键代码位置

### 视图类
```javascript
// agentos/webui/static/js/views/DecisionReviewView.js
class DecisionReviewView {
    async render(container) { ... }
    async loadDecisions() { ... }
    async selectDecision(decision) { ... }
    async submitSignoff(id, signer, note) { ... }
}
```

### 样式
```css
/* agentos/webui/static/css/decision-review.css */
.decision-review-view { ... }
.timeline-item { ... }
.detail-panel { ... }
.signoff-modal { ... }
```

### 集成
```javascript
// agentos/webui/static/js/main.js
case 'decision-review':
    renderDecisionReviewView(container);
    break;
```

## 🔧 开发者注意事项

1. **状态管理**: DecisionReviewView 类管理内部状态
2. **生命周期**: render() 创建，destroy() 清理
3. **API 错误处理**: 所有 API 调用都有错误处理
4. **XSS 防护**: 使用 escapeHtml() 转义用户输入
5. **响应式**: 断点 1024px, 768px

## 📞 支持

如有问题：
1. 检查验证脚本输出
2. 查看浏览器控制台
3. 阅读测试指南
4. 查看 API 响应

---

**快速参考卡片 v1.0**
**更新时间**: 2026-01-31
