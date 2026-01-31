# Dry-Run & Intent API Quick Reference

## Overview

Read-only APIs for accessing dry-run execution plans and intent structures.

**Base URL**: `http://localhost:8000`

---

## 🔍 Dry-Run API

### 1. Get Execution Plan

**Endpoint**: `GET /api/dryrun/{task_id}/plan`

**Purpose**: Retrieve execution plan with steps, dependencies, and risk markers

**Response**:
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
        "description": "Deploy authentication service",
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
    },
    "created_at": "2026-01-29T10:30:00Z"
  }
}
```

**Error Cases**:
- `TASK_NOT_FOUND`: Task ID doesn't exist
- `NO_DRY_RUN_RESULT`: Task has no dry-run plan

---

### 2. Get Plan Explanation

**Endpoint**: `GET /api/dryrun/{task_id}/explain`

**Purpose**: Get natural language explanation of execution plan

**Response**:
```json
{
  "ok": true,
  "data": {
    "task_id": "task_123",
    "summary": "This execution plan consists of 2 steps...",
    "rationale": "Selected deployment workflow based on intent analysis...",
    "alternatives": ["Manual review recommended for high-risk operations"],
    "key_decisions": [
      {
        "decision_type": "graph_structure",
        "decision": "Built execution graph with 2 nodes",
        "rationale": "Graph derived from intent workflows"
      }
    ],
    "structured_fields": {
      "risk_level": "medium",
      "requires_review": true
    }
  }
}
```

---

### 3. Validate Execution Plan

**Endpoint**: `GET /api/dryrun/{task_id}/validate`

**Purpose**: Validate plan against rules and constraints

**Response**:
```json
{
  "ok": true,
  "data": {
    "task_id": "task_123",
    "is_valid": true,
    "checks_passed": [
      "Evidence references",
      "Risk assessment",
      "Constraint enforcement",
      "Lineage tracking"
    ],
    "checks_failed": [],
    "warnings": ["High risk operation detected"],
    "suggested_fixes": []
  }
}
```

**Validation Checks**:
- ✓ Evidence references present
- ✓ Risk assessment completed
- ✓ Constraints enforced (DE1-DE6)
- ✓ Lineage information present

---

### 4. Generate Execution Proposal

**Endpoint**: `POST /api/dryrun/proposal`

**Purpose**: Generate new execution proposal (no actual execution)

**Request Body**:
```json
{
  "task_id": "task_123",
  "params": {
    "mode": "full_auto"
  },
  "actor": "webui_user"
}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "proposal_id": "proposal_xyz789",
    "task_id": "task_123",
    "status": "pending_review",
    "plan": {
      "plan_id": "dryexec_new123",
      "steps": [...],
      "total_steps": 5
    },
    "requires_approval": true,
    "created_at": "2026-01-29T10:35:00Z"
  }
}
```

**Important**:
- Proposal is stored with status `pending_review`
- No execution occurs
- Approval required before execution

---

## 🎯 Intent API

### 1. Get Intent Details

**Endpoint**: `GET /api/intent/{intent_id}`

**Purpose**: Retrieve complete intent structure

**Response**:
```json
{
  "ok": true,
  "data": {
    "intent_id": "intent_abc123",
    "type": "execution_intent",
    "version": "0.9.1",
    "nl_request": {
      "request": "Deploy the authentication service"
    },
    "scope": {
      "targets": {
        "files": ["src/auth.py"]
      }
    },
    "workflows": [...],
    "agents": [...],
    "commands": [],
    "risk": {
      "overall": "medium"
    },
    "constraints": {
      "max_commits": 5
    },
    "created_at": "2026-01-29T10:00:00Z"
  }
}
```

---

### 2. Get Builder Explanation

**Endpoint**: `GET /api/intent/{intent_id}/explain`

**Purpose**: Get NL input → intent → rationale flow

**Response**:
```json
{
  "ok": true,
  "data": {
    "intent_id": "intent_abc123",
    "nl_input": "Deploy the authentication service",
    "intent_structure": {
      "workflows": 1,
      "agents": 1,
      "commands": 0,
      "risk_level": "medium"
    },
    "rationale": "Selected deployment workflow based on intent keywords...",
    "selection_decisions": [
      {
        "type": "workflow",
        "selected": "wf_deploy_001",
        "reason": "Matched based on intent keywords",
        "evidence": ["wf_deploy_001"]
      }
    ],
    "evidence_summary": ["wf_deploy_001", "agent_deploy_001"]
  }
}
```

---

### 3. Compare Intents (Diff)

**Endpoint**: `GET /api/intent/{intent_id}/diff/{other_id}`

**Purpose**: Get field-level changes between two intents

**Response**:
```json
{
  "ok": true,
  "data": {
    "intent_a_id": "intent_abc123",
    "intent_b_id": "intent_xyz789",
    "changes": [
      {
        "field_path": "risk.overall",
        "change_type": "modified",
        "before_value": "low",
        "after_value": "high",
        "risk_hint": "Risk level changed - requires validation"
      },
      {
        "field_path": "agents",
        "change_type": "modified",
        "before_value": [1 agent],
        "after_value": [2 agents],
        "risk_hint": "Execution path modified"
      }
    ],
    "change_summary": "2 field(s) modified",
    "risk_assessment": "high",
    "conflict_count": 0
  }
}
```

**Change Types**:
- `added`: Field exists in B but not A
- `removed`: Field exists in A but not B
- `modified`: Field exists in both but values differ

---

### 4. Generate Merge Proposal

**Endpoint**: `POST /api/intent/{intent_id}/merge-proposal`

**Purpose**: Generate merge plan between two intents (no execution)

**Request Body**:
```json
{
  "intent_id": "intent_abc123",
  "target_intent_id": "intent_xyz789",
  "strategy": "auto",
  "actor": "webui_user"
}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "proposal_id": "merge_proposal_123",
    "intent_a_id": "intent_abc123",
    "intent_b_id": "intent_xyz789",
    "merge_strategy": "auto",
    "conflicts": [
      {
        "field": "scope",
        "type": "scope_conflict",
        "description": "Scopes differ - may target different files",
        "resolution": "requires_review"
      }
    ],
    "merged_intent": {
      "id": "merged_abc_xyz",
      "merged_from": ["intent_abc123", "intent_xyz789"],
      ...
    },
    "requires_approval": true,
    "status": "pending_review",
    "created_at": "2026-01-29T10:40:00Z"
  }
}
```

**Merge Strategies**:
- `auto`: Automatic merge if no conflicts
- `manual`: Manual resolution required
- `conflict_resolution`: Resolve specific conflicts

---

## 📋 Unified Response Format

All endpoints follow the Agent-API-Contract format:

```typescript
interface UnifiedResponse {
  ok: boolean;              // Success indicator
  data?: any;               // Response data (if ok=true)
  error?: string;           // Error message (if ok=false)
  hint?: string;            // User-friendly hint
  reason_code?: string;     // Machine-readable error code
}
```

**Common Reason Codes**:
- `TASK_NOT_FOUND`: Task ID doesn't exist
- `INTENT_NOT_FOUND`: Intent ID doesn't exist
- `NO_DRY_RUN_RESULT`: No dry-run plan available
- `NO_INTENT_DATA`: Task has no intent metadata
- `INTERNAL_ERROR`: Server error

---

## 🔐 Security & Constraints

### Read-Only Guarantees
- ✅ No actual execution (all endpoints are read-only)
- ✅ Proposals require approval (status: `pending_review`)
- ✅ All operations are audited

### Red Lines Enforced
- ❌ No subprocess/exec/eval calls
- ❌ No automatic execution
- ❌ No file system writes (except proposals)
- ❌ No WebUI exec run/rollback entry points

---

## 📊 Audit Trail

All operations are recorded in `task_audits` table:

**Event Types**:
- `dryrun_plan_accessed`
- `dryrun_explain_accessed`
- `dryrun_validate_accessed`
- `dryrun_proposal_generated`
- `intent_accessed`
- `intent_explain_accessed`
- `intent_diff_accessed`
- `intent_merge_proposal_generated`

**Query Audits**:
```python
from agentos.core.task.audit_service import TaskAuditService

audit_service = TaskAuditService()
audits = audit_service.get_task_audits(
    task_id="task_123",
    event_type="dryrun_plan_accessed"
)
```

---

## 🧪 Testing

### cURL Examples

**Get Plan**:
```bash
curl http://localhost:8000/api/dryrun/task_123/plan
```

**Validate Plan**:
```bash
curl http://localhost:8000/api/dryrun/task_123/validate
```

**Generate Proposal**:
```bash
curl -X POST http://localhost:8000/api/dryrun/proposal \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_123",
    "params": {"mode": "auto"},
    "actor": "test_user"
  }'
```

**Compare Intents**:
```bash
curl http://localhost:8000/api/intent/intent_a/diff/intent_b
```

### Python Examples

```python
import httpx

async def get_execution_plan(task_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/dryrun/{task_id}/plan"
        )
        return response.json()

async def compare_intents(intent_a: str, intent_b: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/intent/{intent_a}/diff/{intent_b}"
        )
        return response.json()
```

---

## 🚀 Integration Notes

### Frontend Integration

```javascript
// Fetch execution plan
async function getExecutionPlan(taskId) {
  const response = await fetch(`/api/dryrun/${taskId}/plan`);
  const result = await response.json();

  if (result.ok) {
    displayPlan(result.data);
  } else {
    showError(result.error, result.hint);
  }
}

// Compare intents
async function compareIntents(intentA, intentB) {
  const response = await fetch(`/api/intent/${intentA}/diff/${intentB}`);
  const result = await response.json();

  if (result.ok) {
    displayDiff(result.data.changes);
  }
}
```

### Workflow: Plan → Approve → Execute

```
1. GET /api/dryrun/{task_id}/plan       → Review plan
2. GET /api/dryrun/{task_id}/validate   → Check validation
3. POST /api/dryrun/proposal            → Generate proposal
4. [User approves proposal]             → Manual approval step
5. [Execution service]                  → Execute approved proposal
```

---

## 📚 See Also

- [AGENT_API_EXEC_DELIVERY.md](../../AGENT_API_EXEC_DELIVERY.md) - Implementation details
- [Agent-API-Contract](../../docs/contracts/agent_api_contract.md) - Unified response format
- [Task Service](../../agentos/core/task/service.py) - Task management
- [Dry Executor](../../agentos/core/executor_dry/dry_executor.py) - Plan generation
- [Intent Builder](../../agentos/core/intent_builder/builder.py) - Intent construction

---

## ✅ Quick Checklist

**For Frontend Developers**:
- [ ] Use unified response format (check `ok` field first)
- [ ] Display `hint` field for user-friendly errors
- [ ] Handle `reason_code` for programmatic error handling
- [ ] Never bypass approval flow for proposals
- [ ] Display risk markers prominently

**For Backend Integration**:
- [ ] Ensure task has `dry_run_result` in metadata
- [ ] Ensure task has `intent` in metadata
- [ ] Audit service configured correctly
- [ ] DryExecutor available for proposal generation
- [ ] Database migrations applied

---

**Last Updated**: 2026-01-29
**API Version**: v1.0
**Status**: Production Ready ✅
