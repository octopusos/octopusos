# WebSocket 连接状态显示修复

## 🐛 问题描述

**用户报告**:
- ✅ Provider 状态显示 "Ready (46ms)"（正常）
- ❌ Session 状态显示 "Not Connected"（错误）
- ❌ 发送消息没有任何反应
- 用户选择了：llama.cpp provider, qwen2.5-coder-7b model, session 01KFZQGEAFVVKZ0V76TJ5Y2XA1

**期望行为**:
- WebSocket 连接成功后，状态应该显示 "Connected"（绿色）
- 发送消息应该通过 WebSocket 发送到后端

---

## 🔍 根本原因

### WebSocket 事件处理器缺少 UI 状态更新

#### Before (修复前)

**1. setupWebSocket 函数没有更新 UI 状态**:
```javascript
// Line 400-426 (修复前)
function setupWebSocket() {
    if (state.websocket) {
        state.websocket.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${state.currentSession}`;

    state.websocket = new WebSocket(wsUrl);

    state.websocket.onopen = () => {
        console.log('WebSocket connected');
        // ❌ 没有调用 updateChatWSStatus
    };

    state.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        // ❌ 没有调用 updateChatWSStatus
    };

    state.websocket.onclose = () => {
        console.log('WebSocket closed');
        // ❌ 没有调用 updateChatWSStatus
    };
}
```

**结果**:
- WebSocket 实际上可能已经连接成功
- 但 UI 状态一直显示初始值 "Not Connected"（灰色）
- 用户以为连接失败，但实际上可能已连接

**2. sendMessage 函数检查不充分**:
```javascript
// Line 459-480 (修复前)
function sendMessage() {
    const input = document.getElementById('chat-input');
    const content = input.value.trim();

    if (!content || !state.websocket) return;  // ❌ 只检查对象是否存在

    // Send via WebSocket
    state.websocket.send(JSON.stringify({
        type: 'user_message',
        content: content,
        metadata: {},
    }));
}
```

**问题**:
- 只检查 `state.websocket` 是否存在（truthy check）
- 没有检查 WebSocket 的实际连接状态（readyState）
- WebSocket 对象可能存在，但处于 CONNECTING、CLOSING 或 CLOSED 状态
- 导致调用 `.send()` 时抛出异常

---

## ✅ 修复方案

### 1. 在 WebSocket 事件处理器中添加状态更新

在 `setupWebSocket()` 函数中，为所有 WebSocket 事件添加 UI 状态更新。

### 2. 改进 sendMessage 的连接状态检查

使用 `WebSocket.readyState` 检查实际连接状态，而不仅仅是检查对象是否存在。

### 修改的文件

**agentos/webui/static/js/main.js** (line 400-436, 459-487)

### 修复逻辑

#### 1. setupWebSocket - 添加状态更新

```javascript
// Line 400-436 (修复后)
function setupWebSocket() {
    if (state.websocket) {
        state.websocket.close();
    }

    // ✅ 显示连接中状态
    updateChatWSStatus('connecting', 'Connecting...');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${state.currentSession}`;

    state.websocket = new WebSocket(wsUrl);

    state.websocket.onopen = () => {
        console.log('WebSocket connected');
        // ✅ 更新 UI 状态为已连接
        updateChatWSStatus('connected', 'Connected');
    };

    state.websocket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };

    state.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        // ✅ 更新 UI 状态为错误
        updateChatWSStatus('disconnected', 'Connection Error');
    };

    state.websocket.onclose = () => {
        console.log('WebSocket closed');
        // ✅ 更新 UI 状态为已断开
        updateChatWSStatus('disconnected', 'Disconnected');
    };
}
```

#### 2. sendMessage - 检查实际连接状态

```javascript
// Line 459-487 (修复后)
function sendMessage() {
    const input = document.getElementById('chat-input');
    const content = input.value.trim();

    if (!content) return;

    // ✅ 检查 WebSocket 的实际连接状态
    if (!state.websocket || state.websocket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket is not connected. Ready state:', state.websocket?.readyState);
        alert('WebSocket connection not established. Please wait or refresh the page.');
        return;
    }

    // Add user message to UI
    const messagesDiv = document.getElementById('messages');
    const userMsg = createMessageElement('user', content);
    messagesDiv.appendChild(userMsg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Send via WebSocket
    state.websocket.send(JSON.stringify({
        type: 'user_message',
        content: content,
        metadata: {},
    }));

    // Clear input
    input.value = '';
}
```

### WebSocket.readyState 值

| 常量 | 值 | 描述 |
|------|---|------|
| `WebSocket.CONNECTING` | 0 | 正在连接 |
| `WebSocket.OPEN` | 1 | 已连接，可以发送数据 |
| `WebSocket.CLOSING` | 2 | 正在关闭 |
| `WebSocket.CLOSED` | 3 | 已关闭或连接失败 |

### 关键改进

1. **实时状态反馈**:
   - 连接前：显示 "Connecting..."（黄色，动画）
   - 连接成功：显示 "Connected"（绿色）
   - 连接错误：显示 "Connection Error"（红色）
   - 连接关闭：显示 "Disconnected"（红色）

2. **准确的连接状态检查**:
   - 使用 `state.websocket.readyState === WebSocket.OPEN`
   - 只有在 OPEN 状态才允许发送消息
   - 如果连接未建立，显示友好的提示信息

3. **更好的错误处理**:
   - 如果尝试在未连接时发送消息，显示 alert 提示用户
   - 在控制台记录详细的 readyState 信息，方便调试

---

## 🧪 测试场景

### 场景 1: 正常连接

```
Step 1: 选择 Chat 页面
  - 状态显示: "Connecting..." (黄色，动画) ✅

Step 2: WebSocket 连接成功
  - Console 输出: "WebSocket connected"
  - 状态显示: "Connected" (绿色) ✅

Step 3: 发送消息
  - 消息成功发送到后端 ✅
  - 收到 AI 回复 ✅
```

### 场景 2: 连接失败

```
Step 1: 选择 Chat 页面（后端服务未启动）
  - 状态显示: "Connecting..." (黄色)

Step 2: WebSocket 连接失败
  - Console 输出: "WebSocket error: ..."
  - 状态显示: "Connection Error" (红色) ✅

Step 3: 尝试发送消息
  - Alert 提示: "WebSocket connection not established..." ✅
  - 消息不会发送 ✅
```

### 场景 3: 连接中断

```
Step 1: 正常连接，状态显示 "Connected"

Step 2: 后端服务停止
  - Console 输出: "WebSocket closed"
  - 状态显示: "Disconnected" (红色) ✅

Step 3: 尝试发送消息
  - Alert 提示: "WebSocket connection not established..." ✅
  - 消息不会发送 ✅
```

---

## 📊 状态显示逻辑

| WebSocket Event | updateChatWSStatus 参数 | 显示文本 | 颜色 |
|-----------------|------------------------|---------|------|
| 创建 WebSocket 前 | `('connecting', 'Connecting...')` | "Connecting..." | 黄色，动画 |
| `onopen` 事件 | `('connected', 'Connected')` | "Connected" | 绿色 |
| `onerror` 事件 | `('disconnected', 'Connection Error')` | "Connection Error" | 红色 |
| `onclose` 事件 | `('disconnected', 'Disconnected')` | "Disconnected" | 红色 |

**updateChatWSStatus 函数实现** (Line 682-707):
```javascript
function updateChatWSStatus(status, message) {
    const wsStatus = document.getElementById('chat-ws-status');
    if (!wsStatus) return;

    const dot = wsStatus.querySelector('.w-2');
    const text = wsStatus.querySelector('span');

    if (status === 'connected') {
        dot.className = 'w-2 h-2 rounded-full bg-green-500';
        text.textContent = message || 'Connected';
        text.className = 'text-xs font-medium text-green-700';
    } else if (status === 'connecting') {
        dot.className = 'w-2 h-2 rounded-full bg-yellow-500 animate-pulse';
        text.textContent = message || 'Connecting...';
        text.className = 'text-xs font-medium text-yellow-700';
    } else if (status === 'disconnected') {
        dot.className = 'w-2 h-2 rounded-full bg-red-500';
        text.textContent = message || 'Disconnected';
        text.className = 'text-xs font-medium text-red-700';
    } else {
        dot.className = 'w-2 h-2 rounded-full bg-gray-400';
        text.textContent = message || 'Not Connected';
        text.className = 'text-xs font-medium text-gray-600';
    }
}
```

---

## 🎯 用户体验改进

### Before (修复前)

```
Chat 页面加载:
  - 状态显示: "Not Connected" (灰色) ❌
  - 实际状态: WebSocket 可能已连接
  - 用户操作: 发送消息
  - 结果: 可能成功，也可能失败（取决于实际连接状态）
  - 用户体验: 困惑，不知道是否已连接
```

### After (修复后)

```
Chat 页面加载:
  - 状态显示: "Connecting..." (黄色，动画) ✅

连接成功:
  - 状态显示: "Connected" (绿色) ✅
  - 用户操作: 发送消息
  - 结果: 消息成功发送 ✅
  - 用户体验: 清晰，知道可以开始对话

连接失败:
  - 状态显示: "Connection Error" (红色) ✅
  - 用户操作: 尝试发送消息
  - 结果: Alert 提示连接未建立 ✅
  - 用户体验: 清晰，知道需要等待或刷新页面
```

---

## 🚀 使用方法

### 1. 清除浏览器缓存（必须）

服务器已重启，main.js 版本已更新到 v16。

**Chrome/Edge**:
```
1. F12 打开开发者工具
2. 右键点击刷新按钮
3. 选择 "清空缓存并硬性重新加载"
```

**或使用快捷键**:
```
Mac: Cmd + Shift + R
Windows/Linux: Ctrl + Shift + R
```

### 2. 验证修复

**Step 1: 打开 Chat 页面**
1. 访问 http://127.0.0.1:8080
2. 点击左侧导航栏的 "Chat"
3. 观察右上角的 Session 状态指示器

**Step 2: 验证连接状态**
1. ✅ 应该先显示 "Connecting..."（黄色，动画）
2. ✅ 1-2 秒后显示 "Connected"（绿色）
3. 查看控制台，应该显示:
   ```
   WebSocket connected
   ```

**Step 3: 测试发送消息**
1. 输入一条消息，如 "Hello"
2. 点击发送按钮
3. ✅ 消息应该成功发送
4. ✅ 应该收到 AI 回复

**Step 4: 测试连接失败场景**
1. 停止后端服务（测试用）
2. 刷新页面
3. ✅ 状态应该显示 "Connection Error" 或 "Disconnected"（红色）
4. 尝试发送消息
5. ✅ 应该显示 alert 提示 "WebSocket connection not established..."

---

## 🔍 调试方法

### 检查 WebSocket 连接

打开控制台，执行:
```javascript
// 检查 WebSocket 对象
console.log('WebSocket:', state.websocket);

// 检查连接状态
console.log('ReadyState:', state.websocket?.readyState);
// 0 = CONNECTING
// 1 = OPEN
// 2 = CLOSING
// 3 = CLOSED

// 检查 WebSocket URL
console.log('URL:', state.websocket?.url);
```

### 检查状态更新

刷新页面后，检查控制台输出:
```javascript
// 应该看到
WebSocket connected

// 如果没有看到，检查 Network 标签中的 WebSocket 连接
// 找到 ws://127.0.0.1:8080/ws/chat/xxx
// 查看连接状态和消息
```

### 常见问题排查

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 一直显示 "Connecting..." | 后端 WebSocket 端点未启动 | 检查后端服务，查看日志 |
| 显示 "Connection Error" | WebSocket 连接被拒绝 | 检查防火墙、端口占用 |
| 显示 "Disconnected" | WebSocket 连接后立即关闭 | 检查后端日志，可能是认证失败 |
| 发送消息无反应 | WebSocket 未真正连接 | 查看控制台 readyState，刷新页面 |

---

## 📋 相关修复

本次修复与以下修复配套使用：

1. **LLAMACPP_MODELS_FIX.md** - 修复了 llamacpp provider 的 models API
2. **PROVIDER_STATUS_FIX.md** - 修复了 provider 状态显示
3. **MODEL_PERSISTENCE_FIX.md** - 修复了 model 选择持久化
4. **WEBSOCKET_STATUS_FIX.md** (本文档) - 修复了 WebSocket 连接状态显示

这四个修复共同提供了完整的 Chat 功能体验。

---

## 💡 技术细节

### WebSocket 生命周期

```
1. 创建 WebSocket 对象
   new WebSocket(url)
   readyState = CONNECTING (0)
   UI: "Connecting..."

2. 连接成功
   onopen 事件触发
   readyState = OPEN (1)
   UI: "Connected"

3. 正常通信
   onmessage 事件接收消息
   send() 方法发送消息

4. 连接关闭
   onclose 事件触发
   readyState = CLOSED (3)
   UI: "Disconnected"

5. 连接错误
   onerror 事件触发
   onclose 也会触发
   UI: "Connection Error" → "Disconnected"
```

### 为什么需要检查 readyState？

即使 `state.websocket` 对象存在（truthy），也不代表可以发送消息：

```javascript
// 错误的检查方式
if (state.websocket) {
    state.websocket.send(data);  // ❌ 可能失败
}

// 正确的检查方式
if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
    state.websocket.send(data);  // ✅ 确保可以发送
}
```

**原因**:
- WebSocket 对象在创建后立即存在，但连接可能还在进行中（CONNECTING）
- 连接失败后，WebSocket 对象仍然存在，但状态是 CLOSED
- 只有 readyState === OPEN (1) 时才能安全地调用 .send()

---

## ✅ 验收清单

- [x] setupWebSocket 函数添加了状态更新调用
- [x] onopen 事件调用 updateChatWSStatus('connected')
- [x] onerror 事件调用 updateChatWSStatus('disconnected')
- [x] onclose 事件调用 updateChatWSStatus('disconnected')
- [x] sendMessage 函数检查 readyState === WebSocket.OPEN
- [x] sendMessage 函数在连接未建立时显示提示
- [x] 更新 main.js 版本到 v16
- [x] 重启服务器
- [ ] 清除浏览器缓存
- [ ] 验证连接状态显示正确
- [ ] 验证消息发送功能正常

---

**修复完成时间**: 2026-01-28
**main.js 版本**: v16
**服务器状态**: ✅ 运行中
**需要操作**: 清除浏览器缓存并验证
