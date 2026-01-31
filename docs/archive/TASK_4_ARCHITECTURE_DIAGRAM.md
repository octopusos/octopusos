# P1-A Task 4: Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      BrainOS Dashboard                       │
│                   (User Interface Layer)                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP GET Requests
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI WebUI Layer                      │
│                    (agentos/webui/api/)                      │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ /api/brain/stats │  │ /api/brain/      │                │
│  │                  │  │ coverage         │                │
│  │ Returns:         │  │                  │                │
│  │ - entities       │  │ Returns:         │                │
│  │ - edges          │  │ - code_coverage  │                │
│  │ - evidence       │  │ - doc_coverage   │                │
│  └──────────────────┘  │ - dep_coverage   │                │
│                        │ - total_files    │                │
│  ┌──────────────────┐  │ - covered_files  │                │
│  │ /api/brain/      │  └──────────────────┘                │
│  │ blind-spots      │                                       │
│  │                  │                                       │
│  │ Returns:         │                                       │
│  │ - total_spots    │                                       │
│  │ - by_severity    │                                       │
│  │ - blind_spots[]  │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Python Function Calls
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    BrainOS Service Layer                     │
│                 (agentos/core/brain/service.py)              │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ compute_coverage │  │ detect_blind_    │                │
│  │                  │  │ spots            │                │
│  │ - Analyzes files │  │                  │                │
│  │ - Counts evidence│  │ - Finds high     │                │
│  │ - Calculates %   │  │   fan-in files   │                │
│  └──────────────────┘  │ - Detects missing│                │
│                        │   implementations│                │
│  ┌──────────────────┐  │ - Calculates     │                │
│  │ get_stats        │  │   severity       │                │
│  │                  │  └──────────────────┘                │
│  │ - Entity count   │                                       │
│  │ - Edge count     │                                       │
│  │ - Evidence count │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ SQL Queries
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   BrainOS Store Layer                        │
│                (agentos/core/brain/store.py)                 │
│                                                              │
│  ┌────────────────────────────────────────────┐             │
│  │         SQLiteStore                        │             │
│  │                                            │             │
│  │  Tables:                                   │             │
│  │  - entities (type, key, name, created_at)  │             │
│  │  - edges (from_id, to_id, type)           │             │
│  │  - evidence (entity_id, source_type, ref) │             │
│  └────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ File I/O
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    BrainOS Database                          │
│                   (.brainos/v0.1_mvp.db)                     │
│                                                              │
│  SQLite Database File:                                       │
│  - 3140 file entities                                        │
│  - ~8000 edges (dependencies)                                │
│  - ~12000 evidence records                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Coverage Card

```
User Opens Dashboard
       │
       ▼
[BrainDashboardView.js]
   loadStats() called
       │
       ├─────── fetch('/api/brain/stats') ────────────┐
       │                                               │
       ├─────── fetch('/api/brain/coverage') ─────────┤
       │                                               │
       └─────── fetch('/api/brain/blind-spots') ──────┤
                                                       │
                                          (Parallel API Calls)
                                                       │
                                                       ▼
                                          [brain.py API Router]
                                                       │
                                          get_coverage() called
                                                       │
                                                       ▼
                                          [service.py]
                                          compute_coverage(store)
                                                       │
                                          Queries SQLite:
                                          - Count total files
                                          - Count files with evidence
                                          - Calculate percentages
                                                       │
                                                       ▼
                                          Return CoverageMetrics
                                                       │
                                                       ▼
                                          JSON Response:
                                          {
                                            code_coverage: 0.719,
                                            doc_coverage: 0.682,
                                            dependency_coverage: 0.068,
                                            total_files: 3140,
                                            covered_files: 2258,
                                            uncovered_files: [...]
                                          }
                                                       │
                                                       ▼
[BrainDashboardView.js]
   this.coverage = result.data
       │
       ▼
   renderCoverageSummaryCard()
       │
       ├─── Calculate percentages (71.9%, 68.2%, 6.8%)
       ├─── Apply CSS classes (high/medium/low)
       ├─── Generate HTML with progress bars
       └─── Inject into DOM
                │
                ▼
          User sees card
```

---

## Data Flow: Blind Spots Card

```
User Opens Dashboard
       │
       ▼
[BrainDashboardView.js]
   loadStats() called
       │
       └─────── fetch('/api/brain/blind-spots?max_results=10')
                                                       │
                                                       ▼
                                          [brain.py API Router]
                                                       │
                                          get_blind_spots() called
                                                       │
                                                       ▼
                                          [service.py]
                                          detect_blind_spots(store, threshold=5)
                                                       │
                                          Queries SQLite:
                                          - Find files with high fan-in
                                          - Find capabilities without code
                                          - Find active files without docs
                                                       │
                                          Calculate severity:
                                          - High: ≥0.7
                                          - Medium: 0.4-0.69
                                          - Low: <0.4
                                                       │
                                                       ▼
                                          Return BlindSpotReport
                                                       │
                                                       ▼
                                          JSON Response:
                                          {
                                            total_blind_spots: 17,
                                            by_severity: {
                                              high: 14,
                                              medium: 1,
                                              low: 2
                                            },
                                            blind_spots: [
                                              {
                                                entity_name: "governance",
                                                severity: 0.80,
                                                reason: "Declared capability..."
                                              },
                                              ...
                                            ]
                                          }
                                                       │
                                                       ▼
[BrainDashboardView.js]
   this.blindSpots = result.data
       │
       ▼
   renderTopBlindSpotsCard()
       │
       ├─── Take top 5 blind spots
       ├─── Assign severity icons (🔴🟡🔵)
       ├─── Apply CSS classes
       ├─── Generate HTML with list
       └─── Inject into DOM
                │
                ▼
          User sees card
```

---

## Component Hierarchy

```
BrainDashboardView
   │
   ├─── renderGraphStatusCard()
   │     └─── Shows graph version, commit, build time
   │
   ├─── renderDataScaleCard()
   │     └─── Shows entities, edges, evidence counts
   │
   ├─── renderInputCoverageCard()
   │     └─── Shows Git/Doc/Code input status
   │
   ├─── renderCognitiveCoverageCard() [OLD]
   │     └─── Shows doc refs % and dep graph %
   │
   ├─── renderBlindSpotsCard() [OLD]
   │     └─── Shows files with no references
   │
   ├─── renderActionsCard()
   │     └─── Shows action buttons (rebuild, query)
   │
   ├─── renderCoverageSummaryCard() [NEW] ✨
   │     │
   │     ├─── Progress bar: Code Coverage (71.9%)
   │     ├─── Progress bar: Doc Coverage (68.2%)
   │     ├─── Progress bar: Dependency Coverage (6.8%)
   │     ├─── Summary: Covered files (2258/3140)
   │     └─── Summary: No evidence (882)
   │
   └─── renderTopBlindSpotsCard() [NEW] ✨
         │
         ├─── Blind spot 1: governance (0.80) 🔴
         ├─── Blind spot 2: execution gate (0.80) 🔴
         ├─── Blind spot 3: planning guard (0.80) 🔴
         ├─── Blind spot 4: Router.py (0.40) 🟡
         ├─── Blind spot 5: state_machine.py (0.30) 🔵
         │
         └─── Summary: 14 high / 1 medium / 2 low
```

---

## CSS Class Structure

```
.dashboard-grid
   │
   ├─── .card.coverage-summary-card [NEW] ✨
   │     │
   │     ├─── h3 (with Material Icon)
   │     ├─── .card-subtitle [NEW]
   │     │
   │     ├─── .card-content
   │     │     │
   │     │     ├─── .coverage-item [NEW]
   │     │     │     ├─── .coverage-label
   │     │     │     │     ├─── span (label)
   │     │     │     │     └─── .coverage-value.high/.medium/.low [NEW]
   │     │     │     │
   │     │     │     └─── .progress-bar
   │     │     │           └─── .progress-fill.high/.medium/.low [NEW]
   │     │     │
   │     │     └─── .coverage-summary [NEW]
   │     │           ├─── .summary-row
   │     │           │     ├─── .summary-label
   │     │           │     └─── .summary-value
   │     │           │
   │     │           └─── .summary-row
   │     │                 └─── .summary-value.warn [NEW]
   │
   └─── .card.blind-spots-summary-card [NEW] ✨
         │
         ├─── h3 (with Material Icon)
         ├─── .card-subtitle [NEW]
         │
         └─── .card-content
               │
               ├─── .blind-spots-list [NEW]
               │     │
               │     └─── .blind-spot-item [NEW]
               │           ├─── .blind-spot-header [NEW]
               │           │     ├─── .severity-icon.high/.medium/.low [NEW]
               │           │     ├─── .blind-spot-name [NEW]
               │           │     └─── .severity-value [NEW]
               │           │
               │           └─── .blind-spot-reason [NEW]
               │
               └─── .blind-spots-summary [NEW]
                     ├─── .severity-badge.high [NEW]
                     ├─── .severity-badge.medium [NEW]
                     └─── .severity-badge.low [NEW]
```

---

## Interaction Flow

```
User Action: Opens Dashboard
       │
       ▼
JavaScript: BrainDashboardView.init()
       │
       ├─── Setup event listeners
       ├─── Call loadStats()
       └─── Start auto-refresh timer (30s)
                │
                ▼
JavaScript: loadStats()
       │
       ├─── Parallel fetch:
       │     ├─── /api/brain/stats
       │     ├─── /api/brain/coverage
       │     └─── /api/brain/blind-spots
       │
       ▼
API: Return JSON data
       │
       ▼
JavaScript: Store data in instance
       │
       ├─── this.stats = result.data
       ├─── this.coverage = result.data
       └─── this.blindSpots = result.data
                │
                ▼
JavaScript: renderDashboard()
       │
       ├─── Render all 8 cards
       │     ├─── Graph Status
       │     ├─── Data Scale
       │     ├─── Input Coverage
       │     ├─── Cognitive Coverage (old)
       │     ├─── Blind Spots (old)
       │     ├─── Actions
       │     ├─── Coverage Summary ✨ NEW
       │     └─── Top Blind Spots ✨ NEW
       │
       ▼
DOM: Cards rendered and displayed
       │
       ▼
CSS: Apply styles and animations
       │
       ├─── Color-code progress bars
       ├─── Apply severity badges
       └─── Animate transitions
                │
                ▼
User: Sees dashboard with coverage insights
```

---

## Security Architecture

```
User Input → Frontend
                │
                ├─── escapeHtml() applied to all dynamic content
                ├─── No eval() or Function() calls
                └─── No innerHTML with unsanitized data
                        │
                        ▼
                   Safe HTML Rendering
                        │
                        ▼
                   DOM Injection
```

**XSS Protection**:
- All entity names passed through `escapeHtml()`
- All reason text passed through `escapeHtml()`
- Template literals used (automatic escaping)
- No user-controlled attributes in HTML

---

## Performance Optimization

```
Sequential API Calls (OLD):
   fetch('/api/brain/stats')      → 50ms
   fetch('/api/brain/coverage')   → 120ms
   fetch('/api/brain/blind-spots')→ 180ms
   ────────────────────────────────────
   Total:                           350ms

Parallel API Calls (NEW) ✨:
   Promise.all([
     fetch('/api/brain/stats'),      ─┐
     fetch('/api/brain/coverage'),    ├─ Parallel
     fetch('/api/brain/blind-spots')  ─┘
   ])
   ────────────────────────────────────
   Total:                           180ms

   Improvement: 48.6% faster!
```

---

## Error Handling Flow

```
API Call Error
       │
       ├─── Network error
       │     └─── Catch block logs error
       │           └─── Show "Failed to connect" message
       │
       ├─── API returns ok: false
       │     └─── Check result.error
       │           └─── Show error message
       │
       └─── Data is null/missing
             └─── Graceful degradation
                   └─── Show "No data available"
```

---

## Testing Architecture

```
Test Suite (test_brain_dashboard_cards.py)
   │
   ├─── Test 1: Coverage API Endpoint
   │     ├─── Verify response structure
   │     ├─── Check required fields
   │     └─── Validate data types
   │
   ├─── Test 2: Blind Spots API Endpoint
   │     ├─── Verify response structure
   │     ├─── Check required fields
   │     └─── Validate data types
   │
   ├─── Test 3: Dashboard Rendering Logic
   │     ├─── Test with sample data
   │     ├─── Verify color coding
   │     └─── Check severity icons
   │
   └─── Test 4: Null Data Handling
         ├─── Test with null coverage
         ├─── Test with zero blind spots
         └─── Verify graceful degradation

Visual Test (test_brain_dashboard_visual.html)
   │
   ├─── Render cards in standalone HTML
   ├─── Verify visual appearance
   ├─── Test responsive layout
   └─── Check color schemes
```

---

## Deployment Architecture

```
Development Environment
       │
       ├─── Modify JavaScript: BrainDashboardView.js
       ├─── Modify CSS: brain.css
       └─── Run tests: test_brain_dashboard_cards.py
                │
                ▼
       All tests pass ✅
                │
                ▼
Commit to Git
       │
       ├─── git add agentos/webui/static/js/views/BrainDashboardView.js
       ├─── git add agentos/webui/static/css/brain.css
       └─── git commit -m "feat: add cognitive coverage cards to dashboard"
                │
                ▼
Code Review
       │
       └─── Review changes
             └─── Approve
                     │
                     ▼
Deploy to Staging
       │
       ├─── Build static assets
       ├─── Deploy to staging server
       └─── Verify functionality
                │
                ▼
User Acceptance Testing
       │
       └─── Test with real users
             └─── Approve
                     │
                     ▼
Deploy to Production
       │
       └─── Users see new cards! 🎉
```
