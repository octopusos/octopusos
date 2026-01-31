# Agent-API-Exec: Dry-Run & Intent API Implementation

## 📋 Delivery Summary

**Ticket**: Agent-API-Exec - 实现dry-run与intent相关的只读API端点
**Wave**: Wave1-A3 & Wave1-A4
**Status**: ✅ **COMPLETED**
**Date**: 2026-01-29

---

## 🎯 Objectives

Implement read-only API endpoints for:
1. **Dry-Run API** (Wave1-A3): plan/explain/validate operations
2. **Intent API** (Wave1-A4): builder/evaluator result access

All endpoints follow the unified Agent-API-Contract response format.

---

## 📦 Deliverables

### 1. Dry-Run API Module (`agentos/webui/api/dryrun.py`) ✅

**Endpoints**:
```
GET  /api/dryrun/{task_id}/plan        # Get execution plan
GET  /api/dryrun/{task_id}/explain     # Get plan explanation
GET  /api/dryrun/{task_id}/validate    # Get validation results
POST /api/dryrun/proposal              # Generate execution proposal (no execution)
```

**Features**:
- ✅ Returns execution plan with steps, dependencies, risk markers
- ✅ Provides natural language explanation with rationale and alternatives
- ✅ Validates plans with rule checks, failure reasons, suggested fixes
- ✅ Generates proposals in "pending_review" state (no execution)
- ✅ All operations are audited via TaskAuditService
- ✅ Unified contract response format (ok/data/error/hint/reason_code)

**Response Models**:
- `ExecutionPlan`: Plan with steps structure and risk markers
- `PlanExplanation`: NL rationale with structured fields
- `ValidationResult`: Rule checks with failures and fixes
- `ProposalResponse`: Proposal with pending_review status

**Integration**:
- Extracts dry-run results from task metadata
- Uses `DryExecutor` for proposal generation
- Records all operations in task_audits table
- Compatible with existing TaskService and TaskManager

---

### 2. Intent API Module (`agentos/webui/api/intent.py`) ✅

**Endpoints**:
```
GET  /api/intent/{intent_id}                    # Get intent details
GET  /api/intent/{intent_id}/explain            # Get builder explain output
GET  /api/intent/{intent_id}/diff/{other_id}    # Get evaluator diff results
POST /api/intent/{intent_id}/merge-proposal     # Generate merge proposal (no execution)
```

**Features**:
- ✅ Returns intent details with NL request → intent structure
- ✅ Provides builder explanation with selection decisions and evidence
- ✅ Computes field-level diffs with before/after values and risk hints
- ✅ Generates merge proposals with conflict detection (no execution)
- ✅ All operations are audited
- ✅ Unified contract response format

**Response Models**:
- `IntentDetail`: Complete intent structure with workflows/agents/commands
- `BuilderExplanation`: NL input → intent → rationale + alternatives
- `IntentDiff`: Field-level changes with risk assessment
- `MergeProposal`: Merge plan with conflicts and approval requirement

**Integration**:
- Searches for intents in task metadata
- Uses `IntentBuilder` and `EvaluationResult` components
- Computes semantic diffs with risk hints
- Stores merge proposals in task metadata

---

### 3. App Integration (`agentos/webui/app.py`) ✅

**Changes**:
```python
# Import new API modules
from agentos.webui.api import ..., dryrun, intent

# Register routes
app.include_router(dryrun.router, tags=["dryrun"])
app.include_router(intent.router, tags=["intent"])
```

**Status**: ✅ Routes registered and available

---

### 4. Comprehensive Test Suite ✅

**Dry-Run Tests** (`tests/unit/webui/api/test_dryrun_api.py`):
- ✅ Helper function tests (graph conversion, risk extraction)
- ✅ GET /plan endpoint (success, not found, no result)
- ✅ GET /explain endpoint (success, empty state)
- ✅ GET /validate endpoint (success, failures, warnings)
- ✅ POST /proposal endpoint (success, no intent)
- ✅ Error handling across all endpoints
- ✅ Unified response format validation
- ✅ Full workflow integration test (plan → explain → validate)
- ✅ Edge cases (empty graphs, missing fields)

**Intent Tests** (`tests/unit/webui/api/test_intent_api.py`):
- ✅ Helper function tests (field changes, summary generation)
- ✅ GET /intent/{id} endpoint (success, not found)
- ✅ GET /intent/{id}/explain endpoint (success, minimal intent)
- ✅ GET /intent/{id}/diff/{other_id} endpoint (success, identical intents)
- ✅ POST /merge-proposal endpoint (success, conflicts, not found)
- ✅ Error handling across all endpoints
- ✅ Unified response format validation
- ✅ Full workflow integration test (detail → explain → diff → merge)
- ✅ Edge cases (missing fields, storage errors)

**Test Coverage**:
- 40+ test cases total
- Success paths, error paths, edge cases
- Mock-based unit tests (no database required)
- Async endpoint testing with pytest-asyncio

---

## ✅ Acceptance Criteria

### Contract Compliance
- [x] All endpoints return unified contract format (ok/data/error/hint/reason_code)
- [x] Error responses include reason_code and helpful hints
- [x] Success responses include properly structured data

### Read-Only Guarantees
- [x] No exec run entry points (DryExecutor only generates plans)
- [x] No rollback entry points
- [x] All write operations generate proposals only (pending_review state)
- [x] WebUI cannot directly trigger execution

### Audit & Traceability
- [x] All operations recorded in task_audits table
- [x] Proposal generation writes to audit log
- [x] Actor tracking in all operations
- [x] Event types distinguish operation kinds

### Diff Readability
- [x] Field-level changes with field_path + before/after
- [x] Change summaries (added/removed/modified counts)
- [x] Risk hints for significant changes
- [x] Structured conflict detection

### Integration
- [x] Compatible with existing TaskService
- [x] Compatible with AuditService
- [x] Reuses DryExecutor and IntentBuilder
- [x] Integrates with task metadata storage

### Testing
- [x] pytest tests for all endpoints
- [x] Coverage includes empty/error states
- [x] Unified response format validated
- [x] Integration tests for workflows

---

## 🔒 Red Lines (Enforced)

### No Execution
- ✅ No subprocess calls
- ✅ No os.system, exec, eval
- ✅ DryExecutor only generates plans
- ✅ All mutations require approval

### Audit Trail
- ✅ Every plan read is audited
- ✅ Every proposal generation is audited
- ✅ Actor and timestamp recorded
- ✅ Event types distinguish operations

### Approval Required
- ✅ All proposals marked "pending_review"
- ✅ requires_approval flag always true
- ✅ No automatic execution path

---

## 📊 API Endpoint Summary

### Dry-Run API (4 endpoints)
| Method | Endpoint | Purpose | Returns |
|--------|----------|---------|---------|
| GET | `/api/dryrun/{task_id}/plan` | Get execution plan | ExecutionPlan with steps |
| GET | `/api/dryrun/{task_id}/explain` | Get plan explanation | PlanExplanation with rationale |
| GET | `/api/dryrun/{task_id}/validate` | Validate plan | ValidationResult with checks |
| POST | `/api/dryrun/proposal` | Generate proposal | ProposalResponse (pending_review) |

### Intent API (4 endpoints)
| Method | Endpoint | Purpose | Returns |
|--------|----------|---------|---------|
| GET | `/api/intent/{intent_id}` | Get intent details | IntentDetail structure |
| GET | `/api/intent/{intent_id}/explain` | Get builder explanation | BuilderExplanation |
| GET | `/api/intent/{intent_id}/diff/{other_id}` | Compare intents | IntentDiff with changes |
| POST | `/api/intent/{intent_id}/merge-proposal` | Generate merge plan | MergeProposal (pending_review) |

---

## 🔄 Data Flow

### Dry-Run Plan Access
```
Client → GET /api/dryrun/{task_id}/plan
  → TaskService.get_task()
  → Extract dry_run_result from metadata
  → Convert graph to ExecutionPlan
  → Extract risk markers
  → TaskAuditService.record_operation()
  → Return UnifiedResponse{ok, data}
```

### Intent Diff Computation
```
Client → GET /api/intent/{intent_id}/diff/{other_id}
  → Get both intents from storage
  → Compute field-level changes
  → Assess risk (max of both intents)
  → Detect conflicts
  → Generate change summary
  → TaskAuditService.record_operation()
  → Return UnifiedResponse{ok, data: IntentDiff}
```

### Proposal Generation
```
Client → POST /api/dryrun/proposal
  → TaskService.get_task()
  → Extract intent from metadata
  → DryExecutor.run(intent) [no execution]
  → Generate proposal_id
  → Store in task metadata as pending_review
  → TaskAuditService.record_operation()
  → Return UnifiedResponse{ok, data: ProposalResponse}
```

---

## 📁 File Structure

```
agentos/webui/api/
├── dryrun.py                    # Dry-Run API (NEW)
├── intent.py                    # Intent API (NEW)
└── ...existing APIs...

tests/unit/webui/api/
├── test_dryrun_api.py          # Dry-Run tests (NEW)
├── test_intent_api.py          # Intent tests (NEW)
└── ...existing tests...

agentos/webui/
└── app.py                      # Router registration (MODIFIED)
```

---

## 🧪 Testing

### Run Tests
```bash
# All tests
pytest tests/unit/webui/api/test_dryrun_api.py -v
pytest tests/unit/webui/api/test_intent_api.py -v

# Specific test
pytest tests/unit/webui/api/test_dryrun_api.py::test_get_execution_plan_success -v

# Coverage
pytest tests/unit/webui/api/ --cov=agentos.webui.api --cov-report=html
```

### Test Examples

**Dry-Run Plan Test**:
```python
response = await get_execution_plan("task_123")
assert response.ok is True
assert response.data["total_steps"] == 2
assert "risk_markers" in response.data
```

**Intent Diff Test**:
```python
response = await get_intent_diff("intent_a", "intent_b")
assert response.ok is True
assert len(response.data["changes"]) > 0
assert response.data["risk_assessment"] == "high"
```

---

## 🔍 Usage Examples

### Example 1: Get Execution Plan
```bash
curl http://localhost:8000/api/dryrun/task_123/plan
```

Response:
```json
{
  "ok": true,
  "data": {
    "plan_id": "dryexec_abc123",
    "task_id": "task_123",
    "steps": [
      {
        "step_id": "node_1",
        "step_type": "workflow",
        "name": "Deploy Service",
        "dependencies": [],
        "risk_level": "medium",
        "evidence_refs": ["wf_deploy_001"]
      }
    ],
    "total_steps": 1,
    "risk_markers": {
      "high": [],
      "medium": ["Step 'Deploy Service' has medium risk"],
      "low": []
    }
  }
}
```

### Example 2: Generate Proposal
```bash
curl -X POST http://localhost:8000/api/dryrun/proposal \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_123",
    "params": {"mode": "full_auto"},
    "actor": "webui_user"
  }'
```

Response:
```json
{
  "ok": true,
  "data": {
    "proposal_id": "proposal_xyz789",
    "task_id": "task_123",
    "status": "pending_review",
    "requires_approval": true,
    "plan": { ... }
  }
}
```

### Example 3: Compare Intents
```bash
curl http://localhost:8000/api/intent/intent_a/diff/intent_b
```

Response:
```json
{
  "ok": true,
  "data": {
    "intent_a_id": "intent_a",
    "intent_b_id": "intent_b",
    "changes": [
      {
        "field_path": "risk.overall",
        "change_type": "modified",
        "before_value": "low",
        "after_value": "high",
        "risk_hint": "Risk level changed - requires validation"
      }
    ],
    "change_summary": "1 field(s) modified",
    "risk_assessment": "high",
    "conflict_count": 0
  }
}
```

---

## 🚀 Deployment Notes

### Prerequisites
- FastAPI application running
- TaskService and AuditService available
- Task metadata structure with intent/dry_run_result fields

### Startup Checks
1. Routes registered: `/api/dryrun/*` and `/api/intent/*`
2. Audit middleware active
3. Database migrations applied

### Monitoring
- Check audit table for API operation logs
- Monitor proposal creation rate
- Track validation failure patterns

---

## 📚 Related Documentation

- **Agent-API-Contract**: Unified response format specification
- **DryExecutor**: `agentos/core/executor_dry/dry_executor.py`
- **IntentBuilder**: `agentos/core/intent_builder/builder.py`
- **TaskService**: `agentos/core/task/service.py`
- **AuditService**: `agentos/core/task/audit_service.py`

---

## ✅ Sign-Off

**Implementation**: ✅ Complete
**Testing**: ✅ Comprehensive (40+ tests)
**Documentation**: ✅ This file
**Integration**: ✅ Routes registered
**Contract Compliance**: ✅ Unified format enforced
**Red Lines**: ✅ No execution paths

**Ready for Production**: ✅ YES

---

## 🎉 Summary

Successfully implemented Wave1-A3 (Dry-Run API) and Wave1-A4 (Intent API) with:
- 8 new API endpoints (4 dry-run + 4 intent)
- 40+ comprehensive test cases
- Full audit trail integration
- Unified contract response format
- Read-only guarantees (no execution)
- Approval-required workflow for all proposals

All acceptance criteria met. All red lines enforced. Ready for integration with WebUI frontend.
