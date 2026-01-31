# P2-4 Developer Guide: Subgraph Visualization

**Version**: 1.0
**Date**: 2026-01-30
**Audience**: AgentOS contributors, extension developers
**Purpose**: Understand SubgraphView internals and extend functionality

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [SubgraphView API](#2-subgraphview-api)
3. [Customizing Styles](#3-customizing-styles)
4. [Extending Interactions](#4-extending-interactions)
5. [Integration Patterns](#5-integration-patterns)
6. [Performance Optimization](#6-performance-optimization)
7. [Testing](#7-testing)
8. [Contributing](#8-contributing)

---

## 1. Architecture Overview

### 1.1 Component Stack

```
┌─────────────────────────────────────────┐
│         User Interface                   │
│  (Controls, Legend, Metadata Panel)      │
├─────────────────────────────────────────┤
│         SubgraphView.js                  │
│  (State management, event handling)      │
├─────────────────────────────────────────┤
│         Cytoscape.js                     │
│  (Graph rendering, layout)               │
├─────────────────────────────────────────┤
│         /api/brain/subgraph              │
│  (Data fetching, visual encoding)        │
├─────────────────────────────────────────┤
│         BrainOS Query Engine             │
│  (P2-2: Subgraph construction)           │
└─────────────────────────────────────────┘
```

### 1.2 Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `SubgraphView.js` | ~850 | Core component logic |
| `subgraph.css` | ~500 | Styling and layout |
| `main.js` | +10 | Integration (renderSubgraphView) |
| `index.html` | +20 | CDN imports, navigation, CSS links |

### 1.3 Dependencies

**External**:
- [Cytoscape.js 3.23.0](https://js.cytoscape.org/) (from CDN)

**Internal**:
- `/api/brain/subgraph` (P2-3: API endpoint)
- BrainOS DB (`brainos.db`)

---

## 2. SubgraphView API

### 2.1 Class Structure

```javascript
class SubgraphView {
    constructor() {
        this.cy = null;              // Cytoscape instance
        this.currentSeed = null;     // Current seed entity
        this.currentKHop = 2;        // Current k-hop value
        this.currentMinEvidence = 1; // Current min evidence filter
        this.currentData = null;     // Cached subgraph data
        this.showBlindSpots = true;  // Filter state
        this.showWeakEdges = true;   // Filter state
    }

    // Lifecycle methods
    init()
    cleanup()

    // Data methods
    loadSubgraph(seed, kHop, minEvidence)
    renderSubgraph(data)

    // UI methods
    createContainer()
    updateMetadata(metadata)
    showTooltip(text, position)
    hideTooltip()

    // Event handlers
    bindEvents()
    handleNodeClick(node)
}
```

### 2.2 Public Methods

#### `init()`

Initializes the view. Call this once when the view is loaded.

**Usage**:
```javascript
const view = new SubgraphView();
view.init();
```

**What it does**:
1. Creates DOM container
2. Initializes Cytoscape with COSE layout
3. Binds event handlers
4. Loads seed from URL (if present)

---

#### `loadSubgraph(seed, kHop, minEvidence)`

Loads a subgraph from the API.

**Parameters**:
- `seed` (string): Seed entity (e.g., "file:manager.py")
- `kHop` (number): Number of hops (1-3)
- `minEvidence` (number): Minimum evidence filter (1-10)

**Usage**:
```javascript
view.loadSubgraph('file:manager.py', 2, 1);
```

**Returns**: Promise (resolves when graph is rendered)

**Error Handling**:
- Invalid seed format → Shows error message
- Entity not found → Shows error message
- Network error → Shows error message

---

#### `renderSubgraph(data)`

Renders a subgraph from API response data.

**Parameters**:
- `data` (object): API response `data` object with `nodes`, `edges`, `metadata`

**Usage**:
```javascript
const data = {
    nodes: [...],
    edges: [...],
    metadata: {...}
};
view.renderSubgraph(data);
```

**What it does**:
1. Clears existing graph
2. Converts API data to Cytoscape elements
3. Applies filters
4. Adds elements to graph
5. Runs COSE layout
6. Updates legend and metadata

---

#### `cleanup()`

Cleans up resources when view is destroyed.

**Usage**:
```javascript
view.cleanup();
```

**What it does**:
1. Destroys Cytoscape instance
2. Removes tooltips
3. Clears cached data

**Important**: Call this when switching views to prevent memory leaks!

---

### 2.3 Internal Methods

#### `createContainer()`

Generates the DOM structure (controls, canvas, legend, metadata).

**Returns**: None (modifies `#main-content`)

---

#### `initCytoscape()`

Initializes the Cytoscape instance with COSE layout and styles.

**Configuration**:
```javascript
{
    container: document.getElementById('cytoscape-container'),
    layout: {
        name: 'cose',
        edgeElasticity: (edge) => 1 / Math.sqrt(edge.data('evidence_count'))
    },
    style: [ /* ... */ ],
    minZoom: 0.3,
    maxZoom: 3.0
}
```

---

#### `bindEvents()`

Binds event handlers for user interactions.

**Events**:
- Node hover → Show tooltip
- Edge hover → Show tooltip
- Node click → Re-query with new seed
- Query button → Load subgraph
- K-hop slider → Update state
- Min evidence slider → Update state
- Filter checkboxes → Toggle visibility

---

#### `handleNodeClick(node)`

Handles node click events.

**Default Behavior**: Re-queries graph with clicked node as new seed.

**Customization**: Override this method to change behavior (e.g., open detail panel instead).

---

## 3. Customizing Styles

### 3.1 Node Styles

**Location**: `SubgraphView.js` → `initCytoscape()` → `style` array

**Example**: Change node shape based on entity type:

```javascript
{
    selector: 'node[entity_type = "file"]',
    style: {
        'shape': 'ellipse'  // Default is 'ellipse'
    }
},
{
    selector: 'node[entity_type = "capability"]',
    style: {
        'shape': 'rectangle'
    }
}
```

### 3.2 Edge Styles

**Example**: Change edge arrow style:

```javascript
{
    selector: 'edge',
    style: {
        'target-arrow-shape': 'vee',  // Default is 'triangle'
        'arrow-scale': 1.5
    }
}
```

### 3.3 CSS Customization

**File**: `agentos/webui/static/css/subgraph.css`

**Example**: Change legend background color:

```css
#legend {
    background: #f0f9ff;  /* Light blue instead of white */
}
```

**Example**: Hide metadata panel by default:

```css
#metadata-panel {
    display: none;  /* Add this rule */
}
```

### 3.4 Dark Mode Support

**Current Status**: Not implemented

**How to Add**:
1. Add dark mode CSS rules:
   ```css
   @media (prefers-color-scheme: dark) {
       #cytoscape-container {
           background: #1f2937;
       }
       /* ... */
   }
   ```

2. Update Cytoscape node colors:
   ```javascript
   const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
   const nodeColor = isDarkMode ? '#60a5fa' : '#3b82f6';
   ```

---

## 4. Extending Interactions

### 4.1 Custom Node Click Behavior

**Scenario**: Instead of re-querying, open a detail panel.

**Steps**:
1. Override `handleNodeClick()`:
   ```javascript
   class CustomSubgraphView extends SubgraphView {
       handleNodeClick(node) {
           const data = node.data();
           // Open detail panel instead
           this.openDetailPanel(data.entity_type, data.entity_key);
       }

       openDetailPanel(type, key) {
           // Your custom logic
           console.log('Opening detail panel for', type, key);
       }
   }
   ```

2. Use your custom class:
   ```javascript
   function renderSubgraphView(container) {
       state.currentViewInstance = new CustomSubgraphView();
       state.currentViewInstance.init();
   }
   ```

### 4.2 Adding Context Menu

**Scenario**: Right-click a node to show context menu.

**Steps**:
1. Add context menu library (e.g., `cytoscape-context-menus`):
   ```html
   <script src="https://unpkg.com/cytoscape-context-menus/cytoscape-context-menus.js"></script>
   ```

2. Register extension in `initCytoscape()`:
   ```javascript
   this.cy.contextMenus({
       menuItems: [
           {
               id: 'explain',
               content: 'Explain',
               selector: 'node',
               onClickFunction: (event) => {
                   const node = event.target;
                   ExplainDrawer.show(node.data('entity_type'), node.data('entity_key'));
               }
           },
           {
               id: 'copy-key',
               content: 'Copy Entity Key',
               selector: 'node',
               onClickFunction: (event) => {
                   const key = event.target.data('entity_key');
                   navigator.clipboard.writeText(key);
               }
           }
       ]
   });
   ```

### 4.3 Adding Keyboard Shortcuts

**Scenario**: Press "R" to reload graph, "H" to hide/show blind spots.

**Steps**:
1. Add keyboard listener in `init()`:
   ```javascript
   document.addEventListener('keydown', (e) => {
       if (e.key === 'r' && this.currentSeed) {
           this.loadSubgraph(this.currentSeed, this.currentKHop, this.currentMinEvidence);
       }
       if (e.key === 'h') {
           this.showBlindSpots = !this.showBlindSpots;
           if (this.currentData) {
               this.renderSubgraph(this.currentData);
           }
       }
   });
   ```

---

## 5. Integration Patterns

### 5.1 Embedding in Another View

**Scenario**: Add subgraph visualization to TasksView.

**Steps**:
1. Import SubgraphView:
   ```javascript
   // In TasksView.js
   const subgraphView = new SubgraphView();
   ```

2. Create container:
   ```javascript
   const subgraphContainer = document.createElement('div');
   subgraphContainer.id = 'main-content';  // SubgraphView expects this ID
   myContainer.appendChild(subgraphContainer);
   ```

3. Initialize:
   ```javascript
   subgraphView.init();
   subgraphView.loadSubgraph('file:manager.py');
   ```

4. Clean up when done:
   ```javascript
   subgraphView.cleanup();
   ```

### 5.2 Passing Custom Data

**Scenario**: Render a subgraph from pre-fetched data (not via API).

**Steps**:
1. Prepare data in API response format:
   ```javascript
   const customData = {
       nodes: [
           {
               id: 'n1',
               entity_type: 'file',
               entity_key: 'manager.py',
               visual: {
                   color: '#10b981',
                   size: 40,
                   /* ... */
               }
           }
       ],
       edges: [ /* ... */ ],
       metadata: { /* ... */ }
   };
   ```

2. Call `renderSubgraph()` directly:
   ```javascript
   view.renderSubgraph(customData);
   ```

### 5.3 Linking with ExplainDrawer

**Scenario**: Click a node → open ExplainDrawer instead of re-querying.

**Steps**:
1. Modify `handleNodeClick()`:
   ```javascript
   handleNodeClick(node) {
       const data = node.data();
       // Open ExplainDrawer
       ExplainDrawer.show(data.entity_type, data.entity_key, data.entity_name);
   }
   ```

2. Ensure ExplainDrawer is loaded:
   ```html
   <script src="/static/js/components/ExplainDrawer.js"></script>
   ```

---

## 6. Performance Optimization

### 6.1 Reducing Initial Load Time

**Problem**: Large subgraphs (50+ nodes) load slowly.

**Solutions**:
1. **Backend caching**: Enable Redis cache for `/api/brain/subgraph`
2. **Pagination**: Limit initial load to 20 nodes, add "Load More" button
3. **Lazy loading**: Render nodes first, edges second

**Example** (lazy edge rendering):
```javascript
renderSubgraph(data) {
    // Render nodes first
    this.cy.add(data.nodes);
    this.cy.layout({ name: 'preset' }).run();  // Fast layout

    // Render edges after 100ms
    setTimeout(() => {
        this.cy.add(data.edges);
        this.cy.layout({ name: 'cose' }).run();  // Full layout
    }, 100);
}
```

### 6.2 Improving Layout Performance

**Problem**: COSE layout is slow for 100+ nodes.

**Solutions**:
1. **Reduce iterations**: Set `numIter: 500` (default: 1000)
2. **Use faster layout**: Switch to `dagre` for hierarchical graphs
3. **Pre-computed layouts**: Store layouts in backend, send `x, y` coordinates

**Example** (dagre layout):
```javascript
layout: {
    name: 'dagre',
    rankDir: 'TB',  // Top-to-bottom
    animate: true
}
```

### 6.3 Optimizing Rendering

**Problem**: Re-rendering on filter change is slow.

**Solutions**:
1. **Hide/show instead of re-render**: Use Cytoscape's `ele.hide()` / `ele.show()`
2. **Batch updates**: Use `cy.batch()` for multiple changes

**Example** (hide weak edges):
```javascript
// Bad: Re-renders entire graph
renderSubgraph(this.currentData);

// Good: Just hide weak edges
cy.edges().filter(e => e.data('is_weak')).hide();
```

---

## 7. Testing

### 7.1 Unit Testing

**Not yet implemented** (Cytoscape.js requires DOM).

**Potential Approach**: Use jsdom + Cytoscape.js headless mode.

### 7.2 Manual Testing

**Test File**: `test_p2_subgraph_frontend.html`

**Test Commands** (in browser console):
```javascript
window.testSubgraph.testFile()         // Test file:manager.py
window.testSubgraph.testCapability()   // Test capability:api
window.testSubgraph.testHighEvidence() // Test min_evidence=5
window.testSubgraph.testError()        // Test error handling
```

**Access View**:
```javascript
const view = window.testSubgraph.getView();
const cy = window.testSubgraph.getCy();
```

### 7.3 Acceptance Testing

**Checklist**: `P2_TASK4_ACCEPTANCE_CHECKLIST.md` (80+ items)

**Key Tests**:
- Red Line 1: No evidence edges
- Red Line 2: Blind spot visibility
- Red Line 3: Coverage gaps shown
- Visual encoding correctness
- Interaction functionality
- Performance benchmarks

---

## 8. Contributing

### 8.1 Code Style

**JavaScript**:
- Use ES6 classes
- Use `const` and `let` (not `var`)
- Use template literals for strings
- Add JSDoc comments for public methods

**CSS**:
- Use BEM naming convention (if adding new components)
- Use CSS Grid/Flexbox (not floats)
- Add comments for non-obvious rules

### 8.2 Pull Request Checklist

Before submitting a PR:
- [ ] Code follows style guide
- [ ] Comments explain "why", not "what"
- [ ] No console.log statements (except for [SubgraphView] prefixed logs)
- [ ] Manual testing completed (test_p2_subgraph_frontend.html)
- [ ] Acceptance checklist items pass (P2_TASK4_ACCEPTANCE_CHECKLIST.md)
- [ ] Documentation updated (if API changed)

### 8.3 Adding New Visual Encodings

**Example**: Add "pulse" animation for high-risk blind spots.

**Steps**:
1. Add CSS animation:
   ```css
   @keyframes pulse {
       0%, 100% { opacity: 1; }
       50% { opacity: 0.5; }
   }
   ```

2. Apply to nodes:
   ```javascript
   {
       selector: 'node[is_blind_spot = "true"][blind_spot_severity >= 0.8]',
       style: {
           'animation-name': 'pulse',
           'animation-duration': '1s',
           'animation-iteration-count': 'infinite'
       }
   }
   ```

### 8.4 Adding New Layouts

**Example**: Add hierarchical layout option.

**Steps**:
1. Add layout selector in `createContainer()`:
   ```html
   <select id="layout-select">
       <option value="cose">Force-Directed (COSE)</option>
       <option value="dagre">Hierarchical (Dagre)</option>
   </select>
   ```

2. Handle layout change:
   ```javascript
   document.getElementById('layout-select').addEventListener('change', (e) => {
       const layout = e.target.value;
       this.cy.layout({ name: layout }).run();
   });
   ```

---

## Appendix A: Cytoscape.js Quick Reference

**Add Elements**:
```javascript
cy.add({ data: { id: 'n1', label: 'Node 1' } });
cy.add({ data: { id: 'e1', source: 'n1', target: 'n2' } });
```

**Remove Elements**:
```javascript
cy.elements().remove();
cy.$('#n1').remove();
```

**Query Elements**:
```javascript
cy.nodes()                         // All nodes
cy.edges()                         // All edges
cy.$('#n1')                        // Node with ID 'n1'
cy.$('node[entity_type = "file"]') // Nodes where entity_type is 'file'
```

**Iterate**:
```javascript
cy.nodes().forEach(node => {
    console.log(node.data('label'));
});
```

**Events**:
```javascript
cy.on('tap', 'node', (event) => {
    const node = event.target;
    console.log('Clicked:', node.data('label'));
});
```

**Layout**:
```javascript
const layout = cy.layout({ name: 'cose' });
layout.run();
```

**Docs**: https://js.cytoscape.org/

---

## Appendix B: API Response Format

**Endpoint**: `GET /api/brain/subgraph?seed=file:manager.py&k_hop=2`

**Response**:
```json
{
    "ok": true,
    "data": {
        "nodes": [
            {
                "id": "n123",
                "entity_type": "file",
                "entity_key": "manager.py",
                "evidence_count": 15,
                "coverage_sources": ["git", "doc", "code"],
                "is_blind_spot": false,
                "in_degree": 5,
                "out_degree": 3,
                "visual": {
                    "color": "#10b981",
                    "size": 45,
                    "border_color": "#10b981",
                    "border_width": 1,
                    "border_style": "solid",
                    "label": "manager.py\n✅ 85% | 15 evidence",
                    "tooltip": "Entity: manager.py\n..."
                }
            }
        ],
        "edges": [ /* ... */ ],
        "metadata": {
            "seed_entity": "file:manager.py",
            "total_nodes": 12,
            "coverage_percentage": 0.83,
            "missing_connections_count": 3
        }
    },
    "error": null
}
```

---

**Developer Guide Status**: ✅ Complete
**Word Count**: ~2,600 words
**Last Updated**: 2026-01-30
