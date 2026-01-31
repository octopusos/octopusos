# 标题样式标准化 - 快速参考手册

**最后更新:** 2026-01-30
**状态:** ✅ 已完成验收

---

## 📐 标准模板

### HTML 结构
```html
<div class="view-header">
    <div>
        <h1>页面标题</h1>
        <p class="text-sm text-gray-600 mt-1">页面副标题描述</p>
    </div>
    <div class="header-actions">
        <button class="btn-primary">操作按钮</button>
    </div>
</div>
```

### CSS 样式规范
```css
/* 全局默认 (components.css) */
.view-header h1 {
    font-size: 18px;      /* 1.125rem */
    font-weight: 600;
    color: #212529;
    margin: 0;
}

/* 页面级覆盖（可选）*/
.your-view .view-header h1 {
    font-size: 1.25rem;   /* 20px - 比副标题大1.43x */
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 4px 0;
}

.your-view .view-header p {
    font-size: 0.875rem;  /* 14px - text-sm */
    color: #6b7280;
    margin: 0;
}
```

---

## ✅ 验收检查清单

创建新页面时，请确保：

- [ ] 使用 `<h1>` 标签作为主标题（不是h2或h3）
- [ ] 主标题包裹在 `.view-header` 结构中
- [ ] 副标题使用 `class="text-sm text-gray-600 mt-1"`
- [ ] 主标题字体大小为 18-20px (1.125rem - 1.25rem)
- [ ] 副标题字体大小为 14px (0.875rem, text-sm)
- [ ] 字体比例在 1.25-1.5 倍之间
- [ ] 视觉层级清晰：主标题 > 副标题 > 正文

---

## 📊 合格页面示例

### 示例 1: Extensions View
```javascript
this.container.innerHTML = `
    <div class="extensions-view">
        <div class="view-header">
            <div>
                <h1>Extensions</h1>
                <p class="text-sm text-gray-600 mt-1">Install and manage AgentOS extensions</p>
            </div>
            <div class="header-actions">
                <button class="btn-primary">Create Extension</button>
            </div>
        </div>
        <!-- 页面内容 -->
    </div>
`;
```

### 示例 2: Tasks View (使用自定义字体大小)
```javascript
// HTML 结构
<div class="tasks-view">
    <div class="view-header">
        <h1>Task Management</h1>
        <p class="text-sm text-gray-600 mt-1">Manage and monitor task lifecycle</p>
        <!-- ... -->
    </div>
</div>

// CSS 覆盖 (在 components.css 中)
.tasks-view .view-header h1 {
    font-size: 1.25rem;  /* 20px */
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 4px 0;
}

.tasks-view .view-header p {
    margin: 0;
    font-size: 0.875rem;  /* 14px */
    color: #6b7280;
}
```

---

## 🎨 字体大小对照表

| 用途 | Tailwind | rem | px | 说明 |
|------|----------|-----|-----|------|
| 主标题(默认) | - | 1.125rem | 18px | 全局默认，比例1.29x |
| 主标题(强调) | - | 1.25rem | 20px | 部分页面，比例1.43x |
| 副标题 | text-sm | 0.875rem | 14px | 标准副标题 |
| 正文 | text-base | 1rem | 16px | 页面内容 |
| 小字 | text-xs | 0.75rem | 12px | 辅助信息 |

---

## 🚀 常见场景

### 场景1: 带图标的标题
```html
<h1>🛡️ Mode System Monitor</h1>
<p class="text-sm text-gray-600 mt-1">Real-time mode system monitoring</p>
```

### 场景2: 中文标题
```html
<h1>任务时间线</h1>
<p class="text-sm text-gray-600 mt-1">任务执行时间线和追踪</p>
```

### 场景3: 多语言标题
```html
<h1>Local Model Providers</h1>
<p class="text-sm text-gray-600 mt-1">Configure and monitor local LLM providers</p>
```

### 场景4: 带面包屑的标题
```html
<div class="view-header">
    <div class="header-left">
        <h1>Intent Workbench</h1>
        <p class="text-sm text-gray-600 mt-1">Test and refine intent detection</p>
        <div class="breadcrumb">
            <a href="#" class="breadcrumb-link">
                <span class="material-icons md-18">arrow_back</span>
                Task 123
            </a>
        </div>
    </div>
    <div class="header-actions">...</div>
</div>
```

---

## ⚠️ 常见错误

### ❌ 错误示例 1: 使用 h2 而非 h1
```html
<!-- 错误 -->
<div class="view-header">
    <h2>Projects</h2>  <!-- 应该用 h1 -->
</div>
```

### ❌ 错误示例 2: 缺少副标题样式类
```html
<!-- 错误 -->
<h1>Extensions</h1>
<p>Install and manage extensions</p>  <!-- 缺少样式类 -->

<!-- 正确 -->
<h1>Extensions</h1>
<p class="text-sm text-gray-600 mt-1">Install and manage extensions</p>
```

### ❌ 错误示例 3: 字体大小不当
```css
/* 错误 - 主标题太小 */
.view-header h1 {
    font-size: 14px;  /* 和副标题一样大 */
}

/* 错误 - 主标题太大 */
.view-header h1 {
    font-size: 32px;  /* 比副标题大2.3倍，过于突兀 */
}

/* 正确 */
.view-header h1 {
    font-size: 18px;  /* 或 20px，比副标题大1.29-1.43倍 */
}
```

---

## 📍 文件位置

### JavaScript 视图文件
```
/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/
├── ExtensionsView.js
├── ConfigView.js
├── TasksView.js
└── ... (共32个文件)
```

### CSS 样式文件
```
/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/css/
└── components.css  (第803-2888行包含相关样式)
```

---

## 🔍 验收报告

完整验收报告请查看:
- **主报告:** `/Users/pangge/PycharmProjects/AgentOS/TITLE_STYLE_FINAL_ACCEPTANCE_REPORT.md`
- **验收结果:** 32/32 页面通过 (100% 合规)
- **验收日期:** 2026-01-30

---

## 📞 支持

如有任何关于标题样式的问题，请参考：
1. 本快速参考手册
2. 完整验收报告
3. components.css 中的注释
4. 各个页面的实现示例

**最佳实践:** 参考 ExtensionsView.js、TasksView.js、ConfigView.js 等已验收页面的实现。

---

**文档版本:** 1.0
**维护者:** AgentOS WebUI Team
**最后验收:** 2026-01-30
