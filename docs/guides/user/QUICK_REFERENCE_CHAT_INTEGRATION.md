# Quick Reference: Chat Code Block Integration

## Button Actions

| Button | Icon | Action | API Call |
|--------|------|--------|----------|
| Save | Bookmark | Opens save dialog | `/api/snippets` (POST) |
| Preview | Play | Auto-save → Preview | `/api/snippets/{id}/preview` (POST) |
| Make Task | Checklist | Auto-save → Task Draft | `/api/snippets/{id}/materialize` (POST) |

---

## Code Flow

### Preview Button Click

```javascript
User clicks "Preview"
    ↓
ensureSnippetIdForCodeblock(codeblock)
    ↓ (if no snippet_id)
POST /api/snippets
    {title, language, code, tags, source}
    ↓
snippet_id stored in data-snippet-id
    ↓
Auto-detect preset (Three.js check)
    ↓
POST /api/snippets/{id}/preview
    {preset: "three-webgl-umd" or "html-basic"}
    ↓
Response: {url, preset, deps_injected, expires_at}
    ↓
openPreviewDialog() with iframe
```

### Make Task Button Click

```javascript
User clicks "Make Task"
    ↓
ensureSnippetIdForCodeblock(codeblock)
    ↓ (if no snippet_id)
POST /api/snippets (auto-save)
    ↓
snippet_id stored in data-snippet-id
    ↓
Prompt user for target_path
    ↓
POST /api/snippets/{id}/materialize
    {target_path, description}
    ↓
Response: {task_draft}
    ↓
openTaskDraftDialog() with draft details
```

---

## Auto-Detection Logic

```javascript
// In handlePreviewSnippet()
let preset = 'html-basic';  // Default

if (language === 'javascript' || language === 'js') {
    if (code.includes('THREE.') ||
        code.includes('FontLoader') ||
        code.includes('OrbitControls')) {
        preset = 'three-webgl-umd';
    }
}
```

**Three.js Keywords Detected**:
- `THREE.` (namespace)
- `FontLoader` (font loading)
- `OrbitControls` (camera controls)

**Result**: Preset automatically set to `three-webgl-umd`

---

## Data Attributes

```html
<div class="codeblock"
     data-lang="javascript"
     data-snippet-id=""              <!-- Filled on save -->
     data-session-id="main"           <!-- From state.currentSession -->
     data-message-id="msg-123">       <!-- From message element -->
    <!-- ... -->
</div>
```

**Purpose**:
- `data-snippet-id`: Track if code is saved (reuse on subsequent clicks)
- `data-session-id`: Record source session for audit trail
- `data-message-id`: Link back to original message

---

## API Request Examples

### Auto-Save Snippet

```json
POST /api/snippets

{
    "title": "javascript snippet 2026-01-28",
    "language": "javascript",
    "code": "const scene = new THREE.Scene();",
    "tags": [],
    "source": {
        "type": "chat",
        "session_id": "main",
        "message_id": "msg-123",
        "model": "claude-3-opus-20240229"
    }
}

Response:
{
    "id": "uuid-here",
    "title": "javascript snippet 2026-01-28",
    "language": "javascript",
    ...
}
```

### Create Preview

```json
POST /api/snippets/{id}/preview

{
    "preset": "three-webgl-umd"
}

Response:
{
    "snippet_id": "uuid-here",
    "preview_session_id": "session-uuid",
    "url": "/api/preview/session-uuid",
    "preset": "three-webgl-umd",
    "deps_injected": ["three-core", "three-orbit-controls"],
    "expires_at": 1738123456
}
```

### Create Task Draft

```json
POST /api/snippets/{id}/materialize

{
    "target_path": "examples/threejs_cube.html",
    "description": "Write snippet to examples/threejs_cube.html"
}

Response:
{
    "task_draft": {
        "source": "snippet",
        "snippet_id": "uuid-here",
        "title": "Materialize: javascript snippet 2026-01-28",
        "description": "Write snippet to examples/threejs_cube.html",
        "target_path": "examples/threejs_cube.html",
        "language": "javascript",
        "plan": {
            "action": "write_file",
            "path": "examples/threejs_cube.html",
            "content": "...",
            "create_dirs": true
        },
        "risk_level": "MEDIUM",
        "requires_admin_token": true
    }
}
```

---

## Dialog Components

### Preview Dialog

```javascript
openPreviewDialog({
    url: '/api/preview/session-uuid',
    preset: 'three-webgl-umd',
    deps: ['three-core', 'three-orbit-controls'],
    expiresAt: 1738123456
})
```

**Shows**:
- Header: Title, preset name, expiration time
- Collapsible deps list (if any)
- Iframe with preview URL
- Close button (X)

### Task Draft Dialog

```javascript
openTaskDraftDialog({
    title: 'Materialize: javascript snippet',
    description: 'Write snippet to path',
    target_path: 'examples/file.js',
    risk_level: 'MEDIUM',
    requires_admin_token: true,
    plan: {...}
})
```

**Shows**:
- Title, description, target path
- Risk level badge (color-coded)
- Admin token warning (if required)
- Full JSON preview
- Copy JSON button
- Close button

---

## Error Handling

### Auto-Save Fails

```javascript
try {
    const response = await fetch('/api/snippets', {...});
    if (!response.ok) throw new Error('Failed to save');
    ...
} catch (err) {
    console.error('Failed to auto-save snippet:', err);
    showToast('Failed to save snippet', 'error', 3000);
    return null;  // Stop flow
}
```

### Preview Fails

```javascript
try {
    const response = await fetch(`/api/snippets/${id}/preview`, {...});
    if (!response.ok) throw new Error('Failed to create preview');
    ...
} catch (err) {
    console.error('Preview failed:', err);
    showToast('Failed to create preview: ' + err.message, 'error', 3000);
} finally {
    button.disabled = false;  // Restore button
    button.innerHTML = originalHtml;
}
```

---

## Testing Checklist

- [ ] Code block shows all 3 buttons (Save, Preview, Make Task)
- [ ] Preview button auto-saves unsaved code
- [ ] Preview button reuses snippet_id on saved code
- [ ] Three.js code auto-detects and uses three-webgl-umd preset
- [ ] HTML code uses html-basic preset
- [ ] Preview dialog shows iframe with working preview
- [ ] Preview dialog shows correct preset name
- [ ] Preview dialog shows injected dependencies
- [ ] Preview dialog shows expiration time (1 hour)
- [ ] Make Task button auto-saves unsaved code
- [ ] Make Task button prompts for target path
- [ ] Make Task button creates valid task draft
- [ ] Task draft dialog shows all metadata
- [ ] Task draft dialog has working Copy JSON button
- [ ] No duplicate saves on repeated clicks
- [ ] Error messages show in toasts
- [ ] Button loading states work correctly

---

## Debugging Tips

### Check if snippet_id was saved

```javascript
const codeblock = document.querySelector('.codeblock');
console.log('Snippet ID:', codeblock.dataset.snippetId);
```

### Check Three.js detection

```javascript
const code = document.querySelector('.codeblock pre code').textContent;
const hasThree = code.includes('THREE.') ||
                 code.includes('FontLoader') ||
                 code.includes('OrbitControls');
console.log('Three.js detected:', hasThree);
```

### Check API response

```javascript
// In browser console after clicking Preview
// Check Network tab for:
// 1. POST /api/snippets (if auto-save)
// 2. POST /api/snippets/{id}/preview
// 3. GET /api/preview/{session_id} (iframe load)
```

### Check dialogs

```javascript
// After clicking Preview
const dialog = document.getElementById('previewDialog');
console.log('Dialog exists:', !!dialog);

// After clicking Make Task
const taskDialog = document.getElementById('taskDraftDialog');
console.log('Task dialog exists:', !!taskDialog);
```

---

## Common Issues

### Button click does nothing

**Check**:
1. Event delegation registered? (in setupChat())
2. Button has correct class? (.js-preview-snippet or .js-make-task)
3. Console errors? (check browser dev tools)

### Auto-save fails

**Check**:
1. API endpoint accessible? (curl http://localhost:8000/api/snippets)
2. Request body valid JSON?
3. Required fields present? (title, language, code)

### Preview iframe empty

**Check**:
1. Preview session created? (check response from /preview endpoint)
2. URL correct? (should be /api/preview/{session_id})
3. Session expired? (TTL is 1 hour)

### Three.js not detected

**Check**:
1. Language is 'javascript' or 'js'?
2. Code contains THREE. or FontLoader or OrbitControls?
3. Check detection logic in handlePreviewSnippet()

---

## Performance Notes

- Auto-save only happens once per code block
- Subsequent clicks reuse cached snippet_id
- Preview sessions expire after 1 hour (automatic cleanup)
- No polling or real-time updates (static previews)

---

**Quick Start**: Open `test_chat_codeblock_integration.html` in browser for visual examples
