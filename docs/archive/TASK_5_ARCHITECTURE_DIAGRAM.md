# P1-A Task 5: Architecture Diagram

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Explain Drawer UI                        │
│                    (ExplainDrawer Component)                    │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    User clicks 🧠 Explain button
                                 │
                                 ↓
                    ┌────────────────────────┐
                    │   query(queryType)     │
                    │   - Fetch query data   │
                    └────────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ↓                                     ↓
    ┌──────────────────┐                 ┌──────────────────┐
    │  BrainOS Query   │                 │ Blind Spot Check │
    │ /api/brain/query │                 │ /api/blind-spots │
    └──────────────────┘                 └──────────────────┘
              │                                     │
              │ Returns:                            │ Returns:
              │ - Query results                     │ - Blind spot list
              │ - coverage_info                     │ - severity scores
              │                                     │
              └──────────────────┬──────────────────┘
                                 │
                                 ↓
                    ┌────────────────────────┐
                    │  renderResult()        │
                    │  - Determine query type│
                    │  - Pass blind spot     │
                    └────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ↓                       ↓                       ↓
   renderWhyResult()      renderImpactResult()    renderTraceResult()
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ↓                         ↓
         ┌──────────────────┐      ┌──────────────────┐
         │ Blind Spot       │      │ Coverage Badge   │
         │ Warning          │      │ Visualization    │
         │ (if detected)    │      │ (if coverage_info)│
         └──────────────────┘      └──────────────────┘
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 ↓
                    ┌────────────────────────┐
                    │   Query Results        │
                    │   (Paths/Timeline/etc) │
                    └────────────────────────┘
```

## Data Flow

### 1. Query Execution Flow

```
┌────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
│ User   │────▶│ Query() │────▶│ API Call │────▶│ Backend  │
└────────┘     └─────────┘     └──────────┘     └──────────┘
                                                       │
                               ┌───────────────────────┘
                               │
                               ↓
                    ┌──────────────────────┐
                    │ Query Response       │
                    │ {                    │
                    │   ok: true,          │
                    │   data: {            │
                    │     coverage_info,   │
                    │     paths/timeline,  │
                    │     ...              │
                    │   }                  │
                    │ }                    │
                    └──────────────────────┘
```

### 2. Coverage Badge Rendering

```
coverage_info: {
  evidence_sources: ["git", "doc"],
  source_count: 2,
  explanation: "Based on git/doc. Missing: code."
}
         │
         ↓
renderCoverageBadge()
         │
         ├─→ Determine badge class (high/medium/low)
         ├─→ Select icon (✅/⚠️/❌)
         ├─→ Render source tags (active/inactive)
         └─→ Return HTML
         │
         ↓
┌─────────────────────────────────────────┐
│ 📊 Evidence Sources:                    │
│ [GIT] [DOC] [CODE] (2/3 sources)       │
│ ⚠️ Based on git/doc. Missing: code.    │
└─────────────────────────────────────────┘
```

### 3. Blind Spot Detection Flow

```
checkBlindSpot(entityType, entityKey)
         │
         ↓
GET /api/brain/blind-spots?max_results=100
         │
         ↓
┌──────────────────────────┐
│ Blind Spots Response     │
│ {                        │
│   blind_spots: [         │
│     {                    │
│       entity_type,       │
│       entity_key,        │
│       severity: 0.85,    │
│       reason,            │
│       suggested_action   │
│     }                    │
│   ]                      │
│ }                        │
└──────────────────────────┘
         │
         ↓
Find matching blind spot
         │
         ├─→ Match found?
         │   ├─→ Yes: Return blind spot data
         │   └─→ No: Return null
         │
         ↓
renderBlindSpotWarning()
         │
         ├─→ Determine severity class (high/medium/low)
         ├─→ Select icon (🚨/⚠️/💡)
         └─→ Return HTML
         │
         ↓
┌─────────────────────────────────────────┐
│ 🚨 Blind Spot Detected     [0.85]      │
│ High Fan-In: 12 dependents, no docs   │
│ → Suggested: Add ADR                   │
└─────────────────────────────────────────┘
```

## Component Hierarchy

```
ExplainDrawer
├── createDrawer()
│   ├── Drawer overlay
│   ├── Drawer content
│   ├── Header (title + close button)
│   ├── Tabs (Why/Impact/Trace/Map)
│   └── Content area
│
├── query(queryType)
│   ├── Fetch query results
│   ├── checkBlindSpot() [async]
│   └── renderResult()
│
├── renderResult(queryType, result, blindSpot)
│   ├── renderWhyResult()
│   │   ├── renderBlindSpotWarning() [NEW]
│   │   ├── renderCoverageBadge() [NEW]
│   │   └── Render paths
│   │
│   ├── renderImpactResult()
│   │   ├── renderBlindSpotWarning() [NEW]
│   │   ├── renderCoverageBadge() [NEW]
│   │   └── Render affected nodes
│   │
│   ├── renderTraceResult()
│   │   ├── renderBlindSpotWarning() [NEW]
│   │   ├── renderCoverageBadge() [NEW]
│   │   └── Render timeline
│   │
│   └── renderMapResult()
│       ├── renderBlindSpotWarning() [NEW]
│       ├── renderCoverageBadge() [NEW]
│       └── Render subgraph
│
├── Helper Methods [NEW]
│   ├── checkBlindSpot(entityType, entityKey)
│   ├── renderCoverageBadge(result)
│   ├── renderBlindSpotWarning(blindSpot)
│   ├── getSeverityClass(severity)
│   └── getSeverityIcon(severity)
│
└── Existing Methods
    ├── escapeHtml(str)
    ├── renderError(error)
    └── getSeedForEntity()
```

## State Machine

```
┌─────────────┐
│   CLOSED    │
└─────────────┘
       │
       │ ExplainDrawer.show()
       ↓
┌─────────────┐
│   LOADING   │ ← Show spinner
└─────────────┘
       │
       │ API responses received
       ↓
┌─────────────┐
│  RENDERING  │ ← Render badges + warnings
└─────────────┘
       │
       │ HTML rendered
       ↓
┌─────────────┐
│   DISPLAY   │ ← Show results to user
└─────────────┘
       │
       ├─→ User switches tab → Back to LOADING
       └─→ User closes drawer → Back to CLOSED
```

## CSS Architecture

```
explain.css
├── Explain Button Styles
│   └── .explain-btn
│
├── Drawer Structure
│   ├── .explain-drawer
│   ├── .explain-drawer-overlay
│   └── .explain-drawer-content
│
├── Header & Tabs
│   ├── .explain-drawer-header
│   ├── .explain-tabs
│   └── .explain-tab.active
│
├── [NEW] Coverage Badge
│   ├── .coverage-badge
│   │   ├── .coverage-badge-high (green)
│   │   ├── .coverage-badge-medium (yellow)
│   │   └── .coverage-badge-low (red)
│   ├── .coverage-header
│   ├── .source-tag
│   │   ├── .source-tag.active (green)
│   │   └── .source-tag.inactive (gray)
│   └── .coverage-explanation
│
├── [NEW] Blind Spot Warning
│   ├── .blind-spot-warning
│   │   ├── .blind-spot-warning.high (red)
│   │   ├── .blind-spot-warning.medium (yellow)
│   │   └── .blind-spot-warning.low (blue)
│   ├── .warning-header
│   ├── .severity-badge
│   └── .warning-body
│
├── Query Results
│   ├── .explain-paths (Why)
│   ├── .explain-affected (Impact)
│   ├── .explain-timeline (Trace)
│   └── .explain-nodes (Map)
│
└── Responsive Design
    └── @media (max-width: 768px)
```

## Integration Points

### Backend APIs Used

```
1. Query API
   Endpoint: POST /api/brain/query/{why|impact|trace|subgraph}
   Request: { seed: "file:path" }
   Response: {
     ok: true,
     data: {
       coverage_info: {          ← [NEW] Used by Coverage Badge
         evidence_sources: [],
         source_count: 2,
         explanation: "..."
       },
       paths: [...],             ← Query results
       ...
     }
   }

2. Blind Spots API
   Endpoint: GET /api/brain/blind-spots?max_results=100
   Response: {
     ok: true,
     data: {
       blind_spots: [            ← [NEW] Used by Blind Spot Warning
         {
           entity_type: "file",
           entity_key: "path",
           severity: 0.85,
           reason: "...",
           suggested_action: "..."
         }
       ]
     }
   }
```

### Frontend Components Used

```
ExplainDrawer.js
├── Uses: escapeHtml() for XSS protection
├── Uses: fetch() for API calls
├── Uses: DOM manipulation (innerHTML)
└── Exports: ExplainDrawer class to window

explain.css
├── Uses: Flexbox for layout
├── Uses: CSS variables (colors)
├── Uses: Media queries for responsive
└── Follows: BEM-inspired naming

TasksView.js / ExtensionsView.js / ContextView.js
└── Calls: ExplainDrawer.show(type, key, name)
```

## Error Handling

```
┌────────────────┐
│ API Call       │
└────────────────┘
        │
        ├─→ Success
        │   └─→ Render results
        │
        ├─→ HTTP Error
        │   └─→ renderError(message)
        │
        ├─→ Network Error
        │   └─→ renderError("Failed to query")
        │
        └─→ Parse Error
            └─→ renderError("Invalid response")

Graceful Degradation:
├── No coverage_info? → Don't show badge
├── Blind spot API fails? → Don't show warning
├── No blind spot match? → null, don't show warning
└── Missing fields? → Use fallback values
```

## Performance Optimization

```
Optimization Strategy:

1. Async Blind Spot Check
   ├── Doesn't block query rendering
   └── Runs in parallel with query

2. Lazy Rendering
   ├── Only render visible tab
   └── Switch tab = new query

3. Future: Caching
   ├── Cache blind spots in localStorage
   ├── TTL: 5 minutes
   └── Invalidate on BrainOS rebuild

4. Debouncing (if needed)
   ├── Debounce tab switches
   └── Prevent rapid API calls
```

---

**Diagram Date**: 2026-01-30
**Component**: ExplainDrawer + Coverage Features
**Status**: ✅ Implemented
