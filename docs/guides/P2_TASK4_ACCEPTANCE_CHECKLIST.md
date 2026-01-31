# P2-4 Frontend Visualization Acceptance Checklist

**Version**: 1.0
**Date**: 2026-01-30
**Task**: P2-4 Subgraph Frontend Visualization Component
**Deliverable**: SubgraphView.js + subgraph.css + WebUI integration

---

## Table of Contents

1. [Red Line Validation](#red-line-validation)
2. [Visual Encoding Correctness](#visual-encoding-correctness)
3. [Interaction Functionality](#interaction-functionality)
4. [Performance](#performance)
5. [User Experience](#user-experience)
6. [Integration](#integration)
7. [Documentation](#documentation)

---

## Red Line Validation

These are **non-negotiable** requirements from P2_COGNITIVE_MODEL_DEFINITION.md.

### Red Line 1: No Evidence Edges Must Be Filtered

**Definition**: Every edge in the graph must have >= 1 evidence.

**Test Steps**:
1. Load a subgraph: `/api/brain/subgraph?seed=file:manager.py&k_hop=2&min_evidence=1`
2. Open browser DevTools and inspect the graph data
3. Run: `cy.edges().filter(e => e.data('evidence_count') < 1).length`

**Expected Result**: Should return `0` (no edges without evidence)

**Test Cases**:
- [ ] Confirmed edges all have `evidence_count >= 1`
- [ ] Suspected edges (if any) are clearly marked with dashed style and gray color
- [ ] No edges appear without the `evidence_count` attribute

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Red Line 2: Blind Spot Nodes Must Be Visible

**Definition**: Nodes marked as blind spots must have prominent visual indicators.

**Test Steps**:
1. Load a subgraph that contains blind spots
2. Visually inspect blind spot nodes
3. Check if they have:
   - Red or orange dashed border
   - Border width >= 2px
   - "⚠️" indicator or clear label

**Test Cases**:
- [ ] Blind spot nodes have red (`#dc2626`) or orange (`#ff6600`) border
- [ ] Border style is `dashed`
- [ ] Border width is >= 2px
- [ ] Nodes are visually distinct from normal nodes
- [ ] Hover tooltip shows blind spot severity and reason

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Red Line 3: Blank Areas Must Be Annotated

**Definition**: Missing connections and coverage gaps must be visible.

**Test Steps**:
1. Load a subgraph
2. Check the metadata panel for "Missing Connections"
3. If count > 0, verify that gaps are indicated (e.g., with dashed edges or annotations)

**Test Cases**:
- [ ] Metadata panel shows `missing_connections_count`
- [ ] If > 0, visual indicators are present (e.g., dashed gray edges)
- [ ] Coverage percentage is displayed (not hidden)
- [ ] User cannot mistake the graph for being "complete"

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

## Visual Encoding Correctness

### Node Visual Encoding

**Test Cases**:
- [ ] **Node Color** reflects coverage sources:
  - 3 sources → Green (`#10b981`)
  - 2 sources → Blue (`#3b82f6`)
  - 1 source → Orange (`#f59e0b`)
  - 0 sources → Red (`#ef4444`)

- [ ] **Node Size** reflects importance:
  - Seed node is larger than others
  - Nodes with more evidence are larger
  - Nodes with higher in_degree are larger

- [ ] **Node Border** marks blind spots:
  - Blind spots have dashed border
  - Non-blind spots have solid border

- [ ] **Node Shape** (if implemented):
  - Files are circles
  - Capabilities are squares
  - Other types are distinct

- [ ] **Node Label** shows:
  - Entity name (clear and readable)
  - Coverage badge (✅/⚠️/❌) or percentage

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Edge Visual Encoding

**Test Cases**:
- [ ] **Edge Width** reflects evidence count:
  - 1 evidence → 1px
  - 2-4 evidence → 2px
  - 5-9 evidence → 3px
  - 10+ evidence → 4px

- [ ] **Edge Color** reflects evidence type diversity:
  - 3 types → Green (`#10b981`)
  - 2 types → Blue (`#3b82f6`)
  - 1 type → Gray (`#9ca3af`)
  - Suspected → Light gray (`#d1d5db`)

- [ ] **Edge Style** reflects relationship type:
  - Confirmed → Solid
  - Suspected → Dashed

- [ ] **Edge Opacity** reflects confidence:
  - Low evidence → Semi-transparent
  - High evidence → Opaque

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

## Interaction Functionality

### Hover Interactions

**Test Cases**:
- [ ] Hovering over a node shows tooltip with:
  - Entity type and key
  - Coverage percentage
  - Evidence count
  - In-degree and out-degree
  - Blind spot info (if applicable)

- [ ] Hovering over an edge shows tooltip with:
  - Edge type
  - Evidence count
  - Confidence score
  - Evidence sources

- [ ] Tooltips appear near cursor (not off-screen)
- [ ] Tooltips disappear when mouse moves away

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Click Interactions

**Test Cases**:
- [ ] Clicking a node:
  - Re-queries the graph with that node as the new seed
  - Updates the seed input field
  - Graph animates smoothly to new layout

- [ ] Clicking the background (canvas):
  - Deselects all nodes
  - Clears any selection highlights

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Zoom and Pan

**Test Cases**:
- [ ] Mouse wheel zooms in/out
- [ ] Zoom range is 0.3x to 3.0x
- [ ] Dragging the canvas pans the view
- [ ] Nodes and edges remain visible during zoom/pan
- [ ] Zoom feels responsive (no lag)

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Filters

**Test Cases**:
- [ ] "Show Blind Spots" checkbox:
  - Unchecking hides blind spot nodes
  - Checking shows them again

- [ ] "Show Weak Edges" checkbox:
  - Unchecking hides edges with low evidence
  - Checking shows them again

- [ ] K-Hop slider:
  - Changes value (1-3)
  - Updates display in real-time

- [ ] Min Evidence slider:
  - Changes value (1-10)
  - Updates display in real-time

- [ ] Query button:
  - Re-fetches subgraph with new parameters
  - Shows loading indicator

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

## Performance

### Response Times

**Test Cases**:
- [ ] Subgraph with 12 nodes loads in < 1 second
- [ ] Subgraph with 50 nodes loads in < 3 seconds
- [ ] Subgraph with 100+ nodes either:
  - Loads in < 5 seconds, OR
  - Shows a warning about graph size

**Test Method**: Use browser DevTools Network tab to measure `/api/brain/subgraph` response time.

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Rendering Performance

**Test Cases**:
- [ ] Initial render (from data to visible graph) takes < 1 second
- [ ] Zoom/pan is smooth (60 FPS, no jank)
- [ ] Re-layout animation is smooth (no frame drops)

**Test Method**: Use browser DevTools Performance tab to measure FPS during interactions.

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Memory Usage

**Test Cases**:
- [ ] Memory usage for 50 nodes is < 50 MB
- [ ] Memory usage for 100 nodes is < 100 MB
- [ ] Switching views cleans up Cytoscape instance (no memory leak)

**Test Method**: Use browser DevTools Memory tab to take heap snapshots before and after loading views.

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

## User Experience

### First-Time User Experience

**Test Cases**:
- [ ] Welcome screen is shown when no seed is provided
- [ ] Welcome screen has:
  - Clear title and description
  - Example seeds (file:, capability:, term:)
  - No confusing UI elements

- [ ] After entering a seed and clicking "Query":
  - Welcome screen disappears
  - Graph appears
  - Legend and metadata panels appear

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Error Handling

**Test Cases**:
- [ ] Invalid seed format:
  - Shows error message: "Invalid seed format"
  - Suggests correct format
  - Does not crash

- [ ] Non-existent entity:
  - Shows error message: "Seed entity not found"
  - Suggests running `/brain build`
  - Does not crash

- [ ] Network error:
  - Shows error message: "Network error: [details]"
  - Provides "Try Again" button
  - Does not crash

**Test Method**: Test with intentionally invalid inputs.

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Loading States

**Test Cases**:
- [ ] Loading overlay is shown during API call
- [ ] Loading overlay has:
  - Spinning indicator
  - "Loading subgraph..." text
  - Semi-transparent background

- [ ] Loading overlay disappears after:
  - Successful load, OR
  - Error occurs

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Legend and Metadata

**Test Cases**:
- [ ] Legend is visible and positioned in top-right corner
- [ ] Legend explains:
  - Node colors (3 sources, 2 sources, 1 source)
  - Blind spot indicators (dashed red border)
  - Edge strengths (5+ evidence, 1-2 evidence, suspected)

- [ ] Metadata panel is visible and positioned in bottom-left corner
- [ ] Metadata panel shows:
  - Seed entity
  - K-hop value
  - Node count
  - Edge count (confirmed + suspected)
  - Coverage percentage (with color-coding)
  - Evidence density
  - Blind spot count
  - Missing connections count

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

## Integration

### WebUI Navigation

**Test Cases**:
- [ ] "Subgraph" link appears in Knowledge section of sidebar
- [ ] Clicking "Subgraph" loads SubgraphView
- [ ] Navigation state is preserved (view stays active after refresh)
- [ ] Switching to another view cleans up Cytoscape instance

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Dependencies

**Test Cases**:
- [ ] Cytoscape.js (3.23.0) is loaded from CDN
- [ ] SubgraphView.js is loaded
- [ ] subgraph.css is loaded
- [ ] No console errors related to missing dependencies

**Test Method**: Check browser DevTools Console and Network tabs.

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### API Integration

**Test Cases**:
- [ ] `/api/brain/subgraph` endpoint is called with correct parameters
- [ ] Response is correctly parsed (ok=true, data={nodes, edges, metadata})
- [ ] Error responses (ok=false, error="...") are handled gracefully
- [ ] Cache headers are respected (if implemented)

**Test Method**: Use browser DevTools Network tab to inspect API calls.

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

## Documentation

### Code Comments

**Test Cases**:
- [ ] SubgraphView.js has:
  - File header with description
  - Comments explaining core methods
  - Comments explaining visual encoding logic

- [ ] subgraph.css has:
  - Section comments for each component
  - Comments explaining non-obvious styles

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### User Documentation

**Test Cases**:
- [ ] User guide exists (P2_TASK4_USER_GUIDE.md)
- [ ] User guide explains:
  - How to query a subgraph
  - How to interpret visual encoding
  - How to identify blind spots
  - How to understand missing connections

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

### Developer Documentation

**Test Cases**:
- [ ] Developer guide exists (P2_TASK4_DEVELOPER_GUIDE.md)
- [ ] Developer guide explains:
  - SubgraphView API
  - How to customize styles
  - How to extend interactions
  - How to integrate into other views

**Status**: ☐ Pass / ☐ Fail

**Notes**:

---

## Summary

### Checklist Overview

**Total Items**: 80+
**Passed**: ___
**Failed**: ___
**N/A**: ___

### Critical Issues

List any critical issues that block acceptance:

1.
2.
3.

### Non-Critical Issues

List any non-critical issues that should be fixed but don't block acceptance:

1.
2.
3.

### Acceptance Decision

**Status**: ☐ Accepted / ☐ Accepted with Conditions / ☐ Rejected

**Signed Off By**: _________________________
**Date**: _________________________

**Conditions (if applicable)**:

---

## Appendix A: Test Environment

- **Browser**: _________________________
- **OS**: _________________________
- **Screen Resolution**: _________________________
- **BrainOS Index**: ☐ Built / ☐ Not Built
- **Sample Entities**: _________________________

---

## Appendix B: Test Data

**Sample Seeds Used**:
- `file:manager.py`
- `capability:api`
- `term:authentication`

**Expected Results**:
- `file:manager.py` should return 10+ nodes, 15+ edges
- `capability:api` should return 5+ nodes
- `term:authentication` may return empty graph if not indexed

---

## Appendix C: Known Limitations

1. **Cytoscape.js Performance**: Graphs with 500+ nodes may be slow
2. **Missing Connections Detection**: Only detects basic gaps (code without doc, isolated in capability)
3. **Legend Positioning**: May overlap with graph on small screens
4. **Tooltip Positioning**: May go off-screen on edge cases

---

**End of Checklist**
