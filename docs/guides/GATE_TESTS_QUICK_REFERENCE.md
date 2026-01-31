# Gate Tests Quick Reference

**File**: `/Users/pangge/PycharmProjects/AgentOS/tests/integration/test_mode_phase_gate_e2e.py`

## Quick Run Commands

```bash
# Run all gate tests
pytest tests/integration/test_mode_phase_gate_e2e.py -v

# Run only core scenarios (6 tests)
pytest tests/integration/test_mode_phase_gate_e2e.py::TestConversationModeGates -v

# Run specific scenario
pytest tests/integration/test_mode_phase_gate_e2e.py::TestConversationModeGates::test_scenario_1_default_security -v

# Run with output
pytest tests/integration/test_mode_phase_gate_e2e.py -v -s

# Generate HTML report
pytest tests/integration/test_mode_phase_gate_e2e.py --html=gate_report.html --self-contained-html
```

## Test Structure

```
14 tests total:
├── TestConversationModeGates (6 core scenarios)
│   ├── test_scenario_1_default_security
│   ├── test_scenario_2_mode_switch_no_privilege_escalation
│   ├── test_scenario_3_explicit_execution_switch
│   ├── test_scenario_4_plan_mode_blocks_execution
│   ├── test_scenario_5_task_mode_allows_execution
│   └── test_scenario_6_audit_completeness
│
├── TestPhaseGateEdgeCases (6 edge cases)
│   ├── test_invalid_mode_rejected
│   ├── test_invalid_phase_rejected
│   ├── test_phase_gate_validation
│   ├── test_phase_gate_is_allowed
│   ├── test_multiple_mode_switches
│   └── test_concurrent_phase_changes
│
└── TestPhaseGateWithCommunication (2 integration tests)
    ├── test_comm_search_blocked_in_planning
    └── test_comm_fetch_allowed_in_execution
```

## 6 Core Scenarios Summary

| # | Scenario | Verification |
|---|----------|--------------|
| 1 | Default Security | `mode=chat`, `phase=planning`, `/comm` blocked |
| 2 | Mode Switch No Escalation | Mode change doesn't affect phase |
| 3 | Explicit Execution Switch | Phase switch requires confirmation |
| 4 | Plan Mode Blocks Execution | Plan mode enforces planning |
| 5 | Task Mode Flexible | Allows but doesn't force execution |
| 6 | Audit Completeness | Phase changes audited |

## Expected Output

```
======================== 14 passed, 2 warnings in 0.36s ========================
```

## Key Concepts Tested

### 1. Mode vs Phase Independence
- `conversation_mode`: UI/UX context (chat/discussion/plan/development/task)
- `execution_phase`: Security context (planning/execution)
- **Independent**: Changing mode doesn't change phase

### 2. Phase Gate Security
- Planning phase: Blocks `comm.*` operations
- Execution phase: Allows `comm.*` operations
- Fail-safe: Unknown phase = blocked

### 3. Explicit Opt-In
- Execution phase requires explicit user action
- No automatic escalation
- Confirmation required

## Integration Points

- **ChatService**: Session and metadata management
- **SessionStore**: SQLite persistence
- **PhaseGate**: Security enforcement
- **CommunicationAdapter**: External communication
- **Audit**: Event logging (graceful degradation)

## Common Issues

### Issue: Audit logs not appearing
**Cause**: Async writer not initialized in test
**Solution**: Tests use mocked writer with immediate execution
**Impact**: None - graceful degradation tested

### Issue: Database locked
**Cause**: Multiple connections to temp DB
**Solution**: Each test gets isolated temp DB
**Impact**: None - proper cleanup

## Files Covered

```
agentos/core/chat/
├── service.py (ChatService)
├── models.py (ConversationMode)
├── guards/phase_gate.py (PhaseGate)
└── communication_adapter.py (CommunicationAdapter)

agentos/webui/
└── store/session_store.py (SessionStore)

agentos/core/capabilities/
└── audit.py (Audit logging)
```

## Status

- **Test Count**: 14 tests
- **Pass Rate**: 100% (14/14)
- **Execution Time**: ~0.36 seconds
- **Status**: ✅ ALL PASSED
