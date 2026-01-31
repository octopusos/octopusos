# Memory Proposals UI - Task #18

## Overview

The Memory Proposals UI provides a visual interface for reviewing and managing memory proposals submitted by agents that have the PROPOSE capability but lack direct WRITE access.

## Features

### 1. Proposals Dashboard

**Location**: Navigation Menu → Agent → Memory Proposals

**Features**:
- Filter proposals by status (Pending, Approved, Rejected, All)
- Real-time counts for each status category
- Auto-refresh every 30 seconds
- Manual refresh button

### 2. Proposal Card Display

Each proposal card shows:
- **Header**: Proposal ID, status badge, memory type, and scope
- **Content**: Memory key → value display
- **Proposer Info**: Agent ID and reason (if provided)
- **Review Info**: Reviewer ID, reason, and resulting memory ID (for approved/rejected)
- **Actions**: Approve/Reject buttons (for pending proposals only)

### 3. Approval/Rejection Workflow

**Approve a Proposal**:
1. Click the "Approve" button on a pending proposal
2. Optionally provide an approval reason (prompt dialog)
3. System creates memory item using reviewer's ADMIN capability
4. Proposal status updated to "approved"
5. Toast notification shows success with memory ID

**Reject a Proposal**:
1. Click the "Reject" button on a pending proposal
2. **Required**: Provide a rejection reason (prompt dialog)
3. System marks proposal as rejected
4. Toast notification confirms rejection

### 4. Notification Badge

A notification badge appears on the "Memory Proposals" menu item when there are pending proposals:
- Shows count of pending proposals
- Updates every 30 seconds
- Hidden when no pending proposals exist

## API Integration

The UI integrates with the following endpoints (from Task #17):

- `GET /api/memory/proposals` - List proposals with filtering
- `GET /api/memory/proposals/stats` - Get proposal counts by status
- `POST /api/memory/proposals/{id}/approve` - Approve a proposal (requires ADMIN)
- `POST /api/memory/proposals/{id}/reject` - Reject a proposal (requires ADMIN)

## User Roles

### Chat Agents (PROPOSE capability)
- Cannot directly access this UI
- Submit proposals via `POST /api/memory/propose`
- Proposals enter pending queue

### Admin Users (ADMIN capability)
- Access Memory Proposals UI
- Review pending proposals
- Approve or reject proposals
- See history of all proposals

## Implementation Details

### Files Created
1. `/agentos/webui/static/js/views/MemoryProposalsView.js` - Main view controller
2. `/agentos/webui/static/css/memory-proposals.css` - Styling

### Files Modified
1. `/agentos/webui/templates/index.html`:
   - Added CSS link
   - Added navigation menu item with badge
   - Added script tag for view controller

2. `/agentos/webui/static/js/main.js`:
   - Added routing case for 'memory-proposals'
   - Added `renderMemoryProposalsView()` function
   - Added `updateProposalsBadge()` function
   - Integrated badge updates into `startGovernanceBadgeUpdates()`

3. `/agentos/webui/api/memory.py`:
   - Reordered routes to put `/proposals/stats` before `/proposals/{proposal_id}` (fixes FastAPI route matching)

## Testing

### Manual Testing
1. Start webUI: `agentos webui`
2. Navigate to Memory Proposals
3. Verify empty state shows when no proposals exist
4. Create test proposal via API or chat agent
5. Verify proposal appears in UI
6. Test approve/reject workflow
7. Verify badge updates

### API Testing
```bash
# List proposals
curl "http://localhost:5002/api/memory/proposals?agent_id=user:current"

# Get stats
curl "http://localhost:5002/api/memory/proposals/stats?agent_id=user:current"

# Approve proposal
curl -X POST "http://localhost:5002/api/memory/proposals/{proposal_id}/approve" \
  -H "Content-Type: application/json" \
  -d '{"reviewer_id": "user:current", "reason": "Looks good"}'

# Reject proposal
curl -X POST "http://localhost:5002/api/memory/proposals/{proposal_id}/reject" \
  -H "Content-Type: application/json" \
  -d '{"reviewer_id": "user:current", "reason": "Not needed"}'
```

## Future Enhancements

1. **Batch Operations**: Select multiple proposals for bulk approve/reject
2. **Filtering**: Add filters by proposer, date range, memory type
3. **Search**: Full-text search in proposal content
4. **Comments**: Allow reviewers to add comments before approve/reject
5. **Delegation**: Allow admins to delegate review to other users
6. **Notifications**: Email/webhook notifications for pending proposals
7. **Analytics**: Dashboard showing approval rates, response times

## Related Documentation

- Task #15: Memory Capability Contract specification
- Task #16: Memory Capability checking mechanism
- Task #17: Memory Propose workflow backend implementation
- Task #19: Capability Contract documentation and tests
