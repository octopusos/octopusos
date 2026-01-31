# Network Mode Integration - Flow Diagram

## Page Load Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User Opens Communication View                                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ constructor() → init()                                       │
│   - Render HTML                                              │
│   - setupFilterBar()                                         │
│   - setupDataTable()                                         │
│   - setupEventListeners()                                    │
│   - loadAllData()                                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ loadAllData() - Parallel Execution with Promise.all()       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ loadNetworkMode()│  │ loadStatus() │  │ loadPolicy() │  │
│  │      [NEW]       │  │              │  │              │  │
│  └────────┬────────┘  └──────┬───────┘  └──────┬───────┘  │
│           │                   │                  │          │
│           │  ┌────────────────┴──────────────────┴──┐      │
│           │  │         loadAudits()                  │      │
│           │  └───────────────────────────────────────┘      │
└───────────┼─────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│ loadNetworkMode() Flow                                         │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ GET /api/communication/mode                           │    │
│  └──────────────┬───────────────────────────────────────┘    │
│                 │                                             │
│     ┌───────────┴────────────┐                               │
│     │                         │                               │
│     ▼                         ▼                               │
│  SUCCESS                   ERROR                              │
│     │                         │                               │
│     ▼                         ▼                               │
│  Extract mode            Set default 'on'                     │
│     │                         │                               │
│     ▼                         ▼                               │
│  updateNetworkModeUI()   Toast.warning()                      │
│     │                         │                               │
│     └──────────┬──────────────┘                               │
│                │                                              │
│                ▼                                              │
│  ┌────────────────────────────────────┐                      │
│  │ UI Updated:                         │                      │
│  │ - Active button highlighted         │                      │
│  │ - Description text set              │                      │
│  │ - Mode value displayed (OFF/ON/...) │                      │
│  └────────────────────────────────────┘                      │
└───────────────────────────────────────────────────────────────┘
```

## Mode Change Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User Clicks Mode Button (OFF / READONLY / ON)               │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ setNetworkMode(mode)                                         │
├─────────────────────────────────────────────────────────────┤
│  1. Validate mode (off/readonly/on)                          │
│  2. Disable all mode buttons                                 │
│  3. Set opacity to 0.6                                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌───────────────────────────────────────────────────────────────┐
│ PUT /api/communication/mode                                    │
│                                                                │
│ Body: {                                                        │
│   "mode": "readonly",                                          │
│   "updated_by": "webui_user",                                  │
│   "reason": "Manual change from WebUI"                         │
│ }                                                              │
└─────────────┬─────────────────────────────────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
┌─────────┐      ┌─────────────┐
│ SUCCESS │      │    ERROR    │
└────┬────┘      └──────┬──────┘
     │                  │
     │          ┌───────┴────────┬────────────┬───────────────┐
     │          │                │            │               │
     │          ▼                ▼            ▼               ▼
     │      ┌──────┐        ┌──────┐    ┌────────┐    ┌──────────┐
     │      │ 403  │        │ 400  │    │ Other  │    │ Network  │
     │      │Forbid│        │ Bad  │    │ HTTP   │    │  Error   │
     │      │      │        │Request    │ Error  │    │          │
     │      └──┬───┘        └──┬───┘    └───┬────┘    └────┬─────┘
     │         │               │            │              │
     │         ▼               ▼            ▼              ▼
     │    ┌────────┐      ┌────────┐   ┌────────┐   ┌──────────┐
     │    │Toast:  │      │Toast:  │   │Toast:  │   │Toast:    │
     │    │No perm │      │Invalid │   │Failed  │   │Network   │
     │    │        │      │request │   │        │   │error     │
     │    └────────┘      └────────┘   └────────┘   └──────────┘
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ Success Path                                                  │
├──────────────────────────────────────────────────────────────┤
│  1. updateNetworkModeUI(mode)                                 │
│     - Remove 'active' from all buttons                        │
│     - Add 'active' to selected button                         │
│     - Update description text                                 │
│     - Update mode value display                               │
│                                                               │
│  2. Toast.success("Network mode changed to READONLY")         │
│                                                               │
│  3. console.log("Network mode changed:", result.data)         │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │   FINALLY    │
                   │   Block      │
                   ├──────────────┤
                   │ Re-enable    │
                   │ all buttons  │
                   │              │
                   │ Restore      │
                   │ opacity: 1   │
                   └──────────────┘
```

## Auto-Refresh Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User Enables Auto-Refresh Toggle                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ toggleAutoRefresh(true)                                      │
│   - Set autoRefreshEnabled = true                            │
│   - Start setInterval(10000ms)                               │
│   - Toast.success("Auto-refresh enabled")                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                 Every 10 Seconds                              │
│                       │                                       │
│                       ▼                                       │
│              loadAllData()                                    │
│                       │                                       │
│       ┌───────────────┼───────────────┐                      │
│       │               │               │                      │
│       ▼               ▼               ▼                      │
│ loadNetworkMode() loadStatus()  loadPolicy()                 │
│       │               │               │                      │
│       └───────────────┴───────┬───────┘                      │
│                               │                              │
│                               ▼                              │
│                         loadAudits()                         │
│                                                              │
│  → Network mode stays in sync with backend changes          │
└──────────────────────────────────────────────────────────────┘
```

## Error Handling Decision Tree

```
                    ┌─────────────────────┐
                    │ API Call Initiated  │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
            ┌──────────────┐      ┌──────────────┐
            │  try block   │      │ catch block  │
            └──────┬───────┘      └──────┬───────┘
                   │                     │
        ┌──────────┴──────────┐          │
        │                     │          │
        ▼                     ▼          │
   ┌────────┐          ┌──────────┐     │
   │response│          │response  │     │
   │  .ok   │          │ !.ok     │     │
   │ = true │          │or error  │     │
   └───┬────┘          └────┬─────┘     │
       │                    │           │
       ▼                    ▼           ▼
  ┌─────────┐      ┌─────────────┐  ┌──────────────┐
  │ result  │      │Check status │  │Network error │
  │  .ok    │      │    code:    │  │Type check    │
  │ = true  │      ├─────────────┤  ├──────────────┤
  └───┬─────┘      │ 403? 400?   │  │fetch failed? │
      │            │ other?      │  │other?        │
      │            └──────┬──────┘  └──────┬───────┘
      │                   │                │
      ▼                   ▼                ▼
┌───────────┐    ┌─────────────────┐  ┌──────────────┐
│ SUCCESS   │    │  ERROR PATH     │  │EXCEPTION PATH│
├───────────┤    ├─────────────────┤  ├──────────────┤
│Update UI  │    │Specific error   │  │Generic error │
│Toast OK   │    │Toast message    │  │Toast message │
│Log data   │    │Log error        │  │Log error     │
└───────────┘    └─────────────────┘  └──────────────┘
      │                   │                │
      └───────────────────┴────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ FINALLY block │
                  ├───────────────┤
                  │ Re-enable     │
                  │ buttons       │
                  │ Restore       │
                  │ opacity       │
                  └───────────────┘
```

## State Management

```
┌─────────────────────────────────────────────────────────────┐
│                    UI State Lifecycle                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Initial State (on page load)                                │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Mode Value: "Loading..."                            │     │
│  │ Buttons: All inactive                                │     │
│  │ Description: "Select a network mode..."             │     │
│  └────────────────────────────────────────────────────┘     │
│                          │                                   │
│                          ▼                                   │
│  After loadNetworkMode()                                     │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Mode Value: "ON" (or current mode)                  │     │
│  │ Buttons: Active button highlighted                  │     │
│  │ Description: Mode-specific description              │     │
│  └────────────────────────────────────────────────────┘     │
│                          │                                   │
│                          ▼                                   │
│  User Clicks Button                                          │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Mode Value: Unchanged                               │     │
│  │ Buttons: All disabled, opacity 0.6                  │     │
│  │ Description: Unchanged                              │     │
│  └────────────────────────────────────────────────────┘     │
│                          │                                   │
│               ┌──────────┴──────────┐                        │
│               │                     │                        │
│               ▼                     ▼                        │
│          SUCCESS                 FAILURE                     │
│  ┌──────────────────┐    ┌─────────────────────┐            │
│  │ Mode Value: NEW  │    │ Mode Value: OLD     │            │
│  │ Buttons: New     │    │ Buttons: Old active │            │
│  │   active, enabled│    │   enabled           │            │
│  │ Description: NEW │    │ Description: OLD    │            │
│  │ Toast: Success   │    │ Toast: Error        │            │
│  └──────────────────┘    └─────────────────────┘            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Component Interaction

```
┌───────────────────────────────────────────────────────────────┐
│                  CommunicationView Component                   │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │                User Interface                        │     │
│  ├─────────────────────────────────────────────────────┤     │
│  │  [ OFF ] [ READONLY ] [ ON ]  ← Mode Buttons        │     │
│  │                                                      │     │
│  │  Current Mode: ON                                    │     │
│  │  Description: All external communications enabled    │     │
│  └────────────────┬─────────────────────────────────────┘     │
│                   │                                           │
│  ┌────────────────┴─────────────────────────────────────┐     │
│  │            JavaScript Event Handlers                 │     │
│  ├──────────────────────────────────────────────────────┤     │
│  │  onClick → setNetworkMode(mode)                      │     │
│  │  onLoad  → loadNetworkMode()                         │     │
│  │  onChange → updateNetworkModeUI(mode)                │     │
│  └────────────────┬─────────────────────────────────────┘     │
│                   │                                           │
│  ┌────────────────┴─────────────────────────────────────┐     │
│  │              API Communication Layer                 │     │
│  ├──────────────────────────────────────────────────────┤     │
│  │  GET  /api/communication/mode                        │     │
│  │  PUT  /api/communication/mode                        │     │
│  └────────────────┬─────────────────────────────────────┘     │
│                   │                                           │
└───────────────────┼───────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────┐
│              Backend API (communication.py)                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │           Communication Router                       │     │
│  ├─────────────────────────────────────────────────────┤     │
│  │  @router.get("/api/communication/mode")              │     │
│  │  @router.put("/api/communication/mode")              │     │
│  └────────────────┬─────────────────────────────────────┘     │
│                   │                                           │
│  ┌────────────────┴─────────────────────────────────────┐     │
│  │        CommunicationService                          │     │
│  ├──────────────────────────────────────────────────────┤     │
│  │  network_mode_manager.get_mode_info()                │     │
│  │  network_mode_manager.set_mode()                     │     │
│  └────────────────┬─────────────────────────────────────┘     │
│                   │                                           │
│  ┌────────────────┴─────────────────────────────────────┐     │
│  │        NetworkModeManager                            │     │
│  ├──────────────────────────────────────────────────────┤     │
│  │  - Current mode state                                │     │
│  │  - Mode change history                               │     │
│  │  - Validation logic                                  │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Comprehensive Flow Summary

```
┌──────────────────────────────────────────────────────────────┐
│                 COMPLETE USER JOURNEY                         │
└──────────────────────────────────────────────────────────────┘

1. Page Load
   │
   ├─ HTML rendered with "Loading..." state
   ├─ Event listeners attached
   ├─ loadAllData() called
   │   └─ loadNetworkMode() fetches current mode
   │       └─ updateNetworkModeUI() sets initial state
   └─ User sees current mode (e.g., "ON")

2. Mode Change Requested
   │
   ├─ User clicks "READONLY" button
   ├─ setNetworkMode("readonly") called
   ├─ Buttons disabled (visual feedback)
   ├─ PUT request sent to backend
   │   └─ Body: {mode: "readonly", updated_by: "webui_user", ...}
   └─ User waits (buttons disabled, opacity 0.6)

3. Response Received
   │
   ├─ Success Path:
   │   ├─ updateNetworkModeUI("readonly")
   │   ├─ Toast: "Network mode changed to READONLY"
   │   └─ Console log with change details
   │
   └─ Error Path:
       ├─ Toast shows specific error message
       ├─ UI remains in previous state
       └─ Console error logged

4. Post-Change State
   │
   ├─ Buttons re-enabled (opacity 1)
   ├─ UI reflects new mode (or old mode if error)
   └─ User can interact again

5. Auto-Refresh (if enabled)
   │
   └─ Every 10 seconds:
       └─ loadNetworkMode() called
           └─ UI syncs with backend state
```

---

**Legend:**
- `┌─┐` = Container/Box
- `│` = Vertical flow
- `─` = Horizontal separator
- `▼` = Flow direction
- `→` = Action/Transition
- `├─` = Branch point
- `└─` = End branch

**Notes:**
- All flows are non-blocking (async/await)
- UI updates are atomic (single method)
- Error handling is comprehensive at every step
- State management prevents race conditions (disabled buttons)
