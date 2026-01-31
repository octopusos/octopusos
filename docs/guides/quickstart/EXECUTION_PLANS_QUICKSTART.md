# Execution Plans View - Quick Start Guide

## 🚀 What Was Delivered

A complete frontend view for visualizing dry-run execution plans with proposal/approval workflow.

## 📁 Files Created

```
agentos/webui/static/js/views/ExecutionPlansView.js    # View component (800 lines)
agentos/webui/static/css/execution-plans.css           # Styles (1,100 lines)
test_execution_plans_view.html                         # Test harness
EXECUTION_PLANS_VIEW_DELIVERY.md                       # Full documentation
```

## 📝 Files Modified

```
agentos/webui/static/js/views/TasksView.js             # Added plan tab
agentos/webui/templates/index.html                     # Added CSS/JS includes
```

## 🎯 Features

### 1. Plan Overview
- Plan ID, Task ID, Status, Duration
- Color-coded status badges
- Plan description

### 2. Validation Report
- ✅ Passed rules
- ❌ Failed rules with hints
- 💡 Fix suggestions

### 3. Steps Timeline
- Visual timeline with dependencies
- Risk indicators (low/medium/high)
- Collapsible step details
- Inputs/outputs display

### 4. Explanation Panel
- Markdown summary
- Rationale
- Alternatives considered
- Known risks

### 5. Artifact Links
- Related files list
- Type icons and sizes

### 6. Actions (No Execution!)
- ✅ Generate Proposal
- ✅ Request Approval
- ✅ Refresh Status
- ✅ Export Plan
- ❌ No "Run Now" button

## 🔌 Integration Points

### From Task Detail View
```javascript
// Task drawer → "Execution Plan" tab
// Shows embedded mini-plan
// "View Full Plan" button opens standalone view
```

### Standalone Access
```
URL: /execution-plans?task_id=task-123
Or:  /execution-plans?plan_id=plan-456
```

### Navigation Menu
```
Governance → Execution Plans
```

## 🔗 API Endpoints (Need Implementation)

```javascript
GET  /api/exec/tasks/{task_id}/plan          // Get plan for task
GET  /api/exec/plans/{plan_id}               // Get plan by ID
POST /api/exec/plans/{plan_id}/proposal      // Generate proposal
POST /api/exec/plans/{plan_id}/request-approval // Request approval
```

## 📊 API Response Format

```json
{
  "plan_id": "plan-123",
  "task_id": "task-789",
  "status": "validated",
  "description": "Plan description",
  "created_at": "2026-01-29T10:00:00Z",
  "estimated_duration_ms": 45000,
  "validation": {
    "rules_passed": [...],
    "rules_failed": [...]
  },
  "steps": [
    {
      "name": "Step Name",
      "type": "analysis",
      "description": "What this step does",
      "estimated_duration_ms": 5000,
      "risk_level": "low|medium|high",
      "depends_on": ["Previous Step"],
      "inputs": {...},
      "outputs": {...}
    }
  ],
  "explanation": {
    "summary": "Markdown text",
    "rationale": "Why this plan",
    "alternatives": [...],
    "risks": [...]
  },
  "artifacts": [...]
}
```

## 🧪 Testing

```bash
# Open test harness
open test_execution_plans_view.html

# Or in browser
file:///path/to/AgentOS/test_execution_plans_view.html
```

Test includes:
- Mock API client
- Sample execution plan
- All view features
- Interactive testing

## 🎨 Theming

Colors match Vuexy theme:
- Primary: #0066cc
- Success: #28a745
- Warning: #ffc107
- Danger: #dc3545
- Gray shades: #f8f9fa → #212529

Risk colors:
- 🟢 Low: Green (#28a745)
- 🟡 Medium: Yellow (#ffc107)
- 🔴 High: Red (#dc3545)

## 📱 Responsive Breakpoints

- Desktop: 1400px+ (optimal)
- Tablet: 768px - 1399px
- Mobile: < 768px

## ⚙️ View Lifecycle

```javascript
// 1. Initialize
new ExecutionPlansView(container)

// 2. Load plan
loadPlanForTask(taskId) or loadPlanById(planId)

// 3. Render
renderPlan(data)

// 4. Cleanup
view.destroy()
```

## 🔒 Security Features

- No direct execution capability
- Proposal workflow required
- Permission checks
- All actions via API
- Audit trail support

## 📋 State Management

```javascript
// View states
- Loading: Shows spinner
- Loaded: Displays plan
- Empty: No plan available
- Error: API failure
- No Permission: Access denied
```

## 🛠️ Utility Functions

```javascript
formatTimestamp(ts)      // Pretty dates
formatDuration(ms)       // 5s, 2m 30s, etc.
formatStatus(status)     // Status labels
formatValue(value)       // Input/output display
formatSize(bytes)        // File sizes
renderMarkdown(text)     // Simple markdown
```

## 🔧 Customization

### Add New Step Type
```javascript
// In renderStep(), add to type icons:
const typeIcons = {
  'analysis': 'search',
  'modification': 'edit',
  'validation': 'check',
  'reporting': 'description',
  'your-type': 'your-icon'  // Add here
};
```

### Add New Risk Level
```css
/* In execution-plans.css */
.risk-badge.risk-critical {
    background: #8b0000;
    color: white;
}
```

### Custom Artifact Type
```javascript
// In getArtifactIcon()
const iconMap = {
  'file': 'description',
  'config': 'settings',
  'your-type': 'your-icon'  // Add here
};
```

## 🐛 Troubleshooting

### View Not Loading
```javascript
// Check console for errors
// Verify CSS/JS included in index.html
// Check if ExecutionPlansView is defined
console.log(window.ExecutionPlansView);
```

### API Errors
```javascript
// Mock API client for testing
window.apiClient = {
  get: async (url) => ({
    ok: true,
    data: { /* your test data */ }
  })
};
```

### Styling Issues
```css
/* Check CSS is loaded */
/* Verify execution-plans.css in <head> */
/* Check browser console for 404s */
```

## 📚 Related Documentation

- `EXECUTION_PLANS_VIEW_DELIVERY.md` - Complete implementation details
- `agentos/webui/static/js/views/TasksView.js` - Integration example
- `test_execution_plans_view.html` - Working test case

## 🚦 Next Steps

1. **Implement Backend API**
   - Create `/api/exec/*` endpoints
   - Connect to execution engine
   - Add validation logic

2. **Guardian Integration**
   - Link approval workflow
   - Add review requirements
   - Implement audit trail

3. **Enhanced Features**
   - Real-time status updates
   - Dependency graph view
   - Plan comparison
   - Execution history

## 💡 Tips

- Use test harness for rapid iteration
- Check TasksView for integration patterns
- Follow existing view conventions
- Mock API during frontend development
- Test all state scenarios (empty, error, loading)

## 📞 Support

For questions or issues:
1. Check `EXECUTION_PLANS_VIEW_DELIVERY.md`
2. Review test harness code
3. Inspect TasksView integration
4. Check browser console for errors

---

**Quick Links**:
- View: `agentos/webui/static/js/views/ExecutionPlansView.js`
- CSS: `agentos/webui/static/css/execution-plans.css`
- Test: `test_execution_plans_view.html`
- Docs: `EXECUTION_PLANS_VIEW_DELIVERY.md`
