# Decision Trace Viewer - Quick Start Guide

## What is the Decision Trace Viewer?

The Decision Trace Viewer is a powerful observability feature that answers the question: **"Why was this task allowed, paused, or blocked?"**

It provides a visual timeline of all governance decisions made for a specific task, complete with:
- Decision types (ALLOWED, BLOCKED, PAUSED, RETRY)
- Rules and policies applied
- Risk scores
- Detailed reasoning
- Raw decision snapshots

## How to Access

1. **Navigate to Tasks View**
   - Open AgentOS WebUI: `http://localhost:8080`
   - Click "Tasks" in the sidebar navigation

2. **Open Task Detail**
   - Click any task row in the table
   - Task detail drawer will slide in from the right

3. **Switch to Decision Trace Tab**
   - Click the "Decision Trace" tab in the drawer
   - Timeline will automatically load

## Understanding the Timeline

### Timeline Structure
```
[Timestamp]  ●━━━  [Event/Decision Details]
             │
[Timestamp]  ●━━━  [Event/Decision Details]
             │
[Timestamp]  ●━━━  [Event/Decision Details]
```

### Trace Item Types

#### 1. Supervisor Audit (Decision)
Shows governance decisions made by the Supervisor:

**Components:**
- **Event Type Badge**: Blue "SUPERVISOR AUDIT" label
- **Event Source**: e.g., `SUPERVISOR_ALLOWED`
- **Decision Badge**: Color-coded decision type
  - 🟢 ALLOWED (green)
  - 🔴 BLOCKED (red)
  - 🟠 PAUSED (orange)
  - 🔵 RETRY (blue)
- **Decision Reason**: Why this decision was made
- **Rules Applied**: Which policies were evaluated
- **Risk Score**: Numeric risk assessment (0-100)
- **JSON**: Expandable raw decision snapshot

**Example:**
```
2024-01-28 10:30:00  ●━━━  SUPERVISOR AUDIT
                          SUPERVISOR_ALLOWED

                          ✓ ALLOWED
                          Task approved: Risk score below threshold

                          Rules Applied:
                          [risk_threshold_check] [capability_validation]

                          Risk Score: 35/100

                          [Show JSON]
```

#### 2. Task Event
Shows task lifecycle events:

**Components:**
- **Event Type Badge**: Purple "TASK EVENT" label
- **Event Source**: e.g., `TASK_CREATED`, `TASK_UPDATED`
- **Metadata**: Additional context (source, etc.)
- **JSON**: Expandable raw event payload

**Example:**
```
2024-01-28 10:15:00  ●━━━  TASK EVENT
                          TASK_CREATED

                          Source: chat-handler

                          [Show JSON]
```

## Using Filters

### Search Filter
Located at top-right of the trace view.

**Usage:**
- Type any text to filter trace items
- Searches across all visible text (event types, reasons, rules, etc.)
- Real-time filtering (no need to press Enter)

**Examples:**
- Search "BLOCKED" → Shows only blocked decisions
- Search "risk" → Shows items mentioning risk
- Search "chat-handler" → Shows events from that source

### Decision Type Filter
Dropdown filter next to search box.

**Options:**
- All Decisions (default)
- ALLOWED
- BLOCKED
- PAUSED
- RETRY

**Usage:**
- Select a decision type to filter
- Only shows audit items with that decision
- Task events are hidden when filter is active

### Combining Filters
You can use both filters together:
- Select "BLOCKED" from dropdown
- Type "high_risk" in search
- Result: Only blocked decisions with high risk

## Viewing Raw JSON

Each trace item has a "Show JSON" link.

**To View:**
1. Click "Show JSON" link
2. Raw decision snapshot appears in a code block
3. Click "Hide JSON" to collapse

**JSON Structure (Audit):**
```json
{
  "decision_type": "ALLOWED",
  "rules_applied": ["risk_threshold_check"],
  "blocked_reason_code": null,
  "metadata": {
    "risk_score": 35,
    "reason": "Task approved: Risk score below threshold"
  }
}
```

**JSON Structure (Event):**
```json
{
  "event_type": "TASK_CREATED",
  "source": "chat-handler",
  "task_id": "task-123",
  "timestamp": "2024-01-28T10:15:00Z"
}
```

## Understanding Risk Scores

Risk scores are color-coded for quick assessment:

| Score Range | Color | Risk Level | Typical Decision |
|-------------|-------|------------|------------------|
| 0-49        | 🟢 Green | Low | Usually ALLOWED |
| 50-79       | 🟡 Yellow | Medium | May require review or PAUSED |
| 80-100      | 🔴 Red | High | Often BLOCKED |

## Pagination

If a task has many trace items (>50), pagination is enabled.

**How It Works:**
1. First 50 items load automatically
2. "Load More" button appears at bottom
3. Click to load next 50 items
4. Items are appended to timeline (no scroll reset)
5. Button disappears when all items loaded

## Common Scenarios

### Scenario 1: Task Blocked - Find Out Why
1. Open task in Task Detail drawer
2. Switch to "Decision Trace" tab
3. Look for red BLOCKED badges
4. Read the "Decision Reason" field
5. Check "Rules Applied" to see which policy blocked it
6. Review risk score if present
7. Expand JSON for complete context

### Scenario 2: Trace Decision History
1. Open task in Task Detail drawer
2. Switch to "Decision Trace" tab
3. Scroll through timeline (newest to oldest)
4. Observe decision changes over time
5. Look for PAUSED → RETRY → ALLOWED patterns
6. Understand how governance policies evolved

### Scenario 3: Investigate High-Risk Tasks
1. Open task in Task Detail drawer
2. Switch to "Decision Trace" tab
3. Look for red/yellow risk scores
4. Check which rules were applied
5. Review decision reasons
6. Use search filter: type "risk"
7. Analyze risk assessment patterns

### Scenario 4: Debug Policy Configuration
1. Open task in Task Detail drawer
2. Switch to "Decision Trace" tab
3. Filter by decision type (e.g., BLOCKED)
4. Check "Rules Applied" across multiple items
5. Expand JSON to see policy metadata
6. Identify if rules are firing correctly
7. Compare with expected behavior

## Troubleshooting

### Empty Timeline
**Issue:** "No decision trace available" message

**Possible Causes:**
1. Task has no governance decisions yet
2. Task created before governance system enabled
3. Decision records not persisted

**Solution:**
- Check if task has any audit records in database
- Verify governance system is running
- Check logs for any supervisor errors

### Error Loading Trace
**Issue:** Red error message in trace view

**Possible Causes:**
1. API endpoint not responding
2. Task ID invalid or not found
3. Database connection issue

**Solution:**
1. Check browser console for error details
2. Verify backend is running: `curl http://localhost:8080/api/governance/tasks/{task_id}/decision-trace`
3. Check backend logs for errors

### Missing Decision Details
**Issue:** Decision snapshot fields are empty

**Possible Causes:**
1. Old decision format (before schema update)
2. Incomplete decision recording
3. Snapshot field migration needed

**Solution:**
- Check decision_snapshot structure in database
- Verify supervisor is using latest decision format
- Run database migrations if needed

## Tips & Tricks

1. **Use Timestamps for Correlation**
   - Match trace timestamps with system logs
   - Correlate with external events (deployments, etc.)

2. **Search for Error Codes**
   - Type blocked_reason_code in search
   - Quickly find all instances of specific failures

3. **Compare Risk Scores**
   - Scroll through timeline
   - Observe how risk scores change over time
   - Identify risk pattern trends

4. **Export Decision Data**
   - Expand JSON for any decision
   - Copy-paste into analysis tool
   - Use for reports or incident reviews

5. **Mobile Access**
   - Timeline adapts to mobile screens
   - Vertical line hidden on narrow displays
   - All features work on touch devices

## API Reference

For programmatic access, use the governance API:

```bash
# Get decision trace for a task
GET /api/governance/tasks/{task_id}/decision-trace

# Parameters:
#   limit: Number of items per page (1-500, default: 200)
#   cursor: Pagination cursor (returned in next_cursor field)

# Example:
curl "http://localhost:8080/api/governance/tasks/task-123/decision-trace?limit=50"

# Response:
{
  "task_id": "task-123",
  "trace_items": [...],
  "next_cursor": "2024-01-28T10:00:00Z_456",
  "count": 50
}
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Esc` | Close task detail drawer |
| `Tab` | Navigate between tab buttons |
| `Enter` | Activate focused tab |
| `Ctrl/Cmd+F` | Focus browser search (works on timeline) |

## Related Features

- **Task Overview Tab**: Basic task information and metadata
- **Task Audit Tab**: Coming soon - full audit trail
- **Task History Tab**: Coming soon - state change history
- **Governance Stats**: Dashboard view of decision metrics

## Support

For issues or questions:
1. Check documentation: `/docs/governance/supervisor.md`
2. Review implementation: `DECISION_TRACE_VIEWER_DELIVERY.md`
3. Test standalone UI: `test_decision_trace_viewer.html`
4. Check API docs: `/api/governance/tasks/{task_id}/decision-trace`

---

**Version**: 1.0
**Last Updated**: 2024-01-28
