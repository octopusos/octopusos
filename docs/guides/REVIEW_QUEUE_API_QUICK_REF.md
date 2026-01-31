# Review Queue API - Quick Reference

## Overview
Human review interface for BrainOS improvement proposals. Enables approve/reject/defer workflow with full audit trail.

## Endpoints

### 1. List Proposals
```
GET /api/v3/review-queue
```

**Query Parameters:**
- `status`: Filter by status (pending/accepted/rejected/deferred)
- `risk_level`: Filter by risk (LOW/MEDIUM/HIGH)
- `change_type`: Filter by type (expand_keyword/adjust_threshold/etc.)
- `time_range`: Time filter (24h/7d/30d/custom)
- `start_time`: Custom range start (ISO format)
- `end_time`: Custom range end (ISO format)
- `limit`: Max results (1-200, default 50)
- `offset`: Pagination offset (default 0)

**Example:**
```bash
curl "http://localhost:8000/api/v3/review-queue?status=pending&risk_level=LOW&limit=10"
```

### 2. Get Proposal Details
```
GET /api/v3/review-queue/{proposal_id}
```

Returns:
- Complete proposal information
- Evidence with statistical metrics
- Decision comparison (active vs shadow)
- Proposal history (audit trail)

**Example:**
```bash
curl "http://localhost:8000/api/v3/review-queue/BP-017A3C"
```

### 3. Approve Proposal
```
POST /api/v3/review-queue/{proposal_id}/approve
```

**Request Body:**
```json
{
  "reviewed_by": "admin",
  "notes": "Evidence is solid, proceed with implementation"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v3/review-queue/BP-017A3C/approve" \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "admin", "notes": "LGTM"}'
```

### 4. Reject Proposal
```
POST /api/v3/review-queue/{proposal_id}/reject
```

**Request Body:**
```json
{
  "reviewed_by": "admin",
  "reason": "Risk too high for production deployment"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v3/review-queue/BP-017A3C/reject" \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "admin", "reason": "Risk too high"}'
```

### 5. Defer Proposal
```
POST /api/v3/review-queue/{proposal_id}/defer
```

**Request Body:**
```json
{
  "reviewed_by": "admin",
  "reason": "Need more data before making decision"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v3/review-queue/BP-017A3C/defer" \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "admin", "reason": "Need more data"}'
```

## Response Format

All endpoints return consistent JSON:
```json
{
  "ok": true,
  "data": { ... },
  "error": null
}
```

Error response:
```json
{
  "ok": false,
  "data": null,
  "error": "Error message"
}
```

## Proposal States

```
pending → accepted → (implemented)
        → rejected
        → deferred → (can be reviewed again)
```

## Key Features

1. **Filtering**: Status, risk level, change type, time range
2. **Evidence**: Statistical metrics, improvement rates
3. **Comparison**: Active vs shadow performance data
4. **Audit**: Complete history trail for each proposal
5. **Immutability**: Reviewed proposals cannot be modified
6. **Validation**: All inputs validated, clear error messages

## Integration Points

- **ImprovementProposalStore** (Task #7): Proposal persistence
- **DecisionComparator** (Task #5): Evidence metrics
- **Audit System** (Task #3): Action logging

## Files

- API: `/agentos/webui/api/review_queue.py`
- Tests: `/tests/unit/webui/api/test_review_queue_api.py`
- Routes: Registered in `/agentos/webui/app.py`
- Audit: Event types in `/agentos/core/audit.py`

## Testing

```bash
# Run all tests
pytest tests/unit/webui/api/test_review_queue_api.py -v

# Run specific test
pytest tests/unit/webui/api/test_review_queue_api.py::TestApproveProposal::test_approve_success -v
```

All 18 tests passing ✅

## Common Use Cases

### Reviewing Pending Proposals
```bash
# 1. List pending proposals
curl "http://localhost:8000/api/v3/review-queue?status=pending"

# 2. Get details for specific proposal
curl "http://localhost:8000/api/v3/review-queue/BP-017A3C"

# 3. Approve if evidence is good
curl -X POST "http://localhost:8000/api/v3/review-queue/BP-017A3C/approve" \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "admin", "notes": "Approved"}'
```

### Finding High-Risk Proposals
```bash
curl "http://localhost:8000/api/v3/review-queue?risk_level=HIGH&status=pending"
```

### Reviewing Recent Proposals
```bash
curl "http://localhost:8000/api/v3/review-queue?time_range=24h&status=pending"
```

## Security Notes

- All review actions are logged to audit system
- Reviewer identity is tracked
- Reviewed proposals are immutable
- Timestamps recorded for all actions
- Complete history maintained

## Performance

- Database indexed on status, created_at, affected_version_id
- Pagination prevents large result sets
- Time range filtering reduces query scope
- Default limit: 50 items (max 200)

## Next Steps

After approval, proposals can be:
1. Implemented by Task #11 (Shadow → Active Migration)
2. Tracked in proposal history
3. Monitored for production performance

---

**Status**: ✅ Production Ready
**Test Coverage**: 18/18 tests passing
**Documentation**: Complete
