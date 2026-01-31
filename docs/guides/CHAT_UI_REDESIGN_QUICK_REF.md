# Chat UI Redesign 快速参考

## 新布局一览

```
┌─────────────────────────────────────────────────────────────┐
│ 顶部工具栏 (Toolbar)                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Phase: Planning | Execution]                           │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ 消息区域 (Messages)                                         │
│                                                             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ 输入区域 (Input Area)                                       │
│ ┌────┬───┬───┬────────────────────────────────┬──────┐     │
│ │Mode│📎 │🎤 │ 输入框 (Textarea)               │ 发送 │     │
│ └────┴───┴───┴────────────────────────────────┴──────┘     │
└─────────────────────────────────────────────────────────────┘

尺寸:
- Mode Select: 120px
- 文件上传: 38px
- 语音输入: 38px
- 输入框: flex-grow (自适应)
- 发送按钮: 70px
- 所有高度: 38px
```

## 修改的文件

```
agentos/webui/
├── static/
│   ├── css/
│   │   └── mode-selector.css          # 新增 Select + 图标按钮样式
│   └── js/
│       ├── components/
│       │   ├── ModeSelector.js        # 改为 Select 元素
│       │   └── PhaseSelector.js       # 移除 Emoji
│       └── main.js                    # 重新设计输入区域布局
└── templates/
    └── index.html                     # 调整 HTML 结构（可选）
```

## 代码变更要点

### 1. ModeSelector.js - Select 元素

```javascript
// 旧版 (Emoji 按钮)
<button class="mode-selector-option">
    <span class="mode-icon">💬</span>
    <span class="mode-label">Chat</span>
</button>

// 新版 (Select 下拉框)
<select class="mode-selector-select">
    <option value="chat">Chat - 自由对话</option>
    <option value="discussion">Discussion - 结构化讨论</option>
    ...
</select>
```

### 2. PhaseSelector.js - 移除 Emoji

```javascript
// 旧版
<span class="phase-icon">🧠</span>
<span class="phase-label">Planning</span>

// 新版
<span class="phase-label">Planning</span>
```

### 3. main.js - 新输入区域

```javascript
<div class="flex gap-2 items-center">
    <!-- Mode Select -->
    <div id="input-mode-selector-container"></div>

    <!-- 文件上传 -->
    <button class="chat-input-icon-btn" title="上传文件（即将推出）">
        <span class="material-icons">attach_file</span>
    </button>

    <!-- 语音输入 -->
    <button class="chat-input-icon-btn" title="语音输入（即将推出）">
        <span class="material-icons">mic</span>
    </button>

    <!-- 输入框 -->
    <textarea id="chat-input" style="height: 38px"></textarea>

    <!-- 发送 -->
    <button id="send-btn" style="width: 70px; height: 38px">发送</button>
</div>
```

### 4. mode-selector.css - 新样式

```css
/* Mode Selector */
.mode-selector-select {
    width: 120px;
    height: 38px;
    padding: 0 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
}

/* Icon Buttons */
.chat-input-icon-btn {
    width: 38px;
    height: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #ddd;
    border-radius: 4px;
}
```

## 图标映射

| 功能       | 旧版 Emoji | 新版 Material Icon |
|------------|------------|-------------------|
| 文件上传   | 无         | `attach_file`     |
| 语音输入   | 无         | `mic`             |
| Chat       | 💬         | 移除              |
| Discussion | 🗣️         | 移除              |
| Plan       | 📋         | 移除              |
| Development| ⚙️         | 移除              |
| Task       | ✓          | 移除              |
| Planning   | 🧠         | 移除              |
| Execution  | 🚀         | 移除              |

## 事件处理

```javascript
// Mode Selector (Select)
document.querySelector('.mode-selector-select').addEventListener('change', (e) => {
    const mode = e.target.value;
    // API 调用...
});

// 文件上传
document.getElementById('file-upload-btn').addEventListener('click', () => {
    alert('文件上传功能即将推出');
});

// 语音输入
document.getElementById('voice-input-btn').addEventListener('click', () => {
    alert('语音输入功能即将推出');
});
```

## API 调用不变

```javascript
// Mode 切换
PATCH /api/sessions/{sessionId}/mode
Body: { "mode": "chat" }

// Phase 切换
PATCH /api/sessions/{sessionId}/phase
Body: {
    "phase": "execution",
    "actor": "user",
    "reason": "User switched to execution phase via WebUI",
    "confirmed": true
}
```

## CSS 类名速查

| 类名                    | 用途                     |
|-------------------------|--------------------------|
| `.mode-selector-select` | Mode 下拉框              |
| `.phase-selector-option`| Phase 按钮               |
| `.chat-input-icon-btn`  | 文件/语音图标按钮        |
| `.phase-label`          | Phase 按钮文字           |

## 响应式断点

```css
/* 桌面端 (默认) */
.mode-selector-select { width: 120px; }
.chat-input-icon-btn { width: 38px; height: 38px; }

/* 移动端 (≤ 768px) */
@media (max-width: 768px) {
    .mode-selector-select { width: 100px; font-size: 13px; }
    .chat-input-icon-btn { width: 36px; height: 36px; }
    .material-icons { font-size: 18px; }
}
```

## 测试页面

```bash
# 打开测试页面
open test_ui_redesign.html
# 或
file:///path/to/AgentOS/test_ui_redesign.html
```

## 验收检查清单

- [ ] 所有 Emoji 已移除
- [ ] Mode Selector 是 Select 元素
- [ ] Phase Selector 是文字按钮
- [ ] 文件上传按钮显示正常
- [ ] 语音输入按钮显示正常
- [ ] 所有控件高度 38px
- [ ] 移动端响应式布局
- [ ] Mode 切换 API 正常
- [ ] Phase 切换 API 正常
- [ ] Plan mode 锁定 execution
- [ ] 确认对话框正常

## 常见问题

### Q: Mode Selector 为什么移到输入区域？
A: 更节省工具栏空间，符合用户操作流程（选择模式 → 输入消息）。

### Q: 为什么保留 Phase Selector 在工具栏？
A: Phase 切换需要确认对话框，是系统级设置，应该在醒目位置。

### Q: Material Icons 如何加载？
A: 已在 `index.html` 中引入：
```html
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
```

### Q: 如何添加新图标按钮？
A: 复制 `.chat-input-icon-btn` 结构：
```html
<button class="chat-input-icon-btn" title="新功能">
    <span class="material-icons">icon_name</span>
</button>
```

## 后续功能预览

### 文件上传 (即将推出)
- 支持拖拽上传
- 支持粘贴图片
- 文件类型限制
- 进度显示

### 语音输入 (即将推出)
- 实时语音转文字
- 支持多语言
- 语音命令
- 音频可视化

---

**快速参考版本**: v1.0
**更新日期**: 2026-01-31
