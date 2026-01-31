# Trust Tier Guide

## 概述

Trust Tier（信任层级）是 AgentOS Governance vNext 的核心组件，根据能力来源自动应用不同的治理强度。

**核心概念：** Trust Tier 是"默认治理强度"，不是权限或 enable/disable。

## 信任层级定义

AgentOS 定义了 4 个信任层级：

| 层级 | 名称 | 描述 | 默认风险级别 | 典型来源 |
|------|------|------|-------------|---------|
| **T0** | `local_extension` | 本地扩展 | LOW | 已安装的 Extension |
| **T1** | `local_mcp` | 本地 MCP | MED | stdio MCP (本地命令) |
| **T2** | `remote_mcp` | 远程 MCP | HIGH | tcp/ssh MCP (LAN/私有网络) |
| **T3** | `cloud_mcp` | 云端 MCP | CRITICAL | https/http MCP (互联网) |

### 信任层级拓扑

```
T0 (Extension)  ━━━━━━━━━━━>  最高信任，最宽松策略
       ↓
T1 (Local MCP)  ━━━━━━━━━━━>  高信任，标准策略
       ↓
T2 (Remote MCP) ━━━━━━━━━━━>  中等信任，严格策略
       ↓
T3 (Cloud MCP)  ━━━━━━━━━━━>  最低信任，最严格策略
```

## 自动赋值规则

### Extension → T0

所有 Extension 能力自动赋值为 `T0`（最高信任）。

```python
# agentos/core/capabilities/registry.py
tool = ToolDescriptor(
    tool_id=f"ext:{extension_id}:{capability.name}",
    # ...
    trust_tier=TrustTier.T0  # 自动赋值
)
```

### MCP → T1/T2/T3

MCP 工具根据传输协议自动推断信任层级：

```python
# agentos/core/mcp/adapter.py
def _infer_trust_tier(self, server_config: MCPServerConfig) -> TrustTier:
    transport = server_config.transport.lower()

    if transport == "stdio":
        # 检查命令是否为 HTTP
        command = server_config.command[0] if server_config.command else ""
        if command.startswith("http"):
            return TrustTier.T3  # Cloud
        return TrustTier.T1  # Local

    elif transport in ("tcp", "ssh"):
        return TrustTier.T2  # Remote

    elif transport in ("https", "http"):
        return TrustTier.T3  # Cloud

    else:
        return TrustTier.T2  # 默认中等信任
```

## 默认策略

### 1. 风险级别映射

```python
TRUST_TIER_RISK_MAPPING = {
    TrustTier.T0: RiskLevel.LOW,
    TrustTier.T1: RiskLevel.MED,
    TrustTier.T2: RiskLevel.HIGH,
    TrustTier.T3: RiskLevel.CRITICAL,
}
```

### 2. 配额限制

| 层级 | calls_per_minute | max_concurrent | max_runtime_ms |
|------|------------------|----------------|----------------|
| **T0** | 1000 | 20 | 600000 (10 min) |
| **T1** | 100 | 10 | 300000 (5 min) |
| **T2** | 20 | 5 | 120000 (2 min) |
| **T3** | 10 | 2 | 60000 (1 min) |

### 3. 副作用策略

#### T0 (Extension)
- ✅ 允许副作用
- 黑名单：无

#### T1 (Local MCP)
- ✅ 允许副作用
- 黑名单：无

#### T2 (Remote MCP)
- ⚠️ 有条件允许副作用
- 黑名单：`payments`, `cloud.resource_delete`

#### T3 (Cloud MCP)
- ❌ 默认不允许副作用
- 黑名单：`payments`, `cloud.key_write`, `cloud.resource_delete`, `fs.delete`, `system.exec`

### 4. Admin Token 需求

| 层级 | 基础需求 | 有副作用 |
|------|---------|---------|
| **T0** | ❌ | ❌ |
| **T1** | ❌ | ❌ |
| **T2** | ❌ | ✅ |
| **T3** | ✅ | ✅ |

## 策略集成

### PolicyEngine 自动应用 Trust Tier 策略

```python
# agentos/core/capabilities/policy.py
def _check_policy_gate(self, tool: ToolDescriptor, invocation: ToolInvocation):
    # 获取信任层级的副作用策略
    se_policy = get_side_effects_policy(tool.trust_tier)

    # 检查黑名单
    for effect in tool.side_effect_tags:
        if effect in se_policy["blacklisted_effects"]:
            return (False, f"Side effect '{effect}' is blacklisted for trust tier {tool.trust_tier.value}")

    # T3 默认不允许副作用
    if tool.trust_tier == TrustTier.T3:
        if not se_policy["allow_side_effects"] and tool.side_effect_tags:
            return (False, "Cloud MCP (T3) tools with side effects require explicit approval")

    return (True, None)

def _check_admin_token_gate(self, tool: ToolDescriptor, admin_token: Optional[str]):
    # 基于信任层级判断是否需要 admin token
    trust_tier_needs_admin = should_require_admin_token(
        tool.trust_tier,
        has_side_effects=bool(tool.side_effect_tags)
    )

    needs_admin = (
        tool.requires_admin_token or
        tool.risk_level == RiskLevel.CRITICAL or
        trust_tier_needs_admin
    )

    if needs_admin and not admin_token:
        return (False, f"Tool requires admin_token (trust_tier={tool.trust_tier.value})")

    return (True, None)
```

## Override 方法

虽然 Trust Tier 提供默认策略，但可以在工具级别 override：

### 1. Override 风险级别

```python
tool = ToolDescriptor(
    tool_id="mcp:remote:safe_read",
    trust_tier=TrustTier.T2,  # 默认 HIGH risk
    risk_level=RiskLevel.LOW,  # Override 为 LOW
    # ...
)
```

### 2. Override Admin Token 需求

```python
tool = ToolDescriptor(
    tool_id="mcp:cloud:public_api",
    trust_tier=TrustTier.T3,  # 默认需要 admin token
    requires_admin_token=False,  # Override 为不需要
    # ...
)
```

### 3. 配置 MCP Server 过滤

```yaml
# ~/.agentos/mcp_servers.yaml
mcp_servers:
  - id: cloud_api
    transport: https
    command: ["https://api.example.com"]
    # 限制允许的工具
    allow_tools: ["get_public_data"]
    # 拒绝特定副作用
    deny_side_effect_tags: ["fs.write", "system.exec"]
```

## 使用示例

### 示例 1: Extension 工具（T0）

```python
# Extension 自动获得最高信任
tool = ToolDescriptor(
    tool_id="ext:tools.postman:get",
    name="get",
    trust_tier=TrustTier.T0,  # 自动赋值
    risk_level=RiskLevel.LOW,
    side_effect_tags=["network.http"],
)

# 策略检查
policy = ToolPolicyEngine()
allowed, reason = policy._check_admin_token_gate(tool, admin_token=None)
# allowed=True (T0 不需要 admin token)
```

### 示例 2: Local MCP（T1）

```yaml
# MCP 配置
mcp_servers:
  - id: filesystem
    transport: stdio
    command: ["node", "mcp-server-filesystem.js"]
```

```python
# 自动推断为 T1
tool = ToolDescriptor(
    tool_id="mcp:filesystem:read_file",
    trust_tier=TrustTier.T1,  # 自动推断
    risk_level=RiskLevel.LOW,
    side_effect_tags=["fs.read"],
)

# 配额限制
quota = get_default_quota(TrustTier.T1)
# {
#   "calls_per_minute": 100,
#   "max_concurrent": 10,
#   "max_runtime_ms": 300000
# }
```

### 示例 3: Cloud MCP（T3）

```yaml
mcp_servers:
  - id: cloud_api
    transport: https
    command: ["https://api.example.com"]
```

```python
# 自动推断为 T3
tool = ToolDescriptor(
    tool_id="mcp:cloud_api:create_resource",
    trust_tier=TrustTier.T3,  # 自动推断
    risk_level=RiskLevel.CRITICAL,
    side_effect_tags=["cloud.resource_create"],
)

# 策略检查
policy = ToolPolicyEngine()
invocation = ToolInvocation(
    invocation_id="test",
    tool_id=tool.tool_id,
    mode=ExecutionMode.EXECUTION,
    spec_frozen=True,
    spec_hash="abc123",
    project_id="proj-001",
    inputs={},
    actor="user",
)

allowed, reason = policy.check_allowed(tool, invocation, admin_token=None)
# allowed=False
# reason="Tool requires admin_token (trust_tier=cloud_mcp)"
```

## 最佳实践

### 1. 尽量使用 Local Extension（T0）

对于频繁使用、性能敏感的工具，优先开发为 Extension。

### 2. 为 Cloud MCP 工具准备 Admin Token 流程

T3 工具默认需要 admin token，应用应该实现用户审批流程。

### 3. 合理配置 MCP Server 过滤

使用 `allow_tools` 和 `deny_side_effect_tags` 限制 MCP 工具的能力。

### 4. 监控 Trust Tier 配额

定期检查配额使用情况，调整限制以适应实际需求。

### 5. 审计 Trust Tier 降级

如果需要将高信任层级的工具 override 为低风险，应记录原因并审计。

## 测试

运行 Trust Tier 测试：

```bash
pytest tests/core/capabilities/test_trust_tier.py -v
```

## 相关文档

- [Governance vNext Overview](./README.md)
- [Capability Quota System](./QUOTA_GUIDE.md)
- [Policy Engine](./POLICY_GUIDE.md)
- [Provenance Tracking](./PROVENANCE_GUIDE.md)

## 参考

- PR-B: Trust Tier Implementation
- Architecture: Governance vNext
- Trust Tier Defaults: `agentos/core/capabilities/trust_tier_defaults.py`
