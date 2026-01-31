# Config View CSS 统一指南

## 🎨 视觉统一目标

确保 Config 页面和 Runtime / Providers 页面使用**相同的视觉语言**。

---

## 📐 关键样式规范

### 1. PageHeader 结构

```css
.view-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid #e5e7eb;
}

.view-header h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
    margin: 0;
}

.view-header p {
    font-size: 0.875rem;
    color: #6b7280;
    margin-top: 4px;
}

.header-actions {
    display: flex;
    gap: 8px;
}
```

### 2. Section 和 Card

```css
/* Section 间距（关键） */
.config-section {
    margin-bottom: 24px;
}

.config-section:last-child {
    margin-bottom: 0;
}

/* Section Title */
.config-section-title {
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
}

/* Card 容器 */
.config-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
```

### 3. Property Grid（和 RuntimeView 对齐）

```css
/* Detail Grid（键值对网格） */
.detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
}

.detail-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.detail-label {
    font-size: 0.75rem;
    font-weight: 500;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.detail-value {
    font-size: 0.875rem;
    color: #111827;
}
```

### 4. Environment Variables 表格

```css
.config-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
}

.config-table thead {
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
}

.config-table th {
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    color: #6b7280;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.config-table td {
    padding: 12px;
    border-bottom: 1px solid #f3f4f6;
}

.config-table tbody tr:hover {
    background: #f9fafb;
}

.config-table tbody tr:last-child td {
    border-bottom: none;
}
```

### 5. Filter 输入框

```css
.input-sm {
    padding: 6px 12px;
    font-size: 0.875rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    outline: none;
    transition: border-color 0.2s;
}

.input-sm:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input-sm::placeholder {
    color: #9ca3af;
}
```

### 6. Badge（count / status 标签）

```css
.badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 500;
    border-radius: 12px;
}

.badge-info {
    background: #dbeafe;
    color: #1e40af;
}

.badge-success {
    background: #d1fae5;
    color: #065f46;
}

.badge-warning {
    background: #fef3c7;
    color: #92400e;
}

.badge-error {
    background: #fee2e2;
    color: #991b1b;
}
```

### 7. Buttons（统一按钮风格）

```css
/* Primary Button */
.btn-primary {
    padding: 8px 16px;
    font-size: 0.875rem;
    font-weight: 500;
    color: #ffffff;
    background: #3b82f6;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: background 0.2s;
}

.btn-primary:hover {
    background: #2563eb;
}

/* Secondary Button */
.btn-secondary {
    padding: 8px 16px;
    font-size: 0.875rem;
    font-weight: 500;
    color: #374151;
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
}

.btn-secondary:hover {
    background: #f9fafb;
    border-color: #9ca3af;
}

/* Refresh Button（特殊样式） */
.btn-refresh {
    padding: 8px 16px;
    font-size: 0.875rem;
    font-weight: 500;
    color: #374151;
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
}

.btn-refresh:hover {
    background: #f9fafb;
    border-color: #9ca3af;
}

/* Small Button */
.btn-sm {
    padding: 6px 12px;
    font-size: 0.8125rem;
}

/* Icon Button（表格内操作按钮） */
.btn-icon {
    padding: 4px;
    background: transparent;
    border: none;
    color: #6b7280;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s;
}

.btn-icon:hover {
    background: #f3f4f6;
    color: #111827;
}
```

### 8. Modal（Raw JSON Modal）

```css
.modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1000;
    display: none;
    align-items: center;
    justify-content: center;
}

.modal-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
}

.modal-content {
    position: relative;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15);
    max-width: 90vw;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    z-index: 1001;
}

.modal-lg {
    width: 800px;
}

.modal-header {
    padding: 20px 24px;
    border-bottom: 1px solid #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.modal-header h3 {
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
    margin: 0;
}

.modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: #6b7280;
    cursor: pointer;
    padding: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s;
}

.modal-close:hover {
    background: #f3f4f6;
    color: #111827;
}

.modal-body {
    padding: 24px;
    overflow-y: auto;
    flex: 1;
}
```

---

## 🔍 检查清单

在改造完成后，使用以下清单检查视觉一致性：

### 和 RuntimeView 对比

- [ ] PageHeader 高度、间距一致
- [ ] Section Title 字体、颜色一致
- [ ] Card 圆角、阴影、padding 一致
- [ ] Detail Grid 网格间距一致
- [ ] Button 大小、颜色、hover 效果一致

### 和 ProvidersView 对比

- [ ] 表格样式（thead / tbody / hover）一致
- [ ] Badge 样式（info / success / warning）一致
- [ ] Modal 样式（overlay / content / close）一致

### 整体一致性

- [ ] Icon 大小统一（`md-18` / `md-14`）
- [ ] 颜色使用统一（gray-600 / gray-500 / blue-600）
- [ ] 圆角统一（6px / 8px / 12px）
- [ ] 过渡动画统一（0.2s）

---

## 🎨 颜色规范（Tailwind CSS）

### 主色调

```css
/* Primary */
--color-primary: #3b82f6;
--color-primary-hover: #2563eb;

/* Gray Scale */
--color-gray-50: #f9fafb;
--color-gray-100: #f3f4f6;
--color-gray-200: #e5e7eb;
--color-gray-300: #d1d5db;
--color-gray-400: #9ca3af;
--color-gray-500: #6b7280;
--color-gray-600: #4b5563;
--color-gray-700: #374151;
--color-gray-900: #111827;

/* Status Colors */
--color-success: #10b981;
--color-warning: #f59e0b;
--color-error: #ef4444;
```

### 使用场景

| 元素 | 颜色 |
|------|------|
| 标题 | gray-900 (#111827) |
| 正文 | gray-700 (#374151) |
| 次要文本 | gray-600 (#4b5563) |
| 占位符/提示 | gray-500 (#6b7280) |
| Label | gray-500 (uppercase) |
| 边框 | gray-200 (#e5e7eb) |
| 背景（hover） | gray-50 (#f9fafb) |
| Badge 背景 | blue-50 / green-50 / yellow-50 |

---

## 📏 间距规范

### Spacing Scale（Tailwind）

| Token | Value | 使用场景 |
|-------|-------|----------|
| gap-2 | 8px | Button 内 icon + text |
| gap-3 | 12px | Button group |
| gap-4 | 16px | Detail Grid |
| mb-3 | 12px | Section Title 下方 |
| mb-4 | 16px | Card 内段落 |
| mb-6 | 24px | Section 之间 |
| p-4 | 16px | Card padding |
| p-6 | 24px | Modal padding |

### 关键间距

```css
/* Section 间距 */
.config-section + .config-section {
    margin-top: 24px;
}

/* Card 内间距 */
.config-card {
    padding: 16px;
}

/* 大 Card 内间距 */
.config-card.p-lg {
    padding: 20px 24px;
}

/* PageHeader 下间距 */
.view-header {
    margin-bottom: 24px;
}
```

---

## 🔧 实用工具类

### 快速添加的工具类

```css
/* Text Helpers */
.text-xs { font-size: 0.75rem; }
.text-sm { font-size: 0.875rem; }
.text-base { font-size: 1rem; }
.text-lg { font-size: 1.125rem; }

/* Font Weight */
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }

/* Flex Helpers */
.flex { display: flex; }
.flex-wrap { flex-wrap: wrap; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }

/* Margin Helpers */
.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 16px; }
.mb-2 { margin-top: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.ml-2 { margin-left: 8px; }

/* Padding Helpers */
.p-4 { padding: 16px; }
.py-4 { padding-top: 16px; padding-bottom: 16px; }
.py-8 { padding-top: 32px; padding-bottom: 32px; }
```

---

## ✅ CSS 修改建议

### 如果已有 `config.css`

1. **对比 `runtime.css`**，找出差异
2. **统一 class 命名**（`.config-section` vs `.detail-section`）
3. **调整间距**（Section / Card / Grid）
4. **统一按钮样式**（参考 `providers.css`）

### 如果没有 `config.css`

- 复用全局样式（`main.css` / `views.css`）
- 只需调整局部差异（如 Modal 样式）

---

## 🚀 快速验证方法

### 1. 并排对比

```bash
# 打开 Config 和 Runtime 页面
# 并排放置浏览器窗口
# 逐一对比 Section / Card / Button
```

### 2. Chrome DevTools

```javascript
// 在控制台检查元素样式
document.querySelector('.config-section').style
document.querySelector('.detail-grid').style

// 对比 margin / padding
getComputedStyle(document.querySelector('.config-card')).padding
```

### 3. CSS Diff

```bash
# 如果有独立 CSS 文件
diff agentos/webui/static/css/views/config.css \
     agentos/webui/static/css/views/runtime.css
```

---

## 📝 总结

**核心原则**：

1. **不重复造轮子**：优先复用现有 class
2. **保持一致性**：间距 / 颜色 / 字体完全对齐
3. **简洁优先**：能用 utility class 就不写自定义 CSS

**改造后效果**：

用户从 Overview → Providers → Runtime → **Config**，应该感觉是在**同一个系统**中导航，而不是跳到了"开发者调试页面"。

---

如有疑问，参考 RuntimeView 和 ProvidersView 的样式实现！
