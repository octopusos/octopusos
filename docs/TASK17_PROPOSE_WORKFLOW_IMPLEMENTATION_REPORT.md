# Task #17: Memory Propose Workflow Implementation Report

**Status**: ✅ COMPLETED
**Date**: 2026-02-01
**Related**: ADR-012, Task #16

---

## Executive Summary

Successfully implemented the complete Memory Propose workflow - the **critical anti-hallucination mechanism** that prevents untrusted agents from polluting the Memory system. This implements a human-in-the-loop approval process for memories proposed by chat agents.

### Key Value Proposition

**Before**: Chat agents could directly write to Memory → Risk of hallucination pollution
**After**: Chat agents propose → Admin reviews → Only approved memories written

This is the defense-in-depth mechanism that prevents AI hallucinations from becoming permanent "memories".

---

## Implementation Overview

### 1. Core Module: `agentos/core/memory/proposals.py`

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/memory/proposals.py`

Complete implementation of the proposal service with:
- ✅ `propose_memory()` - Create proposals (requires PROPOSE capability)
- ✅ `approve_proposal()` - Approve and write to memory (requires ADMIN capability)
- ✅ `reject_proposal()` - Reject with reason (requires ADMIN capability)
- ✅ `list_proposals()` - Query proposals with filters
- ✅ `get_proposal()` - Get single proposal
- ✅ `get_proposal_stats()` - Statistics dashboard

**Key Features**:
```python
class MemoryProposalService:
    """Service for managing Memory proposals (PROPOSE capability workflow)"""

    def propose_memory(self, agent_id: str, memory_item: dict, reason: Optional[str] = None) -> str:
        """Create a memory proposal (requires PROPOSE capability)"""
        # Permission check
        self.permission_service.check_capability(agent_id, "propose")

        # Insert proposal into DB with PENDING status
        # Trigger admin notification (non-blocking)
        # Audit event

        return proposal_id

    def approve_proposal(self, reviewer_id: str, proposal_id: str, reason: Optional[str] = None) -> str:
        """Approve proposal and write to memory_items (requires ADMIN capability)"""
        # Permission check (ADMIN required)
        self.permission_service.check_capability(reviewer_id, "approve_proposal")

        # Write memory using reviewer's ADMIN capability
        memory_id = memory_service.upsert(agent_id=reviewer_id, memory_item=...)

        # Update proposal status to APPROVED
        # Link resulting_memory_id
        # Audit event

        return memory_id
```

### 2. MemoryService Integration

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/memory/service.py`

Added `propose()` method to MemoryService:

```python
def propose(self, agent_id: str, memory_item: dict, reason: Optional[str] = None) -> str:
    """
    Propose a memory (requires PROPOSE capability).

    This is an alternative to upsert() for agents with PROPOSE capability.
    The memory enters approval queue instead of being written directly.

    Returns:
        proposal_id (not memory_id - use approve_proposal to get memory_id)
    """
    from agentos.core.memory.proposals import get_proposal_service

    proposal_service = get_proposal_service()
    return proposal_service.propose_memory(
        agent_id=agent_id,
        memory_item=memory_item,
        reason=reason
    )
```

### 3. API Endpoints

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/memory.py`

Added 6 new endpoints:
- ✅ `POST /api/memory/propose` - Propose memory
- ✅ `GET /api/memory/proposals` - List proposals with filters
- ✅ `GET /api/memory/proposals/{id}` - Get proposal details
- ✅ `POST /api/memory/proposals/{id}/approve` - Approve proposal
- ✅ `POST /api/memory/proposals/{id}/reject` - Reject proposal
- ✅ `GET /api/memory/proposals/stats` - Get statistics

All endpoints enforce capability checks and return proper HTTP status codes:
- `403 Forbidden` - Permission denied
- `404 Not Found` - Proposal not found
- `400 Bad Request` - Invalid request (e.g., proposal not pending)

### 4. Database Schema

**Already Exists**: `agentos/store/migrations/schema_v46_memory_capabilities.sql`

Tables used:
```sql
CREATE TABLE memory_proposals (
    proposal_id TEXT PRIMARY KEY,
    proposed_by TEXT NOT NULL,
    proposed_at_ms INTEGER NOT NULL,
    memory_item TEXT NOT NULL,           -- JSON: Complete MemoryItem
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|approved|rejected
    reviewed_by TEXT,
    reviewed_at_ms INTEGER,
    review_reason TEXT,
    resulting_memory_id TEXT,            -- Memory ID after approval
    metadata TEXT
);
```

---

## Test Coverage

### Unit Tests (19 tests, 100% pass)

**File**: `/Users/pangge/PycharmProjects/AgentOS/tests/unit/core/memory/test_proposals.py`

Coverage:
- ✅ `test_propose_memory_success` - Happy path proposal
- ✅ `test_propose_without_capability` - Permission check enforcement
- ✅ `test_approve_proposal_success` - Approval workflow
- ✅ `test_approve_without_admin_capability` - Admin permission required
- ✅ `test_approve_nonexistent_proposal` - Error handling
- ✅ `test_approve_already_reviewed_proposal` - Idempotency
- ✅ `test_reject_proposal_success` - Rejection workflow
- ✅ `test_reject_requires_reason` - Rejection reason required
- ✅ `test_reject_without_admin_capability` - Admin permission required
- ✅ `test_list_proposals_filters` - Filter by status
- ✅ `test_list_proposals_pagination` - Pagination support
- ✅ `test_list_proposals_by_proposer` - Filter by proposer
- ✅ `test_get_proposal_stats` - Statistics aggregation
- ✅ `test_memory_service_propose_method` - MemoryService integration
- ✅ `test_propose_preserves_metadata` - Metadata preservation
- ✅ `test_end_to_end_propose_workflow` - Complete workflow
- ✅ `test_propose_memory_with_complex_content` - Complex nested content
- ✅ `test_list_proposals_requires_read_capability` - READ permission check
- ✅ `test_get_proposal_requires_read_capability` - READ permission check

**Test Results**:
```
============================= 19 passed in 0.24s ==============================
```

### Integration Tests (11 tests, 100% pass)

**File**: `/Users/pangge/PycharmProjects/AgentOS/tests/integration/test_propose_workflow.py`

Coverage:
- ✅ `test_propose_workflow_end_to_end` - Complete approve workflow
- ✅ `test_propose_via_memory_service` - MemoryService.propose() integration
- ✅ `test_reject_workflow_end_to_end` - Complete reject workflow
- ✅ `test_permission_enforcement_throughout_workflow` - Permission checks at every step
- ✅ `test_multiple_proposals_same_agent` - Multiple proposals from same agent
- ✅ `test_proposal_with_project_scope` - Project-scoped memories
- ✅ `test_proposal_stats_integration` - Statistics across workflow
- ✅ `test_conflict_resolution_with_approved_proposal` - Conflict resolution integration
- ✅ `test_transaction_rollback_on_approval_failure` - Transaction integrity
- ✅ `test_readonly_can_list_proposals` - READ capability can list
- ✅ `test_proposal_preserves_all_memory_fields` - Field preservation

**Test Results**:
```
============================= 11 passed in 0.19s ==============================
```

---

## Workflow Diagrams

### Happy Path: Propose → Approve

```
┌─────────────┐
│ Chat Agent  │
│ (PROPOSE)   │
└─────┬───────┘
      │
      │ 1. propose_memory()
      │    memory_item = {scope: "global", type: "preference", ...}
      │    reason = "User said: call me Alice"
      │
      v
┌─────────────────────────────┐
│ MemoryProposalService       │
│                             │
│ ✓ Check PROPOSE capability  │
│ ✓ Insert into proposals DB  │
│ ✓ Status = PENDING          │
│ ✓ Notify admins             │
│ ✓ Audit event               │
└─────┬───────────────────────┘
      │
      │ proposal_id = "01HX123..."
      │
      v
┌─────────────────────────────┐
│ Pending Queue               │
│ (awaiting admin review)     │
└─────┬───────────────────────┘
      │
      │ 2. Admin reviews
      │    list_proposals(status="pending")
      │
      v
┌─────────────┐
│    Admin    │
│   (ADMIN)   │
└─────┬───────┘
      │
      │ 3. approve_proposal()
      │    proposal_id = "01HX123..."
      │    reason = "Verified with user"
      │
      v
┌─────────────────────────────┐
│ MemoryProposalService       │
│                             │
│ ✓ Check ADMIN capability    │
│ ✓ Write to memory_items     │
│ ✓ Update proposal status    │
│ ✓ Link resulting_memory_id  │
│ ✓ Audit event               │
└─────┬───────────────────────┘
      │
      │ memory_id = "mem-abc123..."
      │
      v
┌─────────────────────────────┐
│     memory_items table      │
│  (approved memory written)  │
└─────────────────────────────┘
```

### Rejection Path

```
┌─────────────┐
│ Chat Agent  │
│ (PROPOSE)   │
└─────┬───────┘
      │
      │ propose_memory()
      │ (hallucinated info)
      │
      v
┌─────────────────────────────┐
│ Pending Queue               │
└─────┬───────────────────────┘
      │
      │ Admin reviews
      │
      v
┌─────────────┐
│    Admin    │
│   (ADMIN)   │
└─────┬───────┘
      │
      │ reject_proposal()
      │ reason = "Hallucinated information"
      │
      v
┌─────────────────────────────┐
│ MemoryProposalService       │
│                             │
│ ✓ Check ADMIN capability    │
│ ✓ Update status = REJECTED  │
│ ✓ Store rejection reason    │
│ ✓ Audit event               │
│ ✗ NO write to memory_items  │
└─────────────────────────────┘
      │
      │ Proposal marked rejected
      │ (memory NOT written)
      │
      v
┌─────────────────────────────┐
│   Rejected Proposals Log    │
│ (audit trail for analysis)  │
└─────────────────────────────┘
```

---

## Security & Permission Model

### Capability Requirements

| Operation | Required Capability | Purpose |
|-----------|-------------------|---------|
| `propose_memory()` | `PROPOSE` | Chat agents can propose |
| `approve_proposal()` | `ADMIN` | Only admins approve |
| `reject_proposal()` | `ADMIN` | Only admins reject |
| `list_proposals()` | `READ` | Anyone can view |
| `get_proposal()` | `READ` | Anyone can view |
| `get_proposal_stats()` | `READ` | Anyone can view |

### Default Agent Capabilities (from ADR-012)

```python
DEFAULT_CAPABILITIES = {
    # Tier 2: PROPOSE agents (require approval)
    "chat_agent": MemoryCapability.PROPOSE,
    "extraction_agent": MemoryCapability.PROPOSE,
    "suggestion_agent": MemoryCapability.PROPOSE,
    "learning_agent": MemoryCapability.PROPOSE,

    # Tier 4: ADMIN agents (full control)
    "system": MemoryCapability.ADMIN,
}

# Pattern rules:
# - user:* → ADMIN (all human users have admin access)
# - system → ADMIN (system operations)
```

---

## Design Decisions

### 1. Why Separate `propose()` from `upsert()`?

**Decision**: Two distinct methods rather than auto-routing based on capability.

**Rationale**:
- Explicit is better than implicit
- Makes the workflow clear to developers
- Avoids surprising behavior (chat agent calls `upsert()` but gets proposal instead)
- Return types differ (`proposal_id` vs `memory_id`)

### 2. Why Require Rejection Reason?

**Decision**: Rejection reason is mandatory, approval reason is optional.

**Rationale**:
- Rejections need audit trail for pattern analysis
- "Why did we reject this?" helps improve chat agents
- Approval reasons are nice-to-have but not critical
- Empty rejection reason provides no learning value

### 3. Why Non-Blocking Notifications?

**Decision**: Admin notifications fail gracefully (logged warning).

**Rationale**:
- Proposal creation must not fail due to notification issues
- Notification system may not be available in all environments
- Admins can poll via `list_proposals(status="pending")`
- Future: integrate with proper notification system

### 4. Why Store Complete `memory_item` in Proposal?

**Decision**: Store entire JSON rather than just key fields.

**Rationale**:
- Preserves all metadata (tags, sources, confidence)
- Enables complex memory types with nested content
- Admin can see exactly what will be written
- No information loss during approval

### 5. Why Link `resulting_memory_id`?

**Decision**: Track which memory was created from approved proposal.

**Rationale**:
- Enables traceability (memory → proposal → chat agent)
- Supports "undo" workflows (delete memory and revert proposal)
- Audit trail for "how did this memory get here?"
- Useful for debugging hallucination issues

---

## Integration Points

### 1. Memory Service

```python
# Chat agent with PROPOSE capability
memory_service = MemoryService()
proposal_id = memory_service.propose(
    agent_id="chat_agent",
    memory_item={...},
    reason="User said..."
)
# Returns proposal_id, NOT memory_id
```

### 2. Permission Service

```python
# All operations go through permission checks
permission_service.check_capability("chat_agent", "propose")
# Raises PermissionDenied if agent lacks capability
```

### 3. Audit System

```python
# All events logged (non-blocking)
emit_audit_event(
    event_type="memory_proposal_created",  # or approved/rejected
    metadata={...}
)
```

---

## API Usage Examples

### Propose Memory

```bash
curl -X POST /api/memory/propose \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "chat_agent",
    "memory_item": {
      "scope": "global",
      "type": "preference",
      "content": {"key": "preferred_name", "value": "Alice"}
    },
    "reason": "User said: call me Alice"
  }'

# Response:
{
  "proposal_id": "01HX123ABC...",
  "status": "pending"
}
```

### List Pending Proposals

```bash
curl "/api/memory/proposals?agent_id=admin&status=pending&limit=10"

# Response:
{
  "proposals": [
    {
      "proposal_id": "01HX123...",
      "proposed_by": "chat_agent",
      "proposed_at_ms": 1738406400000,
      "memory_item": {...},
      "status": "pending",
      "metadata": {"reason": "User said..."}
    }
  ],
  "total": 1
}
```

### Approve Proposal

```bash
curl -X POST /api/memory/proposals/01HX123ABC.../approve \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "user:admin",
    "reason": "Verified with user"
  }'

# Response:
{
  "memory_id": "mem-abc123...",
  "status": "approved"
}
```

### Reject Proposal

```bash
curl -X POST /api/memory/proposals/01HX123ABC.../reject \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "user:admin",
    "reason": "Hallucinated information - user never said this"
  }'

# Response:
{
  "status": "rejected",
  "success": true
}
```

### Get Statistics

```bash
curl "/api/memory/proposals/stats?agent_id=admin"

# Response:
{
  "pending": 5,
  "approved": 142,
  "rejected": 23,
  "total": 170
}
```

---

## Observability & Audit

### Audit Events

All proposal lifecycle events are logged:

```python
# Event types:
MEMORY_PROPOSAL_CREATED     # When proposal created
MEMORY_PROPOSAL_APPROVED    # When admin approves
MEMORY_PROPOSAL_REJECTED    # When admin rejects

# Example audit record:
{
  "event_type": "MEMORY_PROPOSAL_APPROVED",
  "metadata": {
    "proposal_id": "01HX123...",
    "agent_id": "chat_agent",
    "reviewer_id": "user:admin",
    "memory_id": "mem-abc123...",
    "timestamp_ms": 1738406400000
  }
}
```

### Permission Checks

Every capability check is audited:

```python
# Event type:
MEMORY_CAPABILITY_CHECK

# Example:
{
  "agent_id": "chat_agent",
  "operation": "propose",
  "capability": "propose",
  "allowed": true,
  "timestamp_ms": 1738406400000
}
```

---

## Future Enhancements

### 1. Notification System Integration

Currently just logs, future should trigger real notifications:

```python
def _notify_admins_new_proposal(self, proposal_id, agent_id, memory_item):
    # TODO: Integrate with notification system
    # - Email admins
    # - Slack notification
    # - Web UI badge count
    # - Push notification to mobile app
    pass
```

### 2. Auto-Approval Rules

High-confidence proposals from trusted agents:

```python
if memory_item.get("confidence", 0) >= 0.95:
    if agent_id in TRUSTED_AGENTS:
        # Auto-approve without admin review
        return auto_approve(proposal_id)
```

### 3. Batch Operations

Approve/reject multiple proposals at once:

```python
def approve_proposals_batch(self, reviewer_id: str, proposal_ids: List[str]) -> List[str]:
    """Approve multiple proposals in transaction"""
    pass
```

### 4. Proposal Expiration

Auto-reject stale proposals after N days:

```python
if proposal.proposed_at_ms < (utc_now_ms() - 7 * 24 * 60 * 60 * 1000):
    # Auto-reject proposals older than 7 days
    service.reject_proposal(
        reviewer_id="system",
        proposal_id=proposal_id,
        reason="Auto-rejected: proposal expired (>7 days)"
    )
```

---

## Acceptance Criteria ✅

All criteria from Task #17 met:

- ✅ proposals.py完整实现(propose/approve/reject)
- ✅ MemoryService.propose()方法添加
- ✅ API端点实现(propose/approve/reject/list)
- ✅ 通知系统hook(placeholder)
- ✅ Audit logging完整
- ✅ 单元测试(19个用例,100%通过)
- ✅ 集成测试(11个用例,100%通过)

---

## Files Changed

### New Files
1. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/memory/proposals.py` - 600+ lines
2. `/Users/pangge/PycharmProjects/AgentOS/tests/unit/core/memory/test_proposals.py` - 500+ lines
3. `/Users/pangge/PycharmProjects/AgentOS/tests/integration/test_propose_workflow.py` - 500+ lines

### Modified Files
1. `/Users/pangge/PycharmProjects/AgentOS/agentos/core/memory/service.py` - Added `propose()` method
2. `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/memory.py` - Added 6 endpoints + docstrings

---

## Next Steps (Task #18)

Now that propose workflow is complete, next task is:

**Task #18: UI显示Capability状态**

Requirements:
1. Display agent capability level in UI
2. Show pending proposals count (badge)
3. Proposal review queue interface
4. Approve/reject buttons with reason input
5. Proposal history view

This will complete the user-facing aspect of the Memory Capability Contract.

---

## Conclusion

Task #17 successfully implements the core defense mechanism against AI hallucination pollution. By requiring human approval for all chat agent memories, we ensure that:

1. **Safety**: No hallucinated info pollutes Memory
2. **Auditability**: Complete trail of all proposals
3. **Flexibility**: Admins can accept/reject with reasons
4. **Scalability**: Efficient queue-based workflow
5. **Observability**: Full logging and stats

This is a critical infrastructure piece for trustworthy AI agents.

---

**Report Generated**: 2026-02-01
**Implementation**: 胖哥 + Claude Sonnet 4.5
**Status**: ✅ PRODUCTION READY
