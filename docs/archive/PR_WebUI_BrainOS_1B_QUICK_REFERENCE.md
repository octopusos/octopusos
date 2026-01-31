# PR-WebUI-BrainOS-1B: Quick Reference
## Explain Button Integration - Developer Guide

**Version**: 1.0
**Date**: 2026-01-30

---

## 📦 Component Overview

### ExplainButton
**Location**: `agentos/webui/static/js/components/ExplainButton.js`

**Purpose**: Reusable button component that triggers BrainOS Explain drawer

**Usage**:
```javascript
// 1. Create button instance
const explainBtn = new ExplainButton(
    'task',                    // entityType: 'task' | 'extension' | 'file'
    task.task_id,              // entityKey: unique identifier
    task.title || task.task_id // entityName: display name
);

// 2. Render in HTML
container.innerHTML = `
    <div class="header">
        <h3>${task.title}</h3>
        ${explainBtn.render()}
    </div>
`;

// 3. Attach event handlers (after DOM render)
ExplainButton.attachHandlers();
```

---

### ExplainDrawer
**Location**: `agentos/webui/static/js/components/ExplainDrawer.js`

**Purpose**: Right-side drawer for displaying BrainOS query results

**Usage**:
```javascript
// Singleton pattern - automatically shown when button clicked
// Can also be triggered programmatically:
ExplainDrawer.show('task', task.task_id, task.title);
```

**Methods**:
- `show(entityType, entityKey, entityName)` - Open drawer
- `hide()` - Close drawer
- `switchTab(tabName)` - Switch to 'why' | 'impact' | 'trace' | 'map'
- `query(queryType)` - Execute BrainOS query

---

## 🔑 Seed Auto-Derivation Rules

The `getSeedForEntity()` method automatically derives BrainOS seeds from entity context:

| Entity Type | Seed Format | Example Input | Example Seed |
|------------|-------------|---------------|--------------|
| `task` | `term:{entityName}` | `{ type: 'task', key: 'task123', name: 'Implement Auth' }` | `term:Implement Auth` |
| `extension` | `capability:{entityKey}` | `{ type: 'extension', key: 'postman', name: 'postman' }` | `capability:postman` |
| `file` | `file:{entityKey}` | `{ type: 'file', key: 'agentos/core/task.py', name: 'task.py' }` | `file:agentos/core/task.py` |
| *(default)* | `{entityKey}` | Custom entity | Direct key |

**Implementation**:
```javascript
getSeedForEntity() {
    switch (this.currentEntityType) {
        case 'task':
            return `term:${this.currentEntityName}`;

        case 'extension':
            return `capability:${this.currentEntityKey}`;

        case 'file':
            return `file:${this.currentEntityKey}`;

        default:
            return this.currentEntityKey;
    }
}
```

---

## 🌐 API Integration

### Endpoint Mapping

| Tab Name | API Endpoint | Seed Used |
|----------|-------------|-----------|
| Why | `POST /api/brain/query/why` | Auto-derived |
| Impact | `POST /api/brain/query/impact` | Auto-derived |
| Trace | `POST /api/brain/query/trace` | Auto-derived |
| Map | `POST /api/brain/query/subgraph` | Auto-derived (k_hop=1) |

### Request Format
```json
{
    "seed": "term:Implement Auth",
    "depth": 1,     // optional (for impact)
    "k_hop": 1      // optional (for subgraph/map)
}
```

### Response Format
```json
{
    "ok": true,
    "data": {
        "graph_version": "...",
        "seed": "term:...",
        "query_type": "why",
        "stats": { ... },
        "summary": "Found 2 path(s)...",
        "paths": [ ... ],        // for Why query
        "affected_nodes": [ ... ], // for Impact query
        "timeline": [ ... ],      // for Trace query
        "nodes": [ ... ],         // for Map query
        "edges": [ ... ],         // for Map query
        "evidence": [ ... ]
    },
    "error": null
}
```

---

## 🎨 Styling Guide

### CSS Classes

#### Button
- `.explain-btn` - Main button style
- `.explain-btn:hover` - Hover state (opacity + scale)

#### Drawer
- `.explain-drawer` - Container (fixed overlay)
- `.explain-drawer.active` - Visible state
- `.explain-drawer-overlay` - Dark background
- `.explain-drawer-content` - Main drawer panel (500px width)
- `.explain-drawer-header` - Header with title + close button
- `.explain-tabs` - Tab navigation
- `.explain-tab` - Individual tab button
- `.explain-tab.active` - Active tab
- `.explain-content` - Scrollable content area

#### Results
- `.explain-summary` - Summary message
- `.explain-paths` - Why query paths
- `.explain-path` - Individual path
- `.path-node` - Node in path
- `.path-edge` - Edge between nodes
- `.node-type` - Entity type badge
- `.evidence-item` - Evidence entry
- `.affected-node` - Impact query result
- `.timeline-event` - Trace query event
- `.subgraph-node` - Map query node

### Custom Layouts

If you need custom positioning:

```css
/* Example: Inline with title */
.my-custom-header {
    display: flex;
    align-items: center;
    gap: 10px;
}

.my-custom-header h3 {
    flex: 1;
}

.my-custom-header .explain-btn {
    flex-shrink: 0;
}
```

---

## 🔧 Integration Checklist

When adding Explain button to a new view:

### 1. Import Dependencies (index.html)
```html
<!-- CSS -->
<link rel="stylesheet" href="/static/css/explain.css?v=1">

<!-- JS -->
<script src="/static/js/components/ExplainButton.js?v=1"></script>
<script src="/static/js/components/ExplainDrawer.js?v=1"></script>
```

### 2. Create Button Instance (in View class)
```javascript
renderEntity(entity) {
    // Create button
    const explainBtn = new ExplainButton(
        'entity-type',        // Choose appropriate type
        entity.id,            // Unique identifier
        entity.name           // Display name
    );

    // Render in HTML
    return `
        <div class="entity-header">
            <h3>${entity.name}</h3>
            ${explainBtn.render()}
        </div>
    `;
}
```

### 3. Attach Handlers (after render)
```javascript
async render() {
    // ... render your view

    // Attach ExplainButton handlers
    if (typeof ExplainButton !== 'undefined') {
        ExplainButton.attachHandlers();
    }
}
```

### 4. Test
- [ ] Button appears correctly
- [ ] Drawer opens on click
- [ ] Seed derives correctly
- [ ] Queries execute
- [ ] No console errors

---

## 🐛 Common Issues & Solutions

### Issue: Button doesn't appear
**Cause**: ExplainButton.js not loaded or render() returns empty string
**Fix**: Check that script is included in index.html and button is instantiated correctly

### Issue: Click does nothing
**Cause**: `attachHandlers()` not called or called before DOM render
**Fix**: Call `attachHandlers()` AFTER the HTML is inserted into DOM

### Issue: Multiple drawers appear
**Cause**: Multiple calls to `new ExplainDrawer()`
**Fix**: Use static `ExplainDrawer.show()` method (singleton pattern)

### Issue: Wrong seed used
**Cause**: Incorrect entityType or entityKey
**Fix**: Verify entity type matches one of: 'task', 'extension', 'file'

### Issue: "BrainOS index not found" error
**Cause**: `.brainos/` directory doesn't exist
**Fix**: This is expected if index not built. User should see friendly error message, not crash.

### Issue: XSS vulnerability
**Cause**: Not escaping HTML in entity names
**Fix**: ExplainButton and ExplainDrawer both use `escapeHtml()` method. Ensure it's called.

---

## 📊 Performance Considerations

### Query Execution Time
- **Typical**: < 500ms for local SQLite index
- **Large graphs**: Up to 2s for complex queries
- **Network issues**: May timeout at 30s (browser default)

### Drawer Animation
- **Duration**: 0.3s slide-in
- **Performance**: GPU-accelerated transform (smooth on all devices)

### Memory Usage
- **Single drawer instance**: ~50KB
- **Query results**: Varies (typically < 100KB JSON)
- **No caching**: Each tab switch triggers new query

---

## 🔍 Debugging Tips

### Enable Verbose Logging
```javascript
// In ExplainDrawer.js, add console logs:
async query(queryType) {
    const seed = this.getSeedForEntity();
    console.log('🧠 Explain Query:', { queryType, seed });

    // ... rest of code

    console.log('🧠 Query Result:', result);
}
```

### Check Network Requests
1. Open DevTools → Network tab
2. Filter: `brain/query`
3. Click Explain button
4. Check request payload and response

### Test Seed Derivation
```javascript
// In browser console:
const btn = new ExplainButton('task', 'task123', 'Test Task');
const drawer = new ExplainDrawer();
drawer.currentEntityType = 'task';
drawer.currentEntityKey = 'task123';
drawer.currentEntityName = 'Test Task';
console.log(drawer.getSeedForEntity()); // Should output: "term:Test Task"
```

---

## 📚 API Error Codes

| Status Code | Meaning | User Message |
|------------|---------|--------------|
| 200 | Success | (Show results) |
| 404 | BrainOS index not found | "BrainOS index not found. Build index first." |
| 500 | Query execution error | "Failed to query BrainOS: [error message]" |
| Network Error | Fetch failed | "Failed to connect to BrainOS API" |

---

## 🎓 Best Practices

### 1. Entity Type Selection
- Use `'task'` for tasks, jobs, work items
- Use `'extension'` for plugins, capabilities, slash commands
- Use `'file'` for files, paths, session contexts
- Use custom type for domain-specific entities (update `getSeedForEntity()`)

### 2. Entity Key Selection
- Use stable identifiers (IDs, paths, names)
- Avoid changing keys (breaks BrainOS links)
- Use hierarchical keys for clarity (e.g., `session:abc123`)

### 3. Entity Name Selection
- Use human-readable names
- Keep under 50 characters (for drawer header)
- Escape HTML to prevent XSS

### 4. Error Handling
- Always check `result.ok` before accessing `result.data`
- Show friendly error messages to users
- Log errors to console for debugging

### 5. Performance
- Avoid calling `attachHandlers()` multiple times on same elements
- Use event delegation for dynamic content
- Consider adding caching for frequently queried entities (future enhancement)

---

## 🔗 Related Documentation

- [PR-WebUI-BrainOS-1B Implementation Report](PR_WebUI_BrainOS_1B_IMPLEMENTATION_REPORT.md)
- [PR-WebUI-BrainOS-1B Manual Test Guide](PR_WebUI_BrainOS_1B_MANUAL_TEST_GUIDE.md)
- [BrainOS API Documentation](agentos/webui/api/brain.py)
- [BrainOS Query Service](agentos/core/brain/service.py)

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-30 | Initial release (PR-1B) |

---

**Maintained by**: AgentOS Team
**Last Updated**: 2026-01-30
