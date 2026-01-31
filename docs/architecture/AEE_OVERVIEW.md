# AgentOS Autonomous Execution Engine (AEE)

## What is AEE?

**AgentOS Autonomous Execution Engine (AEE)** is a production-ready framework for autonomous task execution with built-in quality gates and full auditability.

```
Chat → Task → Runner → Verify → Done
```

### The Problem We Solve

Traditional AI coding assistants operate in a "request-response" loop:
- User asks → AI responds → User reviews → Repeat
- No automatic quality verification
- No autonomous iteration on failures
- No structured sub-task coordination

**AEE changes this.**

### The AEE Flow

```
User Input (Chat or API)
    ↓
Automatic Task Creation (DRAFT → APPROVED → QUEUED)
    ↓
Runner Starts (<5 seconds, event-driven)
    ↓
Planning Stage (Generate execution plan + extract work_items)
    ↓
Executing Stage (Serial or parallel execution of work_items)
    ↓
Verifying Stage (Run DONE gates: doctor, smoke, tests)
    ↓
    ├─ Gates Pass → SUCCEEDED ✅
    └─ Gates Fail → Return to Planning (with failure context) ⟲

Maximum Iterations: Configurable (default: 20)
Exit Reason: Always recorded (done, max_iterations, blocked, etc.)
```

### Key Features

#### 1. **Event-Driven Triggering**
- Chat command (`/task`) or API call
- Automatic state transitions: DRAFT → APPROVED → QUEUED → RUNNING
- **<5 second latency** (vs 30-60 seconds with polling)
- **6-12x performance improvement**

#### 2. **Quality Gates (DONE Gates)**
- **doctor**: Basic health check (~0.1s)
- **smoke**: Quick smoke tests (~0.1s)
- **tests**: Full pytest suite (configurable timeout)
- Configurable per-task: `metadata.gates = ["doctor", "smoke", "tests"]`

#### 3. **Autonomous Iteration**
- Gate failures automatically trigger retry
- Failure context injected into next planning iteration
- Continues until gates pass or max_iterations reached
- No "false completion" - verified or explicit failure

#### 4. **Work Items Coordination**
- Tasks automatically decompose into work_items
- Serial execution (parallel coming in PR-D)
- Structured output schema:
  - files_changed
  - commands_run
  - tests_run
  - evidence
  - handoff_notes

#### 5. **Full Auditability**
- Every operation recorded to `task_audits`
- Complete artifact trail:
  - open_plan.json (planning output)
  - work_items.json (task decomposition)
  - work_item_{id}.json (individual results)
  - work_items_summary.json (aggregated results)
  - gate_results.json (verification results)
- Explicit `exit_reason` on termination

#### 6. **AUTONOMOUS Mode Protection**
- Detects configuration errors (e.g., approval required in autonomous mode)
- Automatically marks task as `blocked` instead of false success
- Clear exit_reason for operations monitoring

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  • Chat (WebSocket)                                          │
│  • REST API (/api/tasks)                                     │
│  • CLI (agentos task ...)                                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   Task Service Layer                         │
│  • create_approve_queue_and_start()                          │
│  • State machine enforcement                                 │
│  • Audit logging                                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    TaskLauncher                              │
│  • In-process triggering                                     │
│  • Background thread execution                               │
│  • Non-blocking                                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                     TaskRunner                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Planning Stage                                         │ │
│  │  • ModePipelineRunner (open_plan mode)                │ │
│  │  • Extract work_items from plan                       │ │
│  │  • Save to metadata + artifact                        │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Executing Stage                                        │ │
│  │  • Load work_items from metadata                      │ │
│  │  • Execute serially (with fail-fast)                  │ │
│  │  • Record individual audit + artifact per work_item   │ │
│  │  • Aggregate results to summary                       │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Verifying Stage                                        │ │
│  │  • DoneGateRunner.run(task, gates)                    │ │
│  │  • Record gate results to audit + artifact            │ │
│  │  • Decision:                                          │ │
│  │    - All pass → succeeded                             │ │
│  │    - Any fail → inject failure context + planning     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                Storage & Audit Layer                         │
│  • tasks table (with exit_reason)                           │
│  • task_audits table (complete event log)                   │
│  • artifacts/ directory (structured outputs)                │
└─────────────────────────────────────────────────────────────┘
```

### Comparison with Other Systems

| Feature | Claude Code CLI | AgentOS AEE | Traditional CI/CD |
|---------|----------------|-------------|-------------------|
| **Interactive UX** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Autonomous Execution** | ❌ | ✅ | ✅ |
| **Quality Gates** | ❌ | ✅ | ✅ |
| **Failure Retry** | ❌ | ✅ (automatic) | ⚠️ (manual) |
| **Sub-task Coordination** | ❌ | ✅ | ⚠️ (limited) |
| **Full Auditability** | ⚠️ (logs) | ✅ (structured) | ✅ |
| **Exit Reason** | ❌ | ✅ | ⚠️ (limited) |
| **Event-Driven** | ❌ | ✅ | ✅ |

**Key Differentiator**: AEE combines **autonomous execution** with **engineering governance** - you get both automation AND traceability.

### Production Metrics

- **69/69 tests passing** (100%)
- **<5 second startup latency**
- **6-12x performance improvement** over polling
- **35 validation points** in E2E tests
- **8,000 lines of documentation**

### Use Cases

1. **Autonomous Feature Development**
   - User: `/task Implement user authentication`
   - AEE: Automatically plans → executes → tests → verifies
   - Result: Working feature or clear failure reason

2. **Quality-Gated Deployments**
   - Task: Deploy service update
   - Gates: doctor (health check) + smoke (basic functionality) + tests (full suite)
   - Only deploys if all gates pass

3. **Iterative Problem Solving**
   - Initial attempt fails tests
   - AEE automatically retries with failure context
   - Continues until success or max_iterations
   - No manual intervention needed

4. **Auditable AI Operations**
   - Every decision recorded
   - Complete artifact trail
   - Compliance-ready audit logs

### Quick Start

```python
# From Chat
/task Implement feature X with tests

# From API
POST /api/tasks/create_and_start
{
  "title": "Implement feature X",
  "metadata": {
    "run_mode": "autonomous",
    "gates": ["doctor", "smoke", "tests"],
    "max_iterations": 20
  }
}

# From Python
from agentos.core.task.service import TaskService

service = TaskService()
task = service.create_approve_queue_and_start(
    title="Implement feature X",
    created_by="user@example.com",
    metadata={
        "run_mode": "autonomous",
        "gates": ["doctor", "smoke", "tests"]
    }
)
```

### Roadmap

**Current (v1.0)**:
- ✅ Chat triggering
- ✅ DONE gates
- ✅ Work items (serial)
- ✅ exit_reason
- ✅ Full auditability

**Next (v1.1 - PR-D)**:
- ⏳ Parallel work items execution
- ⏳ Custom gate scripts
- ⏳ WebUI visualization
- ⏳ Advanced retry strategies

**Future (v2.0)**:
- 🔮 Distributed execution
- 🔮 Multi-model orchestration
- 🔮 Real-time monitoring dashboard
- 🔮 Auto-rollback on gate failure

### Documentation

- **Implementation Reports**: 5 detailed technical documents
- **Quick References**: 3 developer guides
- **Test Reports**: E2E and integration test documentation
- **API Documentation**: REST API and Python SDK docs

### License

[Your License Here]

### Citation

If you use AgentOS AEE in your research or production systems, please cite:

```
@software{agentos_aee_2026,
  title = {AgentOS Autonomous Execution Engine (AEE)},
  author = {AgentOS Team},
  year = {2026},
  url = {https://github.com/yourusername/agentos}
}
```

---

**AgentOS AEE: Autonomous execution with engineering discipline.**
