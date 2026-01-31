# P0 修复报告: echo-math Server 连接

## 问题诊断

**症状**: MCP integration 测试中，8 个测试失败，错误为 `ToolNotFoundError: Tool not found: mcp:echo-math:echo`，伴随 `Request timed out after 5000ms: tools/list` 错误。

**根因**: CapabilityRegistry 的 `_refresh_cache()` 方法在 async context 中使用 `ThreadPoolExecutor` 创建新的 event loop 来调用 `_load_mcp_tools()`，导致 event loop 混乱：
- MCP client 的 subprocess 和 `_read_loop()` 绑定在原 event loop
- 新的 `tools/list` 请求在新 event loop 中发送
- Response 被原 event loop 的 `_read_loop` 读取
- 新 event loop 永远等不到响应
- 超时！

**诊断证据**:
```
# Setup 阶段（成功）
DEBUG    agentos.core.mcp.client:client.py:324 Sent request: tools/list (id=2)
DEBUG    agentos.core.mcp.client:client.py:392 Received response: 2
INFO     agentos.core.mcp.client:client.py:217 Found 3 tools from MCP server: echo-math

# Call 阶段（失败）
DEBUG    agentos.core.mcp.client:client.py:324 Sent request: tools/list (id=3)
ERROR    agentos.core.mcp.client:client.py:333 Request timed out: tools/list (id=3)
```

**精确定位**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/registry.py:218-224`

```python
try:
    loop = asyncio.get_running_loop()
    # We're in an event loop, create task
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        mcp_tools = executor.submit(
            lambda: asyncio.run(self._load_mcp_tools())  # ❌ 创建新 event loop！
        ).result()
```

## 修复方案

**修改文件**:
1. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/capabilities/registry.py`
2. `/Users/pangge/PycharmProjects/AgentOS/tests/integration/mcp/test_mcp_full_chain.py`

**修改内容**:

### 1. 添加 `refresh_async()` 和 `_refresh_cache_async()` 方法

```python
# Before: 只有同步版本
def refresh(self):
    """Force refresh of tool cache"""
    logger.info("Force refreshing capability cache")
    self._refresh_cache()

def _refresh_cache(self):
    """Refresh tool cache from all sources"""
    # ... 使用 ThreadPoolExecutor 创建新 event loop

# After: 添加 async 版本
def refresh(self):
    """Force refresh of tool cache"""
    logger.info("Force refreshing capability cache")
    self._refresh_cache()

async def refresh_async(self):
    """Force refresh of tool cache (async version)"""
    logger.info("Force refreshing capability cache (async)")
    await self._refresh_cache_async()

async def _refresh_cache_async(self):
    """Refresh tool cache from all sources (async version)"""
    logger.debug("Refreshing capability cache (async)")
    new_cache: Dict[str, ToolDescriptor] = {}

    # Load from Extension registry
    extension_tools = self._load_extension_tools()
    for tool in extension_tools:
        new_cache[tool.tool_id] = tool

    # Load from MCP servers
    if self.mcp_config_manager:
        mcp_tools = await self._load_mcp_tools()  # ✅ 在当前 event loop 中执行
        for tool in mcp_tools:
            new_cache[tool.tool_id] = tool

    self._cache = new_cache
    self._cache_timestamp = time.time()
    logger.info(f"Cache refreshed: {len(self._cache)} tools available")
```

### 2. 修改 `_refresh_cache()` 避免在 async context 中重新加载 MCP

```python
# Before: 在 async context 中创建新 event loop
if self.mcp_config_manager:
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            mcp_tools = executor.submit(
                lambda: asyncio.run(self._load_mcp_tools())  # ❌
            ).result()
    except RuntimeError:
        mcp_tools = asyncio.run(self._load_mcp_tools())

# After: 重用已连接的 MCP clients 的 cache
if self.mcp_config_manager:
    if self.mcp_clients:
        # ✅ 重用已有的 MCP tools，避免 event loop 冲突
        logger.debug(f"Reusing {len(self.mcp_clients)} existing MCP clients")
        mcp_tools_from_cache = [
            tool for tool in self._cache.values()
            if tool.source.type == 'mcp'
        ]
        for tool in mcp_tools_from_cache:
            new_cache[tool.tool_id] = tool
    else:
        # 只在没有 MCP clients 时才初始化
        try:
            loop = asyncio.get_running_loop()
            logger.warning(
                "Cannot load MCP tools in sync refresh within async context. "
                "MCP tools should be loaded explicitly via await registry.refresh_async()"
            )
        except RuntimeError:
            mcp_tools = asyncio.run(self._load_mcp_tools())
```

### 3. 更新测试 fixture 使用 `refresh_async()`

```python
# Before
@pytest_asyncio.fixture
async def capability_registry(echo_math_server_config):
    ext_registry = ExtensionRegistry()
    registry = CapabilityRegistry(ext_registry, mcp_config_path=config_path)
    await registry._load_mcp_tools()  # ❌ 不会更新 cache
    yield registry

# After
@pytest_asyncio.fixture
async def capability_registry(echo_math_server_config):
    ext_registry = ExtensionRegistry()
    registry = CapabilityRegistry(ext_registry, mcp_config_path=config_path)
    await registry.refresh_async()  # ✅ 同时加载 MCP tools 并更新 cache
    yield registry
```

**修复理由**:
1. **避免 event loop 混乱**: async 版本的 refresh 在当前 event loop 中执行，不会创建新的 loop
2. **重用已有连接**: 如果 MCP clients 已经连接，直接重用 cache 中的 tools，避免重复连接
3. **清晰的 API**: `refresh_async()` 明确用于 async context，`refresh()` 用于 sync context

## 验证结果

**修复前**:
```
FAILED tests/integration/mcp/test_mcp_full_chain.py::TestMCPRouterIntegration::test_invoke_echo_through_router
FAILED tests/integration/mcp/test_mcp_full_chain.py::TestMCPRouterIntegration::test_invoke_sum_through_router
FAILED tests/integration/mcp/test_mcp_full_chain.py::TestMCPRouterIntegration::test_invoke_multiply_through_router
FAILED tests/integration/mcp/test_mcp_full_chain.py::TestMCPGatesIntegration::test_planning_mode_allowed_for_readonly
FAILED tests/integration/mcp/test_mcp_full_chain.py::TestMCPGatesIntegration::test_execution_requires_spec_frozen
FAILED tests/integration/mcp/test_mcp_full_chain.py::TestMCPAuditIntegration::test_audit_events_emitted
FAILED tests/integration/mcp/test_mcp_full_chain.py::TestMCPToolFiltering::test_allow_tools_filter
FAILED tests/integration/mcp/test_mcp_full_chain.py::TestMCPEndToEnd::test_complete_workflow

8 failed, 9 passed, 3 warnings in 40.90s
```

**修复后**:
```
tests/integration/mcp/test_mcp_full_chain.py::TestMCPClientBasics::test_client_connect PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPClientBasics::test_list_tools PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPClientBasics::test_call_echo PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPClientBasics::test_call_sum PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPClientBasics::test_call_multiply PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPAdapter::test_mcp_tool_to_descriptor PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPAdapter::test_risk_level_inference PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPRouterIntegration::test_invoke_echo_through_router PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPRouterIntegration::test_invoke_sum_through_router PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPRouterIntegration::test_invoke_multiply_through_router PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPGatesIntegration::test_planning_mode_allowed_for_readonly PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPGatesIntegration::test_execution_requires_spec_frozen PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPAuditIntegration::test_audit_events_emitted PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPServerDown::test_graceful_degradation_when_server_down PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPServerDown::test_timeout_handling PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPToolFiltering::test_allow_tools_filter PASSED
tests/integration/mcp/test_mcp_full_chain.py::TestMCPEndToEnd::test_complete_workflow PASSED

17 passed, 3 warnings in 0.69s
```

## 测试通过率

- **tests/core/mcp**: 25/25 passed ✅
- **tests/integration/mcp**: 17/17 passed ✅
- **Total MCP tests**: 42/42 passed ✅

**性能改进**: 测试时间从 40.90s 降至 0.69s（提升 59 倍）

## 合并条件达成

- ✅ **条件 1**: 集成测试全绿 - 17/17 passed
- ✅ **条件 2**: 完成一次完整的 tool 调用 - `test_invoke_echo_through_router` 等测试验证了从 registry → router → mcp client → server → 返回的完整链路
- ✅ **条件 3**: Server down 降级全绿 - `test_graceful_degradation_when_server_down` 和 `test_timeout_handling` 都通过

## 结论

**PASS** ✅

问题已完全修复，所有 MCP 测试通过，集成链路畅通。修复方案优雅地解决了 async event loop 冲突问题，同时提升了性能。
