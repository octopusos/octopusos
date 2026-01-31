# PR-4: Router Visualization Enhancement - Implementation Complete

> **Status**: ✅ COMPLETE
> **Date**: 2026-01-28
> **Target**: WebUI routing visualization for Task Router system
> **Dependencies**: Requires PR-1/PR-2 backend Router implementation

---

## 🎯 Objectives

Enhance WebUI to visualize and manage routing decisions for the Task Router system:
- **ProvidersView Enhancement**: Add tags/ctx/role metadata editing for instances
- **Task View Route Timeline**: Display all routing events and decisions
- **Route Decision Card**: Show routing decision when creating tasks in Chat

---

## 📦 Deliverables

### 1. ProvidersView Enhancement (Tags/Ctx/Role Editing)

**File Modified**: `agentos/webui/static/js/views/ProvidersView.js`

**Features**:
- ✅ **New Table Column**: "Routing Metadata" showing tags, ctx, and role
- ✅ **Visual Display**:
  - Tags: Blue pill badges (e.g., "coding", "big_ctx", "local")
  - Ctx: Purple badge showing context length (e.g., 8192)
  - Role: Green badge showing primary use case (e.g., "coding", "general")
- ✅ **Edit Button**: New target icon (🎯) to open routing metadata editor
- ✅ **Routing Metadata Modal**:
  - Tags input: Comma-separated (e.g., "coding, big_ctx, local")
  - Ctx input: Number field for context length
  - Role input: Text field for primary use case
  - Hints for each field
- ✅ **API Integration**:
  - GET /api/providers/instances/{provider}/{instance} - Fetch current config
  - PUT /api/providers/instances/{provider}/{instance} - Update metadata
  - Metadata saved to providers.json under instance config

**Key Changes**:
```javascript
// Added routing metadata display in instance row
const metadata = inst.metadata || {};
const tags = metadata.tags || [];
const ctx = metadata.ctx || null;
const role = metadata.role || null;

// New edit routing button
<button data-instance-action="edit-routing">🎯</button>

// New methods
async editRoutingMetadata(providerId, instanceId)
showRoutingMetadataModal(instance)
async saveRoutingMetadata(providerId, instanceId, form)
```

---

### 2. Task View Route Timeline

**File Modified**: `agentos/webui/static/js/views/TasksView.js`

**Features**:
- ✅ **Routing Information Section** in task detail drawer
- ✅ **Display Components**:
  - **Selected Instance**: Prominently displayed in blue box
  - **Requirements**: Show task requirements (needs, min_ctx)
  - **Route Plan**: Display reasons, scores, fallback chain
  - **Route Timeline**: Chronological list of routing events
- ✅ **Route Events Supported**:
  - TASK_ROUTED (🎯) - Initial routing decision
  - TASK_ROUTE_VERIFIED (✅) - Runner verified route
  - TASK_REROUTED (🔄) - Automatic failover/reroute
  - TASK_ROUTE_OVERRIDDEN (✏️) - Manual route change
- ✅ **Event Display**:
  - Icon + Event type + Timestamp
  - Instance, Reason, Score (if available)
  - Hover effects for better UX

**Key Methods Added**:
```javascript
renderRouteTimeline(task)
renderRoutePlan(routePlan)
renderRouteEventsTimeline(events)
renderRouteEvent(event)
```

**Data Structure Expected**:
```json
{
  "task_id": "...",
  "route_plan": {
    "selected": "llamacpp:qwen3-coder-30b",
    "scores": {
      "llamacpp:qwen3-coder-30b": 0.92,
      "llamacpp:glm47flash-q8": 0.73
    },
    "reasons": ["READY", "tags_match=coding", "ctx>=8192"],
    "fallback": ["llamacpp:glm47flash-q8", "openai"]
  },
  "requirements": {
    "needs": ["coding", "frontend"],
    "min_ctx": 4096
  },
  "events": [
    {
      "event_type": "TASK_ROUTED",
      "timestamp": "...",
      "data": {
        "selected": "llamacpp:qwen3-coder-30b",
        "reason": "capability_match=coding",
        "score": 0.92
      }
    }
  ]
}
```

---

### 3. RouteDecisionCard Component (Chat Integration)

**File Created**: `agentos/webui/static/js/components/RouteDecisionCard.js`

**Features**:
- ✅ **Standalone Component**: Reusable route decision display
- ✅ **Visual Sections**:
  - **Header**: "Route Decision" + Optional "Change" button
  - **Selected Instance**: Large, prominent display (blue gradient box)
  - **Reasons**: Checkmark list with formatted reasons
  - **Scores**: Horizontal bar chart showing all candidate scores
    - Selected instance highlighted
    - Scores sorted descending
    - Percentage display
  - **Fallback Chain**: Sequential display (1→2→3) with arrows
  - **Footer**: Router version + timestamp
- ✅ **Interactive**:
  - onChangeInstance callback (optional)
  - Update method to refresh display
  - Destroy method for cleanup
- ✅ **Reason Formatting**: Converts technical reasons to human-readable

**Usage Example**:
```javascript
const routeCard = new RouteDecisionCard(container, routePlan, {
    onChangeInstance: (plan) => {
        // Show instance selector modal
        showInstanceSelector(plan);
    }
});

// Later update
routeCard.update(newRoutePlan);
```

**Display Example**:
```
┌─────────────────────────────────────────┐
│ Route Decision              [Change]    │
├─────────────────────────────────────────┤
│                                         │
│  Selected Instance                      │
│  llamacpp:qwen3-coder-30b              │
│                                         │
├─────────────────────────────────────────┤
│ Reasons                                 │
│ ✓ Instance is ready                     │
│ ✓ Tags match requirements               │
│ ✓ Context size sufficient (≥8192)       │
│ ✓ Local instance preferred              │
├─────────────────────────────────────────┤
│ Instance Scores                         │
│ llamacpp:qwen3-coder-30b ████████ 92%  │
│ llamacpp:glm47flash-q8   ██████   73%  │
│ openai                   █████    66%  │
├─────────────────────────────────────────┤
│ Fallback Chain (if primary fails)       │
│ 1 glm47flash-q8 → 2 openai             │
└─────────────────────────────────────────┘
```

---

### 4. CSS Styling (Comprehensive)

**File Modified**: `agentos/webui/static/css/components.css`

**New Styles Added** (~500 lines):

**ProvidersView Styles**:
- `.routing-metadata` - Metadata column layout
- `.metadata-row` - Row layout with label
- `.tag-badge` - Blue pill badges for tags
- `.ctx-badge` - Purple badge for context length
- `.role-badge` - Green badge for role
- `.form-hint` - Helpful hints in forms

**TasksView Route Styles**:
- `.route-section` - Blue left border container
- `.route-selected` - Prominent selected instance box
- `.route-label` - Uppercase section labels
- `.requirements-list` - Yellow requirement badges
- `.reasons-list` - Checkmark list styling
- `.scores-chart` - Score bar chart container
- `.score-bar` - Animated blue gradient bars
- `.fallback-chain` - Sequential fallback display
- `.route-timeline` - Timeline container
- `.timeline-event` - Event card with hover effects
- `.event-icon` - Large emoji icons
- `.event-header` - Type + timestamp layout
- `.event-details` - Instance/reason/score display

**RouteDecisionCard Styles**:
- `.route-decision-card` - Card container with shadow
- `.route-card-header` - Gray header with actions
- `.route-selected-section` - Blue gradient selected box
- `.route-selected-instance` - Large monospace text
- `.route-reasons-section` - Checkmark list section
- `.route-scores-section` - Score chart section
- `.route-score-item` - Individual score display
- `.score-bar-wrapper` - Flex layout for bar + value
- `.route-fallback-section` - Fallback chain section
- `.fallback-item` - Numbered fallback display
- `.route-card-footer` - Metadata footer

**Color Scheme**:
- Primary (Selected): Blue (#2563eb, #3b82f6)
- Tags: Light blue (#e3f2fd, #1976d2)
- Context: Purple (#f3e5f5, #7b1fa2)
- Role: Green (#e8f5e9, #2e7d32)
- Requirements: Yellow (#fef3c7, #92400e)
- Success: Green (#10b981)
- Muted: Gray (#6b7280, #9ca3af)

---

## 📊 Integration Points

### Backend Dependencies (PR-1/PR-2)

**Expected Backend Endpoints**:
```python
# ProvidersView (already exists)
GET /api/providers/instances
GET /api/providers/instances/{provider}/{instance}
PUT /api/providers/instances/{provider}/{instance}

# TasksView (expected from Router backend)
GET /api/tasks/{task_id}
# Response should include:
{
  "task_id": "...",
  "route_plan_json": "..." or "route_plan": {},
  "requirements_json": "..." or "requirements": {},
  "selected_instance_id": "...",
  "events": [...]  # Including TASK_ROUTED/REROUTED/etc
}
```

**Metadata Structure in providers.json**:
```json
{
  "instances": {
    "llamacpp": {
      "qwen3-coder-30b": {
        "base_url": "http://127.0.0.1:11435",
        "metadata": {
          "tags": ["coding", "big_ctx", "local"],
          "ctx": 8192,
          "role": "coding"
        }
      }
    }
  }
}
```

---

## ✅ Verification Checklist

### ProvidersView Testing
- [ ] Open Providers tab
- [ ] Instance table shows "Routing Metadata" column
- [ ] Tags/ctx/role display correctly (or show "no tags"/"—")
- [ ] Click 🎯 button → routing metadata modal opens
- [ ] Enter tags (comma-separated) → Save → table updates
- [ ] Enter ctx number → Save → purple badge appears
- [ ] Enter role → Save → green badge appears
- [ ] Refresh page → metadata persists

### TasksView Testing
- [ ] Open Tasks tab → select a task with routing data
- [ ] Task detail drawer shows "Routing Information" section
- [ ] Selected instance displayed in blue box
- [ ] Requirements badges shown (if present)
- [ ] Route reasons listed with checkmarks
- [ ] Score bars displayed (sorted descending)
- [ ] Fallback chain shown with arrows
- [ ] Route timeline displays events (if present)
- [ ] Timeline events show icon, type, time, instance, reason

### RouteDecisionCard Testing (when Chat integrated)
- [ ] Create task in Chat → route decision card appears
- [ ] Selected instance displayed prominently
- [ ] Reasons list shows human-readable text
- [ ] Scores chart displays all candidates
- [ ] Fallback chain shown with numbered items
- [ ] Change button opens instance selector (if enabled)
- [ ] Card updates when route changes

---

## 🏗️ Technical Implementation

### Component Architecture

**ProvidersView Enhancement**:
```
ProvidersView
├── renderInstanceRow() - Add metadata display
├── editRoutingMetadata() - Fetch and show modal
├── showRoutingMetadataModal() - Render form
└── saveRoutingMetadata() - Update via API
```

**TasksView Enhancement**:
```
TasksView
├── renderTaskDetail()
│   └── renderRouteTimeline()
│       ├── renderRoutePlan()
│       │   ├── Reasons list
│       │   ├── Scores chart
│       │   └── Fallback chain
│       └── renderRouteEventsTimeline()
│           └── renderRouteEvent() (x N)
```

**RouteDecisionCard**:
```
RouteDecisionCard (Standalone Component)
├── constructor(container, routePlan, options)
├── render()
│   ├── Header + Change button
│   ├── Selected instance (prominent)
│   ├── Reasons list
│   ├── Scores chart
│   └── Fallback chain
├── formatReason() - Humanize technical reasons
├── update(routePlan) - Refresh display
└── destroy() - Cleanup
```

---

## 📁 Files Changed

### New Files (2)
```
agentos/webui/static/js/components/
└── RouteDecisionCard.js           # 180 lines - Route decision display

docs/guides/
└── PR-4-Router-Visualization.md   # This file
```

### Modified Files (4)
```
agentos/webui/static/js/views/
├── ProvidersView.js               # +150 lines - Routing metadata editing
└── TasksView.js                   # +200 lines - Route timeline display

agentos/webui/static/css/
└── components.css                 # +500 lines - Routing visualization styles

agentos/webui/templates/
└── index.html                     # +1 line - Import RouteDecisionCard.js
```

**Total Lines Added**: ~850 lines
**Total Files Changed**: 5 files (2 new + 3 modified)

---

## 🎨 UI/UX Design Principles

### Visual Hierarchy
1. **Selected Instance**: Largest, most prominent (24px font, blue gradient)
2. **Section Labels**: Uppercase, small (13px), gray
3. **Data Display**: 14px readable font
4. **Metadata**: 11-12px subtle badges

### Color Coding
- **Blue**: Routing decisions, selected instances
- **Green**: Success states, checkmarks, role badges
- **Purple**: Context/capacity indicators
- **Yellow**: Requirements, constraints
- **Gray**: Metadata, timestamps, fallback items

### Interactions
- **Hover Effects**: Timeline events, score bars, buttons
- **Click Actions**: Edit button, Change button, view events
- **Loading States**: N/A (static display from fetched data)

---

## 🔄 Integration with PR-1 & PR-2 Backend

PR-4 is **UI-only** and waits for backend Router implementation:

| Backend Component | PR-4 Integration Point |
|-------------------|------------------------|
| **Router.route()** | RouteDecisionCard displays output |
| **RoutePlan** | TasksView displays plan + scores |
| **TASK_ROUTED events** | Timeline displays routing events |
| **Instance metadata** | ProvidersView edits tags/ctx/role |
| **verify_or_reroute()** | Timeline shows TASK_REROUTED |

**Backend Contract Expected**:
```python
# Task model additions (from router.md PR-1)
class Task:
    route_plan_json: str  # JSON serialized RoutePlan
    requirements_json: str  # JSON serialized TaskRequirements
    selected_instance_id: str  # e.g., "llamacpp:qwen3-coder-30b"
    router_version: str  # e.g., "v1"

# Event types (from router.md PR-1)
EventType = Enum(
    "TASK_ROUTED",          # Initial route decision
    "TASK_ROUTE_VERIFIED",  # Runner verified route still valid
    "TASK_REROUTED",        # Automatic failover occurred
    "TASK_ROUTE_OVERRIDDEN" # User manually changed route
)
```

---

## 📈 Benefits

### For Users
1. **Transparency**: See why tasks are routed to specific instances
2. **Control**: Manually edit instance capabilities (tags/ctx/role)
3. **Debugging**: View full routing timeline when things go wrong
4. **Confidence**: See scores and fallback chains before running

### For Architecture
1. **Observability**: All routing decisions visible and auditable
2. **Metadata Management**: Centralized place to configure instances
3. **Foundation for Supervisor**: Route visualization is prerequisite for task management
4. **Pattern Consistency**: Follows PR-2 component architecture

---

## 🚀 Next Steps

### Phase 1: Backend Integration (PR-5)
Once backend Router (from router.md PR-1/PR-2/PR-3) is implemented:
1. Connect Chat task creation to Router.route()
2. Display RouteDecisionCard when task created
3. Implement "Change" button → manual instance selector
4. Write TASK_ROUTED events to event stream
5. Runner verify_or_reroute() → write TASK_REROUTED events

### Phase 2: Advanced Features (Future)
- **Real-time Route Updates**: WebSocket updates for route changes
- **Route Override UI**: Modal to manually select different instance
- **Route Analytics**: Stats on which instances used most
- **Capability Auto-detection**: Probe instances for tags/ctx automatically
- **Route Simulation**: "What if" testing for different routing rules

---

## ✨ Summary

PR-4 successfully implements comprehensive routing visualization:

- ✅ **ProvidersView Enhancement**: Full routing metadata editing (tags/ctx/role)
- ✅ **Task View Route Timeline**: Complete routing history display
- ✅ **RouteDecisionCard Component**: Beautiful, reusable route decision display
- ✅ **Comprehensive CSS**: 500+ lines of polished routing styles
- ✅ **Ready for Backend**: All UI components waiting for Router backend

**Key Achievement**: The WebUI now has **complete routing visualization infrastructure** ready to integrate with the Task Router backend. When PR-1/PR-2/PR-3 (Router backend) land, users will immediately see:
- Which instance is handling their task (and why)
- Full routing decision breakdown (reasons + scores + fallback)
- Complete routing timeline (initial route + any reroutes)
- Ability to configure instance capabilities

**Design Philosophy**:
- Transparency > Complexity
- Visual Hierarchy (most important info largest)
- Color-coded information architecture
- Follows established PR-2 patterns

---

**Status**: ✅ Ready for Backend Integration
**Documentation**: Complete
**Next PR**: PR-5 (Backend Router + Chat Integration)
**Roadmap Alignment**: On track for Task Router milestone
