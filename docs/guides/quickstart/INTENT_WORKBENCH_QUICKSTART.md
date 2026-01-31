# Intent Workbench - Quick Start Guide

**Wave2-C1: Intent Workbench View**
**Version:** 0.3.2

## Overview

The Intent Workbench is a WebUI view for reviewing NL→Intent transformations, comparing intent versions, and generating merge proposals with Guardian review integration.

## Quick Navigation

### From Task View
```javascript
// In TasksView detail drawer
window.navigateToView('intent-workbench', {
    task_id: 'task-123',
    intent_id: 'intent-456'
});
```

### Direct Access
Click **Governance** → **Intent Workbench** in the left navigation menu.

## Features at a Glance

### 1. Builder Explain Tab
**Purpose**: Review how NL requests are transformed into intents

**What you see**:
- Original NL request text
- Intent JSON structure (expandable tree)
- Transformation reasoning/rationale
- Alternative interpretations
- Confidence score
- Guardian review status

**Actions**:
- Copy intent JSON
- Search in JSON structure
- Submit for Guardian review

### 2. Evaluator Diff Tab
**Purpose**: Compare two intent versions field-by-field

**What you see**:
- Side-by-side intent comparison
- Field-level changes (Added/Deleted/Modified)
- Before/After values
- Risk assessment warnings
- Change navigation sidebar

**Actions**:
- Select two intents to compare
- Jump to specific changes
- Export diff as JSON
- Create merge proposal

### 3. Merge Proposal Tab
**Purpose**: Generate merge proposals for approval

**What you see**:
- Field-by-field selection UI
- Merge preview (read-only)
- Proposal status tracking
- Change count summary

**Actions**:
- Select which fields to keep (A or B)
- Preview merged result
- Generate proposal
- Submit for approval

### 4. History Tab
**Purpose**: View intent version timeline

**What you see**:
- Chronological version list
- Version badges and timestamps
- Author information
- Version comments

**Actions**:
- View specific version
- Compare with previous version

## Common Workflows

### Workflow 1: Review Intent Transformation
1. Navigate to Intent Workbench with `intent_id`
2. Review NL request in **Builder Explain** tab
3. Inspect intent structure in JSON viewer
4. Check transformation reasoning
5. If approved, submit for Guardian review

### Workflow 2: Compare Intent Versions
1. Go to **Evaluator Diff** tab
2. Enter two intent IDs
3. Click "Run Diff"
4. Review field-level changes
5. Check risk assessment
6. Export diff if needed

### Workflow 3: Merge Intents
1. Run diff between two intents
2. Click "Create Merge Proposal"
3. Select fields to keep (A or B)
4. Review merge preview
5. Generate proposal
6. Submit for approval

### Workflow 4: Guardian Review
1. Load intent in **Builder Explain**
2. Review intent structure and reasoning
3. Click "Submit for Guardian Review"
4. View review status in Guardian Status Card
5. Check verdict (PASS/FAIL/NEEDS_REVIEW)

## API Endpoints

### Intent Operations
```bash
# Load intent
GET /api/intent/{intent_id}

# Load intents for task
GET /api/intent/task/{task_id}

# Get builder explanation
GET /api/intent/{intent_id}/explain

# Run diff
POST /api/intent/evaluate/diff
Body: {
  "intent_a_id": "intent-123",
  "intent_b_id": "intent-456"
}

# Generate merge proposal
POST /api/intent/evaluate/merge-proposal
Body: {
  "intent_a_id": "intent-123",
  "intent_b_id": "intent-456",
  "selections": {
    "field.path": "a",  // or "b" or "manual"
    ...
  }
}

# Submit proposal for review
POST /api/intent/proposals/{proposal_id}/submit-review

# Get version history
GET /api/intent/{intent_id}/history
```

### Guardian Integration
```bash
# Submit for Guardian review
POST /api/guardian/reviews
Body: {
  "target_type": "intent",
  "target_id": "intent-123",
  "review_type": "INTENT_VERIFICATION"
}

# Get review status
GET /api/guardian/reviews?target_type=intent&target_id=intent-123
```

## UI Components

### JSON Tree Viewer
- **Expand/Collapse**: Click arrows to expand/collapse nodes
- **Copy**: Use toolbar button to copy entire JSON
- **Search**: Expand all nodes to search (Search button)

### Diff Viewer
- **Change Types**:
  - 🟢 Green: Added fields
  - 🔴 Red: Deleted fields
  - 🟡 Yellow: Modified fields
- **Navigation**: Click sidebar items to jump to changes
- **Risk Warnings**: Red banners indicate high-risk changes

### Merge Selector
- **Radio Options**:
  - Keep A: Use value from Intent A
  - Keep B: Use value from Intent B
  - Manual: Custom value (placeholder for future)
- **Preview**: Real-time JSON preview updates as you select

## Status Indicators

### Guardian Review Status
- **No Reviews**: Gray info icon
- **PASS**: Green badge
- **FAIL**: Red badge
- **NEEDS_REVIEW**: Yellow badge

### Merge Proposal Status
- **PENDING**: Yellow badge
- **APPROVED**: Green badge
- **REJECTED**: Red badge

## Error Handling

### Empty States
Each tab shows helpful guidance when no data is available:
- **Explain**: "Enter an Intent ID above to view..."
- **Diff**: "Select two intents to compare..."
- **Merge**: "Run a diff comparison first..."
- **History**: "Intent version history will appear here..."

### Error States
Clear error messages with:
- Error icon
- Error description
- Retry button

### Loading States
- Skeleton screens during data fetch
- Spinners for actions
- Progress indicators

## Keyboard Shortcuts

*Future Enhancement*
- `Ctrl+E`: Jump to Explain tab
- `Ctrl+D`: Jump to Diff tab
- `Ctrl+M`: Jump to Merge tab
- `Ctrl+H`: Jump to History tab

## Best Practices

### 1. Review Before Merge
Always review the diff carefully before creating a merge proposal. Check:
- Risk assessment warnings
- Security/permission changes
- Data structure modifications

### 2. Use Guardian Review
Submit intents for Guardian review when:
- High-risk operations detected
- Security constraints modified
- Production deployment intent
- Compliance requirements

### 3. Document Changes
When submitting merge proposals:
- Add clear commit messages
- Document why fields were chosen
- Note any manual interventions

### 4. Version Control
Use the History tab to:
- Track intent evolution
- Compare with previous versions
- Understand change rationale

## Troubleshooting

### Issue: Intent not loading
**Solution**: Check console for API errors. Verify intent_id is correct.

### Issue: Diff shows no changes
**Solution**: Ensure intent A and B are different versions.

### Issue: Guardian status not updating
**Solution**: Manually refresh the page or click Refresh button.

### Issue: Merge preview not updating
**Solution**: Ensure all changed fields have a selection (A or B).

### Issue: Navigation not working
**Solution**: Check that `window.navigateToView` is available (should be in main.js).

## Developer Notes

### Adding Custom Diff Logic
Modify `runDiff()` method in IntentWorkbenchView.js:
```javascript
async runDiff(intentA, intentB) {
    // Your custom diff logic
}
```

### Extending Merge Options
Add custom merge logic in `generateMergeProposal()`:
```javascript
async generateMergeProposal() {
    // Process manual selections
    // Apply custom merge rules
}
```

### Styling Customization
Edit `/static/css/intent-workbench.css`:
```css
/* Custom theme colors */
.intent-workbench { ... }
```

## Files Reference

```
agentos/webui/static/
├── js/views/
│   └── IntentWorkbenchView.js      # Main view class
├── css/
│   └── intent-workbench.css        # View styles
└── js/
    └── main.js                     # Routing (renderIntentWorkbenchView)

agentos/webui/templates/
└── index.html                      # Navigation menu + CSS/JS refs
```

## Related Documentation

- **Architecture**: See `INTENT_WORKBENCH_DELIVERY.md`
- **API Specs**: See `/api/intent/*` endpoint documentation
- **Guardian Integration**: See Guardian workflow documentation
- **Component Library**: See JsonViewer and GuardianReviewPanel docs

## Support

**Questions?** Contact the AgentOS Frontend Team
**Issues?** File in repository with label `webui-intent-workbench`
**Feature Requests?** Add to backlog with label `enhancement`

---

**Quick Tip**: Use `Ctrl+Shift+I` to open browser DevTools and inspect the view's state in the Console.
