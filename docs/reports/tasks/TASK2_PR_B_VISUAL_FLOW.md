# Task #2: PR-B Visual Flow Diagram

## Complete Task Lifecycle with DONE Gates

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TASK LIFECYCLE                                │
└─────────────────────────────────────────────────────────────────────┘

    START
      │
      v
┌──────────┐
│  DRAFT   │  ← Create task
└────┬─────┘
     │
     │ approve
     v
┌──────────┐
│ APPROVED │  ← Task approved
└────┬─────┘
     │
     │ queue
     v
┌──────────┐
│  QUEUED  │  ← Waiting for runner
└────┬─────┘
     │
     │ start
     v
┌──────────┐
│ RUNNING  │  ← Runner executing
└────┬─────┘
     │
     │ States within RUNNING:
     │
     ├─→ created
     ├─→ intent_processing
     ├─→ planning
     ├─→ executing  ◄─────────────────┐
     │                                 │
     │ [NEW in PR-B]                   │
     │                                 │
     v                                 │
┌──────────────┐                       │
│  VERIFYING   │  ← Run DONE gates    │
└───────┬──────┘                       │
        │                              │
        │ [Check gates]                │
        │                              │
   ┌────┴─────┐                        │
   │          │                        │
   v          v                        │
PASS         FAIL                      │
   │          │                        │
   │          │ Inject failure context │
   │          │ Return to planning ────┘
   │          │
   │          v
   │    ┌──────────┐
   │    │ planning │ ← Retry with context
   │    └────┬─────┘
   │         │
   │         └─────→ executing (retry)
   │
   │
   v
┌──────────┐
│   DONE   │  ← Task completed successfully
└──────────┘

```

## DONE Gates Execution Detail

```
┌───────────────────────────────────────────────────────────────────┐
│              VERIFYING STATE - Gate Execution                      │
└───────────────────────────────────────────────────────────────────┘

Entry: task.status = "verifying"
       task.metadata.gates = ["doctor", "smoke", "tests"]

┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Load Configuration                                       │
├─────────────────────────────────────────────────────────────────┤
│ • Read task.metadata.gates                                       │
│ • Default to ["doctor"] if not specified                         │
│ • Log: "Starting DONE gate verification"                         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            v
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Execute Gates (Sequential, Fail-Fast)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Gate 1: "doctor"                                               │
│  ┌────────────────────────────────────────┐                    │
│  │ Run: python -c "print('Doctor check')" │                    │
│  │ Timeout: 300s                           │                    │
│  │ Capture: stdout, stderr, exit_code     │                    │
│  └────────────────┬───────────────────────┘                    │
│                   │                                              │
│              ┌────┴─────┐                                        │
│              │          │                                        │
│            PASS       FAIL                                       │
│              │          │                                        │
│              v          v                                        │
│         Continue    STOP HERE ──┐                               │
│              │                   │                               │
│  Gate 2: "smoke"                │                               │
│  ┌────────────────────────────┐ │                               │
│  │ Run: python -c "..."       │ │                               │
│  └────────────┬───────────────┘ │                               │
│               │                  │                               │
│          ┌────┴─────┐           │                               │
│          │          │            │                               │
│        PASS       FAIL           │                               │
│          │          │            │                               │
│          v          v            │                               │
│     Continue    STOP HERE ───────┤                               │
│          │                       │                               │
│  Gate 3: "tests"                │                               │
│  ┌────────────────────────────┐ │                               │
│  │ Run: pytest -v --tb=short  │ │                               │
│  └────────────┬───────────────┘ │                               │
│               │                  │                               │
│          ┌────┴─────┐           │                               │
│          │          │            │                               │
│        PASS       FAIL           │                               │
│          │          │            │                               │
│          v          v            │                               │
│   All Complete  STOP HERE ───────┤                               │
│          │                       │                               │
│          v                       v                               │
│   ┌────────────┐         ┌─────────────┐                        │
│   │ ALL PASSED │         │ SOME FAILED │                        │
│   └─────┬──────┘         └──────┬──────┘                        │
└─────────┼───────────────────────┼─────────────────────────────┘
          │                       │
          v                       v
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Save Artifacts                                           │
├─────────────────────────────────────────────────────────────────┤
│ • Write: store/artifacts/{task_id}/gate_results.json            │
│ • Contents: Full gate results with stdout/stderr                │
│ • Size: ~1-5 KB (may be larger with verbose output)             │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Record in Audit                                          │
├─────────────────────────────────────────────────────────────────┤
│ • Event: GATE_VERIFICATION_RESULT                                │
│ • Level: info (pass) or error (fail)                             │
│ • Payload: Full gate results                                     │
└─────────────────┬───────────────────────────────────────────────┘
                  │
             ┌────┴──────┐
             │           │
        ALL PASSED   ANY FAILED
             │           │
             v           v
    ┌────────────┐  ┌──────────────────────┐
    │ STEP 5A:   │  │ STEP 5B:             │
    │ Success    │  │ Failure              │
    ├────────────┤  ├──────────────────────┤
    │ Return:    │  │ 1. Inject context:   │
    │ "succeeded"│  │    task.metadata[    │
    │            │  │     "gate_failure_   │
    │            │  │      context"] = {   │
    │            │  │      "failed_at",    │
    │            │  │      "summary",      │
    │            │  │      "results"       │
    │            │  │    }                 │
    │            │  │                      │
    │            │  │ 2. Return:           │
    │            │  │    "planning"        │
    │            │  │    (for retry)       │
    └────────────┘  └──────────────────────┘
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA FLOW IN PR-B                           │
└─────────────────────────────────────────────────────────────────┘

INPUT                    PROCESSING                    OUTPUT
━━━━━                    ━━━━━━━━━━                    ━━━━━━

task.metadata.gates      DoneGateRunner                Artifacts:
["doctor", "smoke"]  ──→ .run_gates()      ──→  gate_results.json
                             │
                             │
task_id              ──→     │
                             │
                             │
timeout (300s)       ──→     │
                             │
                             v
                      Execute gates:
                      1. doctor (0.1s)
                      2. smoke (0.1s)
                             │
                             │
                             v
                      Collect results:
                      - exit_code
                      - stdout
                      - stderr
                      - duration
                             │
                             │
                             v
                      Save artifacts  ──→  Audit Trail:
                             │             task_audits table
                             │
                             v
                      IF ALL PASS:
                        status = "succeeded"
                             │
                      IF ANY FAIL:
                        inject_context()  ──→  Metadata:
                        status = "planning"    gate_failure_context
```

## Failure Context Structure

```
task.metadata["gate_failure_context"]
│
├─ failed_at: "2026-01-29T12:34:56.789Z"  ← Timestamp
│
├─ failure_summary: """                    ← Human-readable
│    - doctor: passed
│    - smoke: failed (Exit code: 1)
│    - tests: error (Timeout)
│  """
│
└─ gate_results:                           ← Full details
     ├─ task_id: "01ABC123..."
     ├─ overall_status: "failed"
     ├─ total_duration_seconds: 10.5
     ├─ executed_at: "2026-01-29T..."
     └─ gates_executed: [
          {
            gate_name: "doctor",
            status: "passed",
            exit_code: 0,
            stdout: "...",
            stderr: "",
            duration_seconds: 0.1
          },
          {
            gate_name: "smoke",
            status: "failed",
            exit_code: 1,
            stdout: "",
            stderr: "Test failed...",
            duration_seconds: 0.2,
            error_message: "Exit code: 1"
          }
        ]
```

## Timeline Visualization

```
Time →

t=0s        t=1s        t=2s        t=3s        t=4s        t=5s
│           │           │           │           │           │
│ Start     │ Execute   │ Verify    │ Gates     │ Results   │ Decision
│ task      │ impl      │ start     │ run       │ saved     │ made
│           │           │           │           │           │
v           v           v           v           v           v

┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐
│Draft│→→→│Exec │→→→│Verif│   │Gate1│   │Artif│   │Next │
└─────┘   │ ute │   │ying │   │Gate2│   │acts │   │state│
          │ ... │   │     │   │Gate3│   │Audit│   │     │
          └─────┘   └─────┘   └─────┘   └─────┘   └─────┘
                                                        │
                                          ┌─────────────┴─────────────┐
                                          │                           │
                                          v                           v
                                      ┌────────┐                 ┌─────────┐
                                      │SUCCESS │                 │ FAILURE │
                                      └────┬───┘                 └────┬────┘
                                           │                          │
                                           v                          v
                                      succeeded                   planning
                                           │                          │
                                           v                          v
                                         DONE                    RETRY LOOP
```

## Retry Loop Detail

```
┌─────────────────────────────────────────────────────────────────┐
│                   RETRY LOOP ON GATE FAILURE                     │
└─────────────────────────────────────────────────────────────────┘

Iteration 1:
  planning → executing → verifying → [FAIL] → planning
                                      ↑         │
                                      │         │ Inject:
                                      │         │ - failure_summary
                                      │         │ - gate_results
                                      │         │
                                      └─────────┘

Iteration 2 (with context):
  planning → executing → verifying → [FAIL] → planning
   ↑                                   ↑         │
   │ Context:                          │         │
   │ "Previous attempt                 │         │
   │  failed doctor gate"              └─────────┘
   │
   │
Iteration 3 (with accumulated context):
  planning → executing → verifying → [PASS] → succeeded
   ↑                                            ↓
   │ Context:                                  DONE
   │ "Failed 2 times"
   │ "Issues: X, Y, Z"
   │

```

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  COMPONENT INTERACTIONS                          │
└─────────────────────────────────────────────────────────────────┘

TaskRunner                DoneGateRunner           Database
    │                          │                      │
    │ 1. Status="verifying"    │                      │
    ├──────────────────────────┼──────────────────────┤
    │                          │                      │
    │ 2. run_gates()           │                      │
    ├────────────────────────→ │                      │
    │                          │                      │
    │                          │ 3. Execute gates     │
    │                          │    (subprocess)      │
    │                          ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
    │                          │                      │
    │                          │ 4. Collect results   │
    │                          │                      │
    │ 5. GateRunResult         │                      │
    │ ←────────────────────────┤                      │
    │                          │                      │
    │ 6. save_artifacts()      │                      │
    ├────────────────────────→ │                      │
    │                          │ 7. Write JSON        │
    │                          ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ → │
    │                          │                      │
    │ 8. add_audit()           │                      │
    ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ → │
    │                          │                      │
    │ 9. update_metadata()     │                      │
    │    (if failed)           │                      │
    ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ → │
    │                          │                      │
    │ 10. update_status()      │                      │
    │     (succeeded/planning) │                      │
    ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ → │
    │                          │                      │
```

## File System Structure

```
AgentOS/
├── agentos/
│   └── core/
│       ├── gates/
│       │   ├── __init__.py          ← Exports DoneGateRunner
│       │   ├── done_gate.py         ← NEW: Gate execution logic
│       │   └── pause_gate.py        ← Existing
│       │
│       ├── runner/
│       │   └── task_runner.py       ← MODIFIED: Added verifying handler
│       │
│       └── task/
│           ├── state_machine.py     ← MODIFIED: Added transition
│           └── states.py            ← Existing (VERIFYING already defined)
│
├── tests/
│   ├── unit/
│   │   └── gates/
│   │       └── test_done_gate.py    ← NEW: 22 unit tests
│   │
│   └── integration/
│       └── test_verify_loop.py      ← NEW: 14 integration tests
│
└── store/
    └── artifacts/
        └── {task_id}/
            └── gate_results.json    ← Generated at runtime
```

---

## Key Insights

1. **Fail-Fast Strategy**: Stops on first gate failure, saves time
2. **Context Preservation**: Failure details carried forward to retry
3. **Audit Trail**: Complete history of gate executions
4. **Artifact Storage**: Persistent storage for debugging
5. **Automatic Retry**: Failed gates trigger retry with context

## Performance Impact

```
Before PR-B:
  executing → succeeded
  Duration: ~3s

After PR-B (gates pass):
  executing → verifying → succeeded
  Duration: ~3.2s (+0.2s for gates)

After PR-B (gates fail):
  executing → verifying → planning → executing → verifying → succeeded
  Duration: Varies (depends on retry attempts)
```
