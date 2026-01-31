# 网络模式快速参考

## 概述

网络模式控制 AgentOS CommunicationOS 的外部通信访问级别。

## 三种模式

| 模式 | 值 | 描述 | 允许的操作 |
|------|-----|------|-----------|
| 🔴 OFF | `off` | 完全禁用 | 无 |
| 🟡 READONLY | `readonly` | 只读访问 | fetch, search, get, read, query, list |
| 🟢 ON | `on` | 完全访问 | 所有操作 |

## API 端点

### 获取当前模式
```bash
GET /api/communication/mode
```

### 设置模式
```bash
PUT /api/communication/mode
Content-Type: application/json

{
  "mode": "readonly",
  "reason": "Optional reason",
  "updated_by": "Optional identifier"
}
```

### 获取历史
```bash
GET /api/communication/mode/history?limit=10
```

### 检查状态（包含模式）
```bash
GET /api/communication/status
```

## Python API

### 基本使用
```python
from agentos.core.communication.network_mode import NetworkMode, NetworkModeManager

# 创建管理器
manager = NetworkModeManager()

# 获取当前模式
current_mode = manager.get_mode()
print(f"Current mode: {current_mode.value}")

# 设置模式
result = manager.set_mode(
    NetworkMode.READONLY,
    updated_by="admin",
    reason="Maintenance"
)

# 检查操作是否允许
is_allowed, reason = manager.is_operation_allowed("search")
if not is_allowed:
    print(f"Blocked: {reason}")
```

### 检查模式信息
```python
# 获取详细信息
info = manager.get_mode_info()
print(f"Current: {info['current_state']['mode']}")
print(f"Available: {info['available_modes']}")
print(f"History: {len(info['recent_history'])} changes")

# 获取历史记录
history = manager.get_history(limit=10)
for record in history:
    print(f"{record['previous_mode']} → {record['new_mode']}")
```

### 在 CommunicationService 中使用
```python
from agentos.core.communication.service import CommunicationService
from agentos.core.communication.network_mode import NetworkModeManager

# 创建服务（会自动包含 network_mode_manager）
service = CommunicationService()

# 模式检查会自动在 execute() 中执行
response = await service.execute(
    connector_type=ConnectorType.WEB_SEARCH,
    operation="search",
    params={"query": "test"},
)

# 如果被阻止，response.status == RequestStatus.DENIED
# 错误消息格式：NETWORK_MODE_BLOCKED: {reason}
```

## 操作分类

### 只读操作（READONLY 模式下允许）
- `fetch` - 获取内容
- `search` - 搜索
- `get` - 获取资源
- `read` - 读取数据
- `query` - 查询
- `list` - 列出项目

### 写入操作（READONLY 模式下禁止）
- `send` - 发送数据
- `post` - 发布内容
- `put` - 更新资源
- `delete` - 删除资源
- `create` - 创建资源
- `update` - 更新数据
- `write` - 写入数据
- `publish` - 发布内容

## 常见场景

### 场景 1: 维护窗口
```bash
# 开始维护：切换到只读
curl -X PUT http://localhost:8080/api/communication/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "readonly", "reason": "Maintenance window", "updated_by": "ops"}'

# 维护完成：恢复正常
curl -X PUT http://localhost:8080/api/communication/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "on", "reason": "Maintenance completed", "updated_by": "ops"}'
```

### 场景 2: 紧急关闭
```bash
# 完全禁用外部通信
curl -X PUT http://localhost:8080/api/communication/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "off", "reason": "Security incident", "updated_by": "security"}'
```

### 场景 3: 审计历史
```bash
# 查看最近的模式变更
curl "http://localhost:8080/api/communication/mode/history?limit=20"
```

## 数据库位置

默认：`~/.agentos/communication.db`

表：
- `network_mode_state` - 当前状态（单行）
- `network_mode_history` - 变更历史

## 日志

网络模式操作会记录到应用日志：

```
INFO: Network mode changed: on -> readonly (by: admin, reason: Maintenance)
WARNING: Operation 'send' blocked by network mode (readonly): ...
```

## 错误处理

### 无效模式
```json
{
  "ok": false,
  "error": "Invalid network mode: invalid",
  "hint": "Valid modes: off, readonly, on"
}
```

### 操作被阻止
CommunicationService 返回：
```json
{
  "request_id": "comm-xxx",
  "status": "denied",
  "error": "NETWORK_MODE_BLOCKED: Network mode is READONLY - write operation 'send' blocked"
}
```

## 测试

```bash
# 运行单元测试
python3 test_network_mode.py

# 运行集成测试
python3 test_network_mode_integration.py
```

## 相关文档

- [完整实施总结](./NETWORK_MODE_IMPLEMENTATION_SUMMARY.md)
- [CommunicationOS 架构](./communication/README.md)

## 最佳实践

1. **设置原因** - 总是提供 `reason` 字段，方便审计
2. **标识变更者** - 使用 `updated_by` 标识谁做了变更
3. **监控历史** - 定期检查模式变更历史
4. **渐进恢复** - 从 OFF → READONLY → ON 逐步恢复
5. **测试模式** - 在测试环境中验证模式行为

## 性能提示

- 当前模式缓存在内存中，查询非常快
- 历史查询有索引支持
- 模式检查在请求处理早期执行，避免浪费资源
