# HTML Preview 功能实施计划

## 📋 需求概述

在 Chat 页面的 assistant 消息中：
1. 解析 Markdown 代码块（```language\ncode\n```）
2. 识别 HTML 代码块
3. 为 HTML 代码块添加 Preview（▶）按钮
4. 点击后用 `<dialog>` + `iframe srcdoc` 预览 HTML 效果
5. 使用 `sandbox` 属性隔离安全风险

## 🎯 实施目标

- ✅ 不修改后端代码
- ✅ 纯前端实现
- ✅ 支持动态流式消息渲染
- ✅ 安全的 iframe 沙箱隔离
- ✅ 美观的 UI 设计

## 📂 文件结构

```
agentos/webui/
├── static/
│   ├── js/
│   │   ├── utils/
│   │   │   └── codeblocks.js          # 新增：代码块解析工具
│   │   └── main.js                     # 修改：消息渲染逻辑
│   └── css/
│       └── components.css              # 修改：添加预览样式
└── templates/
    └── index.html                      # 修改：添加 Dialog 结构
```

## 🔧 实施步骤

### Step 1: 创建代码块解析工具（`codeblocks.js`）

**文件**: `agentos/webui/static/js/utils/codeblocks.js`

**功能**：
- `parseFencedCodeBlocks(text)` - 解析 Markdown 代码块
- `isHtmlBlock(lang, code)` - 判断是否为 HTML 代码
- `escapeHtml(text)` - HTML 转义
- `renderCodeBlock({lang, code})` - 渲染代码块 HTML

**核心逻辑**：
```javascript
// 解析 Markdown 代码块，返回 [{type:'text', content}, {type:'code', lang, code}]
export function parseFencedCodeBlocks(input) {
  const re = /```([\w-]+)?\n([\s\S]*?)```/g;
  const out = [];
  let lastIndex = 0;
  let m;

  while ((m = re.exec(input)) !== null) {
    if (m.index > lastIndex) {
      out.push({ type: "text", content: input.slice(lastIndex, m.index) });
    }
    const lang = (m[1] || "").trim().toLowerCase();
    const code = (m[2] || "").replace(/\s+$/, "");
    out.push({ type: "code", lang, code });
    lastIndex = re.lastIndex;
  }

  if (lastIndex < input.length) {
    out.push({ type: "text", content: input.slice(lastIndex) });
  }
  return out;
}

// 判断是否为 HTML 代码块
export function isHtmlBlock(lang, code) {
  if (lang === "html" || lang === "htm") return true;

  // 启发式识别
  const s = (code || "").trim().toLowerCase();
  return (
    s.startsWith("<!doctype html") ||
    s.startsWith("<html") ||
    (s.includes("<head") && s.includes("<body")) ||
    (s.includes("<div") && s.includes("</div>"))
  );
}
```

### Step 2: 修改消息渲染逻辑（`main.js`）

**修改点**：

1. **导入工具函数**：
```javascript
// 在文件顶部添加（注意：当前没有用 ES6 模块，需要直接引入）
```

2. **修改 `createMessageElement` 函数**：
```javascript
// 添加一个新参数 renderCodeBlocks
function createMessageElement(role, content, renderCodeBlocks = false) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    let contentHtml = escapeHtml(content);

    // 如果需要渲染代码块（assistant 消息完成后）
    if (renderCodeBlocks && role === 'assistant') {
        contentHtml = renderAssistantMessage(content);
    }

    div.innerHTML = `
        <div class="role">${role}</div>
        <div class="content">${contentHtml}</div>
        <div class="timestamp">${new Date().toLocaleTimeString()}</div>
    `;

    return div;
}
```

3. **修改 `handleWebSocketMessage` 函数**：
```javascript
// 在 message.end 时，重新渲染消息内容
else if (message.type === 'message.end') {
    console.log('Finished receiving message:', message.message_id, message.metadata);

    // 找到对应的消息元素
    let lastMsg = messagesDiv.querySelector(`[data-message-id="${message.message_id}"]`);
    if (lastMsg && lastMsg.classList.contains('assistant')) {
        const contentDiv = lastMsg.querySelector('.content');
        const fullText = contentDiv.textContent;

        // 重新渲染，解析代码块
        contentDiv.innerHTML = renderAssistantMessage(fullText);
    }
}
```

4. **新增 `renderAssistantMessage` 函数**：
```javascript
// 渲染 assistant 消息，解析代码块
function renderAssistantMessage(text) {
    const parts = parseFencedCodeBlocks(text);

    return parts.map(p => {
        if (p.type === 'text') {
            // 保持原有的文本渲染方式
            return `<div class="msg-text">${escapeHtml(p.content).replace(/\n/g, '<br>')}</div>`;
        }
        return renderCodeBlock(p);
    }).join('');
}

// 渲染代码块
function renderCodeBlock({lang, code}) {
    const canPreview = isHtmlBlock(lang, code);

    return `
    <div class="codeblock">
        <div class="codeblock__hdr">
            <span class="codeblock__lang">${lang || "code"}</span>
            <div class="codeblock__actions">
                ${canPreview ? `<button class="btn-preview js-preview" title="Preview HTML">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Preview
                </button>` : ''}
                <button class="btn-copy js-copy" title="Copy code">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                </button>
            </div>
        </div>
        <pre><code>${escapeHtml(code)}</code></pre>
    </div>`;
}
```

5. **新增 Preview Dialog 相关函数**：
```javascript
// 初始化 Preview Dialog
function ensurePreviewDialog() {
    const dlg = document.getElementById('htmlPreviewDlg');
    const btnClose = document.getElementById('htmlPreviewClose');
    const frame = document.getElementById('htmlPreviewFrame');

    if (!dlg || !btnClose || !frame) return null;

    // 绑定关闭按钮
    btnClose.addEventListener('click', () => dlg.close());

    // 点击空白处关闭
    dlg.addEventListener('click', (e) => {
        const rect = dlg.getBoundingClientRect();
        const inDialog =
            rect.top <= e.clientY &&
            e.clientY <= rect.bottom &&
            rect.left <= e.clientX &&
            e.clientX <= rect.right;
        if (!inDialog) dlg.close();
    });

    return { dlg, frame };
}

// 打开 HTML 预览
function openHtmlPreview(htmlCode) {
    const refs = ensurePreviewDialog();
    if (!refs) return;

    // 如果没有完整的 HTML 结构，添加基础框架
    const wrapped = htmlCode.includes('<html')
        ? htmlCode
        : `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    padding: 16px;
    line-height: 1.6;
}
</style>
</head>
<body>
${htmlCode}
</body>
</html>`;

    refs.frame.srcdoc = wrapped;
    refs.dlg.showModal();
}
```

6. **修改 `renderChatView` 函数，绑定事件**：
```javascript
function renderChatView(container) {
    // ... 现有代码 ...

    // 绑定 Chat 消息区域的事件（代码块操作）
    bindChatActions();
}

// 绑定 Chat 操作事件（Preview、Copy）
function bindChatActions() {
    const messagesDiv = document.getElementById('messages');
    if (!messagesDiv) return;

    messagesDiv.addEventListener('click', (e) => {
        const previewBtn = e.target.closest('.js-preview');
        const copyBtn = e.target.closest('.js-copy');

        if (previewBtn) {
            const codeEl = previewBtn.closest('.codeblock')?.querySelector('pre code');
            if (!codeEl) return;
            openHtmlPreview(codeEl.textContent);
            return;
        }

        if (copyBtn) {
            const codeEl = copyBtn.closest('.codeblock')?.querySelector('pre code');
            if (!codeEl) return;
            navigator.clipboard?.writeText(codeEl.textContent);

            // 显示复制成功提示
            copyBtn.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                Copied!
            `;
            setTimeout(() => {
                copyBtn.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                `;
            }, 2000);
            return;
        }
    });
}
```

### Step 3: 添加 Dialog HTML 结构（`index.html`）

**位置**: 在 `</body>` 之前添加

```html
<!-- HTML Preview Dialog -->
<dialog id="htmlPreviewDlg" class="preview-dlg">
    <div class="preview-dlg__hdr">
        <div class="preview-dlg__title">
            <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            HTML Preview
        </div>
        <button class="btn-dialog-close" id="htmlPreviewClose" title="Close">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>
    </div>

    <div class="preview-dlg__body">
        <iframe
            id="htmlPreviewFrame"
            class="preview-dlg__frame"
            sandbox="allow-scripts allow-forms allow-modals"
            referrerpolicy="no-referrer"
        ></iframe>
    </div>
</dialog>
```

### Step 4: 添加 CSS 样式（`components.css`）

```css
/* ========================================
   Code Block Styles
   ======================================== */

.codeblock {
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 8px;
    overflow: hidden;
    margin: 12px 0;
    background: #fff;
}

.codeblock__hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.03);
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.codeblock__lang {
    font-size: 12px;
    font-weight: 600;
    color: rgba(0, 0, 0, 0.6);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.codeblock__actions {
    display: flex;
    gap: 8px;
}

.codeblock pre {
    margin: 0;
    padding: 16px;
    overflow-x: auto;
    background: #0d1117;
    color: #e6edf3;
    font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;
}

.codeblock pre code {
    display: block;
}

/* Code Block Buttons */
.btn-preview,
.btn-copy {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 6px;
    background: white;
    color: #374151;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-preview:hover,
.btn-copy:hover {
    background: #f9fafb;
    border-color: rgba(0, 0, 0, 0.2);
}

.btn-preview {
    color: #2563eb;
    border-color: #2563eb;
}

.btn-preview:hover {
    background: #eff6ff;
    border-color: #1d4ed8;
}

.btn-preview svg,
.btn-copy svg {
    width: 16px;
    height: 16px;
}

/* ========================================
   Preview Dialog Styles
   ======================================== */

.preview-dlg {
    width: min(1200px, 94vw);
    height: min(800px, 90vh);
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 12px;
    padding: 0;
    overflow: hidden;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.preview-dlg::backdrop {
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(4px);
}

.preview-dlg__hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: #f9fafb;
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.preview-dlg__title {
    display: flex;
    align-items: center;
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
}

.btn-dialog-close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: #6b7280;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-dialog-close:hover {
    background: rgba(0, 0, 0, 0.05);
    color: #1f2937;
}

.preview-dlg__body {
    height: calc(100% - 56px);
    background: white;
}

.preview-dlg__frame {
    width: 100%;
    height: 100%;
    border: 0;
    background: white;
}

/* ========================================
   Message Text Styles
   ======================================== */

.msg-text {
    white-space: pre-wrap;
    word-wrap: break-word;
}
```

### Step 5: 更新 HTML 引用（`index.html`）

在现有的 `<script>` 标签之前添加：

```html
<!-- Code Block Utils -->
<script src="/static/js/utils/codeblocks.js?v=1"></script>
```

注意：版本号需要递增以强制刷新缓存。

## 🎨 产品化增强（可选）

### 增强 1: "Open in new tab" 按钮

在 Preview Dialog 头部添加：

```javascript
function openHtmlInNewTab(htmlCode) {
    const blob = new Blob([htmlCode], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
}
```

### 增强 2: Console 输出显示

在 iframe 内覆写 console 方法，通过 postMessage 发送到父窗口：

```javascript
// 在 wrapped HTML 中注入
const consoleScript = `
<script>
(function() {
    const original = {
        log: console.log,
        error: console.error,
        warn: console.warn
    };

    ['log', 'error', 'warn'].forEach(method => {
        console[method] = function(...args) {
            original[method].apply(console, args);
            window.parent.postMessage({
                type: 'console',
                method: method,
                args: args.map(String)
            }, '*');
        };
    });
})();
</script>
`;
```

## ✅ 测试清单

- [ ] 普通文本消息正常显示
- [ ] 代码块正确识别（带语言标识）
- [ ] HTML 代码块显示 Preview 按钮
- [ ] 非 HTML 代码块不显示 Preview 按钮
- [ ] 点击 Preview 打开 Dialog
- [ ] iframe 正确渲染 HTML
- [ ] 点击 Dialog 外部关闭
- [ ] 点击关闭按钮关闭
- [ ] Copy 按钮正确复制代码
- [ ] 多个代码块正确处理
- [ ] 流式消息正确累积并最终渲染

## 📝 注意事项

1. **安全性**：
   - 使用 `sandbox="allow-scripts allow-forms allow-modals"`
   - 不添加 `allow-same-origin`，避免 XSS 攻击
   - 使用 `referrerpolicy="no-referrer"`

2. **性能**：
   - 只在 `message.end` 时解析代码块，避免流式过程中频繁解析
   - 使用事件委托，避免为每个按钮绑定事件

3. **兼容性**：
   - `<dialog>` 需要现代浏览器支持
   - `navigator.clipboard` 需要 HTTPS 或 localhost

4. **样式**：
   - 保持与现有 UI 风格一致
   - 使用 Tailwind 类名风格

## 🚀 部署步骤

1. 创建 `codeblocks.js` 文件
2. 修改 `main.js` 添加功能
3. 修改 `index.html` 添加 Dialog
4. 修改 `components.css` 添加样式
5. 更新版本号强制刷新缓存
6. 重启 WebUI 服务
7. 测试功能

---

**实施开始**: 准备就绪
**预计完成**: 约 1-2 小时
