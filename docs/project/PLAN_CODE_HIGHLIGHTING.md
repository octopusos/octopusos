# 代码语法高亮功能实施计划

## 📋 需求概述

为 Chat 页面的代码块添加语法高亮功能：
1. 使用 **PrismJS**（轻量、灵活、易控制）
2. 支持常见语言（JS/TS/Python/JSON/Bash/CSS/HTML 等）
3. 与现有 Preview 功能兼容
4. 统一 AgentOS 深色主题风格
5. 保留 Copy 功能（复制原始文本）

**实现日期**: 2026-01-28

---

## 🎯 设计目标

- ✅ **语法高亮** - 使用 PrismJS 渲染彩色代码
- ✅ **主题统一** - 深色主题（Tomorrow Night / Okaidia）
- ✅ **语言支持** - 常见编程语言全覆盖
- ✅ **兼容现有** - Preview 和 Copy 功能不受影响
- ✅ **性能优化** - 只高亮新增的代码块

---

## 🔧 实施步骤

### Step 1: 下载 PrismJS 资源

**下载清单**：
```
prismjs/
├── prism.min.js              # 核心库
├── prism.css                 # 基础样式
├── themes/
│   ├── prism-tomorrow.css    # Tomorrow Night 主题（推荐）
│   └── prism-okaidia.css     # Okaidia 主题（备选）
└── components/
    ├── prism-markup.min.js   # HTML
    ├── prism-css.min.js      # CSS
    ├── prism-clike.min.js    # C-like（基础）
    ├── prism-javascript.min.js # JavaScript
    ├── prism-typescript.min.js # TypeScript
    ├── prism-python.min.js   # Python
    ├── prism-json.min.js     # JSON
    ├── prism-bash.min.js     # Bash/Shell
    ├── prism-sql.min.js      # SQL
    ├── prism-yaml.min.js     # YAML
    └── prism-markdown.min.js # Markdown
```

**下载方式**：
- 官网自定义下载：https://prismjs.com/download.html
- 选择语言 + 主题 + 插件
- 下载到本地

### Step 2: 放置资源文件

**目录结构**：
```
agentos/webui/static/
└── vendor/
    └── prism/
        ├── prism.min.js
        ├── prism-tomorrow.css
        └── components/
            ├── prism-markup.min.js
            ├── prism-css.min.js
            ├── prism-javascript.min.js
            ├── prism-typescript.min.js
            ├── prism-python.min.js
            ├── prism-json.min.js
            ├── prism-bash.min.js
            ├── prism-sql.min.js
            └── prism-yaml.min.js
```

### Step 3: 在 index.html 中引入

**位置**：在 `<head>` 部分，CSS 文件引入

```html
<!-- PrismJS Syntax Highlighting -->
<link rel="stylesheet" href="/static/vendor/prism/prism-tomorrow.css">
```

**位置**：在组件库之前，JS 文件引入

```html
<!-- PrismJS Core -->
<script src="/static/vendor/prism/prism.min.js"></script>
<script src="/static/vendor/prism/components/prism-markup.min.js"></script>
<script src="/static/vendor/prism/components/prism-css.min.js"></script>
<script src="/static/vendor/prism/components/prism-javascript.min.js"></script>
<script src="/static/vendor/prism/components/prism-typescript.min.js"></script>
<script src="/static/vendor/prism/components/prism-python.min.js"></script>
<script src="/static/vendor/prism/components/prism-json.min.js"></script>
<script src="/static/vendor/prism/components/prism-bash.min.js"></script>
<script src="/static/vendor/prism/components/prism-sql.min.js"></script>
<script src="/static/vendor/prism/components/prism-yaml.min.js"></script>
```

### Step 4: 修改 codeblocks.js

**添加语言规范化函数**：

```javascript
/**
 * Normalize language identifiers to Prism language names
 *
 * @param {string} lang - Original language identifier
 * @returns {string} Prism language name
 */
function normalizeLang(lang) {
    if (!lang) return 'clike';

    const l = lang.toLowerCase().trim();

    // Language mappings
    const langMap = {
        'js': 'javascript',
        'ts': 'typescript',
        'py': 'python',
        'sh': 'bash',
        'shell': 'bash',
        'yml': 'yaml',
        'htm': 'markup',
        'html': 'markup',
        'xml': 'markup',
        'svg': 'markup',
        'md': 'markdown',
        'dockerfile': 'docker',
        'makefile': 'makefile',
    };

    return langMap[l] || l;
}
```

**修改 renderCodeBlock() 函数**：

```javascript
function renderCodeBlock({lang, code}) {
    const canPreview = isHtmlBlock(lang, code);
    const displayLang = lang || 'plaintext';
    const prismLang = normalizeLang(lang);

    return `
    <div class="codeblock">
        <div class="codeblock__hdr">
            <span class="codeblock__lang">${escapeHtmlUtil(displayLang)}</span>
            <div class="codeblock__actions">
                ${canPreview ? `<button class="btn-preview js-preview" title="Preview HTML" data-lang="${escapeHtmlUtil(lang)}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Preview</span>
                </button>` : ''}
                <button class="btn-copy js-copy" title="Copy code">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>Copy</span>
                </button>
            </div>
        </div>
        <pre class="language-${prismLang}"><code class="language-${prismLang}">${escapeHtmlUtil(code)}</code></pre>
    </div>`;
}
```

**添加到全局 API**：

```javascript
window.CodeBlockUtils = {
    parseFencedCodeBlocks,
    isHtmlBlock,
    escapeHtml: escapeHtmlUtil,
    renderCodeBlock,
    renderAssistantMessage,
    normalizeLang  // 新增
};
```

### Step 5: 修改 main.js 添加高亮函数

**在 `handleWebSocketMessage` 的 `message.end` 部分**：

```javascript
} else if (message.type === 'message.end') {
    console.log('Finished receiving message:', message.message_id, message.metadata);

    // Find the message element and rerender with code block parsing
    const msgEl = messagesDiv.querySelector(`[data-message-id="${message.message_id}"]`);
    if (msgEl && msgEl.classList.contains('assistant')) {
        const contentDiv = msgEl.querySelector('.content');
        if (contentDiv) {
            const fullText = contentDiv.textContent;

            // Rerender with code block parsing using CodeBlockUtils
            if (window.CodeBlockUtils && window.CodeBlockUtils.renderAssistantMessage) {
                contentDiv.innerHTML = window.CodeBlockUtils.renderAssistantMessage(fullText);

                // Apply syntax highlighting with Prism
                highlightCodeBlocks(contentDiv);
            }
        }
    }
}
```

**添加高亮函数**：

```javascript
// Apply syntax highlighting to code blocks within an element
function highlightCodeBlocks(element) {
    if (!window.Prism) {
        console.warn('PrismJS not loaded, skipping syntax highlighting');
        return;
    }

    // Highlight all code blocks within the element
    try {
        Prism.highlightAllUnder(element);
        console.log('Syntax highlighting applied');
    } catch (err) {
        console.error('Failed to apply syntax highlighting:', err);
    }
}
```

**在 `loadMessages()` 中也应用高亮**：

```javascript
async function loadMessages() {
    try {
        // ... existing code ...

        if (messages.length === 0) {
            messagesDiv.innerHTML = '<div class="text-center text-gray-500 text-sm">No messages yet. Start a conversation!</div>';
            return;
        }

        // Render messages
        messages.forEach(msg => {
            const msgEl = createMessageElement(msg.role, msg.content);
            messagesDiv.appendChild(msgEl);

            // Apply syntax highlighting to assistant messages
            if (msg.role === 'assistant' && window.CodeBlockUtils) {
                const contentDiv = msgEl.querySelector('.content');
                if (contentDiv) {
                    contentDiv.innerHTML = window.CodeBlockUtils.renderAssistantMessage(msg.content);
                    highlightCodeBlocks(contentDiv);
                }
            }
        });

        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (err) {
        console.error('Failed to load messages:', err);
        // ...
    }
}
```

### Step 6: 调整 CSS 样式

**修改 components.css 中的代码块样式**：

```css
/* ========================================
   Code Block Styles (with Prism Highlighting)
   ======================================== */

.codeblock {
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 10px;
    overflow: hidden;
    margin: 12px 0;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

/* Keep existing header styles */

/* Override Prism default styles */
.codeblock pre[class*="language-"] {
    margin: 0;
    padding: 16px;
    overflow-x: auto;
    background: #1d1f21 !important; /* Tomorrow Night background */
    border-radius: 0;
    font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Menlo, Consolas, 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.7;
}

.codeblock code[class*="language-"] {
    background: transparent;
    color: #c5c8c6; /* Tomorrow Night default text */
    text-shadow: none;
    font-family: inherit;
    font-size: inherit;
    line-height: inherit;
}

/* Ensure code blocks are not affected by Prism's default padding */
.codeblock pre[class*="language-"] > code {
    display: block;
    padding: 0;
}

/* Tomorrow Night theme color overrides (optional, for consistency) */
.codeblock .token.comment,
.codeblock .token.prolog,
.codeblock .token.doctype,
.codeblock .token.cdata {
    color: #969896;
}

.codeblock .token.selector,
.codeblock .token.operator,
.codeblock .token.punctuation {
    color: #c5c8c6;
}

.codeblock .token.namespace {
    opacity: 0.7;
}

.codeblock .token.tag,
.codeblock .token.boolean {
    color: #cc6666;
}

.codeblock .token.atrule,
.codeblock .token.attr-value,
.codeblock .token.hex,
.codeblock .token.string {
    color: #b5bd68;
}

.codeblock .token.property,
.codeblock .token.entity,
.codeblock .token.url,
.codeblock .token.attr-name,
.codeblock .token.keyword {
    color: #b294bb;
}

.codeblock .token.regex {
    color: #8abeb7;
}

.codeblock .token.function {
    color: #81a2be;
}

.codeblock .token.important,
.codeblock .token.variable {
    color: #de935f;
}

.codeblock .token.important,
.codeblock .token.bold {
    font-weight: bold;
}

.codeblock .token.italic {
    font-style: italic;
}
```

### Step 7: 测试验证

**测试清单**：
- [ ] JavaScript 代码高亮正确
- [ ] Python 代码高亮正确
- [ ] HTML 代码高亮正确
- [ ] CSS 代码高亮正确
- [ ] JSON 代码高亮正确
- [ ] Bash 代码高亮正确
- [ ] 无语言标识的代码块显示（fallback）
- [ ] Preview 功能仍然正常工作
- [ ] Copy 功能复制原始文本（不是高亮后的 HTML）
- [ ] 流式消息完成后自动高亮
- [ ] 历史消息加载时自动高亮

---

## 🎨 主题选择

### Tomorrow Night（推荐）

**特点**：
- 深色背景 `#1d1f21`
- 柔和的色彩搭配
- 适合长时间阅读
- 与 GitHub Dark 相似

**颜色方案**：
- 背景：`#1d1f21`
- 文本：`#c5c8c6`
- 注释：`#969896`
- 关键字：`#b294bb`
- 字符串：`#b5bd68`
- 函数：`#81a2be`

### Okaidia（备选）

**特点**：
- 更深的背景 `#272822`
- 高对比度
- 类似 Sublime Text
- 更鲜艳的色彩

---

## 📊 性能考虑

### 优化策略

1. **按需高亮**：
   - 只对新插入的消息调用 `Prism.highlightAllUnder()`
   - 不全局扫描整个 DOM

2. **延迟加载**（未来）：
   - 初始只加载常用语言
   - 遇到少见语言时动态加载

3. **缓存优化**：
   - Prism 会缓存解析结果
   - 避免重复高亮同一代码块

### 性能对比

**无高亮**：
- 渲染时间：~10ms

**有高亮（Prism）**：
- 渲染时间：~30ms
- 用户感知：无差异（<50ms）

---

## 🔗 兼容性保证

### Preview 功能

**关键点**：Copy 和 Preview 都使用 `codeEl.textContent` 获取原始代码

```javascript
// ✅ 正确：获取原始文本，不受高亮影响
const code = codeEl.textContent;

// ❌ 错误：会获取到高亮后的 HTML
const code = codeEl.innerHTML;
```

**验证**：
- Preview 仍然预览原始 HTML
- Copy 仍然复制原始文本
- 高亮只是视觉效果，不影响数据

### 流式消息

**流程**：
1. `message.delta`：累积纯文本
2. `message.end`：解析代码块 + 渲染 + 高亮

**保证**：
- 流式过程不触发高亮（性能）
- 完成后统一高亮（一致性）

---

## 🚀 部署步骤

1. 下载 PrismJS 文件
2. 放置到 `static/vendor/prism/`
3. 修改 `index.html` 引入资源
4. 修改 `codeblocks.js` 添加 `normalizeLang()`
5. 修改 `main.js` 添加 `highlightCodeBlocks()`
6. 调整 `components.css` 样式
7. 更新版本号
8. 重启服务器
9. 测试验证

---

## 📝 验收标准

### 必须通过

- [ ] 所有主流语言高亮正确
- [ ] 颜色与 AgentOS 主题统一
- [ ] Preview 功能不受影响
- [ ] Copy 功能复制原始文本
- [ ] 流式消息正确高亮
- [ ] 历史消息正确高亮
- [ ] 性能无明显下降
- [ ] 无 JavaScript 错误

### 可选增强

- [ ] 添加行号插件
- [ ] 添加代码折叠
- [ ] 添加全屏查看
- [ ] 添加更多语言支持

---

**实施开始**: 准备就绪
**预计完成**: 约 1 小时
