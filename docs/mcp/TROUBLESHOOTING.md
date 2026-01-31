# MCP Troubleshooting Guide

本指南帮助您诊断和解决 AgentOS MCP 集成中的常见问题。

## 目录

1. [快速诊断](#快速诊断)
2. [连接问题](#连接问题)
3. [工具调用问题](#工具调用问题)
4. [权限和策略问题](#权限和策略问题)
5. [性能问题](#性能问题)
6. [日志查看](#日志查看)
7. [常见错误代码](#常见错误代码)

---

## 快速诊断

### 诊断检查清单

运行以下命令进行快速诊断:

```bash
# 1. 检查配置文件
cat ~/.agentos/mcp_servers.yaml

# 2. 检查 Python 环境
python3 --version  # 应为 3.9+

# 3. 检查 Node.js (如使用 Node MCP servers)
node --version     # 应为 18+

# 4. 测试 MCP server 手动启动
node servers/echo-math-mcp/index.js
# (输入 JSON-RPC 请求测试)

# 5. 检查 AgentOS 日志
tail -f ~/.agentos/webui.log | grep -i mcp
```

### 健康检查 API

```bash
# 检查 MCP 系统健康状态
curl http://localhost:8000/api/mcp/health

# 预期输出:
# {
#   "status": "healthy",  # 或 "degraded", "unhealthy"
#   "servers": {
#     "echo-math": {
#       "status": "connected",
#       "health": "healthy",
#       "last_seen": "2026-01-30T23:00:00Z"
#     }
#   }
# }
```

---

## 连接问题

### 问题 1: MCP Server 连接超时

**症状**:
```
ERROR: Request timed out: tools/list (id=3)
ERROR: Failed to list tools: Request timed out after 5000ms: tools/list
```

**可能原因**:

#### 1.1 Node.js 未安装或版本不兼容

**检查**:
```bash
node --version
```

**解决**:
```bash
# macOS
brew install node

# Ubuntu/Debian
sudo apt install nodejs npm

# 验证
node --version  # 应显示 v18.0.0 或更高
```

---

#### 1.2 MCP Server 脚本路径错误

**检查配置**:
```yaml
# ~/.agentos/mcp_servers.yaml
mcp_servers:
  - id: echo-math
    command: ["node", "/incorrect/path/index.js"]  # ❌ 路径错误
```

**解决**:
```yaml
# 使用绝对路径
mcp_servers:
  - id: echo-math
    command: ["node", "/Users/you/AgentOS/servers/echo-math-mcp/index.js"]
```

**验证路径**:
```bash
# 检查文件是否存在
ls -la /Users/you/AgentOS/servers/echo-math-mcp/index.js

# 手动运行测试
node /Users/you/AgentOS/servers/echo-math-mcp/index.js
# (应保持运行,等待 JSON-RPC 输入)
```

---

#### 1.3 MCP Server 依赖缺失

**检查**:
```bash
cd servers/echo-math-mcp/
cat package.json  # 查看依赖
npm list         # 检查已安装的依赖
```

**解决**:
```bash
cd servers/echo-math-mcp/
npm install  # 安装依赖
```

---

#### 1.4 MCP Server 启动失败

**诊断**:
```bash
# 手动启动 server 并查看错误
node servers/echo-math-mcp/index.js 2>&1

# 检查是否有语法错误或运行时错误
```

**常见错误**:
```javascript
// 语法错误
SyntaxError: Unexpected token

// 模块未找到
Error: Cannot find module 'readline'

// 权限问题
Error: EACCES: permission denied
```

**解决**:
- 语法错误: 检查 MCP server 代码
- 模块未找到: `npm install`
- 权限问题: `chmod +x servers/echo-math-mcp/index.js`

---

#### 1.5 超时设置过短

**检查配置**:
```yaml
mcp_servers:
  - id: echo-math
    timeout_ms: 1000  # ❌ 太短,可能导致超时
```

**解决**:
```yaml
mcp_servers:
  - id: echo-math
    timeout_ms: 5000   # ✅ 简单操作
  - id: database
    timeout_ms: 30000  # ✅ 数据库查询
  - id: api-client
    timeout_ms: 60000  # ✅ 外部 API 调用
```

---

### 问题 2: MCP Server 断开连接

**症状**:
```
WARNING: MCP server disconnected: echo-math
ERROR: Server not connected: echo-math
```

**可能原因**:

#### 2.1 Server 进程崩溃

**检查日志**:
```bash
tail -f ~/.agentos/webui.log | grep -i 'echo-math'
```

**查找崩溃原因**:
- 内存不足
- 未捕获的异常
- 资源泄漏

**解决**:
- 修复 server 代码bug
- 增加内存限制
- 添加错误处理

---

#### 2.2 stdio 管道损坏

**症状**:
- Server 进程仍在运行
- 但无法通信

**诊断**:
```bash
# 检查进程
ps aux | grep node | grep echo-math

# 如果进程存在但无响应,可能是管道问题
```

**解决**:
```bash
# 强制重启 server
pkill -f echo-math
# AgentOS 会自动重新连接
```

---

### 问题 3: 配置文件不存在或格式错误

**症状**:
```
WARNING: MCP config file not found: ~/.agentos/mcp_servers.yaml
ERROR: No 'mcp_servers' section found in config
```

**解决**:

```bash
# 1. 创建配置目录
mkdir -p ~/.agentos

# 2. 复制示例配置
cp examples/mcp_servers.yaml.example ~/.agentos/mcp_servers.yaml

# 3. 编辑配置
vim ~/.agentos/mcp_servers.yaml

# 4. 验证 YAML 格式
python3 -c "import yaml; yaml.safe_load(open('~/.agentos/mcp_servers.yaml'))"
```

**正确格式**:
```yaml
# ✅ 正确
mcp_servers:
  - id: server1
    enabled: true
    transport: stdio
    command: ["node", "server.js"]

# ❌ 错误 (缩进问题)
mcp_servers:
- id: server1
  enabled: true
```

---

## 工具调用问题

### 问题 4: 工具未找到

**症状**:
```
ToolNotFoundError: Tool not found: mcp:echo-math:echo
```

**可能原因**:

#### 4.1 MCP Server 未连接

**诊断**:
```python
# Python 测试
from agentos.core.capabilities.registry import CapabilityRegistry
registry = CapabilityRegistry(...)
tools = registry.list_tools(source_types=['mcp'])
print(f"Found {len(tools)} MCP tools")
```

**解决**: 先解决连接问题 (见上文)

---

#### 4.2 工具被过滤

**检查配置**:
```yaml
mcp_servers:
  - id: echo-math
    allow_tools: ["sum", "multiply"]  # ❌ echo 工具被过滤
```

**解决**:
```yaml
mcp_servers:
  - id: echo-math
    allow_tools: []  # ✅ 允许所有工具
    # 或
    allow_tools: ["echo", "sum", "multiply"]  # ✅ 显式包含
```

---

#### 4.3 工具 ID 格式错误

**错误示例**:
```python
# ❌ 错误
router.invoke_tool("echo-math:echo", ...)

# ✅ 正确
router.invoke_tool("mcp:echo-math:echo", ...)
```

**工具 ID 格式**: `{source}:{server_id}:{tool_name}`

---

### 问题 5: 工具调用返回错误

**症状**:
```
ToolResult(success=False, error="Unknown tool: echo")
```

**诊断步骤**:

```bash
# 1. 检查 server 是否返回该工具
curl http://localhost:8000/api/mcp/tools | jq '.tools[] | select(.tool_id | contains("echo"))'

# 2. 手动测试 server
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | node servers/echo-math-mcp/index.js

# 3. 检查工具名称拼写
```

---

### 问题 6: 工具调用参数错误

**症状**:
```
MCPError: Invalid parameters: Missing required field 'text'
```

**诊断**:
```python
# 检查工具 schema
tool = registry.get_tool("mcp:echo-math:echo")
print(tool.input_schema)
# {
#   "type": "object",
#   "properties": {"text": {"type": "string"}},
#   "required": ["text"]  # ← text 是必需的
# }
```

**解决**:
```python
# ❌ 错误
router.invoke_tool("mcp:echo-math:echo", {})

# ✅ 正确
router.invoke_tool("mcp:echo-math:echo", {"text": "hello"})
```

---

## 权限和策略问题

### 问题 7: Planning 模式被阻止

**症状**:
```
PolicyViolation: Planning mode cannot use tools with side effects
```

**原因**: 工具有副作用标签,但上下文是 planning 模式

**诊断**:
```python
tool = registry.get_tool("mcp:database:delete")
print(tool.side_effect_tags)  # ['database.delete']

ctx = InvocationContext(mode='planning', ...)
# ❌ Planning 模式不能调用有副作用的工具
```

**解决**:

**方案 1**: 切换到 execution 模式
```python
ctx = InvocationContext(mode='execution', ...)
```

**方案 2**: 使用只读工具
```python
tool = registry.get_tool("mcp:database:query")  # 没有副作用
```

---

### 问题 8: spec_frozen 要求

**症状**:
```
PolicyViolation: Execution mode requires spec_frozen=True
```

**原因**: 高风险工具需要 spec_frozen

**解决**:
```python
ctx = InvocationContext(
    mode='execution',
    spec_frozen=True,        # ✅ 添加
    spec_hash='abc123...',   # ✅ 添加
    ...
)
```

---

### 问题 9: project_id 要求

**症状**:
```
PolicyViolation: Tool requires project_id
```

**原因**: 中等或更高风险工具需要 project_id

**解决**:
```python
ctx = InvocationContext(
    project_id='proj_123',   # ✅ 添加
    ...
)
```

---

### 问题 10: admin_token 要求

**症状**:
```
PolicyViolation: Tool requires admin_token
```

**原因**: Critical 工具需要 admin token

**解决**:

**方案 1**: 提供 admin token
```python
ctx = InvocationContext(
    admin_token='secret_admin_token_xyz',  # ✅ 添加
    ...
)
```

**方案 2**: 降低工具风险级别 (如果合理)
```python
# 在 MCPAdapter 中自定义推断逻辑
```

**方案 3**: 使用低风险替代工具

---

### 问题 11: 副作用被黑名单

**症状**:
```
PolicyViolation: Side effect 'payments' is blacklisted
```

**原因**: 策略黑名单包含该副作用

**检查**:
```python
tool = registry.get_tool("mcp:payment:charge")
print(tool.side_effect_tags)  # ['payments']

# 检查策略
print(ctx.policy_blacklist)  # ['payments']
```

**解决**:

**方案 1**: 移除黑名单 (如果合理)
```python
ctx = InvocationContext(
    policy_blacklist=[],  # 或不包含 'payments'
    ...
)
```

**方案 2**: 配置 MCP server 过滤
```yaml
mcp_servers:
  - id: payment-server
    deny_side_effect_tags: []  # 移除黑名单
```

---

## 性能问题

### 问题 12: 工具调用慢

**症状**: 工具调用需要 > 5 秒

**诊断**:

```python
import time

start = time.time()
result = await router.invoke_tool("mcp:slow:operation", ...)
duration = time.time() - start
print(f"Duration: {duration}s")
```

**可能原因**:

#### 12.1 MCP Server 响应慢

**检查**:
```bash
# 直接测试 server 响应时间
time echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"slow"},"id":1}' | node server.js
```

**解决**:
- 优化 server 代码
- 增加超时时间
- 使用异步处理

---

#### 12.2 网络延迟 (如 HTTP 工具)

**检查**:
```python
tool = registry.get_tool("mcp:http:fetch")
print(tool.timeout_ms)  # 检查超时设置
```

**解决**:
```yaml
mcp_servers:
  - id: http-fetch
    timeout_ms: 60000  # 增加超时
```

---

#### 12.3 Registry 缓存未命中

**检查**:
```python
# 第一次调用慢 (缓存未命中)
tools = registry.list_tools(source_types=['mcp'])  # ~500ms

# 第二次调用快 (缓存命中)
tools = registry.list_tools(source_types=['mcp'])  # ~5ms
```

**解决**: 预热缓存
```python
# 启动时预加载
await registry.refresh_mcp_servers()
```

---

### 问题 13: 内存占用高

**症状**: AgentOS 进程内存 > 500MB

**诊断**:
```python
import tracemalloc
tracemalloc.start()

# 运行操作
registry = CapabilityRegistry(...)
await registry.refresh_mcp_servers()

current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.2f}MB")
print(f"Peak: {peak / 1024 / 1024:.2f}MB")
```

**可能原因**:

#### 13.1 过多 MCP Servers

**解决**: 禁用不需要的 servers
```yaml
mcp_servers:
  - id: unused-server
    enabled: false  # ✅ 禁用
```

---

#### 13.2 缓存过大

**解决**: 调整缓存 TTL
```python
# registry.py
CACHE_TTL = 300  # 默认 5 分钟
# 改为更短
CACHE_TTL = 60   # 1 分钟
```

---

## 日志查看

### AgentOS 主日志

```bash
# 实时查看
tail -f ~/.agentos/webui.log

# 过滤 MCP 相关
tail -f ~/.agentos/webui.log | grep -i mcp

# 查看错误
tail -f ~/.agentos/webui.log | grep -i error | grep -i mcp
```

### MCP Client 日志

```python
import logging

# 启用 MCP 客户端详细日志
logging.getLogger('agentos.core.mcp.client').setLevel(logging.DEBUG)
```

**日志示例**:
```
INFO  MCPClient: Connected to server: echo-math
DEBUG MCPClient: Sending request: tools/list (id=1)
DEBUG MCPClient: Received response: 200 OK
ERROR MCPClient: Request timed out: tools/list (id=3)
```

### 审计日志

```sql
-- 查看 MCP 工具调用历史
SELECT
  event_type,
  context->>'tool_id' as tool_id,
  context->>'success' as success,
  context->>'error' as error,
  created_at
FROM task_audits
WHERE context->>'source_type' = 'mcp'
ORDER BY created_at DESC
LIMIT 20;
```

---

## 常见错误代码

### MCP 协议错误

| 代码 | 含义 | 解决方法 |
|------|------|----------|
| -32700 | Parse error | 检查 JSON 格式 |
| -32600 | Invalid Request | 检查请求格式 |
| -32601 | Method not found | 检查 MCP server 实现 |
| -32602 | Invalid params | 检查参数格式和必需字段 |
| -32603 | Internal error | 查看 server 日志 |

### AgentOS 错误

| 错误类型 | 含义 | 解决方法 |
|---------|------|----------|
| `MCPTimeoutError` | 请求超时 | 增加 timeout_ms 或优化 server |
| `MCPConnectionError` | 连接失败 | 检查 server 进程和配置 |
| `MCPClientError` | 客户端错误 | 查看详细错误信息 |
| `ToolNotFoundError` | 工具未找到 | 检查工具 ID 和 server 连接 |
| `PolicyViolationError` | 策略违规 | 检查上下文和工具风险级别 |

---

## 调试技巧

### 1. 启用详细日志

```python
import logging

# 所有 MCP 相关日志
logging.getLogger('agentos.core.mcp').setLevel(logging.DEBUG)

# 策略引擎日志
logging.getLogger('agentos.core.capabilities.policy').setLevel(logging.DEBUG)

# Router 日志
logging.getLogger('agentos.core.capabilities.router').setLevel(logging.DEBUG)
```

### 2. 使用 Python Debugger

```python
# 在关键位置设置断点
import pdb; pdb.set_trace()

# 或使用 IDE 断点功能
result = await router.invoke_tool(...)  # ← 设置断点
```

### 3. 手动测试 MCP Server

```bash
# 启动 server
node servers/echo-math-mcp/index.js

# 发送测试请求 (另一个终端)
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | nc localhost stdin

# 或使用 Python 脚本
python3 scripts/test_mcp_server.py
```

### 4. 检查 Registry 状态

```python
from agentos.core.capabilities.registry import CapabilityRegistry

registry = CapabilityRegistry(...)

# 列出所有 MCP 工具
mcp_tools = registry.list_tools(source_types=['mcp'])
for tool in mcp_tools:
    print(f"{tool.tool_id}: {tool.name} (risk={tool.risk_level})")

# 检查特定工具
tool = registry.get_tool("mcp:echo-math:echo")
if tool:
    print(f"Found: {tool.name}")
else:
    print("Not found!")
```

---

## 获取帮助

### 内部资源

- [MCP 架构文档](./ARCHITECTURE.md)
- [安全治理文档](../capabilities/SECURITY_GOVERNANCE.md)
- [MCP API 参考](../api/MCP_API.md)

### 社区支持

- GitHub Issues: https://github.com/your-org/agentos/issues
- Slack Channel: #mcp-support
- 文档: https://docs.agentos.dev/mcp

### 报告问题

报告问题时,请包含:

1. **错误信息**: 完整的错误堆栈
2. **配置文件**: `~/.agentos/mcp_servers.yaml`
3. **日志片段**: 最近的日志 (50-100行)
4. **重现步骤**: 如何重现问题
5. **环境信息**:
   ```bash
   python3 --version
   node --version
   uname -a
   ```

---

## 附录: 健康检查脚本

创建 `scripts/mcp_health_check.py`:

```python
#!/usr/bin/env python3
"""MCP Health Check Script"""

import asyncio
import sys
from agentos.core.mcp.client import MCPClient
from agentos.core.mcp.config import MCPConfigManager

async def main():
    config_manager = MCPConfigManager()
    servers = config_manager.get_enabled_servers()

    print(f"Checking {len(servers)} MCP servers...\n")

    for server_config in servers:
        print(f"Server: {server_config.id}")
        print(f"  Command: {' '.join(server_config.command)}")

        client = MCPClient(server_config)

        try:
            # 连接
            connected = await client.connect()
            if not connected:
                print(f"  Status: ❌ FAILED TO CONNECT")
                continue

            print(f"  Status: ✅ CONNECTED")

            # 列出工具
            tools = await client.list_tools()
            print(f"  Tools: {len(tools)} available")
            for tool in tools[:3]:  # 显示前3个
                print(f"    - {tool.name}")

            # 健康检查
            health = await client.health_check()
            print(f"  Health: {health}")

            await client.disconnect()

        except Exception as e:
            print(f"  Status: ❌ ERROR")
            print(f"  Error: {e}")

        print()

if __name__ == "__main__":
    asyncio.run(main())
```

使用:
```bash
python3 scripts/mcp_health_check.py
```

---

**文档版本**: 1.0
**最后更新**: 2026-01-30
**维护者**: AgentOS Core Team
