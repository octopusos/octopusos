# AutoComm Health API 使用文档

## 端点信息

**路径**：`GET /api/autocomm`

**描述**：检查 AutoComm 子系统健康状态

**标签**：health

---

## 响应格式

### 成功响应（200 OK）

```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T12:22:09.856380Z",
  "components": {
    "adapter": {
      "status": "ok",
      "message": "CommunicationAdapter initialized successfully"
    },
    "policy": {
      "status": "ok",
      "enabled": true,
      "message": "AutoCommPolicy initialized (enabled=True)"
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `status` | string | 整体健康状态：`healthy` / `disabled` / `unhealthy` |
| `timestamp` | string | ISO 8601 时间戳（UTC时区，Z后缀） |
| `components` | object | 组件详细状态 |
| `components.adapter` | object | CommunicationAdapter 状态 |
| `components.adapter.status` | string | 组件状态：`ok` / `error` |
| `components.adapter.message` | string | 状态描述 |
| `components.policy` | object | AutoCommPolicy 状态 |
| `components.policy.status` | string | 组件状态：`ok` / `error` |
| `components.policy.enabled` | boolean? | Policy 启用状态（可为 null） |
| `components.policy.message` | string | 状态描述 |

### 状态枚举

#### Overall Status

| 值 | 含义 | 条件 |
|----|------|------|
| `healthy` | 健康 | 所有组件正常且 policy 启用 |
| `disabled` | 禁用 | 组件正常但 policy 未启用 |
| `unhealthy` | 不健康 | 任一组件初始化失败 |

#### Component Status

| 值 | 含义 |
|----|------|
| `ok` | 组件正常 |
| `error` | 组件故障 |

---

## 使用示例

### curl

```bash
# 基本请求
curl http://localhost:8000/api/autocomm

# 格式化输出
curl http://localhost:8000/api/autocomm | jq .

# 仅获取状态
curl -s http://localhost:8000/api/autocomm | jq -r '.status'
```

### Python

```python
import requests

# 请求健康状态
response = requests.get("http://localhost:8000/api/autocomm")
data = response.json()

# 检查状态
if data["status"] == "healthy":
    print("✅ AutoComm is healthy")
elif data["status"] == "disabled":
    print("⚠️  AutoComm policy is disabled")
else:
    print("❌ AutoComm is unhealthy")
    print("Details:", data)
```

### JavaScript/TypeScript

```typescript
// Fetch health status
const response = await fetch('/api/autocomm');
const health = await response.json();

// Check status
if (health.status === 'healthy') {
  console.log('✅ AutoComm is healthy');
} else if (health.status === 'disabled') {
  console.warn('⚠️  AutoComm policy is disabled');
} else {
  console.error('❌ AutoComm is unhealthy', health);
}
```

---

## 响应示例

### 场景 1：正常运行

```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T12:22:09.856380Z",
  "components": {
    "adapter": {
      "status": "ok",
      "message": "CommunicationAdapter initialized successfully"
    },
    "policy": {
      "status": "ok",
      "enabled": true,
      "message": "AutoCommPolicy initialized (enabled=True)"
    }
  }
}
```

### 场景 2：Policy 禁用

```json
{
  "status": "disabled",
  "timestamp": "2026-01-31T12:25:30.123456Z",
  "components": {
    "adapter": {
      "status": "ok",
      "message": "CommunicationAdapter initialized successfully"
    },
    "policy": {
      "status": "ok",
      "enabled": false,
      "message": "AutoCommPolicy initialized (enabled=False)"
    }
  }
}
```

### 场景 3：组件故障

```json
{
  "status": "unhealthy",
  "timestamp": "2026-01-31T12:30:45.789012Z",
  "components": {
    "adapter": {
      "status": "error",
      "message": "Failed to initialize: Connection refused"
    },
    "policy": {
      "status": "ok",
      "enabled": true,
      "message": "AutoCommPolicy initialized (enabled=True)"
    }
  }
}
```

### 场景 4：严重故障

```json
{
  "status": "unhealthy",
  "timestamp": "2026-01-31T12:35:15.345678Z",
  "error": "Module not found: agentos.core.chat.communication_adapter",
  "error_type": "ImportError"
}
```

---

## 监控集成

### Shell 脚本监控

```bash
#!/bin/bash
# autocomm_monitor.sh

URL="http://localhost:8000/api/autocomm"

while true; do
    STATUS=$(curl -s $URL | jq -r '.status')

    case $STATUS in
        "healthy")
            echo "✅ [$(date)] AutoComm is healthy"
            ;;
        "disabled")
            echo "⚠️  [$(date)] AutoComm policy is disabled"
            ;;
        *)
            echo "❌ [$(date)] AutoComm is unhealthy"
            curl -s $URL | jq .
            ;;
    esac

    sleep 30
done
```

### Prometheus Exporter 示例

```python
from prometheus_client import Gauge, start_http_server
import requests
import time

# Define metrics
autocomm_health = Gauge('autocomm_health_status', 'AutoComm health status (1=healthy, 0.5=disabled, 0=unhealthy)')
autocomm_adapter = Gauge('autocomm_adapter_status', 'Adapter status (1=ok, 0=error)')
autocomm_policy = Gauge('autocomm_policy_status', 'Policy status (1=ok, 0=error)')
autocomm_policy_enabled = Gauge('autocomm_policy_enabled', 'Policy enabled (1=true, 0=false)')

def check_health():
    """Check AutoComm health and update metrics"""
    try:
        response = requests.get('http://localhost:8000/api/autocomm', timeout=5)
        data = response.json()

        # Update overall status
        status_map = {'healthy': 1.0, 'disabled': 0.5, 'unhealthy': 0.0}
        autocomm_health.set(status_map.get(data['status'], 0.0))

        # Update component metrics
        components = data.get('components', {})

        adapter = components.get('adapter', {})
        autocomm_adapter.set(1.0 if adapter.get('status') == 'ok' else 0.0)

        policy = components.get('policy', {})
        autocomm_policy.set(1.0 if policy.get('status') == 'ok' else 0.0)
        autocomm_policy_enabled.set(1.0 if policy.get('enabled') else 0.0)

    except Exception as e:
        print(f"Error checking health: {e}")
        autocomm_health.set(0.0)

if __name__ == '__main__':
    # Start Prometheus metrics server
    start_http_server(9090)
    print("Prometheus exporter listening on :9090")

    # Check health every 30 seconds
    while True:
        check_health()
        time.sleep(30)
```

### Grafana 查询示例

```promql
# AutoComm Health Status
autocomm_health_status

# Adapter Uptime (last 1 hour)
avg_over_time(autocomm_adapter_status[1h])

# Policy Status
autocomm_policy_status

# Policy Enabled
autocomm_policy_enabled

# Alert: AutoComm Unhealthy
autocomm_health_status < 1
```

---

## 故障排查

### 问题：status = "unhealthy"

**可能原因**：
1. CommunicationAdapter 初始化失败
2. AutoCommPolicy 初始化失败
3. 依赖模块缺失

**排查步骤**：

1. 检查组件详情
```bash
curl -s http://localhost:8000/api/autocomm | jq '.components'
```

2. 查看错误消息
```bash
curl -s http://localhost:8000/api/autocomm | jq '.components.adapter.message'
curl -s http://localhost:8000/api/autocomm | jq '.components.policy.message'
```

3. 检查日志
```bash
# 查看 AgentOS 日志
tail -f /path/to/agentos.log | grep -i "autocomm\|communication"
```

### 问题：status = "disabled"

**原因**：AutoCommPolicy 未启用

**解决方法**：
1. 检查配置文件
2. 启用 AutoComm Policy
3. 重启服务

### 问题：端点不可访问（404）

**可能原因**：
1. 路由未注册
2. 服务未启动
3. URL 错误

**排查步骤**：

1. 确认服务运行
```bash
curl http://localhost:8000/api/health
```

2. 检查路由注册
```python
from agentos.webui.app import app
for route in app.routes:
    print(route.path)
```

3. 验证 URL 路径
```bash
# 正确路径
curl http://localhost:8000/api/autocomm

# 错误路径（会返回 404）
curl http://localhost:8000/autocomm
curl http://localhost:8000/api/health/autocomm
```

---

## 测试

### 运行验证脚本

```bash
# 完整验证测试（23 项检查）
python3 tests/webui/api/validate_autocomm_health.py
```

**预期输出**：
```
======================================================================
  Validation Summary
======================================================================
Tests Passed: 23/23
Success Rate: 100.0%

✅ All validations passed!
```

### 运行单元测试

```bash
# 运行所有 AutoComm health 测试
pytest tests/webui/api/test_health_autocomm.py -v

# 运行特定测试类
pytest tests/webui/api/test_health_autocomm.py::TestAutoCommHealthEndpoint -v

# 运行特定测试
pytest tests/webui/api/test_health_autocomm.py::TestAutoCommHealthEndpoint::test_autocomm_health_endpoint_registered -v
```

---

## 相关文档

- **完成报告**：`docs/P1_3_AUTOCOMM_HEALTH_COMPLETION_REPORT.md`
- **测试文件**：`tests/webui/api/test_health_autocomm.py`
- **验证脚本**：`tests/webui/api/validate_autocomm_health.py`
- **源代码**：`agentos/webui/api/health.py` (第 224-293 行)

---

**文档版本**：1.0
**最后更新**：2026-01-31
**维护者**：AgentOS Team
