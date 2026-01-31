# MCP Acceptance Verification - Example Output

This document shows the complete output from running `./scripts/verify_mcp_acceptance.sh`.

## Successful Run (All Tests Pass)

```bash
$ ./scripts/verify_mcp_acceptance.sh
========================================
MCP Acceptance Verification
========================================

Environment:
  OS: Darwin 25.2.0
  Python: 3.14.2
  pytest: 9.0.2
  Node.js: v20.19.5

========================================
Running Test Suite: MCP Client (25 tests)
========================================
agentos/schemas/project.py:46
  /Users/pangge/PycharmProjects/AgentOS/agentos/schemas/project.py:46: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
    class ProjectSettings(BaseModel):

tests/core/mcp/test_mcp_client.py::test_mcp_client_connect
tests/core/mcp/test_mcp_client.py::test_mcp_client_timeout
  /Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/client.py:321: RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
    self.process.stdin.write(request_json.encode("utf-8"))
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/core/mcp/test_mcp_client.py::test_mcp_client_connect
  /Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/client.py:359: RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
    self.process.stdin.write(notification_json.encode("utf-8"))
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/core/mcp/test_mcp_client.py::test_mcp_client_disconnect
  /Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/client.py:175: RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
    self.process.terminate()
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 25 passed, 6 warnings in 0.70s ========================

✅ PASSED: 25/25 tests

========================================
Running Test Suite: Policy Gates (19 tests)
========================================
tests/core/capabilities/test_policy_gates.py::TestProjectBindingGate::test_project_binding_gate_requires_project PASSED [ 36%]
tests/core/capabilities/test_policy_gates.py::TestProjectBindingGate::test_project_binding_gate_allows_with_project PASSED [ 42%]
tests/core/capabilities/test_policy_gates.py::TestPolicyGate::test_policy_gate_blocks_blacklisted_effects PASSED [ 47%]
tests/core/capabilities/test_policy_gates.py::TestPolicyGate::test_policy_gate_allows_non_blacklisted PASSED [ 52%]
tests/core/capabilities/test_policy_gates.py::TestAdminTokenGate::test_admin_token_gate_requires_token PASSED [ 57%]
tests/core/capabilities/test_policy_gates.py::TestAdminTokenGate::test_admin_token_gate_validates_token PASSED [ 63%]
tests/core/capabilities/test_policy_gates.py::TestAdminTokenGate::test_admin_token_gate_allows_low_risk_without_token PASSED [ 68%]
tests/core/capabilities/test_policy_gates.py::TestFullGatePipeline::test_full_gate_pipeline_all_pass PASSED [ 73%]
tests/core/capabilities/test_policy_gates.py::TestFullGatePipeline::test_full_gate_pipeline_stops_at_first_failure PASSED [ 78%]
tests/core/capabilities/test_policy_gates.py::TestFullGatePipeline::test_disabled_tool_rejected PASSED [ 84%]
tests/core/capabilities/test_policy_gates.py::TestPolicyHelperMethods::test_requires_spec_freezing PASSED [ 89%]
tests/core/capabilities/test_policy_gates.py::TestPolicyHelperMethods::test_requires_admin_approval PASSED [ 94%]
tests/core/capabilities/test_policy_gates.py::TestPolicyHelperMethods::test_check_side_effects_allowed PASSED [100%]

=============================== warnings summary ===============================
agentos/schemas/project.py:15
  /Users/pangge/PycharmProjects/AgentOS/agentos/schemas/project.py:15: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
    class RiskProfile(BaseModel):

agentos/schemas/project.py:46
  /Users/pangge/PycharmProjects/AgentOS/agentos/schemas/project.py:46: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
    class ProjectSettings(BaseModel):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 19 passed, 2 warnings in 0.17s ========================

✅ PASSED: 19/19 tests

========================================
Running Test Suite: MCP Integration (17 tests)
========================================
tests/integration/mcp/test_mcp_full_chain.py::TestMCPRouterIntegration::test_invoke_sum_through_router PASSED [ 52%]
tests/integration/mcp/test_mcp_full_chain.py::TestMCPRouterIntegration::test_invoke_multiply_through_router PASSED [ 58%]
tests/integration/mcp/test_mcp_full_chain.py::TestMCPGatesIntegration::test_planning_mode_allowed_for_readonly PASSED [ 64%]
tests/integration/mcp/test_mcp_full_chain.py::TestMCPGatesIntegration::test_execution_requires_spec_frozen PASSED [ 70%]
tests/integration/mcp/test_mcp_full_chain.py::TestMCPAuditIntegration::test_audit_events_emitted PASSED [ 76%]
tests/integration/mcp/test_mcp_full_chain.py::TestMCPServerDown::test_graceful_degradation_when_server_down PASSED [ 82%]
tests/integration/mcp/test_mcp_full_chain.py::TestMCPServerDown::test_timeout_handling PASSED [ 88%]
tests/integration/mcp/test_mcp_full_chain.py::TestMCPToolFiltering::test_allow_tools_filter PASSED [ 94%]
tests/integration/mcp/test_mcp_full_chain.py::TestMCPEndToEnd::test_complete_workflow PASSED [100%]

=============================== warnings summary ===============================
agentos/schemas/project.py:15
  /Users/pangge/PycharmProjects/AgentOS/agentos/schemas/project.py:15: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
    class RiskProfile(BaseModel):

agentos/schemas/project.py:46
  /Users/pangge/PycharmProjects/AgentOS/agentos/schemas/project.py:46: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
    class ProjectSettings(BaseModel):

tests/integration/mcp/test_mcp_full_chain.py::TestMCPClientBasics::test_client_connect
  tests/integration/mcp/test_mcp_full_chain.py:91: PytestWarning: The test <Function test_client_connect> is marked with '@pytest.mark.asyncio' but it is not an async function. Please remove the asyncio mark. If the test is not marked explicitly, check for global marks applied via 'pytestmark'.
    @pytest.mark.asyncio

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 17 passed, 3 warnings in 0.75s ========================

✅ PASSED: 17/17 tests

========================================
FINAL RESULT: ✅ PASS (61/61)
========================================

All MCP acceptance tests passed!
```

## Exit Code

When all tests pass:
```bash
$ echo $?
0
```

When tests fail:
```bash
$ echo $?
1
```

## Example Failure Output

If some tests fail, you would see:

```bash
========================================
FINAL RESULT: ❌ FAIL (52/61)
========================================

Failed Suites:
  - MCP Integration (17 tests) (9/17 passed)

See above output for details.
```

## What This Verifies

The verification script confirms that:

1. **MCP Client Layer (25 tests)**: Core MCP protocol client implementation
   - Connection lifecycle management
   - Request/response handling
   - Error handling and timeouts
   - Tool discovery and invocation

2. **Policy Gates (19 tests)**: Security and governance layer
   - Project binding enforcement
   - Side effect validation
   - Admin token requirements
   - Risk level checks
   - Full gate pipeline integration

3. **MCP Integration (17 tests)**: End-to-end system integration
   - Router integration with capability registry
   - Policy gate application to MCP tools
   - Audit trail generation
   - Graceful degradation
   - Tool filtering and configuration

## Usage

```bash
# Run from project root
./scripts/verify_mcp_acceptance.sh

# Check exit code
echo $?

# Run with timestamp
./scripts/verify_mcp_acceptance.sh | tee "mcp_verification_$(date +%Y%m%d_%H%M%S).log"
```

## Troubleshooting

If the script fails to run:

1. **Python not found**: Install Python 3.9+ and ensure it's in PATH
2. **pytest not found**: Install pytest via `pip install pytest`
3. **Permission denied**: Run `chmod +x scripts/verify_mcp_acceptance.sh`
4. **Tests fail**: Check the detailed output above each failed suite

For more help, see [MCP Troubleshooting Guide](./TROUBLESHOOTING.md).
