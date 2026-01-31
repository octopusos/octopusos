# 代码块高级功能实施计划 (Phase 2-4)

## 📋 功能清单

### Phase 2（短期 - 立即实施）
1. ✅ **"Open in new tab" 按钮** - 在新标签页打开预览
2. ✅ **Console 输出显示** - 显示 iframe 内的 console 输出
3. ✅ **行号显示** - Prism 行号插件
4. ✅ **代码折叠** - 长代码块可折叠

### Phase 3（中期 - 立即实施）
5. ✅ **全屏预览** - Preview Dialog 全屏模式
6. ✅ **代码格式化** - 美化代码按钮
7. ✅ **主题切换** - 代码块主题切换
8. ⚠️ **实时代码编辑** - 需要集成 Monaco Editor（延后）

### Phase 4（长期 - 立即实施）
9. ✅ **导出功能** - 下载代码为文件
10. ✅ **历史记录** - 记录预览过的 HTML
11. ⚠️ **多文件支持** - HTML/CSS/JS 分离（复杂，延后）
12. ⚠️ **分享链接** - 需要后端支持（延后）

---

## 🎯 实施优先级

### 优先级 1（核心功能）- 立即实施
1. "Open in new tab" 按钮
2. 全屏预览
3. 行号显示
4. Console 输出显示
5. 导出功能

### 优先级 2（增强功能）- 立即实施
6. 代码折叠
7. 代码格式化
8. 主题切换
9. 历史记录

### 优先级 3（复杂功能）- 延后实施
10. 实时代码编辑（需要 Monaco Editor，较重）
11. 多文件支持（需要重构架构）
12. 分享链接（需要后端 API）

---

## 🔧 详细实施方案

### 1. "Open in new tab" 按钮

**实现方式**：
```javascript
function openHtmlInNewTab(htmlCode) {
    const blob = new Blob([htmlCode], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');

    // 5秒后释放 URL（避免内存泄漏）
    setTimeout(() => URL.revokeObjectURL(url), 5000);
}
```

**UI 位置**：Preview Dialog 头部右侧

**图标**：外部链接图标 ↗

---

### 2. Console 输出显示

**实现方式**：

在 iframe HTML 中注入脚本：
```javascript
const consoleScript = `
<script>
(function() {
    const original = {
        log: console.log,
        error: console.error,
        warn: console.warn,
        info: console.info
    };

    ['log', 'error', 'warn', 'info'].forEach(method => {
        console[method] = function(...args) {
            original[method].apply(console, args);
            window.parent.postMessage({
                type: 'console',
                method: method,
                args: args.map(arg => {
                    try {
                        return typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
                    } catch {
                        return '[Object]';
                    }
                })
            }, '*');
        };
    });
})();
</script>
`;
```

**UI 位置**：Preview Dialog 底部，可展开的 Console 面板

**功能**：
- 显示 log/error/warn/info
- 不同类型不同颜色
- 时间戳
- 清空按钮

---

### 3. 行号显示

**实现方式**：使用 Prism Line Numbers 插件

**引入**：
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.js"></script>
```

**使用**：
```html
<pre class="line-numbers language-javascript"><code>...</code></pre>
```

**CSS 调整**：
```css
.codeblock pre.line-numbers {
    padding-left: 3.8em;
}

.codeblock .line-numbers-rows {
    border-right: 1px solid rgba(255, 255, 255, 0.1);
}
```

---

### 4. 代码折叠

**实现方式**：CSS + JavaScript

**触发条件**：代码行数 > 20 行

**UI**：
```html
<div class="codeblock collapsible">
    <div class="codeblock__hdr">
        <!-- 添加折叠按钮 -->
        <button class="btn-collapse js-collapse" title="Collapse">
            <svg><!-- 展开/收起图标 --></svg>
        </button>
    </div>
    <pre class="collapsed">...</pre>
</div>
```

**CSS**：
```css
.codeblock pre.collapsed {
    max-height: 300px;
    overflow: hidden;
}

.codeblock pre.expanded {
    max-height: none;
}
```

---

### 5. 全屏预览

**实现方式**：使用 Fullscreen API

```javascript
function toggleFullscreen(element) {
    if (!document.fullscreenElement) {
        element.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}
```

**UI 位置**：Preview Dialog 头部右侧

**图标**：全屏图标 ⛶

**快捷键**：F11 或 ESC 退出

---

### 6. 代码格式化

**实现方式**：使用 Prettier（轻量版）

**引入**：
```html
<script src="https://unpkg.com/prettier@2.8.8/standalone.js"></script>
<script src="https://unpkg.com/prettier@2.8.8/parser-html.js"></script>
<script src="https://unpkg.com/prettier@2.8.8/parser-babel.js"></script>
<script src="https://unpkg.com/prettier@2.8.8/parser-postcss.js"></script>
```

**函数**：
```javascript
function formatCode(code, lang) {
    try {
        let parser = 'babel';
        if (lang === 'html') parser = 'html';
        if (lang === 'css') parser = 'css';

        return prettier.format(code, {
            parser: parser,
            printWidth: 80,
            tabWidth: 2,
            semi: true,
        });
    } catch (err) {
        console.error('Format failed:', err);
        return code;
    }
}
```

**UI 位置**：代码块头部按钮

**图标**：魔术棒图标 ✨

---

### 7. 主题切换

**实现方式**：动态切换 Prism CSS

**支持主题**：
- Tomorrow Night（当前）
- Okaidia
- Dracula
- One Dark
- Solarized Dark
- Monokai

**UI 位置**：代码块头部下拉菜单

**实现**：
```javascript
function switchCodeTheme(themeName) {
    const link = document.getElementById('prism-theme');
    link.href = `/static/vendor/prism/themes/prism-${themeName}.css`;
    localStorage.setItem('code-theme', themeName);
}
```

---

### 8. 导出功能

**实现方式**：Blob + download

**功能**：
- 导出为 .html 文件
- 导出为 .js/.py/.css 等（根据语言）
- 文件名自动生成或自定义

**实现**：
```javascript
function downloadCode(code, filename, mimeType) {
    const blob = new Blob([code], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}
```

**UI 位置**：代码块头部按钮（下载图标）

---

### 9. 历史记录

**实现方式**：LocalStorage

**功能**：
- 记录最近预览的 10 个 HTML
- 显示预览时间
- 快速重新打开
- 清空历史

**数据结构**：
```javascript
{
    timestamp: 1234567890,
    title: 'Button Example',
    code: '<html>...</html>',
    preview: 'data:image/png;base64,...' // 可选的缩略图
}
```

**UI 位置**：Preview Dialog 侧边栏

---

## 📂 文件结构

```
agentos/webui/
├── static/
│   ├── js/
│   │   ├── utils/
│   │   │   ├── codeblocks.js          [修改] 添加新功能
│   │   │   └── prettier-utils.js      [新增] 代码格式化
│   │   ├── components/
│   │   │   ├── ConsolePanel.js        [新增] Console 面板
│   │   │   └── PreviewHistory.js      [新增] 历史记录
│   │   └── main.js                     [修改] 整合所有功能
│   └── css/
│       └── components.css              [修改] 新增样式
└── templates/
    └── index.html                      [修改] 引入新资源
```

---

## 🎨 UI 设计

### Preview Dialog 增强版

```
┌────────────────────────────────────────────────┐
│ 🌐 HTML Preview     [全屏] [新标签] [×关闭]   │
├────────────────────────────────────────────────┤
│                                                │
│           [iframe 预览区域]                     │
│                                                │
├────────────────────────────────────────────────┤
│ 📺 Console (展开/收起)                          │
│ > console.log("Hello")                         │
│ > 2 + 2 = 4                                    │
└────────────────────────────────────────────────┘
```

### 代码块增强版

```
┌────────────────────────────────────────────┐
│ JavaScript  [主题▼] [格式化] [折叠] [下载] [复制] [预览] │
├────────────────────────────────────────────┤
│ 1  function hello() {                      │
│ 2      console.log("Hello");               │
│ 3  }                                       │
└────────────────────────────────────────────┘
```

---

## 🚀 实施步骤

### Step 1: 引入必要的库
- Prism Line Numbers 插件
- Prettier（格式化）
- Fullscreen API（原生）

### Step 2: 实施 Phase 2 功能
1. Open in new tab 按钮
2. Console 输出显示
3. 行号显示
4. 代码折叠

### Step 3: 实施 Phase 3 功能
5. 全屏预览
6. 代码格式化
7. 主题切换

### Step 4: 实施 Phase 4 功能
8. 导出功能
9. 历史记录

### Step 5: 测试和优化
- 功能测试
- 性能测试
- UI/UX 优化
- 文档更新

---

## ⚠️ 延后实施的功能

### 实时代码编辑
**原因**：需要集成 Monaco Editor（~5MB），体积较大

**替代方案**：
- 提供 "Open in new tab" 后手动编辑
- 或使用 CodeMirror（较轻量）

### 多文件支持
**原因**：需要重构架构，支持 HTML/CSS/JS 分离

**实施建议**：
- 作为独立项目
- 单独的 UI 面板
- Tab 切换

### 分享链接
**原因**：需要后端 API 支持

**实施建议**：
- 后端添加 `/api/share` 端点
- 生成短链接
- 存储代码片段

---

## ✅ 验收标准

### 功能完整性
- [ ] 所有按钮正常工作
- [ ] Console 输出正确显示
- [ ] 行号显示正确
- [ ] 代码折叠流畅
- [ ] 全屏模式正常
- [ ] 代码格式化正确
- [ ] 主题切换生效
- [ ] 导出功能正常
- [ ] 历史记录保存和读取

### 性能要求
- [ ] 格式化响应时间 < 500ms
- [ ] 主题切换响应时间 < 100ms
- [ ] 导出功能响应时间 < 200ms
- [ ] 无内存泄漏

### UI/UX 质量
- [ ] 所有图标清晰
- [ ] 按钮布局合理
- [ ] 颜色搭配协调
- [ ] 响应式设计
- [ ] 无视觉冲突

---

## 📊 预估工作量

| 功能 | 难度 | 预估时间 |
|------|------|----------|
| Open in new tab | 简单 | 10 分钟 |
| Console 输出 | 中等 | 30 分钟 |
| 行号显示 | 简单 | 15 分钟 |
| 代码折叠 | 中等 | 20 分钟 |
| 全屏预览 | 简单 | 15 分钟 |
| 代码格式化 | 中等 | 25 分钟 |
| 主题切换 | 中等 | 20 分钟 |
| 导出功能 | 简单 | 15 分钟 |
| 历史记录 | 中等 | 30 分钟 |
| **总计** | - | **约 3 小时** |

---

**实施开始**: 准备就绪
**预计完成**: 约 3 小时
