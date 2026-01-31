# WebSocket 和进度更新调试指南

## 问题描述
Index Jobs 页面的 progress 一直显示 "Initializing..."，没有看到 WebSocket 推送数据。

## 已实施的修复

### 1. 后端日志增强
在 `/agentos/webui/api/knowledge.py` 中添加了详细的日志：
- Task 创建日志
- 事件发送日志
- 进度更新日志

### 2. 前端 WebSocket 调试
在 `/agentos/webui/static/js/views/KnowledgeJobsView.js` 中添加了 WebSocket 消息日志。

### 3. 数据库同步
确保 `task.metadata["progress"]` 在每次发送 WebSocket 事件前都更新到数据库。

## 调试步骤

### Step 1: 重启后端服务
```bash
# 确保所有代码更改生效
# 重启 AgentOS 服务
```

### Step 2: 打开浏览器开发者工具
1. 打开 Chrome/Firefox 开发者工具 (F12)
2. 切换到 **Console** 标签
3. 清空所有日志

### Step 3: 打开 Index Jobs 页面
1. 导航到：Knowledge / Index Jobs
2. 观察控制台输出，应该看到：
   ```
   KnowledgeJobsView: WebSocket connected
   ```

### Step 4: 检查 WebSocket 连接状态
在浏览器控制台输入：
```javascript
// 检查 WebSocket 状态
const jobsView = window.currentView;
console.log('WebSocket:', jobsView?.websocket);
console.log('WebSocket readyState:', jobsView?.websocket?.readyState);
// readyState 值:
// 0 = CONNECTING
// 1 = OPEN (正常)
// 2 = CLOSING
// 3 = CLOSED
```

### Step 5: 触发索引任务
1. 点击页面上的 **"Incremental"** 按钮
2. 观察控制台输出，应该看到类似：
   ```
   KnowledgeJobsView: WebSocket message received: {
     type: "task.started",
     entity: { kind: "task", id: "01HXYZ..." },
     payload: { ... }
   }

   KnowledgeJobsView: WebSocket message received: {
     type: "task.progress",
     entity: { kind: "task", id: "01HXYZ..." },
     payload: { progress: 5, message: "Starting index operation..." }
   }

   KnowledgeJobsView: WebSocket message received: {
     type: "task.progress",
     entity: { kind: "task", id: "01HXYZ..." },
     payload: { progress: 20, message: "Scanning for changed files..." }
   }
   ```

### Step 6: 查看后端日志
在后端日志中应该看到：
```
[KB Index Job] Starting: task_id=01HXYZ..., job_type=incremental
[KB Index Job] Task updated: status=in_progress, progress=5
[KB Index Job] Emitting task.progress event: progress=5
[KB Index Job] Event emitted successfully
[KB Index Job] Initializing KB service
...
```

### Step 7: 检查 WebSocket 连接数
访问：http://localhost:8000/ws/events/status
应该返回：
```json
{
  "active_connections": 1,
  "event_bus_subscribers": 1
}
```

## 常见问题排查

### 问题 1: WebSocket 连接失败
**症状**：控制台显示 `WebSocket error` 或没有 "WebSocket connected" 消息

**排查**：
1. 检查后端是否启动：`curl http://localhost:8000/api/health`
2. 检查 WebSocket 路由：`curl http://localhost:8000/ws/events/status`
3. 检查浏览器网络工具的 WS 标签

### 问题 2: 收不到 WebSocket 消息
**症状**：WebSocket 已连接，但控制台没有 "WebSocket message received" 日志

**排查**：
1. 检查后端日志是否有 "Emitting task.progress event"
2. 检查 EventBus 是否有订阅者：访问 `/ws/events/status`
3. 在后端添加断点或日志到 `EventStreamManager._on_event()`

### 问题 3: Progress 不更新
**症状**：收到 WebSocket 消息，但进度条不更新

**排查**：
1. 检查 `handleWebSocketMessage()` 是否被调用
2. 检查 `updateJobFromEvent()` 逻辑
3. 检查 `this.jobs` 数组是否包含当前 job_id
4. 验证 DataTable 是否调用 `setData()`

## 手动测试 WebSocket

在浏览器控制台运行：
```javascript
// 创建新的 WebSocket 连接
const ws = new WebSocket('ws://localhost:8000/ws/events');

ws.onopen = () => {
  console.log('✓ WebSocket connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('✓ WebSocket message:', data);
};

ws.onerror = (error) => {
  console.error('✗ WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket closed');
};
```

然后触发一个索引任务，应该能看到实时事件。

## 预期输出示例

### 正常流程的控制台输出
```
KnowledgeJobsView: WebSocket connected
KnowledgeJobsView: WebSocket message received: {type: "task.started", ...}
KnowledgeJobsView: WebSocket message received: {type: "task.progress", payload: {progress: 5, ...}}
KnowledgeJobsView: WebSocket message received: {type: "task.progress", payload: {progress: 20, ...}}
KnowledgeJobsView: WebSocket message received: {type: "task.progress", payload: {progress: 90, ...}}
KnowledgeJobsView: WebSocket message received: {type: "task.completed", payload: {duration_ms: 1234, ...}}
```

### 正常流程的后端日志
```
INFO - EventStreamManager subscribed to EventBus
INFO - Event stream client connected: abc-123 (total: 1)
INFO - Emitting task.started event for task_id=01HXYZ...
INFO - Task.started event emitted successfully
INFO - [KB Index Job] Starting: task_id=01HXYZ..., job_type=incremental
INFO - [KB Index Job] Task updated: status=in_progress, progress=5
INFO - [KB Index Job] Emitting task.progress event: progress=5
INFO - [KB Index Job] Event emitted successfully
...
```

## 版本信息

- **knowledge.py**: 添加了完整的日志记录
- **KnowledgeJobsView.js**: v3 → v4 (添加 WebSocket 调试日志)
- **DataTable.js**: v2 → v3 (修复 appendChild 错误)

## 下一步

如果以上步骤都正常，但进度仍然不更新，请提供：
1. 浏览器控制台的完整日志
2. 后端日志的相关部分
3. `/ws/events/status` 的响应
