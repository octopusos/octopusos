# PR-V3 快速参考指南

## 概述

PR-V3 实现了实时事件通道（SSE），支持：
- ✅ 实时推送（< 500ms）
- ✅ 断点续流（Gap detection）
- ✅ 自动重连（指数退避）
- ✅ Keepalive（30s 心跳）

---

## 快速开始

### 1. 启动 WebUI

```bash
uvicorn agentos.webui.app:app --reload
```

### 2. 打开演示页面

浏览器访问: http://localhost:8000/demo_sse_streaming.html

### 3. 发射测试事件

```bash
python test_sse_manual.py
```

---

## API 使用

### 服务端 SSE 端点

```
GET /sse/tasks/{task_id}/events?since_seq=0&batch_size=10&flush_interval=0.5
```

**参数**:
- `since_seq`: 从哪个 seq 开始（不包含）
- `batch_size`: 批量大小（1-100，默认 10）
- `flush_interval`: 刷新间隔（0.1-5s，默认 0.5s）

**响应格式**:
```
data: {"seq": 123, "event_type": "phase_enter", "phase": "executing", ...}

data: {"seq": 124, "event_type": "work_item_started", ...}

: keepalive
```

### 健康检查

```
GET /sse/health
```

**响应**:
```json
{
  "status": "ok",
  "service": "task_events_sse",
  "version": "v0.32",
  "protocol": "sse"
}
```

---

## 客户端使用

### 基础用法

```javascript
import { EventStreamService } from '/static/js/services/EventStreamService.js';

const stream = new EventStreamService('task_123', {
    since_seq: 0,
    onEvent: (event) => {
        console.log('Event:', event.event_type, event.seq);
    },
    onStateChange: (state) => {
        console.log('State:', state);
    },
    onError: (error) => {
        console.error('Error:', error);
    }
});

stream.start();
```

### 连接状态组件

```javascript
import { ConnectionStatus } from '/static/js/components/ConnectionStatus.js';

const status = new ConnectionStatus({
    container: document.getElementById('status-container'),
    showStats: true,
    showReconnectTimer: true
});

// 更新状态
eventStream.options.onStateChange = (state) => {
    status.setState(state, {
        reconnectAttempt: eventStream.reconnectAttempts,
        reconnectDelay: eventStream.currentReconnectDelay
    });
};
```

---

## 配置选项

### 服务端配置

```python
from agentos.webui.sse.task_events import SSEConfig

config = SSEConfig(
    batch_size=10,              # 批量大小
    flush_interval=0.5,         # 刷新间隔（秒）
    keepalive_interval=30.0,    # Keepalive 间隔（秒）
    poll_interval=0.1,          # 轮询间隔（秒）
    max_poll_interval=2.0,      # 最大轮询间隔（秒）
    poll_backoff_factor=1.5,    # 退避因子
    max_events_per_stream=10000 # 单连接最大事件数
)
```

### 客户端配置

```javascript
const stream = new EventStreamService(taskId, {
    since_seq: 0,                    // 起始 seq
    batch_size: 10,                  // 批量大小
    flush_interval: 0.5,             // 刷新间隔
    reconnectDelay: 1000,            // 初始重连延迟（毫秒）
    maxReconnectDelay: 30000,        // 最大重连延迟（毫秒）
    reconnectBackoff: 2,             // 重连退避因子
    maxReconnectAttempts: Infinity,  // 最大重连次数
    autoReconnect: true,             // 自动重连
    gapDetection: true,              // Gap 检测
    baseUrl: ''                      // API 基础 URL
});
```

---

## 测试

### 集成测试

```bash
pytest tests/integration/test_sse_task_events.py -v
```

**测试用例**:
- `test_sse_basic_streaming`: 基础流式传输
- `test_sse_resumption`: 断点续流
- `test_sse_batching`: 批量推送
- `test_sse_keepalive`: Keepalive 心跳
- `test_sse_error_handling`: 错误处理
- `test_sse_health_check`: 健康检查

### E2E 测试

```bash
npx playwright test tests/e2e/test_sse_reconnect.spec.js
```

**测试场景**:
- 连接和接收事件
- 离线/在线切换
- 重连倒计时
- Gap detection

---

## 故障排查

### 问题: 连接失败

**检查**:
1. WebUI 是否启动？`http://localhost:8000/sse/health`
2. 任务 ID 是否存在？
3. 浏览器控制台是否有错误？

**解决**:
```javascript
// 启用详细日志
console.log('[EventStreamService] enabled');
```

### 问题: 重连循环

**检查**:
1. 服务端是否正常？检查 `/sse/health`
2. 网络是否稳定？
3. 重连次数是否超限？

**解决**:
```javascript
// 增加最大重连次数
maxReconnectAttempts: 100

// 增加最大延迟
maxReconnectDelay: 60000
```

### 问题: Gap 未恢复

**检查**:
1. Gap detection 是否启用？`gapDetection: true`
2. REST API 是否可访问？`/api/tasks/{id}/events`
3. 浏览器控制台日志

**解决**:
```javascript
// 手动触发恢复
stream._handleGap(expectedSeq);
```

---

## 性能调优

### 低延迟场景

```python
# 服务端
SSEConfig(
    batch_size=1,          # 单个事件立即推送
    flush_interval=0.1,    # 100ms 刷新
    poll_interval=0.05     # 50ms 轮询
)
```

### 高吞吐场景

```python
# 服务端
SSEConfig(
    batch_size=50,         # 大批量
    flush_interval=2.0,    # 2 秒刷新
    poll_interval=0.5      # 500ms 轮询
)
```

### 低带宽场景

```javascript
// 客户端 - 减少重连频率
const stream = new EventStreamService(taskId, {
    reconnectDelay: 5000,      // 5s
    maxReconnectDelay: 60000   // 60s
});
```

---

## 监控指标

### 服务端指标

```python
# 查看活跃连接数
from agentos.webui.sse.task_events import manager
print(f"Active connections: {len(manager.active_connections)}")
```

### 客户端指标

```javascript
// 获取统计信息
const stats = stream.getStats();
console.log('Stats:', stats);
// {
//   eventsReceived: 1234,
//   reconnects: 5,
//   errors: 2,
//   gapsDetected: 1,
//   gapsRecovered: 1
// }
```

---

## 安全建议

1. **认证**: 在生产环境添加 Bearer Token 认证
2. **HTTPS**: 使用 HTTPS 保护 SSE 连接
3. **CORS**: 配置 CORS 白名单
4. **速率限制**: 限制每个客户端的连接数

```python
# 示例: 添加认证中间件
from fastapi import Header, HTTPException

@router.get("/sse/tasks/{task_id}/events")
async def stream_task_events(
    task_id: str,
    authorization: str = Header(None)
):
    if not is_valid_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # ...
```

---

## 常见用例

### 用例 1: 任务进度实时监控

```javascript
const stream = new EventStreamService(taskId, {
    since_seq: 0,
    onEvent: (event) => {
        if (event.event_type === 'progress_update') {
            updateProgressBar(event.payload.progress);
        }
    }
});
stream.start();
```

### 用例 2: 工作项状态追踪

```javascript
const workItems = new Map();

const stream = new EventStreamService(taskId, {
    onEvent: (event) => {
        if (event.event_type === 'work_item_start') {
            workItems.set(event.span_id, 'running');
        } else if (event.event_type === 'work_item_complete') {
            workItems.set(event.span_id, 'completed');
        }
        renderWorkItems(workItems);
    }
});
```

### 用例 3: 断点续流（刷新页面后恢复）

```javascript
// 保存最新 seq 到 localStorage
const lastSeq = parseInt(localStorage.getItem('lastSeq') || '0');

const stream = new EventStreamService(taskId, {
    since_seq: lastSeq,
    onEvent: (event) => {
        localStorage.setItem('lastSeq', event.seq);
        // ... handle event
    }
});
```

---

## 资源链接

- **实现报告**: `PR_V3_IMPLEMENTATION_REPORT.md`
- **演示页面**: `http://localhost:8000/demo_sse_streaming.html`
- **测试脚本**: `test_sse_manual.py`
- **源码目录**: `agentos/webui/sse/`

---

## 联系和支持

如有问题，请查看：
1. 实现报告中的"故障排查"章节
2. 集成测试用例（示例代码）
3. 演示页面（交互式验证）

**状态**: ✅ 生产就绪
