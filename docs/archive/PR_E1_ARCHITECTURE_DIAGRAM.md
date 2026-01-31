# PR-E1 Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         WebUI / Chat                             │
│                    User types: /test hello                       │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POST /api/extensions/execute                  │
│              { session_id, command, dry_run }                    │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     extensions_execute.py                        │
│   1. Parse command → extension_id + action_id + args             │
│   2. Create RunRecord (status: PENDING)                          │
│   3. Generate run_id                                             │
│   4. Create Invocation                                           │
│   5. Start background thread                                     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Background Thread                           │
│   ┌─────────────────────────────────────────────────┐           │
│   │            MockRunner.run()                      │           │
│   │  ┌──────────────────────────────────────────┐   │           │
│   │  │  Stage 1: VALIDATING (5%)                │   │           │
│   │  │    progress_cb("VALIDATING", 5, "...")   │───┼──┐        │
│   │  └──────────────────────────────────────────┘   │  │        │
│   │  ┌──────────────────────────────────────────┐   │  │        │
│   │  │  Stage 2: LOADING (15%)                  │   │  │        │
│   │  │    progress_cb("LOADING", 15, "...")     │───┼──┤        │
│   │  └──────────────────────────────────────────┘   │  │        │
│   │  ┌──────────────────────────────────────────┐   │  │        │
│   │  │  Stage 3: EXECUTING (60%)                │   │  │        │
│   │  │    progress_cb("EXECUTING", 60, "...")   │───┼──┤        │
│   │  └──────────────────────────────────────────┘   │  │        │
│   │  ┌──────────────────────────────────────────┐   │  │        │
│   │  │  Stage 4: FINALIZING (90%)               │   │  │        │
│   │  │    progress_cb("FINALIZING", 90, "...")  │───┼──┤        │
│   │  └──────────────────────────────────────────┘   │  │        │
│   │  ┌──────────────────────────────────────────┐   │  │        │
│   │  │  Stage 5: DONE (100%)                    │   │  │        │
│   │  │    progress_cb("DONE", 100, "...")       │───┼──┤        │
│   │  └──────────────────────────────────────────┘   │  │        │
│   └─────────────────────────────────────────────────┘  │        │
│                                                         │        │
│                         Returns RunResult               │        │
│                  { success, output, duration }          │        │
└─────────────────────────────────────────────────────────┼────────┘
                                                          │
                   Progress Callbacks                     │
                           │                              │
                           ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         RunStore                                 │
│   ┌─────────────────────────────────────────────────────┐       │
│   │  update_progress(run_id, stage, pct, msg)           │       │
│   │    • Update run.progress_pct                        │       │
│   │    • Update run.current_stage                       │       │
│   │    • Append to run.stages[]                         │       │
│   │    • Set status to RUNNING if PENDING               │       │
│   └─────────────────────────────────────────────────────┘       │
│   ┌─────────────────────────────────────────────────────┐       │
│   │  complete_run(run_id, status, stdout, error)        │       │
│   │    • Set run.status = SUCCEEDED/FAILED              │       │
│   │    • Set run.ended_at = now()                       │       │
│   │    • Append stdout/stderr                           │       │
│   │    • Set progress_pct = 100 if SUCCEEDED            │       │
│   └─────────────────────────────────────────────────────┘       │
│                                                                  │
│   Storage: Dict[run_id, RunRecord]                              │
│   Thread-safe: threading.Lock                                   │
│   Retention: 1 hour (auto cleanup)                              │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  │ Query
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GET /api/runs/{run_id}                         │
│   1. store.get_run(run_id)                                       │
│   2. Return RunStatusResponse                                    │
│      {                                                            │
│        run_id, status, progress_pct,                             │
│        current_stage, stages[], stdout, stderr,                  │
│        started_at, ended_at, duration                            │
│      }                                                            │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                         WebUI / Chat                             │
│   Poll every 500ms until status ∈ {SUCCEEDED, FAILED, ...}      │
│   Display progress bar: 5% → 15% → 60% → 90% → 100%             │
│   Show output when complete                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Sequence

```
Time    API                 RunStore              Runner
─────   ─────────────────   ──────────────────   ────────────────────
T0      POST /execute       create_run()
        ← run_id            → PENDING

T1                                                run() starts
                                                  ↓
T1.5                        update_progress()    ← VALIDATING (5%)
                            → RUNNING

T2                          update_progress()    ← LOADING (15%)

T2.5                        update_progress()    ← EXECUTING (60%)

T3                          update_progress()    ← FINALIZING (90%)

T3.5                        update_progress()    ← DONE (100%)
                            complete_run()       ← RunResult
                            → SUCCEEDED

T4      GET /runs/{id}      get_run()
        ← status data       → RunRecord
```

## Class Relationships

```
┌────────────────────────────────────────────────────────────────┐
│                         Runner (ABC)                            │
│  + run(invocation, progress_cb) → RunResult                     │
│  + runner_type: str                                             │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     │ implements
                     ▼
         ┌──────────────────────────┐
         │      MockRunner          │
         │  runner_type = "mock"    │
         │  delay_per_stage = 0.5s  │
         └──────────────────────────┘
                     │
                     │ uses
                     ▼
         ┌──────────────────────────┐         ┌─────────────────────┐
         │      Invocation          │         │     RunResult       │
         │  + extension_id          │         │  + success: bool    │
         │  + action_id             │         │  + output: str      │
         │  + session_id            │         │  + error: str?      │
         │  + args: list            │         │  + exit_code: int   │
         │  + flags: dict           │         │  + duration_ms: int │
         └──────────────────────────┘         └─────────────────────┘
```

## RunRecord State Machine

```
         ┌─────────────────┐
         │     PENDING     │  ← create_run()
         └────────┬────────┘
                  │
                  │ update_progress() called
                  ▼
         ┌─────────────────┐
         │     RUNNING     │  ← Execution in progress
         └────────┬────────┘
                  │
                  │ complete_run() called
                  ▼
    ┌─────────────┴─────────────────────┐
    │                                    │
    ▼                                    ▼
┌──────────┐  ┌────────┐  ┌─────────┐  ┌───────────┐
│SUCCEEDED │  │ FAILED │  │ TIMEOUT │  │ CANCELED  │
└──────────┘  └────────┘  └─────────┘  └───────────┘
(Terminal states - no further transitions)
```

## Storage Structure

```
RunStore._runs = {
  "run_abc123": RunRecord {
    run_id: "run_abc123",
    extension_id: "test.test",
    action_id: "execute",
    status: RUNNING,
    progress_pct: 60,
    current_stage: "EXECUTING",
    stages: [
      {
        stage: "VALIDATING",
        progress_pct: 5,
        message: "Validating invocation parameters",
        timestamp: "2024-01-30T10:00:00.123Z"
      },
      {
        stage: "LOADING",
        progress_pct: 15,
        message: "Loading extension resources",
        timestamp: "2024-01-30T10:00:00.623Z"
      },
      {
        stage: "EXECUTING",
        progress_pct: 60,
        message: "Executing test.test/execute",
        timestamp: "2024-01-30T10:00:01.123Z"
      }
    ],
    stdout: "Mock execution successful\nExtension: test.test\n...",
    stderr: "",
    error: null,
    metadata: {
      session_id: "sess_123",
      command: "/test hello world"
    },
    created_at: datetime(...),
    started_at: datetime(...),
    ended_at: null
  },
  "run_def456": RunRecord { ... },
  ...
}
```

## API Response Examples

### Execute Response
```json
{
  "run_id": "run_abc123def456",
  "status": "PENDING"
}
```

### Status Response (Running)
```json
{
  "run_id": "run_abc123def456",
  "extension_id": "test.test",
  "action_id": "execute",
  "status": "RUNNING",
  "progress_pct": 60,
  "current_stage": "EXECUTING",
  "stages": [
    {
      "stage": "VALIDATING",
      "progress_pct": 5,
      "message": "Validating invocation parameters",
      "timestamp": "2024-01-30T10:00:00.123Z"
    },
    {
      "stage": "LOADING",
      "progress_pct": 15,
      "message": "Loading extension resources",
      "timestamp": "2024-01-30T10:00:00.623Z"
    },
    {
      "stage": "EXECUTING",
      "progress_pct": 60,
      "message": "Executing test.test/execute",
      "timestamp": "2024-01-30T10:00:01.123Z"
    }
  ],
  "stdout": "Mock execution successful\nExtension: test.test\n...",
  "stderr": "",
  "error": null,
  "started_at": "2024-01-30T10:00:00.000Z",
  "ended_at": null,
  "duration_seconds": null,
  "metadata": {
    "session_id": "sess_123",
    "command": "/test hello world"
  }
}
```

### Status Response (Completed)
```json
{
  "run_id": "run_abc123def456",
  "extension_id": "test.test",
  "action_id": "execute",
  "status": "SUCCEEDED",
  "progress_pct": 100,
  "current_stage": "DONE",
  "stages": [ /* all 5 stages */ ],
  "stdout": "Mock execution successful\n...",
  "stderr": "",
  "error": null,
  "started_at": "2024-01-30T10:00:00.000Z",
  "ended_at": "2024-01-30T10:00:02.500Z",
  "duration_seconds": 2.5,
  "metadata": { /* ... */ }
}
```

## Thread Safety

```
┌──────────────────────────────────────────────────────────────┐
│                      RunStore                                 │
│                                                               │
│   Thread 1 (API)        Thread 2 (Exec)      Thread 3 (API) │
│       │                     │                     │          │
│       │ get_run(id1)        │                     │          │
│       ├─→ [LOCK ACQUIRED]───┤                     │          │
│       │   read _runs[id1]   │                     │          │
│       │ [LOCK RELEASED] ←───┤                     │          │
│       │                     │                     │          │
│       │                     │ update_progress()   │          │
│       │                     ├─→ [LOCK ACQUIRED]───┤          │
│       │                     │   write _runs[id2]  │          │
│       │                     │ [LOCK RELEASED] ←───┤          │
│       │                     │                     │          │
│       │                     │                     │ list()   │
│       │                     │                     ├─→ [WAIT] │
│       │                     │ [LOCK RELEASED]     │          │
│       │                     │                     ├─→ [ACQ]  │
│       │                     │                     │   read   │
│       │                     │                     │ [REL] ←──┤
└──────────────────────────────────────────────────────────────┘

All RunStore operations use threading.Lock to ensure thread safety.
```

## Extension Points

Future runners can extend the base system:

```
Runner (ABC)
  ├── MockRunner (PR-E1) ✓
  ├── ExecRunner (PR-E2) - Execute CLI tools
  ├── AnalyzeRunner (PR-E3) - LLM analysis
  └── CustomRunner (Extensions) - User-defined
```

All runners use the same interface:
- Input: `Invocation` + `progress_cb`
- Output: `RunResult`
- Progress: Call `progress_cb(stage, pct, msg)`

## Summary

This architecture provides:
- ✅ Clean separation of concerns
- ✅ Thread-safe state management
- ✅ Real-time progress tracking
- ✅ RESTful API for status queries
- ✅ Extensible runner interface
- ✅ Background execution
- ✅ Complete execution history
