# 网络模式管理

## 快速开始

网络模式功能允许您控制 AgentOS 的外部通信访问级别。

### 三种模式

- **OFF** 🔴 - 完全禁用所有外部通信
- **READONLY** 🟡 - 仅允许读取操作（fetch, search）
- **ON** 🟢 - 完全访问（默认）

### 基本使用

```python
from agentos.core.communication.network_mode import NetworkMode, NetworkModeManager

# 创建管理器
manager = NetworkModeManager()

# 获取当前模式
mode = manager.get_mode()
print(f"Current: {mode.value}")

# 设置模式
manager.set_mode(
    NetworkMode.READONLY,
    updated_by="admin",
    reason="Maintenance"
)
```

### REST API

```bash
# 获取当前模式
curl http://localhost:8080/api/communication/mode

# 设置为只读模式
curl -X PUT http://localhost:8080/api/communication/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "readonly", "reason": "Maintenance window"}'

# 查看历史
curl "http://localhost:8080/api/communication/mode/history?limit=10"
```

## 文档

- [快速参考](../NETWORK_MODE_QUICK_REFERENCE.md) - API 和使用指南
- [实施总结](../NETWORK_MODE_IMPLEMENTATION_SUMMARY.md) - 完整技术文档
- [实施报告](../../NETWORK_MODE_IMPLEMENTATION_REPORT.md) - 项目交付报告

## 示例

运行示例代码：
```bash
python3 examples/network_mode_usage.py
```

## 测试

运行测试：
```bash
# 单元测试
python3 test_network_mode.py

# 集成测试
python3 test_network_mode_integration.py
```

## 常见场景

### 场景 1: 维护窗口
```bash
# 开始维护
curl -X PUT .../mode -d '{"mode": "readonly", "reason": "Maintenance"}'

# 完成维护
curl -X PUT .../mode -d '{"mode": "on", "reason": "Maintenance completed"}'
```

### 场景 2: 紧急关闭
```bash
curl -X PUT .../mode -d '{"mode": "off", "reason": "Security incident"}'
```

### 场景 3: 审计检查
```bash
curl "http://localhost:8080/api/communication/mode/history?limit=20"
```

## 支持

如有问题，请查看完整文档或提交 issue。
