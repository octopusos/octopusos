# Modal 样式统一指南

## 概述

AgentOS WebUI 现在使用统一的 Modal 样式系统，所有弹窗保持一致的外观和交互体验。

## 样式文件位置

- **主样式文件**: `agentos/webui/static/css/modal-unified.css`
- 已在 `index.html` 中引入

## 标准 Modal 结构

```html
<div class="modal active">
    <!-- 背景遮罩层 -->
    <div class="modal-overlay"></div>

    <!-- Modal 内容容器 -->
    <div class="modal-content">
        <!-- Header: 标题和关闭按钮 -->
        <div class="modal-header">
            <h2>Modal 标题</h2>
            <button class="modal-close">&times;</button>
        </div>

        <!-- Body: 主要内容 -->
        <div class="modal-body">
            <div class="form-group">
                <label>字段名称</label>
                <input type="text" placeholder="请输入...">
                <div class="field-hint">提示信息</div>
            </div>
        </div>

        <!-- Footer: 操作按钮 -->
        <div class="modal-footer">
            <button class="btn-secondary">取消</button>
            <button class="btn-primary">确认</button>
        </div>
    </div>
</div>
```

## 关闭按钮统一样式

所有弹窗的关闭按钮已统一为以下样式：

```css
.modal-close {
    background: none;
    border: none;
    font-size: 24px;
    color: #6b7280;
    cursor: pointer;
    padding: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    transition: all 0.15s ease;
    flex-shrink: 0;
}

.modal-close:hover {
    background: #f3f4f6;
    color: #1f2937;
}

.modal-close:active {
    background: #e5e7eb;
}
```

### 统一的关闭按钮类名

以下所有类名都使用相同的样式规范：
- `.modal-close` - 标准 modal 关闭按钮
- `.btn-close` - 通用关闭按钮
- `.drawer-close-btn` - Drawer 关闭按钮
- `.history-close-btn` - 历史记录关闭按钮
- `.error-modal-close` - 错误弹窗关闭按钮
- `.pet-task-modal-close` - 宠物任务弹窗关闭按钮

### 关闭按钮规范

| 属性 | 值 | 说明 |
|------|-----|------|
| 尺寸 | `32x32px` | 固定尺寸 |
| 字体大小 | `24px` | 统一字号 |
| 圆角 | `6px` | 统一圆角 |
| 默认颜色 | `#6b7280` | 灰色 |
| Hover 背景 | `#f3f4f6` | 浅灰背景 |
| Hover 颜色 | `#1f2937` | 深灰色 |
| Active 背景 | `#e5e7eb` | 更深的灰背景 |
| 过渡时间 | `0.15s ease` | 平滑过渡 |

## Modal 尺寸

使用预定义的尺寸类：

```html
<!-- 小型 (400px) -->
<div class="modal-content modal-sm">...</div>

<!-- 中型 (600px, 默认) -->
<div class="modal-content modal-md">...</div>

<!-- 大型 (800px) -->
<div class="modal-content modal-lg">...</div>

<!-- 超大型 (1000px) -->
<div class="modal-content modal-xl">...</div>
```

## 按钮样式

### 主要按钮类型

| 类名 | 用途 | 颜色 |
|------|------|------|
| `.btn-primary` | 主要操作（确认、保存、提交） | 蓝色 |
| `.btn-secondary` | 次要操作（取消、关闭） | 灰色 |
| `.btn-danger` | 危险操作（删除、移除） | 红色 |
| `.btn-success` | 成功操作（完成、确认） | 绿色 |
| `.btn-ghost` | 轻量操作 | 透明 |

### 按钮位置规范

- **按钮对齐**: 所有按钮右对齐（`justify-content: flex-end`）
- **按钮顺序**: 次要按钮在左，主要按钮在右
- **按钮间距**: 12px gap

```html
<div class="modal-footer">
    <button class="btn-secondary">取消</button>
    <button class="btn-primary">确认</button>
</div>
```

## 表单元素

### Form Group 结构

```html
<div class="form-group">
    <label>字段标签</label>
    <input type="text" placeholder="请输入...">
    <div class="field-hint">辅助提示信息</div>
</div>
```

### 支持的输入类型

- `input[type="text"]`
- `input[type="email"]`
- `input[type="password"]`
- `input[type="url"]`
- `input[type="number"]`
- `input[type="file"]`
- `textarea`
- `select`

## JavaScript 使用示例

### 创建 Modal

```javascript
const modal = document.createElement('div');
modal.className = 'modal active';
modal.innerHTML = `
    <div class="modal-overlay"></div>
    <div class="modal-content modal-md">
        <div class="modal-header">
            <h2>标题</h2>
            <button class="modal-close" id="btnClose">&times;</button>
        </div>
        <div class="modal-body">
            <!-- 内容 -->
        </div>
        <div class="modal-footer">
            <button class="btn-secondary" id="btnCancel">取消</button>
            <button class="btn-primary" id="btnConfirm">确认</button>
        </div>
    </div>
`;

document.body.appendChild(modal);
```

### 关闭 Modal

```javascript
const closeModal = () => {
    modal.remove();
};

// 关闭按钮
document.getElementById('btnClose').addEventListener('click', closeModal);

// 取消按钮
document.getElementById('btnCancel').addEventListener('click', closeModal);

// 点击遮罩层关闭
modal.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal();
    }
});
```

## Modal 变体

### 带颜色的 Modal 类型

```html
<!-- 信息 Modal -->
<div class="modal modal-info active">...</div>

<!-- 成功 Modal -->
<div class="modal modal-success active">...</div>

<!-- 警告 Modal -->
<div class="modal modal-warning active">...</div>

<!-- 错误 Modal -->
<div class="modal modal-error active">...</div>
```

### 输出/代码 Modal

```html
<div class="modal-content output-modal modal-lg">
    <div class="modal-header">
        <h2>输出结果</h2>
        <button class="modal-close">&times;</button>
    </div>
    <div class="modal-body">
        <pre><code>代码内容</code></pre>
    </div>
</div>
```

## Footer 左右分栏

```html
<div class="modal-footer with-left">
    <div class="modal-footer-left">
        <button class="btn-ghost">帮助</button>
    </div>
    <div class="modal-footer-right">
        <button class="btn-secondary">取消</button>
        <button class="btn-primary">确认</button>
    </div>
</div>
```

## 尺寸规范

### 间距 (Padding)

- **modal-header**: `20px 24px`
- **modal-body**: `24px`
- **modal-footer**: `16px 24px`

### 字体大小

- **modal-header h2/h3**: `18px`, `font-weight: 600`
- **modal-body**: `14px`, `line-height: 1.6`
- **按钮**: `14px`, `font-weight: 500`
- **label**: `14px`, `font-weight: 500`
- **field-hint**: `13px`

### 按钮尺寸

- **标准按钮**: `padding: 10px 20px`
- **最小宽度**: `100px` (确保所有按钮宽度统一)
- **小型按钮**: `min-width: 80px`
- **圆角**: `6px`
- **按钮间距**: `12px gap`
- **移动端**: `min-width: 120px` (< 768px)
- **文字对齐**: `justify-content: center` (确保文字始终居中)

## 响应式设计

在移动设备上（< 768px）：

- Modal 宽度自动调整为 95%
- 所有尺寸变体统一为 95% 宽度
- Footer 按钮可能换行显示
- 间距适当缩小

## 迁移指南

### 从旧样式迁移

**旧代码**:
```html
<div class="modal active">
    <div class="modal-content">
        <h2>标题</h2>
        <input type="text">
        <div class="modal-actions">
            <button class="btn-secondary">取消</button>
            <button class="btn-primary">确认</button>
        </div>
    </div>
</div>
```

**新代码**:
```html
<div class="modal active">
    <div class="modal-overlay"></div>
    <div class="modal-content modal-md">
        <div class="modal-header">
            <h2>标题</h2>
            <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
            <div class="form-group">
                <label>字段标签</label>
                <input type="text">
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn-secondary">取消</button>
            <button class="btn-primary">确认</button>
        </div>
    </div>
</div>
```

### 关键变更

1. ✅ 添加 `modal-overlay` 遮罩层
2. ✅ 将标题移到 `modal-header` 中
3. ✅ 添加 `modal-close` 关闭按钮
4. ✅ 将内容包裹在 `modal-body` 中
5. ✅ 使用 `modal-footer` 替代 `modal-actions`
6. ✅ 使用 `form-group` 包裹表单字段

## 已完成的迁移

- ✅ `ExtensionsView.js` - Upload 和 URL 安装弹窗
- ✅ `extensions.css` - 移除重复的 modal 样式
- ✅ `components.css` - 注释掉旧的 modal 定义

## 待迁移的文件

以下文件仍使用旧的 modal 样式，建议逐步迁移：

- `ProvidersView.js`
- `TasksView.js`
- `ConfigView.js`
- `TimelineView.js`
- `KnowledgeSourcesView.js`
- `ContextView.js`
- `SnippetsView.js`
- `ProjectsView.js`
- `ContentRegistryView.js`
- `GovernanceFindingsView.js`

## 注意事项

1. **兼容性**: 旧的 `modal-actions` 类名仍然有效（作为 `modal-footer` 的别名）
2. **z-index**: Modal 使用 `z-index: 9999`，确保在最上层
3. **动画**: 包含淡入动画，可通过 `prefers-reduced-motion` 禁用
4. **焦点管理**: 按钮支持键盘导航和焦点样式
5. **关闭方式**: 支持三种关闭方式（关闭按钮、取消按钮、点击遮罩）

## 测试检查清单

- [ ] Modal 是否正确居中显示
- [ ] 遮罩层是否正确遮盖背景
- [ ] 关闭按钮是否正常工作
- [ ] 点击遮罩是否可以关闭
- [ ] 按钮样式是否统一
- [ ] 按钮顺序是否正确（次要在左，主要在右）
- [ ] 表单输入焦点样式是否正确
- [ ] 响应式布局是否正常（移动端）
- [ ] 滚动是否正常（内容超长时）

## 常见问题

### Q: 如何自定义 Modal 宽度？

A: 使用内联样式或添加自定义类：

```html
<div class="modal-content" style="max-width: 700px;">...</div>
```

### Q: 如何禁用点击遮罩关闭？

A: 不绑定遮罩点击事件即可：

```javascript
// 移除这段代码
modal.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal();
    }
});
```

### Q: 如何添加自定义按钮样式？

A: 扩展统一样式系统：

```css
.modal .btn-custom {
    background: #your-color;
    color: white;
}
```

## 参考资源

- **样式文件**: `agentos/webui/static/css/modal-unified.css`
- **示例实现**: `agentos/webui/static/js/views/ExtensionsView.js`
- **测试页面**: Extensions 页面的安装弹窗
