# HTML Preview 功能实现

## 📝 功能概述

为 Chat 页面的 assistant 消息添加 HTML 代码块预览功能：
1. 自动识别 Markdown 代码块（```language）
2. 为 HTML 代码块添加 Preview（▶）按钮
3. 点击后用 `<dialog>` + `iframe srcdoc` 预览 HTML 效果
4. 使用 `sandbox` 属性安全隔离
5. 支持 Copy 代码功能

**实现日期**: 2026-01-28

---

## 🎯 设计目标

- ✅ **纯前端实现** - 不修改后端代码
- ✅ **安全隔离** - iframe sandbox 防止 XSS
- ✅ **流式兼容** - 支持动态流式消息渲染
- ✅ **美观设计** - 现代化 UI，与现有风格一致
- ✅ **高性能** - 只在消息完成后解析，避免频繁计算

---

## 🏗️ 架构设计

### 数据流

```
WebSocket Stream → message.delta (累积文本)
                 ↓
              message.end (触发解析)
                 ↓
         parseFencedCodeBlocks() 解析代码块
                 ↓
         isHtmlBlock() 判断是否为 HTML
                 ↓
         renderCodeBlock() 渲染 UI + 按钮
                 ↓
         用户点击 Preview → openHtmlPreview()
                 ↓
         iframe srcdoc 渲染 HTML
```

### 组件架构

```
CodeBlockUtils (utils/codeblocks.js)
├── parseFencedCodeBlocks()  - 解析 Markdown 代码块
├── isHtmlBlock()             - 判断是否为 HTML
├── escapeHtml()              - HTML 转义
├── renderCodeBlock()         - 渲染代码块 UI
└── renderAssistantMessage()  - 渲染完整消息

Chat Handler (main.js)
├── handleWebSocketMessage()  - WebSocket 消息处理
│   └── message.end          - 触发代码块解析
├── setupCodeBlockActions()   - 绑定事件（Preview/Copy）
├── ensurePreviewDialog()     - 初始化 Dialog
└── openHtmlPreview()         - 打开预览

UI Components
├── Dialog (index.html)       - 预览对话框
├── CodeBlock (generated)     - 代码块卡片
└── Buttons (generated)       - Preview/Copy 按钮
```

---

## 🔧 技术实现

### 1. 代码块解析（`codeblocks.js`）

**核心算法**：正则表达式匹配 Markdown 代码块

```javascript
// 匹配格式: ```language\ncode\n```
const re = /```([\w-]+)?\n([\s\S]*?)```/g;
```

**解析结果**：
```javascript
[
  {type: 'text', content: '这是普通文本'},
  {type: 'code', lang: 'html', code: '<div>...</div>'},
  {type: 'text', content: '更多文本'}
]
```

**HTML 识别规则**：
1. 显式语言标识：`lang === 'html' || lang === 'htm'`
2. 启发式识别（无语言标识时）：
   - 以 `<!doctype html>` 开头
   - 以 `<html` 开头
   - 包含 `<head>` 和 `<body>`
   - 包含 `<div>...</div>` 结构

### 2. 消息渲染流程

**流式阶段**（`message.delta`）：
- 直接追加文本到 `contentDiv.textContent`
- 不解析代码块（性能优化）
- 用户看到原始 Markdown

**完成阶段**（`message.end`）：
- 获取完整文本 `contentDiv.textContent`
- 调用 `renderAssistantMessage(fullText)`
- 替换 `contentDiv.innerHTML` 为解析后的 HTML
- 代码块渲染为卡片 + 按钮

### 3. 代码块 UI 结构

```html
<div class="codeblock">
    <!-- 头部：语言 + 按钮 -->
    <div class="codeblock__hdr">
        <span class="codeblock__lang">html</span>
        <div class="codeblock__actions">
            <button class="btn-preview js-preview">
                <svg>▶</svg>
                <span>Preview</span>
            </button>
            <button class="btn-copy js-copy">
                <svg>📋</svg>
                <span>Copy</span>
            </button>
        </div>
    </div>

    <!-- 代码内容 -->
    <pre><code>escaped html code</code></pre>
</div>
```

### 4. 事件处理（事件委托）

**优势**：
- 只绑定一次事件监听器（在 `messages` 容器上）
- 支持动态添加的代码块
- 性能更好

**实现**：
```javascript
messagesDiv.addEventListener('click', (e) => {
    const previewBtn = e.target.closest('.js-preview');
    const copyBtn = e.target.closest('.js-copy');

    if (previewBtn) {
        // 找到对应的代码块
        const codeEl = previewBtn.closest('.codeblock')?.querySelector('pre code');
        openHtmlPreview(codeEl.textContent);
    }

    if (copyBtn) {
        // 复制代码
        navigator.clipboard.writeText(codeEl.textContent);
    }
});
```

### 5. Preview Dialog

**HTML 结构**：
```html
<dialog id="htmlPreviewDlg" class="preview-dlg">
    <div class="preview-dlg__hdr">
        <div class="preview-dlg__title">HTML Preview</div>
        <button id="htmlPreviewClose">✕</button>
    </div>
    <div class="preview-dlg__body">
        <iframe
            id="htmlPreviewFrame"
            sandbox="allow-scripts allow-forms allow-modals"
            referrerpolicy="no-referrer"
        ></iframe>
    </div>
</dialog>
```

**Dialog API 使用**：
```javascript
dlg.showModal();  // 打开对话框（模态）
dlg.close();      // 关闭对话框
```

**关闭方式**：
1. 点击关闭按钮
2. 点击对话框外部
3. 按 Escape 键

### 6. iframe Sandbox 安全

**Sandbox 属性**：
```html
sandbox="allow-scripts allow-forms allow-modals"
```

**允许的操作**：
- `allow-scripts` - JavaScript 执行
- `allow-forms` - 表单提交
- `allow-modals` - alert/confirm/prompt

**禁止的操作**（未添加）：
- `allow-same-origin` - **不添加！** 防止访问父页面
- `allow-top-navigation` - 防止导航父页面
- `allow-popups` - 防止打开新窗口

**安全验证**：
```javascript
// 在 iframe 内执行（应该失败）
parent.document;           // ❌ 被阻止
window.top.location.href;  // ❌ 被阻止
```

### 7. HTML 包装逻辑

**完整文档检测**：
```javascript
htmlCode.includes('<html')
```

**自动包装**（片段）：
```html
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
body {
    font-family: system-ui, -apple-system;
    padding: 20px;
    line-height: 1.6;
}
</style>
</head>
<body>
${htmlCode}  <!-- 用户的 HTML 片段 -->
</body>
</html>
```

**优点**：
- 支持不完整的 HTML 片段
- 提供基础样式，避免白屏
- 自动响应式支持

---

## 🎨 UI 设计

### 设计原则

1. **一致性** - 与现有 WebUI 风格保持一致
2. **清晰性** - 按钮图标 + 文字，明确功能
3. **反馈性** - Hover/Active 状态，操作有反馈
4. **层次性** - 代码块卡片化，头部/内容分离

### 颜色方案

**代码块**：
- 头部背景：渐变灰 `linear-gradient(rgba(0,0,0,0.02), rgba(0,0,0,0.04))`
- 代码背景：GitHub Dark `#0d1117`
- 代码文字：浅灰 `#e6edf3`

**Preview 按钮**：
- 背景：浅蓝 `#eff6ff`
- 边框：蓝色 `#93c5fd`
- 文字：深蓝 `#2563eb`
- Hover：更深蓝 `#dbeafe`

**Copy 按钮**：
- 背景：白色
- 边框：浅灰 `rgba(0,0,0,0.12)`
- 文字：灰色 `#4b5563`
- 成功：绿色 `#059669`

**Dialog**：
- 背景：白色 + 阴影
- Backdrop：半透明黑 + 模糊
- 头部：渐变灰
- 关闭按钮 Hover：红色 `#dc2626`

### 动画效果

- 按钮 Hover：`translateY(-1px)` + 颜色变化
- 按钮 Active：`translateY(0)`
- 关闭按钮 Hover：背景淡红色
- Copy 成功：绿色渐变 + 勾号，2 秒后恢复
- Transition 时间：`0.15s ease`

### 响应式设计

```css
.preview-dlg {
    width: min(1200px, 94vw);  /* 桌面 1200px，移动端 94% 宽度 */
    height: min(820px, 90vh);   /* 桌面 820px，移动端 90% 高度 */
}
```

---

## 📂 文件结构

```
agentos/webui/
├── static/
│   ├── js/
│   │   ├── utils/
│   │   │   └── codeblocks.js          [新增] 代码块解析工具
│   │   └── main.js                     [修改] 消息渲染 + 事件处理
│   └── css/
│       └── components.css              [修改] 代码块 + Dialog 样式
└── templates/
    └── index.html                      [修改] Dialog HTML + 脚本引用
```

**修改统计**：
- 新增：1 个文件（`codeblocks.js`）
- 修改：3 个文件（`main.js`, `index.html`, `components.css`）
- 总行数：~500 行

---

## 🧪 测试覆盖

### 单元测试（函数级）

1. **parseFencedCodeBlocks()**
   - 单个代码块
   - 多个代码块
   - 无代码块
   - 有/无语言标识
   - 嵌套代码块

2. **isHtmlBlock()**
   - 显式 HTML 标识
   - 启发式识别
   - 非 HTML 代码块

3. **escapeHtml()**
   - 特殊字符转义
   - 空字符串
   - null/undefined

### 集成测试（UI 级）

1. **消息渲染**
   - 纯文本消息
   - 单个代码块
   - 多个混合代码块
   - HTML + 非 HTML 代码块

2. **Preview 功能**
   - 完整 HTML 文档
   - HTML 片段
   - 带 JavaScript 的 HTML
   - 带 CSS 的 HTML

3. **Copy 功能**
   - 复制成功
   - 复制失败
   - 状态恢复

4. **Dialog 交互**
   - 打开/关闭
   - 多次打开
   - 键盘操作
   - 鼠标操作

### 安全测试

1. **XSS 防护**
   - 恶意脚本注入
   - 父页面访问尝试
   - 跨域资源加载

2. **输入验证**
   - 超长代码
   - 特殊字符
   - 空输入

---

## 🔒 安全考虑

### Sandbox 安全策略

**策略矩阵**：

| 权限 | 状态 | 原因 |
|------|------|------|
| `allow-scripts` | ✅ 启用 | 允许 JavaScript 执行（预览功能必需） |
| `allow-forms` | ✅ 启用 | 允许表单提交（常见 HTML 功能） |
| `allow-modals` | ✅ 启用 | 允许 alert/confirm（调试需要） |
| `allow-same-origin` | ❌ **禁用** | **防止访问父页面（XSS 防护）** |
| `allow-top-navigation` | ❌ 禁用 | 防止导航劫持 |
| `allow-popups` | ❌ 禁用 | 防止弹窗滥用 |

### XSS 攻击向量分析

**攻击场景 1**：恶意代码尝试访问父页面

```javascript
// 攻击代码（在 iframe 内）
parent.document.cookie;
```

**防护**：`allow-same-origin` 未启用，`parent` 对象访问被阻止

**攻击场景 2**：尝试导航父页面

```javascript
window.top.location.href = 'http://evil.com';
```

**防护**：Sandbox 阻止 top navigation

**攻击场景 3**：HTML 注入

```html
<img src=x onerror="alert(document.cookie)">
```

**防护**：代码在 iframe 内执行，无法访问主页面 cookie

### Content Security Policy（未来）

可以考虑添加 CSP 头部：

```http
Content-Security-Policy:
    default-src 'self';
    script-src 'self' 'unsafe-inline';
    style-src 'self' 'unsafe-inline';
```

---

## 📊 性能优化

### 1. 延迟解析

**策略**：只在 `message.end` 时解析代码块

**优势**：
- 避免流式过程中频繁正则匹配
- 减少 DOM 操作
- 提升响应速度

**对比**：
- ❌ 每次 `message.delta` 都解析：~50ms/次，累计 1-2 秒
- ✅ 只在 `message.end` 解析一次：~50ms 总计

### 2. 事件委托

**策略**：在父容器上绑定事件，而不是每个按钮

**优势**：
- 减少事件监听器数量
- 支持动态添加的元素
- 内存占用更小

**对比**：
- ❌ 每个按钮绑定：10 个代码块 = 20 个监听器
- ✅ 事件委托：只需 1 个监听器

### 3. Dialog 复用

**策略**：全局唯一 Dialog，多次打开复用同一个

**优势**：
- 减少 DOM 节点
- 避免重复初始化
- 更快的打开速度

### 4. 懒加载

**当前**：所有功能在页面加载时就绪

**未来优化**（可选）：
- 代码高亮库按需加载
- 大代码块虚拟滚动

---

## 💡 未来增强

### Phase 2: 增强功能

1. **Open in New Tab** 按钮
   ```javascript
   const blob = new Blob([htmlCode], {type: 'text/html'});
   const url = URL.createObjectURL(blob);
   window.open(url, '_blank');
   ```

2. **Console 输出显示**
   - 在 Dialog 底部添加 Console 面板
   - 覆写 iframe 内的 `console` 方法
   - 通过 `postMessage` 发送到父窗口
   - 显示 log/error/warn 输出

3. **代码高亮**
   - 集成 Prism.js 或 Highlight.js
   - 语法高亮显示
   - 行号显示

4. **代码格式化**
   - 集成 Prettier
   - 一键格式化按钮
   - 自动缩进

5. **全屏模式**
   - 全屏预览按钮
   - ESC 退出全屏
   - 响应式布局

### Phase 3: 高级功能

1. **实时编辑**
   - 代码编辑器（Monaco Editor）
   - 实时预览更新
   - 保存修改

2. **导出功能**
   - 下载为 .html 文件
   - 复制 CodePen/JSFiddle 链接
   - 生成分享链接

3. **多文件支持**
   - HTML/CSS/JS 分离显示
   - Tab 切换
   - 组合预览

4. **历史记录**
   - 保存预览过的代码
   - 快速重新打开
   - 收藏功能

---

## 📝 使用说明

### 用户操作流程

1. **发送消息**
   ```
   用户：请生成一个带按钮的 HTML 页面
   ```

2. **查看回复**
   - Assistant 回复包含 HTML 代码块
   - 代码块显示语言标识 "HTML"
   - 右上角有 "Preview" 和 "Copy" 按钮

3. **预览 HTML**
   - 点击 "Preview" 按钮（播放图标）
   - 对话框打开，显示渲染后的 HTML
   - 可以与页面交互（点击按钮等）

4. **关闭预览**
   - 点击右上角 × 按钮
   - 点击对话框外部区域
   - 按 Escape 键

5. **复制代码**
   - 点击 "Copy" 按钮
   - 按钮变为绿色 "Copied!"
   - 代码已复制到剪贴板

### 开发者调试

**浏览器 DevTools**：
```javascript
// 检查 CodeBlockUtils 是否加载
console.log(window.CodeBlockUtils);

// 手动测试解析
const text = "```html\n<div>test</div>\n```";
const parts = window.CodeBlockUtils.parseFencedCodeBlocks(text);
console.log(parts);

// 检查 Dialog 元素
document.getElementById('htmlPreviewDlg');
```

**日志输出**：
- `message.end` 触发时的日志
- 代码块解析结果
- Preview 打开/关闭事件

---

## 🐛 已知问题

### 1. 代码高亮

**问题**：当前没有语法高亮

**影响**：代码可读性一般

**解决方案**：Phase 2 集成 Prism.js

### 2. 大文件性能

**问题**：超长代码块（>10000 行）渲染慢

**影响**：极少见场景

**解决方案**：添加虚拟滚动

### 3. 移动端体验

**问题**：小屏幕上对话框可能过大

**影响**：部分移动设备

**解决方案**：已添加响应式设计，但可进一步优化

---

## ✅ 部署清单

- [x] 创建 `codeblocks.js` 工具文件
- [x] 修改 `main.js` 消息渲染逻辑
- [x] 修改 `index.html` 添加 Dialog 和脚本
- [x] 修改 `components.css` 添加样式
- [x] 更新版本号（v20 → v21）
- [x] 重启服务器
- [ ] 用户测试验证
- [ ] 收集反馈

---

## 📚 相关文档

- [实施计划](../../PLAN_HTML_PREVIEW.md)
- [测试指南](../../TEST_HTML_PREVIEW.md)
- [MDN: HTML5 Dialog Element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/dialog)
- [MDN: iframe sandbox](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#attr-sandbox)
- [OWASP: XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)

---

**功能完成**: 2026-01-28
**测试状态**: 准备测试
**版本**: main.js v21
**服务器**: ✅ 运行中 http://127.0.0.1:8080
