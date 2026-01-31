# PR-B: Trust Tier Implementation Summary

## 概述

成功实现了 **Trust Tier（信任层级拓扑）** 系统，根据能力来源自动应用不同的治理强度。

**实施日期：** 2026-01-30

## 核心概念

Trust Tier 是"默认治理强度"，不是权限或 enable/disable。系统根据能力来源自动推断信任层级，并应用相应的治理策略。

## 实施内容

### 1. TrustTier 枚举定义

**文件：** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/capability_models.py`

定义了 4 个信任层级：

```python
class TrustTier(str, Enum):
    T0 = "local_extension"    # Local Extension (最高信任)
    T1 = "local_mcp"          # Local MCP (same host)
    T2 = "remote_mcp"         # Remote MCP (LAN/private)
    T3 = "cloud_mcp"          # Cloud MCP (internet, 最低信任)
```

### 2. ToolDescriptor 扩展

在 `ToolDescriptor` 中添加 `trust_tier` 字段：

```python
class ToolDescriptor(BaseModel):
    # ... existing fields ...

    trust_tier: TrustTier = Field(
        default=TrustTier.T1,
        description="信任层级，影响默认治理策略"
    )
```

### 3. Trust Tier 默认策略

**文件：** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/trust_tier_defaults.py`

定义了信任层级的默认策略映射表：

#### 风险级别映射
- T0 → LOW
- T1 → MED
- T2 → HIGH
- T3 → CRITICAL

#### 配额限制
| 层级 | calls_per_minute | max_concurrent | max_runtime_ms |
|------|------------------|----------------|----------------|
| T0 | 1000 | 20 | 600000 |
| T1 | 100 | 10 | 300000 |
| T2 | 20 | 5 | 120000 |
| T3 | 10 | 2 | 60000 |

#### 副作用策略
- T0/T1: 允许所有副作用
- T2: 黑名单 `payments`, `cloud.resource_delete`
- T3: 默认禁止副作用，严格黑名单

#### Admin Token 需求
- T0/T1: 不需要
- T2: 有副作用时需要
- T3: 默认需要

### 4. MCP Adapter 自动赋值

**文件：** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/adapter.py`

实现了 `_infer_trust_tier()` 方法，根据 MCP 传输协议自动推断信任层级：

```python
def _infer_trust_tier(self, server_config: MCPServerConfig) -> TrustTier:
    transport = server_config.transport.lower()

    if transport == "stdio":
        command = server_config.command[0] if server_config.command else ""
        if command.startswith("http"):
            return TrustTier.T3  # Cloud
        return TrustTier.T1  # Local

    elif transport in ("tcp", "ssh"):
        return TrustTier.T2  # Remote

    elif transport in ("https", "http"):
        return TrustTier.T3  # Cloud

    else:
        return TrustTier.T2  # 默认
```

### 5. Extension Adapter 默认 T0

**文件：** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/registry.py`

Extension 能力自动赋值为 T0（最高信任）：

```python
tool = ToolDescriptor(
    tool_id=f"ext:{extension_id}:{capability.name}",
    # ... other fields ...
    trust_tier=TrustTier.T0  # Extension 默认最高信任
)
```

### 6. PolicyEngine 集成

**文件：** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/policy.py`

PolicyEngine 使用 Trust Tier 策略：

#### Policy Gate
```python
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
```

#### Admin Token Gate
```python
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

    # ... validation logic ...
```

### 7. MCP Config 扩展

**文件：** `/Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/config.py`

扩展了 `MCPServerConfig` 以支持多种传输协议：

```python
transport: str = Field(
    default="stdio",
    description="Transport protocol (stdio, tcp, ssh, https, http)"
)

@field_validator("transport")
@classmethod
def validate_transport(cls, v):
    allowed = ["stdio", "tcp", "ssh", "https", "http"]
    if v.lower() not in allowed:
        logger.warning(f"Transport {v} not in standard list {allowed}")
    return v
```

## 测试覆盖

**文件：** `/Users/pangge/PycharmProjects/AgentOS/tests/core/capabilities/test_trust_tier.py`

实现了全面的测试套件（17 个测试，全部通过）：

### 测试类别

1. **TestTrustTierDefaults（4 tests）**
   - 风险映射
   - 配额映射
   - Admin token 需求
   - 副作用策略

2. **TestTrustTierAssignment（5 tests）**
   - MCP stdio local → T1
   - MCP stdio http → T3
   - MCP tcp → T2
   - MCP https → T3
   - 未知传输协议 → T2

3. **TestTrustTierPolicyIntegration（6 tests）**
   - T3 阻止副作用
   - T3 需要 admin token
   - T2 + 副作用需要 admin token
   - T2 无副作用不需要 admin token
   - T0 最宽松
   - 信任层级黑名单强制执行

4. **TestTrustTierEndToEnd（2 tests）**
   - MCP 工具描述符包含 trust_tier
   - 完整策略检查集成 trust_tier

### 测试结果

```bash
$ pytest tests/core/capabilities/test_trust_tier.py -v
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0
collected 17 items

tests/core/capabilities/test_trust_tier.py::TestTrustTierDefaults::test_risk_mapping PASSED [  5%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierDefaults::test_quota_mapping PASSED [ 11%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierDefaults::test_admin_token_requirement PASSED [ 17%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierDefaults::test_side_effects_policy PASSED [ 23%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierAssignment::test_mcp_stdio_local PASSED [ 29%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierAssignment::test_mcp_stdio_http PASSED [ 35%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierAssignment::test_mcp_tcp_remote PASSED [ 41%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierAssignment::test_mcp_https_cloud PASSED [ 47%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierAssignment::test_mcp_unknown_transport PASSED [ 52%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierPolicyIntegration::test_t3_blocks_side_effects PASSED [ 58%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierPolicyIntegration::test_t3_requires_admin_token PASSED [ 64%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierPolicyIntegration::test_t2_with_side_effects_requires_admin_token PASSED [ 70%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierPolicyIntegration::test_t2_without_side_effects_no_admin_token PASSED [ 76%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierPolicyIntegration::test_t0_extension_most_permissive PASSED [ 82%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierPolicyIntegration::test_trust_tier_blacklist_enforcement PASSED [ 88%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierEndToEnd::test_mcp_tool_descriptor_has_trust_tier PASSED [ 94%]
tests/core/capabilities/test_trust_tier.py::TestTrustTierEndToEnd::test_full_policy_check_with_trust_tier PASSED [100%]

======================== 17 passed, 2 warnings in 0.17s ========================
```

## 文档

创建了完整的用户指南：

**文件：** `/Users/pangge/PycharmProjects/AgentOS/docs/governance/TRUST_TIER_GUIDE.md`

包含：
- 信任层级定义
- 自动赋值规则
- 默认策略详解
- 策略集成说明
- Override 方法
- 使用示例
- 最佳实践

## 文件清单

### 新增文件

1. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/trust_tier_defaults.py`
   - Trust tier 默认策略定义

2. `/Users/pangge/PycharmProjects/AgentOS/tests/core/capabilities/test_trust_tier.py`
   - 完整测试套件

3. `/Users/pangge/PycharmProjects/AgentOS/docs/governance/TRUST_TIER_GUIDE.md`
   - 用户指南

### 修改文件

1. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/capability_models.py`
   - 添加 `TrustTier` 枚举
   - 在 `ToolDescriptor` 中添加 `trust_tier` 字段

2. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/adapter.py`
   - 添加 `_infer_trust_tier()` 方法
   - 在 `mcp_tool_to_descriptor()` 中自动赋值 trust_tier

3. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/registry.py`
   - Extension 能力自动赋值 T0

4. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/policy.py`
   - `_check_policy_gate()` 使用 trust tier 策略
   - `_check_admin_token_gate()` 使用 trust tier 判断

5. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/config.py`
   - 扩展传输协议支持
   - 更新验证器

6. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/__init__.py`
   - 导出 `TrustTier`

## 验收标准

✅ **TrustTier 自动赋值**
- Extension → T0
- MCP stdio (本地) → T1
- MCP tcp/ssh → T2
- MCP https/http → T3

✅ **不同 tier 应用不同策略**
- 风险级别映射正确
- 配额限制按层级递减
- 副作用黑名单按层级递增
- Admin token 需求符合预期

✅ **可 override 默认行为**
- 可以在工具级别 override risk_level
- 可以在工具级别 override requires_admin_token
- MCP server 配置可以过滤工具

✅ **测试全部通过**
- 17/17 tests passed

## 架构集成

Trust Tier 与其他 Governance 组件无缝集成：

```
┌─────────────────────────────────────────────────┐
│           Capability Abstraction Layer           │
│  ┌───────────────────────────────────────────┐  │
│  │         ToolDescriptor                     │  │
│  │  - tool_id                                 │  │
│  │  - trust_tier  ← PR-B                     │  │
│  │  - risk_level                              │  │
│  │  - side_effect_tags                        │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│            ToolPolicyEngine (7-Layer)            │
│  1. Mode Gate                                   │
│  2. Spec Frozen Gate                            │
│  3. Project Binding Gate                        │
│  4. Quota Gate          ← PR-A                 │
│  5. Policy Gate         ← PR-B (Trust Tier)    │
│  6. Admin Token Gate    ← PR-B (Trust Tier)    │
│  7. Audit Gate          ← PR-C (Provenance)    │
└─────────────────────────────────────────────────┘
```

## 影响范围

### 向后兼容性
✅ 完全向后兼容
- 现有代码无需修改
- `trust_tier` 有默认值（T1）
- 旧的 `risk_level` 和 `requires_admin_token` 仍然生效

### 性能影响
✅ 最小性能影响
- Trust tier 推断在工具注册时进行（一次性）
- 策略查询使用内存字典（O(1)）
- 无额外 I/O 或网络请求

## 已知限制

1. **MCP 传输协议检测有限**
   - 目前基于配置中的 `transport` 字段
   - 无法检测运行时的实际网络连接

2. **Trust Tier Override 需要手动**
   - 如果自动推断不准确，需要手动设置
   - 未来可以考虑基于机器学习的动态调整

## 后续工作

1. ⏭️ **PR-C: Provenance（溯源）**
   - 为 Trust Tier 决策添加溯源记录
   - 审计 Trust Tier override 操作

2. ⏭️ **动态 Trust Tier 调整**
   - 基于工具历史行为动态调整信任层级
   - 实现"信任降级"机制

3. ⏭️ **Trust Tier 可视化**
   - 在 WebUI 中显示工具的信任层级
   - 提供 Trust Tier 调整界面

## 总结

PR-B: Trust Tier 实施成功！

- ✅ 4 个信任层级定义清晰
- ✅ 自动赋值规则准确
- ✅ 默认策略完整
- ✅ 策略集成无缝
- ✅ 测试覆盖全面（17/17）
- ✅ 文档完备

Trust Tier 为 AgentOS 提供了基于来源的自动化治理强度分级，大大简化了安全配置，同时保持了灵活性。

---

**实施者：** Claude Sonnet 4.5
**日期：** 2026-01-30
**状态：** ✅ COMPLETE
