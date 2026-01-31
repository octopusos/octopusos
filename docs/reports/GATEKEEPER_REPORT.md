# Gatekeeper 验收报告

**验收时间**: 2026-01-30
**验收人**: Gatekeeper Agent
**结论**: FAIL

---

## 验收环境

- **OS**: Darwin 25.2.0 (macOS)
- **Python**: Python 3.14.2
- **pytest**: pytest 9.0.2
- **Node.js**: v20.19.5
- **Working Directory**: /Users/pangge/PycharmProjects/AgentOS

---

## 验收结果

### 2.1 基础环境

- ✅ **工作区状态**: Clean working tree, on branch master, up to date with origin/master
- ✅ **Python 版本**: Python 3.14.2
- ✅ **pytest 可用**: pytest 9.0.2

---

### 2.2 文件结构

- ✅ **capabilities/ 存在**:
  - `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities`
  - 包含核心文件: `registry.py`, `router.py`, `policy.py`, `audit.py`, `capability_models.py`

- ✅ **mcp/ 存在**:
  - `/Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp`
  - 包含核心文件: `client.py`, `adapter.py`, `config.py`, `health.py`, `sandbox.py`

- ✅ **mcp.py 存在**:
  - `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/mcp.py` (17k)

- ✅ **echo-math server 存在**:
  - `/Users/pangge/PycharmProjects/AgentOS/servers/echo-math-mcp/index.js` (3.8k)

---

### 2.3 Registry 合并

- ✅ **ToolDescriptor**: `agentos/core/capabilities/capability_models.py:76`
  ```
  class ToolDescriptor(BaseModel):
  ```

- ✅ **CapabilityRegistry**: `agentos/core/capabilities/registry.py:53`
  ```
  class CapabilityRegistry:
  ```

- ✅ **tool_id mcp**:
  ```
  agentos/core/capabilities/README_CAPABILITY_ABSTRACTION.md:53:  - `tool_id`: Unique identifier (format: `ext:<ext_id>:<cmd>` or `mcp:<server>:<tool>`)
  agentos/core/capabilities/router.py:312:            tool_id: Tool identifier (format: mcp:<server_id>:<tool_name>)
  agentos/core/capabilities/router.py:323:            # Parse tool_id: mcp:<server_id>:<tool_name>
  agentos/core/mcp/adapter.py:77:        # Generate tool_id: mcp:<server_id>:<tool_name>
  agentos/core/mcp/adapter.py:78:        tool_id = f"mcp:{server_id}:{tool_name}"
  ```

- ✅ **tool_id ext**:
  ```
  agentos/core/capabilities/registry.py:149:            tool_id: Tool identifier (e.g., "ext:tools.postman:get")
  agentos/core/capabilities/registry.py:308:        tool_id = f"ext:{extension_id}:{capability.name}"
  agentos/core/capabilities/router.py:22:        tool_id="ext:tools.postman:get",
  agentos/core/capabilities/router.py:264:            # Parse tool_id: "ext:<extension_id>:<command>"
  ```

---

### 2.4 6 层闸门

**代码证据**:

- ✅ **Mode Gate**: `agentos/core/capabilities/policy.py:108-188`
  ```
  # Gate 1: Mode Gate
  allowed, reason = self._check_mode_gate(tool, invocation)
  if invocation.mode == ExecutionMode.PLANNING:
  ```

- ✅ **Spec Frozen Gate**: `agentos/core/capabilities/policy.py:118,203`
  ```
  # Gate 2: Spec Frozen Gate
  Gate 2: Spec Frozen Gate - Execution requires frozen spec
  ```

- ✅ **Project Binding Gate**: `agentos/core/capabilities/policy.py:128,275`
  ```
  # Gate 3: Project Binding Gate
  Gate 3: Project Binding Gate - Require project_id
  ```

- ✅ **Admin Token Gate**: `agentos/core/capabilities/policy.py:148,335`
  ```
  # Gate 5: Admin Token Gate
  Gate 5: Admin Token Gate - High-risk operations require approval
  ```

- ✅ **Audit**: `agentos/core/capabilities/audit.py:50,120`
  ```
  def emit_tool_invocation_start(
  def emit_tool_invocation_end(
  ```

**闸门测试结果**: ✅ **19/19 passed** (100%)

```
tests/core/capabilities/test_policy_gates.py::TestModeGate::test_mode_gate_blocks_planning_side_effects PASSED
tests/core/capabilities/test_policy_gates.py::TestModeGate::test_mode_gate_allows_planning_read_only PASSED
tests/core/capabilities/test_policy_gates.py::TestModeGate::test_mode_gate_allows_execution_with_side_effects PASSED
tests/core/capabilities/test_policy_gates.py::TestSpecFrozenGate::test_spec_frozen_gate_requires_frozen_spec PASSED
tests/core/capabilities/test_policy_gates.py::TestSpecFrozenGate::test_spec_frozen_gate_requires_spec_hash PASSED
tests/core/capabilities/test_policy_gates.py::TestSpecFrozenGate::test_spec_frozen_gate_allows_valid_execution PASSED
tests/core/capabilities/test_policy_gates.py::TestProjectBindingGate::test_project_binding_gate_requires_project PASSED
tests/core/capabilities/test_policy_gates.py::TestProjectBindingGate::test_project_binding_gate_allows_with_project PASSED
tests/core/capabilities/test_policy_gates.py::TestPolicyGate::test_policy_gate_blocks_blacklisted_effects PASSED
tests/core/capabilities/test_policy_gates.py::TestPolicyGate::test_policy_gate_allows_non_blacklisted PASSED
tests/core/capabilities/test_policy_gates.py::TestAdminTokenGate::test_admin_token_gate_requires_token PASSED
tests/core/capabilities/test_policy_gates.py::TestAdminTokenGate::test_admin_token_gate_validates_token PASSED
tests/core/capabilities/test_policy_gates.py::TestAdminTokenGate::test_admin_token_gate_allows_low_risk_without_token PASSED
tests/core/capabilities/test_policy_gates.py::TestFullGatePipeline::test_full_gate_pipeline_all_pass PASSED
tests/core/capabilities/test_policy_gates.py::TestFullGatePipeline::test_full_gate_pipeline_stops_at_first_failure PASSED
tests/core/capabilities/test_policy_gates.py::TestFullGatePipeline::test_disabled_tool_rejected PASSED
tests/core/capabilities/test_policy_gates.py::TestPolicyHelperMethods::test_requires_spec_freezing PASSED
tests/core/capabilities/test_policy_gates.py::TestPolicyHelperMethods::test_requires_admin_approval PASSED
tests/core/capabilities/test_policy_gates.py::TestPolicyHelperMethods::test_check_side_effects_allowed PASSED

======================== 19 passed, 2 warnings in 0.24s =========================
```

---

### 2.5 MCP Client

- ✅ **stdio 实现**: `agentos/core/mcp/client.py:2,5,50,52`
  ```
  MCP Client - JSON-RPC 2.0 over stdio implementation
  stdio transport. It handles:
  MCP stdio client implementation
  Manages a subprocess running an MCP server and communicates via stdio
  ```

- ✅ **JSON-RPC**: `agentos/core/mcp/client.py:12-14,308,352`
  ```
  - Request: {"jsonrpc": "2.0", "id": <int>, "method": <string>, "params": <object>}
  - Response: {"jsonrpc": "2.0", "id": <int>, "result": <any>}
  - Error: {"jsonrpc": "2.0", "id": <int>, "error": {"code": <int>, "message": <string>}}
  "jsonrpc": "2.0",
  ```

- ✅ **list_tools**: `agentos/core/mcp/client.py:195`
  ```
  async def list_tools(self) -> List[Dict[str, Any]]:
  ```

- ✅ **call_tool**: `agentos/core/mcp/client.py:224`
  ```
  async def call_tool(
  ```

- ✅ **测试结果**: **25/25 passed** (100%)

```
tests/core/mcp/test_mcp_client.py::test_config_loading PASSED
tests/core/mcp/test_mcp_client.py::test_config_get_enabled_servers PASSED
tests/core/mcp/test_mcp_client.py::test_config_is_tool_allowed PASSED
tests/core/mcp/test_mcp_client.py::test_config_empty_allow_tools_allows_all PASSED
tests/core/mcp/test_mcp_client.py::test_config_is_side_effect_denied PASSED
tests/core/mcp/test_mcp_client.py::test_mcp_client_connect PASSED
tests/core/mcp/test_mcp_client.py::test_mcp_client_list_tools PASSED
tests/core/mcp/test_mcp_client.py::test_mcp_client_call_tool PASSED
tests/core/mcp/test_mcp_client.py::test_mcp_client_timeout PASSED
tests/core/mcp/test_mcp_client.py::test_mcp_client_disconnect PASSED
tests/core/mcp/test_mcp_client.py::test_mcp_adapter_mapping PASSED
tests/core/mcp/test_mcp_client.py::test_risk_inference_critical PASSED
tests/core/mcp/test_mcp_client.py::test_risk_inference_high PASSED
tests/core/mcp/test_mcp_client.py::test_risk_inference_low PASSED
tests/core/mcp/test_mcp_client.py::test_risk_inference_medium PASSED
tests/core/mcp/test_mcp_client.py::test_side_effects_inference PASSED
tests/core/mcp/test_mcp_client.py::test_mcp_result_to_tool_result PASSED
tests/core/mcp/test_mcp_client.py::test_mcp_result_error_handling PASSED
tests/core/mcp/test_mcp_client.py::test_health_check_healthy PASSED
tests/core/mcp/test_mcp_client.py::test_health_check_degraded PASSED
tests/core/mcp/test_mcp_client.py::test_health_check_unhealthy PASSED
tests/core/mcp/test_mcp_client.py::test_health_check_monitoring PASSED
tests/core/mcp/test_mcp_client.py::test_registry_integration PASSED
tests/core/mcp/test_mcp_client.py::test_router_mcp_dispatch PASSED
tests/core/mcp/test_mcp_client.py::test_server_down_graceful_degradation PASSED

======================== 25 passed, 6 warnings in 0.63s =========================
```

---

### 2.6 集成测试 (关键!)

- ✅ **Node.js 可用**: v20.19.5

- ✅ **Server 启动**: Server 可以响应 initialize 请求
  ```json
  {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"echo-math-mcp","version":"1.0.0"}}}
  ```

- ❌ **集成测试**: **9 passed, 8 failed** (52.9% pass rate)

**失败原因**: MCP Server 连接超时

```
ERROR    agentos.core.mcp.client:client.py:333 Request timed out: tools/list (id=3)
ERROR    agentos.core.mcp.client:client.py:221 Failed to list tools: Request timed out after 5000ms: tools/list
ERROR    agentos.core.capabilities.registry:registry.py:525 Failed to load tools from MCP server echo-math: Failed to list tools: Request timed out after 5000ms: tools/list
```

**失败测试清单**:
1. ❌ `TestMCPRouterIntegration::test_invoke_echo_through_router` - Tool not found: mcp:echo-math:echo
2. ❌ `TestMCPRouterIntegration::test_invoke_sum_through_router` - Tool not found: mcp:echo-math:sum
3. ❌ `TestMCPRouterIntegration::test_invoke_multiply_through_router` - Tool not found: mcp:echo-math:multiply
4. ❌ `TestMCPGatesIntegration::test_planning_mode_allowed_for_readonly` - Tool not found: mcp:echo-math:echo
5. ❌ `TestMCPGatesIntegration::test_execution_requires_spec_frozen` - Tool not found: mcp:echo-math:echo
6. ❌ `TestMCPAuditIntegration::test_audit_events_emitted` - Tool not found: mcp:echo-math:echo
7. ❌ `TestMCPToolFiltering::test_allow_tools_filter` - assert 'echo' in []
8. ❌ `TestMCPEndToEnd::test_complete_workflow` - assert 0 > 0

**通过测试**:
1. ✅ `TestMCPClientBasics::test_client_connect`
2. ✅ `TestMCPClientBasics::test_list_tools`
3. ✅ `TestMCPClientBasics::test_call_echo`
4. ✅ `TestMCPClientBasics::test_call_sum`
5. ✅ `TestMCPClientBasics::test_call_multiply`
6. ✅ `TestMCPAdapter::test_mcp_tool_to_descriptor`
7. ✅ `TestMCPAdapter::test_risk_level_inference`
8. ✅ `TestMCPServerDown::test_graceful_degradation_when_server_down`
9. ✅ `TestMCPServerDown::test_timeout_handling`

**完整错误输出**:
```
___________ TestMCPRouterIntegration.test_invoke_echo_through_router ___________
tests/integration/mcp/test_mcp_full_chain.py:228: in test_invoke_echo_through_router
    result = await tool_router.invoke_tool(
agentos/core/capabilities/router.py:128: in invoke_tool
    raise ToolNotFoundError(f"Tool not found: {tool_id}")
E   agentos.core.capabilities.router.ToolNotFoundError: Tool not found: mcp:echo-math:echo
------------------------------ Captured log call -------------------------------
ERROR    agentos.core.mcp.client:client.py:333 Request timed out: tools/list (id=3)
ERROR    agentos.core.mcp.client:client.py:221 Failed to list tools: Request timed out after 5000ms: tools/list
Traceback (most recent call last):
  File "/opt/homebrew/Cellar/python@3.14/3.14.2_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py", line 488, in wait_for
    return await fut
           ^^^^^^^^^
asyncio.exceptions.CancelledError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/client.py", line 328, in _send_request
    result = await asyncio.wait_for(future, timeout=timeout_seconds)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.2_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py", line 487, in wait_for
    async with timeouts.timeout(timeout):
               ~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.2_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/timeouts.py", line 114, in __aexit__
    raise TimeoutError from exc_val
TimeoutError

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/client.py", line 210, in list_tools
    result = await self._send_request(
             ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/client.py", line 334, in _send_request
    raise MCPTimeoutError(f"Request timed out after {timeout_ms}ms: {method}")
agentos.core.mcp.client.MCPTimeoutError: Request timed out after 5000ms: tools/list
ERROR    agentos.core.capabilities.registry:registry.py:525 Failed to load tools from MCP server echo-math: Failed to list tools: Request timed out after 5000ms: tools/list
```

---

### 2.7 WebUI API

- ✅ **调用 router**: `agentos/webui/api/mcp.py:391-393`
  ```python
  # Route through tool router (includes all security gates)
  result = await router_instance.invoke_tool(
  ```

- ✅ **无捷径**: 代码检查通过，WebUI API 不直接调用 MCP Client，全部通过 ToolRouter

- ❌ **测试通过**: **4/18 passed** (22.2% pass rate)

**通过测试**:
1. ✅ `TestListMCPTools::test_list_tools_invalid_risk_level`
2. ✅ `TestCallMCPTool::test_call_tool_missing_project_id`
3. ✅ `TestCallMCPTool::test_call_tool_invalid_tool_id_format`
4. ✅ `TestMCPHealthCheck::test_health_check_degraded`

**失败测试** (14 个):
1. ❌ `TestListMCPServers::test_list_servers_no_config` - Expected empty list, got echo-math server
2. ❌ `TestListMCPServers::test_list_servers_with_connected_servers` - Wrong server ID
3. ❌ `TestListMCPServers::test_list_servers_with_disabled_server` - Wrong server ID
4. ❌ `TestRefreshMCPServers::test_refresh_servers_success` - Expected 2 servers, got 1
5. ❌ `TestRefreshMCPServers::test_refresh_servers_no_servers` - Expected 0, got 1
6. ❌ `TestListMCPTools::test_list_tools_all` - Expected 2 tools, got 0
7. ❌ `TestListMCPTools::test_list_tools_with_server_filter` - Expected 1 tool, got 0
8. ❌ `TestListMCPTools::test_list_tools_with_risk_filter` - Expected 1 tool, got 0
9. ❌ `TestCallMCPTool::test_call_tool_success` - Got 500 instead of 200
10. ❌ `TestCallMCPTool::test_call_tool_policy_violation` - Got 500 instead of 200
11. ❌ `TestCallMCPTool::test_call_tool_with_admin_token` - Got 500 instead of 200
12. ❌ `TestMCPHealthCheck::test_health_check_healthy` - Expected healthy, got degraded
13. ❌ `TestMCPHealthCheck::test_health_check_unhealthy` - Expected unhealthy, got degraded
14. ❌ `TestMCPAPIIntegration::test_full_workflow` - Expected healthy, got degraded

**根本原因**: 同 2.6，MCP Server 连接超时导致工具未加载

---

## 合并硬条件

- ❌ **条件 1: 集成测试全绿** - FAIL (9/17 passed, 52.9%)
  - 根本原因: MCP Server 连接超时 (Request timed out after 5000ms: tools/list)

- ❌ **条件 2: WebUI e2e 至少一条全绿** - FAIL
  - `test_call_tool_success` FAILED (500 Internal Server Error)
  - 根本原因: 同上，工具未加载

- ✅ **条件 3: Server down 降级全绿** - PASS (2/2 passed, 100%)
  - `TestMCPServerDown::test_graceful_degradation_when_server_down` PASSED
  - `TestMCPServerDown::test_timeout_handling` PASSED

---

## 最终裁决

**结论**: **FAIL**

**理由**:
1. **P0 阻塞问题**: MCP Server 连接超时，导致 tools/list 失败
   - 错误: `MCPTimeoutError: Request timed out after 5000ms: tools/list`
   - 影响范围: 8/17 集成测试失败，14/18 WebUI API 测试失败
   - 服务器手动测试可以正常响应，但集成测试中无法连接

2. **合并硬条件不满足**:
   - 条件 1 (集成测试全绿): ❌ FAIL
   - 条件 2 (WebUI e2e 至少一条全绿): ❌ FAIL
   - 条件 3 (Server down 降级全绿): ✅ PASS

3. **通过项**:
   - 文件结构: 100%
   - Registry 合并: 100%
   - 6 层闸门: 100% (19/19 测试通过)
   - MCP Client: 100% (25/25 测试通过)
   - Server down 降级: 100% (2/2 测试通过)

---

## P0 问题清单

1. **MCP Server 连接超时问题** (CRITICAL)
   - **现象**: `MCPTimeoutError: Request timed out after 5000ms: tools/list`
   - **位置**: `agentos/core/mcp/client.py:328` → `agentos/core/capabilities/registry.py:486`
   - **影响**:
     - 8/17 集成测试失败
     - 14/18 WebUI API 测试失败
     - 工具无法加载到 Registry
   - **根因**:
     - Server 手动测试正常响应 initialize 请求
     - 但在集成测试 fixture 中，registry 尝试 `list_tools` 时超时
     - 可能是 asyncio 事件循环或 fixture 生命周期问题

2. **Server 注册与 Mock 冲突** (HIGH)
   - **现象**: 测试期望空列表，实际返回 echo-math server
   - **位置**: `test_list_servers_no_config`, `test_refresh_servers_no_servers`
   - **根因**: 配置文件 `mcp_servers.yaml` 被测试读取，mock 未生效
   - **解决**: 需要隔离测试配置或修复 mock

---

## 可合并条件

**当前状态: 不可合并**

**必须满足的条件**:

1. **[P0] 修复 MCP Server 连接超时问题**
   - 集成测试: `tests/integration/mcp/test_mcp_full_chain.py` 必须 100% 通过 (当前 52.9%)
   - 目标: 17/17 tests passed

2. **[P0] WebUI API e2e 测试至少一条全绿**
   - 最低要求: `TestCallMCPTool::test_call_tool_success` 返回 200 (当前 500)
   - 推荐目标: 所有 call_tool 测试通过 (当前 0/3)

3. **[P1] 修复 Server 列表测试**
   - 修复测试配置隔离问题
   - 目标: `TestListMCPServers` 和 `TestRefreshMCPServers` 全部通过

**验收标准**:
- 集成测试: 17/17 passed (100%)
- WebUI API 测试: 至少 10/18 passed (55%+)
- 无 P0 阻塞问题

---

## 附加说明

**已验证的正向指标**:
- 架构设计: 100% 符合预期
- 安全闸门: 100% 测试覆盖
- 单元测试: 100% 通过 (44/44 core tests)
- 降级处理: 100% 通过 (2/2 tests)

**问题定位建议**:
1. 检查 `tests/integration/mcp/conftest.py` 中的 `registry` fixture
2. 验证 asyncio 事件循环是否正确传递
3. 检查 `list_tools` 调用时 server 进程状态
4. 增加调试日志查看 stdin/stdout 交互细节

**验收重测触发条件**:
- P0 问题修复完成
- 集成测试通过率 > 90%
- WebUI API 测试通过率 > 50%
