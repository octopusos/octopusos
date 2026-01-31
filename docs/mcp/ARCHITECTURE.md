# MCP Architecture in AgentOS

## Overview

AgentOS 的 MCP (Model Context Protocol) 集成提供了一个统一的、安全的、可审计的方式来集成外部工具服务器。本文档描述了 MCP 在 AgentOS 中的架构设计、核心组件以及数据流。

## 定位

### MCP 在 AgentOS 中的角色

MCP 是 AgentOS 的三大工具来源之一:

```
AgentOS Tool Ecosystem
├── 1. Extension Tools (本地扩展)
│   ├── 通过 Extension 系统管理
│   ├── Python/Node.js 插件
│   └── 示例: Postman, GitHub, Slack
│
├── 2. MCP Tools (外部 MCP 服务器)
│   ├── 通过 MCP Client 连接
│   ├── Stdio 进程通信
│   └── 示例: echo-math, filesystem, database
│
└── 3. Built-in Tools (内置工具)
    ├── AgentOS 核心功能
    └── 示例: file_read, bash_exec
```

### 为什么需要 MCP?

1. **标准化**: MCP 是业界标准协议,易于集成第三方工具
2. **隔离性**: MCP 服务器独立进程,故障隔离
3. **扩展性**: 社区可以贡献 MCP 服务器,无需修改 AgentOS
4. **安全性**: 统一的安全闸门和审计机制

---

## 架构图

### 高层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         AgentOS Core                             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Unified Capability Layer                     │   │
│  │                                                            │   │
│  │  ┌────────────┐     ┌──────────────┐    ┌─────────────┐  │   │
│  │  │  Registry  │────▶│  Router      │───▶│   Policy    │  │   │
│  │  │            │     │              │    │   Engine    │  │   │
│  │  │ - list()   │     │ - invoke()   │    │             │  │   │
│  │  │ - get()    │     │ - dispatch() │    │ - check()   │  │   │
│  │  └────────────┘     └──────────────┘    └─────────────┘  │   │
│  │         │                   │                    │         │   │
│  └─────────┼───────────────────┼────────────────────┼─────────┘   │
│            │                   │                    │             │
│            ▼                   ▼                    ▼             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               Tool Sources Integration                   │    │
│  │                                                           │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │    │
│  │  │  Extension  │  │  MCP Adapter │  │  Built-in      │  │    │
│  │  │  Adapter    │  │              │  │  Tools         │  │    │
│  │  └─────────────┘  └──────┬───────┘  └────────────────┘  │    │
│  │                          │                               │    │
│  └──────────────────────────┼───────────────────────────────┘    │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   MCP Client     │
                    │                  │
                    │  - connect()     │
                    │  - list_tools()  │
                    │  - call_tool()   │
                    │  - health_check()│
                    └─────────┬────────┘
                              │ stdio
                              ▼
              ┌───────────────────────────────┐
              │    MCP Server Processes       │
              │                               │
              │  ┌──────────┐  ┌───────────┐  │
              │  │echo-math │  │filesystem │  │
              │  └──────────┘  └───────────┘  │
              │  ┌──────────┐  ┌───────────┐  │
              │  │database  │  │http-fetch │  │
              │  └──────────┘  └───────────┘  │
              └───────────────────────────────┘
```

### 详细组件架构

```
┌────────────────────────────────────────────────────────────────────┐
│                        MCP Integration Layer                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    CapabilityRegistry                         │  │
│  │                                                                │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Extension │  │   MCP    │  │ Built-in │  │  Cache   │     │  │
│  │  │  Tools   │  │  Tools   │  │  Tools   │  │          │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │                                                                │  │
│  │  API:                                                          │  │
│  │  - list_tools(source_types=['mcp', 'extension', 'builtin'])   │  │
│  │  - get_tool(tool_id) -> ToolDescriptor                        │  │
│  │  - refresh_mcp_servers() -> int                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      ToolRouter                               │  │
│  │                                                                │  │
│  │  ┌────────────────────┐           ┌──────────────────────┐   │  │
│  │  │  Policy Gates      │           │  Audit Logger        │   │  │
│  │  │  (6 layers)        │           │                      │   │  │
│  │  │                    │           │  - tool_invocation_* │   │  │
│  │  │  1. DisabledTool   │──────────▶│  - policy_decision   │   │  │
│  │  │  2. ModeGate       │           │  - policy_violation  │   │  │
│  │  │  3. SpecFrozenGate │           └──────────────────────┘   │  │
│  │  │  4. ProjectBinding │                                       │  │
│  │  │  5. PolicyGate     │                                       │  │
│  │  │  6. AdminTokenGate │                                       │  │
│  │  └────────────────────┘                                       │  │
│  │                                                                │  │
│  │  API:                                                          │  │
│  │  - invoke_tool(tool_id, args, ctx) -> ToolResult              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      MCPAdapter                               │  │
│  │                                                                │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  MCP Tool → ToolDescriptor Mapping                     │  │  │
│  │  │                                                          │  │  │
│  │  │  - mcp_tool_to_descriptor()                            │  │  │
│  │  │  - infer_risk_level()       (keywords → RiskLevel)     │  │  │
│  │  │  - infer_side_effects()     (keywords → tags)          │  │  │
│  │  │  - mcp_result_to_tool_result()                         │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      MCPClient                                │  │
│  │                                                                │  │
│  │  ┌────────────┐         ┌────────────┐       ┌───────────┐   │  │
│  │  │ Connection │────────▶│ JSON-RPC   │──────▶│  Process  │   │  │
│  │  │ Manager    │         │ Protocol   │       │  Manager  │   │  │
│  │  └────────────┘         └────────────┘       └───────────┘   │  │
│  │                                                                │  │
│  │  Methods:                                                      │  │
│  │  - connect(server_id) -> bool                                 │  │
│  │  - list_tools() -> List[MCPTool]                              │  │
│  │  - call_tool(name, args) -> MCPResult                         │  │
│  │  - health_check() -> HealthStatus                             │  │
│  │  - disconnect()                                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      MCPConfigManager                         │  │
│  │                                                                │  │
│  │  Config File: ~/.agentos/mcp_servers.yaml                     │  │
│  │                                                                │  │
│  │  - load_config() -> List[MCPServerConfig]                     │  │
│  │  - get_enabled_servers() -> List[MCPServerConfig]             │  │
│  │  - is_tool_allowed(server_id, tool) -> bool                   │  │
│  │  - is_side_effect_denied(server_id, effects) -> bool          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 核心组件说明

### 1. MCPClient (agentos/core/mcp/client.py)

**职责**: MCP 协议的 Python 客户端实现

**核心功能**:
- 启动和管理 MCP server 子进程
- 通过 stdio 进行 JSON-RPC 通信
- 实现 MCP 协议方法 (initialize, tools/list, tools/call)
- 处理超时和错误
- 健康检查和监控

**关键方法**:
```python
class MCPClient:
    async def connect(self) -> bool
    async def list_tools(self) -> List[MCPTool]
    async def call_tool(self, name: str, arguments: Dict) -> MCPResult
    async def health_check(self) -> HealthStatus
    async def disconnect(self)
```

**通信协议**:
```
AgentOS                   MCP Server
   │                           │
   ├──── initialize() ────────▶│
   │◀──── capabilities ────────┤
   │                           │
   ├──── tools/list ──────────▶│
   │◀──── [tools] ─────────────┤
   │                           │
   ├──── tools/call ──────────▶│
   │◀──── result ──────────────┤
   │                           │
```

---

### 2. MCPAdapter (agentos/core/mcp/adapter.py)

**职责**: 将 MCP 工具适配为 AgentOS ToolDescriptor

**核心功能**:
- MCP Tool → ToolDescriptor 转换
- 风险级别推断 (基于关键词)
- 副作用标签推断
- 结果格式转换

**风险级别推断规则**:
```python
CRITICAL_KEYWORDS = ['delete', 'drop', 'destroy', 'payment']
HIGH_KEYWORDS = ['write', 'update', 'modify', 'create']
MEDIUM_KEYWORDS = ['network', 'fetch', 'http', 'api']
LOW_KEYWORDS = ['read', 'get', 'list', 'search', 'echo']
```

**副作用推断规则**:
```python
SIDE_EFFECT_MAPPING = {
    'write': ['fs.write'],
    'delete': ['fs.delete'],
    'network': ['network.http'],
    'payment': ['payments'],
    'execute': ['system.exec'],
    ...
}
```

---

### 3. CapabilityRegistry (agentos/core/capabilities/registry.py)

**职责**: 统一的工具注册中心

**核心功能**:
- 聚合三种来源的工具 (Extension, MCP, Built-in)
- 提供统一的查询接口
- 缓存和性能优化
- MCP server 刷新管理

**关键方法**:
```python
class CapabilityRegistry:
    def list_tools(
        self,
        source_types: Optional[List[ToolSource]] = None,
        risk_levels: Optional[List[RiskLevel]] = None,
        side_effect_tags: Optional[List[str]] = None
    ) -> List[ToolDescriptor]

    def get_tool(self, tool_id: str) -> Optional[ToolDescriptor]

    async def refresh_mcp_servers(self) -> int
```

**工具 ID 格式**:
```
Extension: ext:{extension_id}:{capability_id}
MCP:       mcp:{server_id}:{tool_name}
Built-in:  builtin:{tool_name}
```

---

### 4. ToolRouter (agentos/core/capabilities/router.py)

**职责**: 工具调用路由和执行

**核心功能**:
- 根据 tool_id 路由到正确的执行器
- 执行 6 层安全闸门检查
- 审计日志记录
- 错误处理和恢复

**调用流程**:
```python
async def invoke_tool(tool_id, args, ctx) -> ToolResult:
    # 1. 获取工具描述符
    tool = registry.get_tool(tool_id)

    # 2. 执行安全闸门检查
    decision = policy_engine.check(tool, ctx)
    if not decision.allowed:
        return ToolResult(error=decision.reason)

    # 3. 路由到执行器
    if tool.source_type == 'mcp':
        result = await mcp_client.call_tool(...)
    elif tool.source_type == 'extension':
        result = await extension_executor.execute(...)

    # 4. 审计日志
    await audit_logger.log_invocation_end(...)

    return result
```

---

### 5. PolicyEngine (agentos/core/capabilities/policy.py)

**职责**: 6 层安全闸门实现

**闸门列表**:

```python
class ToolPolicyEngine:
    def check(self, tool: ToolDescriptor, ctx: InvocationContext) -> PolicyDecision:
        # Gate 1: 禁用工具检查
        if not tool.enabled:
            return DENIED("Tool is disabled")

        # Gate 2: 模式检查 (Planning vs Execution)
        if ctx.mode == 'planning' and tool.side_effect_tags:
            return DENIED("Planning mode cannot use tools with side effects")

        # Gate 3: Spec Frozen 检查
        if ctx.mode == 'execution' and tool.risk_level >= HIGH:
            if not ctx.spec_frozen or not ctx.spec_hash:
                return DENIED("Execution mode requires spec_frozen=True")

        # Gate 4: Project Binding 检查
        if tool.risk_level >= MEDIUM and not ctx.project_id:
            return DENIED("Tool requires project_id")

        # Gate 5: Policy 黑名单检查
        if any(tag in ctx.policy_blacklist for tag in tool.side_effect_tags):
            return DENIED(f"Side effect {tag} is blacklisted")

        # Gate 6: Admin Token 检查
        if tool.requires_admin_token and not ctx.admin_token:
            return DENIED("Tool requires admin_token")

        return ALLOWED()
```

**闸门优先级**: 按顺序执行,第一个拒绝立即返回。

---

### 6. MCPConfigManager (agentos/core/mcp/config.py)

**职责**: MCP 服务器配置管理

**配置文件位置**: `~/.agentos/mcp_servers.yaml`

**配置格式**:
```yaml
mcp_servers:
  - id: echo-math
    enabled: true
    transport: stdio
    command: ["node", "servers/echo-math/index.js"]
    allow_tools: []  # 空 = 允许所有
    deny_side_effect_tags: []
    timeout_ms: 5000
    env:
      NODE_ENV: "production"
```

**验证规则**:
- `transport` 必须是 "stdio"
- `command` 不能为空
- `timeout_ms` 必须 > 0
- `allow_tools` 空列表表示允许所有工具

---

## 数据流图

### 工具列表查询流程

```
User/Agent
   │
   ├─ list_tools(source_types=['mcp'])
   │
   ▼
CapabilityRegistry
   │
   ├─ 检查缓存
   │
   ├─ 遍历 enabled MCP servers
   │
   ▼
MCPClient (for each server)
   │
   ├─ connect()
   │   └─ spawn subprocess
   │   └─ send initialize()
   │
   ├─ list_tools()
   │   └─ send tools/list JSON-RPC
   │   └─ receive [MCPTool, ...]
   │
   ▼
MCPAdapter
   │
   ├─ for each MCPTool:
   │   ├─ mcp_tool_to_descriptor()
   │   ├─ infer_risk_level()
   │   ├─ infer_side_effects()
   │   └─ create ToolDescriptor
   │
   ▼
CapabilityRegistry
   │
   ├─ 合并结果
   ├─ 更新缓存
   │
   ▼
return [ToolDescriptor, ...]
```

---

### 工具调用流程

```
User/Agent
   │
   ├─ invoke_tool("mcp:echo-math:echo", {"text": "hello"}, ctx)
   │
   ▼
ToolRouter
   │
   ├─ get_tool("mcp:echo-math:echo")
   │   └─ CapabilityRegistry
   │
   ├─ PolicyEngine.check(tool, ctx)
   │   ├─ Gate 1: Disabled? ───▶ DENY (if disabled)
   │   ├─ Gate 2: Mode? ────────▶ DENY (if planning + side effects)
   │   ├─ Gate 3: SpecFrozen? ──▶ DENY (if not frozen)
   │   ├─ Gate 4: ProjectId? ───▶ DENY (if missing)
   │   ├─ Gate 5: Blacklist? ───▶ DENY (if blacklisted)
   │   └─ Gate 6: AdminToken? ──▶ DENY (if missing)
   │
   ├─ audit_logger.log_invocation_start()
   │   └─ INSERT INTO task_audits
   │
   ├─ Dispatch to MCPClient
   │   ├─ call_tool("echo", {"text": "hello"})
   │   │   └─ send tools/call JSON-RPC
   │   │   └─ receive MCPResult
   │   │
   │   └─ MCPAdapter.mcp_result_to_tool_result()
   │
   ├─ audit_logger.log_invocation_end()
   │   └─ INSERT INTO task_audits
   │
   ▼
return ToolResult(success=True, payload={...})
```

---

### 安全闸门决策流程

```
                    ┌─────────────────┐
                    │  Tool Invocation │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Gate 1: Disabled │
                    └────────┬─────────┘
                             │ enabled?
                             ├─ NO ──▶ DENY + audit
                             │
                             ▼ YES
                    ┌─────────────────┐
                    │ Gate 2: Mode    │
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    │ planning mode?  │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │ has side effects?│
                    └────────┬────────┘
                             │
                             ├─ YES ──▶ DENY + audit
                             │
                             ▼ NO or execution mode
                    ┌─────────────────┐
                    │ Gate 3: SpecFrozen│
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    │ execution mode? │
                    │ AND risk≥HIGH?  │
                    └────────┬────────┘
                             │
                             ├─ spec_frozen? NO ──▶ DENY + audit
                             │
                             ▼ YES or N/A
                    ┌─────────────────┐
                    │ Gate 4: Project │
                    └────────┬─────────┘
                             │
                             ├─ risk≥MEDIUM + no project_id ──▶ DENY
                             │
                             ▼
                    ┌─────────────────┐
                    │ Gate 5: Policy  │
                    └────────┬─────────┘
                             │
                             ├─ side effects blacklisted? ──▶ DENY
                             │
                             ▼
                    ┌─────────────────┐
                    │ Gate 6: AdminToken│
                    └────────┬─────────┘
                             │
                             ├─ requires admin + no token ──▶ DENY
                             │
                             ▼
                    ┌─────────────────┐
                    │     ALLOWED     │
                    └─────────────────┘
```

---

## 与 Extension 系统的关系

### 相似性

| 特性 | Extension | MCP |
|------|-----------|-----|
| 目的 | 扩展 AgentOS 功能 | 扩展 AgentOS 功能 |
| 工具提供 | ✅ | ✅ |
| 动态加载 | ✅ | ✅ |
| 配置管理 | ✅ manifest.json | ✅ mcp_servers.yaml |
| 安全闸门 | ✅ 统一策略 | ✅ 统一策略 |
| 审计日志 | ✅ | ✅ |

### 差异性

| 特性 | Extension | MCP |
|------|-----------|-----|
| 实现语言 | Python/Node.js | 任意 (独立进程) |
| 进程模型 | 同进程 | 独立进程 (stdio) |
| 故障隔离 | 一般 | 优秀 (进程隔离) |
| 性能 | 高 (本地调用) | 中 (进程通信) |
| 开发难度 | 中 (需了解 AgentOS) | 低 (标准 MCP 协议) |
| 社区生态 | AgentOS 专用 | 通用 MCP 生态 |

### 选择建议

**使用 Extension 当**:
- 需要深度集成 AgentOS 功能
- 需要最佳性能
- 工具逻辑复杂,需要访问 AgentOS 内部 API
- 示例: GitHub integration, Slack bot

**使用 MCP 当**:
- 使用标准 MCP 协议工具
- 需要进程隔离和故障隔离
- 工具可能不稳定或有安全风险
- 利用现有 MCP 服务器社区
- 示例: filesystem, database, API clients

---

## 扩展点

### 1. 自定义 MCP Server

创建自己的 MCP Server:

```javascript
// my-mcp-server/index.js
class MyMCPServer {
  constructor() {
    this.tools = [
      {
        name: "my_tool",
        description: "My custom tool",
        inputSchema: { /* JSON Schema */ }
      }
    ];
  }

  handleRequest(request) {
    // 实现 MCP 协议
    // - initialize
    // - tools/list
    // - tools/call
  }
}
```

配置:
```yaml
# ~/.agentos/mcp_servers.yaml
mcp_servers:
  - id: my-server
    enabled: true
    transport: stdio
    command: ["node", "path/to/my-mcp-server/index.js"]
```

### 2. 自定义风险推断规则

扩展 MCPAdapter:

```python
# custom_adapter.py
class CustomMCPAdapter(MCPAdapter):
    @staticmethod
    def infer_risk_level(tool_name: str, description: str) -> RiskLevel:
        # 自定义逻辑
        if "critical_operation" in description:
            return RiskLevel.CRITICAL
        # 回退到默认
        return MCPAdapter.infer_risk_level(tool_name, description)
```

### 3. 自定义 Policy Gate

添加新的安全闸门:

```python
class CustomGate(PolicyGate):
    def check(self, tool: ToolDescriptor, ctx: InvocationContext) -> PolicyDecision:
        # 自定义检查逻辑
        if custom_condition:
            return PolicyDecision(allowed=False, reason="Custom rule")
        return PolicyDecision(allowed=True)

# 注册到 PolicyEngine
policy_engine.register_gate(CustomGate())
```

### 4. 自定义审计处理

扩展审计系统:

```python
class CustomAuditHandler:
    async def handle_audit_event(self, event: AuditEvent):
        # 发送到外部系统 (如 Elasticsearch, Datadog)
        await send_to_external_system(event)

# 注册处理器
audit_logger.register_handler(CustomAuditHandler())
```

---

## 性能考虑

### 缓存策略

1. **工具列表缓存**: Registry 缓存 MCP 工具列表,TTL 5 分钟
2. **连接复用**: MCPClient 保持与 server 的长连接
3. **惰性加载**: 只在需要时连接 MCP server

### 超时设置

```python
# 配置推荐
mcp_servers:
  - timeout_ms: 5000   # 简单操作 (echo, sum)
  - timeout_ms: 30000  # 网络操作 (http fetch)
  - timeout_ms: 60000  # 复杂操作 (database query)
```

### 并发限制

- MCPClient 支持并发调用 (通过 request_id 区分)
- 建议每个 server 最多 10 个并发请求

---

## 安全考虑

### MCP Server 信任模型

```
┌─────────────────────────────────────┐
│   Trust Level: MCP Server           │
│                                     │
│   ┌───────────────────────────────┐ │
│   │ HIGH TRUST                    │ │
│   │ - Official servers            │ │
│   │ - Verified sources            │ │
│   │ - Read-only operations        │ │
│   └───────────────────────────────┘ │
│                                     │
│   ┌───────────────────────────────┐ │
│   │ MEDIUM TRUST                  │ │
│   │ - Community servers           │ │
│   │ - Limited side effects        │ │
│   │ - Monitored operations        │ │
│   └───────────────────────────────┘ │
│                                     │
│   ┌───────────────────────────────┐ │
│   │ LOW TRUST / UNTRUSTED         │ │
│   │ - Unknown sources             │ │
│   │ - Dangerous operations        │ │
│   │ - Require admin approval      │ │
│   └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 配置最佳实践

1. **最小权限原则**: 使用 `allow_tools` 白名单
2. **黑名单副作用**: 使用 `deny_side_effect_tags` 禁止危险操作
3. **审计所有操作**: 确保审计日志启用
4. **定期审查**: 定期检查 MCP 配置和使用情况
5. **隔离敏感操作**: 高风险 server 默认 `enabled: false`

---

## 监控和诊断

### 健康检查

```python
# 检查所有 MCP servers 健康状态
health = await mcp_health_check.check_all()
# {
#   "echo-math": "healthy",
#   "database": "degraded",
#   "filesystem": "unhealthy"
# }
```

### 日志

```python
# MCP Client 日志
logger.info(f"Connected to MCP server: {server_id}")
logger.error(f"Request timed out: {method} (id={request_id})")

# Router 日志
logger.info(f"Tool invoked: {tool_id}, result: {result.success}")
logger.warning(f"Policy violation: {decision.reason}")
```

### 审计查询

```sql
-- 查询 MCP 工具调用历史
SELECT * FROM task_audits
WHERE event_type IN ('tool_invocation_start', 'tool_invocation_end')
  AND context->>'source_type' = 'mcp'
ORDER BY created_at DESC;

-- 查询策略违规
SELECT * FROM task_audits
WHERE event_type = 'policy_violation'
  AND context->>'source_type' = 'mcp';
```

---

## 参考资料

### 内部文档

- [安全治理文档](../capabilities/SECURITY_GOVERNANCE.md)
- [MCP API 参考](../api/MCP_API.md)
- [故障排查指南](./TROUBLESHOOTING.md)

### 外部资源

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [MCP Server Examples](https://github.com/modelcontextprotocol/servers)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)

---

**文档版本**: 1.0
**最后更新**: 2026-01-30
**维护者**: AgentOS Core Team
