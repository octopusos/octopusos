# Task #3: Mode Selector Quick Reference Card

## API Endpoints

### Update Conversation Mode
```http
PATCH /api/sessions/{session_id}/mode
Content-Type: application/json

{
  "mode": "development"  // chat | discussion | plan | development | task
}
```

**Response**:
```json
{
  "ok": true,
  "session": {
    "session_id": "01xxx",
    "conversation_mode": "development",
    "execution_phase": "planning",
    "title": "Session Title"
  }
}
```

### Update Execution Phase
```http
PATCH /api/sessions/{session_id}/phase
Content-Type: application/json

{
  "phase": "execution",  // planning | execution
  "actor": "user",
  "reason": "Enable external search",
  "confirmed": true  // Required for execution phase
}
```

**Response**:
```json
{
  "ok": true,
  "session": {
    "session_id": "01xxx",
    "conversation_mode": "development",
    "execution_phase": "execution",
    "title": "Session Title"
  },
  "audit_id": "audit_abc123"
}
```

---

## JavaScript Components

### ModeSelector

```javascript
// Initialize
const modeSelector = new ModeSelector({
  container: document.getElementById('mode-selector-container'),
  currentMode: 'chat',
  sessionId: 'session-123',
  onChange: (mode, data) => {
    console.log('Mode changed to:', mode);
  }
});

// Update session
modeSelector.setSessionId('new-session-id');

// Set mode programmatically (no API call)
modeSelector.setMode('development');

// Trigger mode change (with API call)
await modeSelector.selectMode('development');
```

**Available Modes**:
- `chat` - Free-form conversation 💬
- `discussion` - Structured brainstorming 🗣️
- `plan` - Planning and design 📋
- `development` - Active development work ⚙️
- `task` - Task-focused conversation ✓

### PhaseSelector

```javascript
// Initialize
const phaseSelector = new PhaseSelector({
  container: document.getElementById('phase-selector-container'),
  currentPhase: 'planning',
  sessionId: 'session-123',
  conversationMode: 'chat',
  onChange: (phase, data) => {
    console.log('Phase changed to:', phase);
  }
});

// Update session
phaseSelector.setSessionId('new-session-id');

// Set phase programmatically (no API call)
phaseSelector.setPhase('execution');

// Update mode (affects disabled state)
phaseSelector.setConversationMode('plan');  // Disables selector

// Trigger phase change (with API call + confirmation)
await phaseSelector.selectPhase('execution');
```

**Available Phases**:
- `planning` - Internal operations only 🧠
- `execution` - External communication enabled 🚀

---

## CSS Classes

### Mode Selector
```html
<div class="mode-selector">
  <label class="mode-selector-label">Conversation Mode</label>
  <div class="mode-selector-options">
    <button class="mode-selector-option active" data-mode="chat">
      <span class="mode-icon">💬</span>
      <span class="mode-label">Chat</span>
    </button>
  </div>
</div>
```

### Phase Selector
```html
<div class="phase-selector">
  <label class="phase-selector-label">Execution Phase</label>
  <div class="phase-selector-options">
    <button class="phase-selector-option active" data-phase="planning">
      <span class="phase-icon">🧠</span>
      <span class="phase-label">Planning</span>
    </button>
  </div>
  <div class="phase-selector-hint">Fixed to Planning in Plan mode</div>
</div>
```

### States
- `.mode-selector-option.active` - Selected mode (blue)
- `.phase-selector-option.active` - Selected phase (green/amber)
- `.phase-selector-option.disabled` - Disabled state (gray, 50% opacity)
- `.phase-selector.disabled` - Entire selector disabled

---

## Browser Console Commands

### Check Component State
```javascript
// Check mode selector state
modeSelectorInstance.currentMode         // Current mode
modeSelectorInstance.sessionId           // Current session

// Check phase selector state
phaseSelectorInstance.currentPhase       // Current phase
phaseSelectorInstance.conversationMode   // Current mode
phaseSelectorInstance.isDisabled()       // Disabled state
```

### Manual API Calls
```javascript
// Update mode
await fetch('/api/sessions/01xxx/mode', {
  method: 'PATCH',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({mode: 'development'})
}).then(r => r.json());

// Update phase
await fetch('/api/sessions/01xxx/phase', {
  method: 'PATCH',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    phase: 'execution',
    confirmed: true,
    actor: 'console',
    reason: 'Manual test'
  })
}).then(r => r.json());
```

### Get Session Data
```javascript
// Fetch session with mode/phase
await fetch('/api/sessions/01xxx')
  .then(r => r.json())
  .then(session => {
    console.log('Mode:', session.conversation_mode);
    console.log('Phase:', session.execution_phase);
  });
```

---

## Interaction Rules

### Mode → Phase Behavior

| Mode        | Phase Selector State | Allowed Phases    |
|-------------|----------------------|-------------------|
| chat        | Enabled              | planning, execution |
| discussion  | Enabled              | planning, execution |
| **plan**    | **Disabled**         | **planning only**   |
| development | Enabled              | planning, execution |
| task        | Enabled              | planning, execution |

### Confirmation Rules

| Phase      | Confirmation Required | Dialog Shown |
|------------|-----------------------|--------------|
| planning   | No                    | No           |
| execution  | **Yes**               | **Yes**      |

---

## Error Codes

| Code | Error | Description |
|------|-------|-------------|
| 400  | Bad Request | Invalid mode/phase, missing confirmation |
| 403  | Forbidden | Plan mode blocks execution phase |
| 404  | Not Found | Session not found |
| 500  | Internal Server Error | Server-side error |

---

## Debug Checklist

### Components Not Visible
```javascript
// Check if components exist
console.log('Mode:', modeSelectorInstance);
console.log('Phase:', phaseSelectorInstance);

// Check containers
console.log(document.getElementById('mode-selector-container'));
console.log(document.getElementById('phase-selector-container'));
```

### API Calls Failing
```javascript
// Check session ID
console.log('Current session:', state.currentSession);

// Test health endpoint
fetch('/api/health').then(r => r.json()).then(console.log);

// Check if routes are registered
fetch('/api/sessions').then(r => r.json()).then(console.log);
```

### Mode/Phase Not Updating
```javascript
// Manually trigger update
updateModePhaseSelectorsForSession(state.currentSession, {
  conversation_mode: 'development',
  execution_phase: 'planning'
});

// Check if selectors received update
console.log('Mode:', modeSelectorInstance.currentMode);
console.log('Phase:', phaseSelectorInstance.currentPhase);
```

---

## Common Patterns

### Pattern 1: Initialize on Session Load
```javascript
async function initializeSession(sessionId) {
  const response = await fetch(`/api/sessions/${sessionId}`);
  const sessionData = await response.json();

  updateModePhaseSelectorsForSession(sessionId, sessionData);
}
```

### Pattern 2: Sync Mode with Phase
```javascript
modeSelectorInstance = new ModeSelector({
  onChange: (mode, data) => {
    // Automatically update phase selector
    phaseSelectorInstance.setConversationMode(mode);

    // Force planning phase when switching to plan mode
    if (mode === 'plan') {
      phaseSelectorInstance.selectPhase('planning');
    }
  }
});
```

### Pattern 3: Validate Before Phase Change
```javascript
phaseSelectorInstance = new PhaseSelector({
  onChange: async (phase, data) => {
    if (phase === 'execution') {
      // Show custom warning
      console.warn('Execution phase enables external communication');

      // Log to audit
      console.log('Audit ID:', data.audit_id);
    }
  }
});
```

---

## File Locations

### Backend
- API: `/agentos/webui/api/sessions.py`
- Service: `/agentos/core/chat/service.py`
- Models: `/agentos/core/chat/models.py`

### Frontend
- ModeSelector: `/agentos/webui/static/js/components/ModeSelector.js`
- PhaseSelector: `/agentos/webui/static/js/components/PhaseSelector.js`
- CSS: `/agentos/webui/static/css/mode-selector.css`
- Main: `/agentos/webui/static/js/main.js`

### Template
- HTML: `/agentos/webui/templates/index.html`

---

## Version Info

- **Implemented**: Task #3
- **Enhanced in**: Task #4 (confirmation + mode-phase rules)
- **CSS Version**: v1
- **Component Version**: v1
- **API Version**: v0.3.2+

---

## Related Documentation

- Full Implementation: `TASK_3_IMPLEMENTATION_SUMMARY.md`
- Manual Testing: `TASK_3_MANUAL_TEST_GUIDE.md`
- API Spec: `agentos/webui/api/sessions.py` docstrings
- Architecture: AgentOS WebUI docs

---

**Quick Tip**: Use browser DevTools Network tab to inspect API calls and Console tab to check component state.
