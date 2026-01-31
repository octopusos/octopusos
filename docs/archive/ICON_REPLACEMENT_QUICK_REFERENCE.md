# Icon Replacement Quick Reference Card

**快速参考**: Material Design Icons → Emoji/Unicode 替换指南

---

## 基础替换模式

### 静态 HTML 图标

```html
<!-- ❌ OLD -->
<i class="material-icons">warning</i>

<!-- ✅ NEW -->
<span class="icon-emoji" role="img" aria-label="Warning">⚠️</span>
```

### 带尺寸修饰符

```html
<!-- ❌ OLD -->
<span class="material-icons md-18">info</span>

<!-- ✅ NEW -->
<span class="icon-emoji sz-18" role="img" aria-label="Info">ℹ️</span>
```

### JavaScript 动态生成

```javascript
// ❌ OLD
const icon = '<span class="material-icons md-18">refresh</span>';

// ✅ NEW
const icon = '<span class="icon-emoji sz-18" role="img" aria-label="Refresh">🔄</span>';
```

---

## 尺寸类映射

| 旧类名 | 新类名 | 大小 |
|-------|-------|-----|
| `md-14` | `sz-14` | 14px |
| `md-16` | `sz-16` | 16px |
| `md-18` | `sz-18` | 18px |
| `md-20` | `sz-20` | 20px |
| `md-24` | `sz-24` | 24px |
| `md-36` | `sz-36` | 36px |
| `md-48` | `sz-48` | 48px |

---

## 常用图标映射 (Top 20)

| Material Icon | Emoji | Aria Label | 使用场景 |
|--------------|-------|-----------|---------|
| `warning` | ⚠️ | "Warning" | 警告提示 |
| `refresh` | 🔄 | "Refresh" | 刷新按钮 |
| `content_copy` | 📋 | "Copy" | 复制操作 |
| `check` | ✓ | "Check" | 勾选标记 |
| `check_circle` | ✅ | "Success" | 成功状态 |
| `cancel` | ❌ | "Cancel" | 取消/错误 |
| `info` | ℹ️ | "Info" | 信息提示 |
| `search` | 🔍 | "Search" | 搜索功能 |
| `add` | ➕ | "Add" | 添加按钮 |
| `save` | 💾 | "Save" | 保存操作 |
| `download` | ⬇️ | "Download" | 下载操作 |
| `edit` | ✏️ | "Edit" | 编辑操作 |
| `delete` | 🗑️ | "Delete" | 删除操作 |
| `error` | ⛔ | "Error" | 错误状态 |
| `close` | ✖️ | "Close" | 关闭按钮 |
| `folder_open` | 📂 | "Folder" | 文件夹 |
| `play_arrow` | ▶️ | "Play" | 播放/运行 |
| `done` | ✔️ | "Done" | 完成状态 |
| `schedule` | ⏰ | "Schedule" | 时间/计划 |
| `lock` | 🔒 | "Lock" | 锁定/安全 |

**完整映射表**: 见 `ICON_TO_EMOJI_MAPPING.md` (125 个图标)

---

## CSS 类更新

### 旧样式规则

```css
/* ❌ 需要替换 */
.material-icons {
    font-family: 'Material Icons';
    font-size: 24px;
}

.material-icons.md-18 { font-size: 18px; }
```

### 新样式规则

```css
/* ✅ 新规则 */
.icon-emoji {
    display: inline-block;
    font-style: normal;
    line-height: 1;
    vertical-align: middle;
    user-select: none;
}

.icon-emoji.sz-18 { font-size: 18px; }
```

---

## 可访问性必需属性

### 必须添加的属性

1. **role="img"** - 告诉屏幕阅读器这是一个图标
2. **aria-label="描述"** - 提供图标的文字描述

### 示例

```html
<!-- ✅ 正确：包含可访问性属性 -->
<span class="icon-emoji" role="img" aria-label="Warning">⚠️</span>

<!-- ❌ 错误：缺少可访问性属性 -->
<span class="icon-emoji">⚠️</span>
```

### 高级用法（带 title 工具提示）

```html
<span class="icon-emoji" role="img" aria-label="Warning" title="警告：需要注意">⚠️</span>
```

---

## 工具函数（推荐）

### JavaScript 图标生成函数

```javascript
/**
 * 生成 emoji 图标 HTML
 * @param {string} emoji - emoji 字符
 * @param {string} label - aria-label 文本
 * @param {string} size - 尺寸类名 (sz-14, sz-16, sz-18, sz-20, sz-24, sz-36, sz-48)
 * @returns {string} HTML 字符串
 */
function createIcon(emoji, label, size = '') {
    const sizeClass = size ? ` ${size}` : '';
    return `<span class="icon-emoji${sizeClass}" role="img" aria-label="${label}">${emoji}</span>`;
}

// 使用示例
const warningIcon = createIcon('⚠️', 'Warning', 'sz-18');
const refreshIcon = createIcon('🔄', 'Refresh', 'sz-16');
```

### 图标常量（推荐定义）

```javascript
// icons.js - 图标常量定义
const ICONS = {
    WARNING: { emoji: '⚠️', label: 'Warning' },
    REFRESH: { emoji: '🔄', label: 'Refresh' },
    COPY: { emoji: '📋', label: 'Copy' },
    CHECK: { emoji: '✓', label: 'Check' },
    SUCCESS: { emoji: '✅', label: 'Success' },
    CANCEL: { emoji: '❌', label: 'Cancel' },
    INFO: { emoji: 'ℹ️', label: 'Info' },
    SEARCH: { emoji: '🔍', label: 'Search' },
    ADD: { emoji: '➕', label: 'Add' },
    SAVE: { emoji: '💾', label: 'Save' }
};

// 使用示例
function createIconFromConstant(iconKey, size = '') {
    const icon = ICONS[iconKey];
    return createIcon(icon.emoji, icon.label, size);
}

const warningIcon = createIconFromConstant('WARNING', 'sz-18');
```

---

## 常见场景示例

### 按钮中的图标

```html
<!-- ❌ OLD -->
<button class="btn">
    <span class="material-icons md-18">add</span> Create
</button>

<!-- ✅ NEW -->
<button class="btn">
    <span class="icon-emoji sz-18" role="img" aria-label="Add">➕</span> Create
</button>
```

### 状态指示器

```html
<!-- ❌ OLD -->
<div class="status">
    <span class="material-icons md-16">check_circle</span>
    <span>Success</span>
</div>

<!-- ✅ NEW -->
<div class="status">
    <span class="icon-emoji sz-16" role="img" aria-label="Success">✅</span>
    <span>Success</span>
</div>
```

### 列表项图标

```html
<!-- ❌ OLD -->
<li>
    <span class="material-icons md-18">folder_open</span>
    <span>Documents</span>
</li>

<!-- ✅ NEW -->
<li>
    <span class="icon-emoji sz-18" role="img" aria-label="Folder">📂</span>
    <span>Documents</span>
</li>
```

### 提示横幅

```html
<!-- ❌ OLD -->
<div class="alert alert-warning">
    <span class="material-icons md-24">warning</span>
    <span>This action cannot be undone</span>
</div>

<!-- ✅ NEW -->
<div class="alert alert-warning">
    <span class="icon-emoji sz-24" role="img" aria-label="Warning">⚠️</span>
    <span>This action cannot be undone</span>
</div>
```

---

## JavaScript 模板字面量

### 旧代码模式

```javascript
// ❌ OLD
const html = `
    <button class="btn-action">
        <span class="material-icons md-18">refresh</span>
        Refresh
    </button>
`;
```

### 新代码模式

```javascript
// ✅ NEW
const html = `
    <button class="btn-action">
        <span class="icon-emoji sz-18" role="img" aria-label="Refresh">🔄</span>
        Refresh
    </button>
`;
```

### 动态图标

```javascript
// ❌ OLD
function createButton(iconName, label) {
    return `<button><span class="material-icons">${iconName}</span> ${label}</button>`;
}

// ✅ NEW
function createButton(icon, label) {
    return `<button><span class="icon-emoji" role="img" aria-label="${label}">${icon.emoji}</span> ${label}</button>`;
}

// 使用
const refreshBtn = createButton(ICONS.REFRESH, 'Refresh');
```

---

## 特殊情况处理

### 需要改变颜色的图标

**问题**: emoji 有固定颜色，无法用 CSS 修改

**解决方案**: 使用 Unicode 符号而不是彩色 emoji

```html
<!-- ✅ 可以改变颜色 -->
<span class="icon-emoji" style="color: red;" role="img" aria-label="Check">✓</span>

<!-- ❌ 无法改变颜色 -->
<span class="icon-emoji" style="color: red;" role="img" aria-label="Check">✅</span>
```

**推荐映射** (可变色):
- 勾选: `✓` (U+2713) 而不是 `✅` (U+2705)
- 叉号: `✗` (U+2717) 而不是 `❌` (U+274C)
- 箭头: `→` (U+2192) 而不是 `➡️` (U+27A1)

### 需要旋转动画的图标

**问题**: emoji 难以进行 CSS 动画

**解决方案**: 对容器 span 应用动画

```css
/* ✅ 正确：动画应用于容器 */
@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.icon-emoji.spinning {
    display: inline-block; /* 必需 */
    animation: spin 1s linear infinite;
}
```

```html
<span class="icon-emoji spinning sz-18" role="img" aria-label="Loading">🔄</span>
```

### Linux 系统备用方案

**问题**: Linux 可能缺少彩色 emoji 字体

**解决方案**: 提供 Unicode 备用方案

```html
<span class="icon-emoji" role="img" aria-label="Warning">
    <span class="emoji-primary" aria-hidden="true">⚠️</span>
    <span class="emoji-fallback" aria-hidden="true">!</span>
</span>
```

```css
.emoji-fallback {
    display: none;
}

/* Linux 或不支持 emoji 的系统 */
@supports not (font-variation-settings: normal) {
    .emoji-primary { display: none; }
    .emoji-fallback { display: inline; }
}
```

---

## 检查清单

### 替换前检查
- [ ] 识别 Material Icon 名称
- [ ] 在映射表中找到对应的 emoji
- [ ] 确定图标尺寸 (md-XX → sz-XX)
- [ ] 确定语义标签 (aria-label)

### 替换后检查
- [ ] 图标显示正确
- [ ] 尺寸与原来一致
- [ ] 包含 role="img"
- [ ] 包含 aria-label
- [ ] 在不同浏览器中测试
- [ ] 使用屏幕阅读器测试

---

## 常见错误

### ❌ 错误 1: 缺少可访问性属性

```html
<!-- ❌ 错误 -->
<span class="icon-emoji">⚠️</span>

<!-- ✅ 正确 -->
<span class="icon-emoji" role="img" aria-label="Warning">⚠️</span>
```

### ❌ 错误 2: 使用了错误的尺寸类

```html
<!-- ❌ 错误: 仍使用旧类名 -->
<span class="icon-emoji md-18" role="img" aria-label="Info">ℹ️</span>

<!-- ✅ 正确: 使用新类名 -->
<span class="icon-emoji sz-18" role="img" aria-label="Info">ℹ️</span>
```

### ❌ 错误 3: 使用了 <i> 标签

```html
<!-- ❌ 错误: <i> 标签不语义化 -->
<i class="icon-emoji" role="img" aria-label="Warning">⚠️</i>

<!-- ✅ 正确: 使用 <span> -->
<span class="icon-emoji" role="img" aria-label="Warning">⚠️</span>
```

### ❌ 错误 4: emoji 和 Unicode 混用不当

```html
<!-- ❌ 错误: 使用 emoji 但需要改变颜色 -->
<span class="icon-emoji" style="color: red;">✅</span>

<!-- ✅ 正确: 使用 Unicode 符号 -->
<span class="icon-emoji" style="color: red;">✓</span>
```

---

## 测试命令

### 查找需要替换的代码

```bash
# 查找 material-icons 类使用
grep -rn "material-icons" agentos/webui/static/js/ --include="*.js"

# 查找特定图标使用
grep -rn ">warning</span>" agentos/webui/static/js/ --include="*.js"

# 统计待替换数量
grep -r "material-icons" agentos/webui/static/js/ --include="*.js" | wc -l
```

### 验证替换后的代码

```bash
# 确认没有遗漏的 material-icons 类
grep -rn "material-icons" agentos/webui/static/js/ --include="*.js" | grep -v "icon-emoji"

# 检查是否包含可访问性属性
grep -rn "icon-emoji" agentos/webui/static/js/ | grep -v 'aria-label'
```

---

## 资源链接

### 文档
- [HTML_REPLACEMENT_LOG.md](./HTML_REPLACEMENT_LOG.md) - 详细替换日志
- [ICON_TO_EMOJI_MAPPING.md](./ICON_TO_EMOJI_MAPPING.md) - 完整图标映射表 (125 个)
- [MATERIAL_ICONS_INVENTORY.md](./MATERIAL_ICONS_INVENTORY.md) - 使用情况清单

### 外部工具
- [Emojipedia](https://emojipedia.org/) - emoji 查找和预览
- [Unicode Table](https://unicode-table.com/) - Unicode 字符参考
- [Can I Use: Emoji](https://caniuse.com/emoji) - 浏览器兼容性
- [WebAIM: Alternative Text](https://webaim.org/techniques/alttext/) - 可访问性指南

---

## 获取帮助

### 如何查找图标映射？
1. 打开 `ICON_TO_EMOJI_MAPPING.md`
2. 按 Ctrl/Cmd+F 搜索 Material Icon 名称
3. 找到对应的 emoji 和 aria-label

### 如何测试可访问性？
1. 安装屏幕阅读器 (NVDA/JAWS/VoiceOver)
2. 导航到包含图标的页面
3. 验证图标的 aria-label 被正确朗读

### 如何处理不确定的情况？
1. 参考 `HTML_REPLACEMENT_LOG.md` 中的示例
2. 查看同类型图标的替换方式
3. 在测试环境中验证效果
4. 咨询团队成员

---

## 更新历史

| 日期 | 版本 | 变更 |
|-----|------|-----|
| 2026-01-30 | 1.0 | 初始版本 |

---

**打印版本**: 适合打印后放在工作台作为快速参考
**最后更新**: 2026-01-30
**维护者**: AgentOS Team
