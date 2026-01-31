# Snippet Explain Feature - Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Action                                  │
│                  Click "Explain" Button                              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Frontend: SnippetsView.js                           │
│              Method: showExplainDialog(snippet)                      │
├─────────────────────────────────────────────────────────────────────┤
│  1. Remove existing dialog if any                                    │
│  2. Create modal dialog HTML with:                                   │
│     - Runtime selector (Local/Cloud)                                 │
│     - Provider selector                                              │
│     - Model selector                                                 │
│  3. Attach event listeners:                                          │
│     - Runtime change → Update provider options                       │
│     - Provider change → Load models from API                         │
│     - Confirm button → explainSnippetWithSession()                   │
│     - Cancel/Close/Escape → Close dialog                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     User Selects Configuration                       │
│              Runtime + Provider + Model                              │
│                  Click "Create & Explain"                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Frontend: SnippetsView.js                           │
│         Method: explainSnippetWithSession(snippet, config)           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Step 1: Get Language Preference                                     │
│  ┌─────────────────────────────────────────┐                        │
│  │ GET /api/config                         │                        │
│  │ Response: { settings: { language: "zh" }}│                        │
│  └─────────────────────────────────────────┘                        │
│                             │                                         │
│                             ▼                                         │
│  Step 2: Generate Explanation Prompt                                 │
│  ┌─────────────────────────────────────────┐                        │
│  │ POST /api/snippets/{id}/explain?lang=zh │                        │
│  │ Response: { prompt: "请逐行解释..." }    │                        │
│  └─────────────────────────────────────────┘                        │
│                             │                                         │
│                             ▼                                         │
│  Step 3: Create New Chat Session                                     │
│  ┌─────────────────────────────────────────┐                        │
│  │ POST /api/sessions                      │                        │
│  │ Body: {                                 │                        │
│  │   title: "Explain: {snippet_title}",    │                        │
│  │   metadata: {                           │                        │
│  │     runtime: "local",                   │                        │
│  │     provider: "ollama",                 │                        │
│  │     model: "llama2",                    │                        │
│  │     snippet_id: "xxx"                   │                        │
│  │   }                                     │                        │
│  │ }                                       │                        │
│  │ Response: { id: "01H...", title: "..." }│                        │
│  └─────────────────────────────────────────┘                        │
│                             │                                         │
│                             ▼                                         │
│  Step 4: Send Prompt as First Message                                │
│  ┌─────────────────────────────────────────┐                        │
│  │ POST /api/sessions/{id}/messages        │                        │
│  │ Body: {                                 │                        │
│  │   role: "user",                         │                        │
│  │   content: "请逐行解释..."              │                        │
│  │ }                                       │                        │
│  │ Response: { id: "msg-xxx", ... }        │                        │
│  └─────────────────────────────────────────┘                        │
│                             │                                         │
│                             ▼                                         │
│  Step 5: Navigate to Chat View                                       │
│  ┌─────────────────────────────────────────┐                        │
│  │ window.navigateToView('chat',           │                        │
│  │   { session_id: "01H..." })             │                        │
│  └─────────────────────────────────────────┘                        │
│                                                                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Frontend: main.js                               │
│              Function: navigateToView(viewName, filters)             │
├─────────────────────────────────────────────────────────────────────┤
│  1. Update navigation state                                          │
│  2. Load chat view                                                   │
│  3. Call switchSession(session_id)                                   │
│     - Update state.currentSession                                    │
│     - Load messages from session                                     │
│     - Reconnect WebSocket                                            │
│     - Update UI                                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Chat View Display                               │
├─────────────────────────────────────────────────────────────────────┤
│  Session: "Explain: {snippet_title}"                                 │
│  ┌─────────────────────────────────────────┐                        │
│  │ [User] 请逐行解释以下代码...            │                        │
│  │                                         │                        │
│  │ **标题**: Python Helper Function        │                        │
│  │                                         │                        │
│  │ ```python                               │                        │
│  │ def calculate_sum(a, b):                │                        │
│  │     return a + b                        │                        │
│  │ ```                                     │                        │
│  │                                         │                        │
│  │ 请提供：                                │                        │
│  │ 1. 代码的整体功能说明                   │                        │
│  │ 2. 逐行或逐块的详细解释                 │                        │
│  │ 3. 适用场景                             │                        │
│  │ 4. 使用时需要注意的事项                 │                        │
│  │ 5. 可能的改进建议（如有）               │                        │
│  └─────────────────────────────────────────┘                        │
│                                                                       │
│  [Ready to receive AI response...]                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Points

### API Calls Sequence
1. `GET /api/config` - Get language preference
2. `POST /api/snippets/{id}/explain?lang={lang}` - Generate prompt
3. `POST /api/sessions` - Create session with metadata
4. `POST /api/sessions/{id}/messages` - Send prompt as first message
5. Navigate to chat view with new session

### Error Handling
- Each API call has try-catch with appropriate error messages
- Validation before session creation (model must be selected)
- Toast notifications for all state changes
- Graceful fallback if config API fails (default to 'zh')

### Dialog Features
- Dynamic provider options based on runtime selection
- Asynchronous model loading from provider API
- Multiple close methods (button, overlay, cancel, escape)
- Loading states for model dropdown
- Inline styles for consistent appearance

### Session Metadata
Stored in session for future reference:
- runtime: "local" | "cloud"
- provider: "ollama" | "anthropic" | etc.
- model: model name
- snippet_id: original snippet ID
- language: "zh" | "en" (from config)
