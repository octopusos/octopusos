# Sprint B · Task #5 - Ollama 启停 API

**Status**: ✅ COMPLETED
**Date**: 2026-01-27
**Sprint**: Sprint B (WebUI 增强)
**Task ID**: W-P1-05

---

## 📋 Task Overview

Implement Ollama lifecycle management (start/stop) with WebUI API integration.

**Scope (Frozen)**:
- ✅ Start/Stop Ollama (local only)
- ✅ Idempotent operations
- ✅ PID tracking via file
- ✅ Event emission on state change
- ✅ WebUI API endpoints

**Out of Scope**:
- ❌ Installation
- ❌ Model downloads
- ❌ Port management
- ❌ Multi-instance support
- ❌ Authentication

---

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                       WebUI API Layer                       │
│  POST /api/providers/ollama/start                          │
│  POST /api/providers/ollama/stop                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────────────────────┐
│                   OllamaController                          │
│  - start() → ControlResult                                  │
│  - stop() → ControlResult                                   │
│  - is_running() → bool                                      │
│  - get_pid() → Optional[int]                                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├─────────> Process Management
                  │           - subprocess.Popen(['ollama', 'serve'])
                  │           - PID tracking via ~/.agentos/ollama.pid
                  │           - SIGTERM → SIGKILL fallback
                  │
                  ├─────────> Health Probe
                  │           - GET http://127.0.0.1:11434/api/tags
                  │           - 1.5s timeout
                  │
                  └─────────> Event Emission
                              - provider.status_changed
                              - EventBus integration
```

### Data Flow

**Start Operation**:
```
1. API Request: POST /api/providers/ollama/start
2. Controller: Check is_running()
   ├─ If READY → return (idempotent)
   └─ If DISCONNECTED → continue
3. Controller: subprocess.Popen(['ollama', 'serve'])
4. Controller: Save PID to ~/.agentos/ollama.pid
5. Controller: Wait 3s (poll 6 times @ 0.5s)
   ├─ Success → state=READY, emit event
   └─ Timeout → state=DEGRADED, emit event
6. API Response: ControlResult JSON
```

**Stop Operation**:
```
1. API Request: POST /api/providers/ollama/stop
2. Controller: Check is_running()
   ├─ If DISCONNECTED → return (idempotent)
   └─ If READY → continue
3. Controller: Get PID from file
   ├─ No PID → ERROR (external process)
   └─ Has PID → continue
4. Controller: Send SIGTERM
5. Controller: Wait 1s
   ├─ Stopped → clean PID file, emit event
   └─ Still running → SIGKILL, emit event
6. API Response: ControlResult JSON
```

---

## 📦 Implementation

### File Tree

```
agentos/
├── providers/
│   └── ollama_controller.py          ← NEW (OllamaController class)
└── webui/
    └── api/
        └── providers_control.py       ← NEW (API endpoints)

tests/
└── webui/
    ├── test_ollama_control_api.py     ← NEW (6 unit tests)
    └── validate_ollama_control.sh     ← NEW (manual validation)
```

### Key Classes

#### 1. OllamaController

**File**: `agentos/providers/ollama_controller.py`

```python
class OllamaController:
    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:11434",
        store_dir: str = None,
    ):
        self.endpoint = endpoint
        self.store_dir = Path(store_dir or Path.home() / ".agentos")
        self.pid_file = self.store_dir / "ollama.pid"
        self.log_file = self.store_dir / "ollama.log"

    def is_running(self) -> bool:
        """Probe endpoint to check if Ollama is running"""

    def get_pid(self) -> Optional[int]:
        """Get PID from tracking file (if valid)"""

    def start(self) -> ControlResult:
        """Start Ollama server (idempotent)"""

    def stop(self) -> ControlResult:
        """Stop Ollama server (idempotent)"""

    def _emit_status_event(self, state: str, pid: Optional[int]):
        """Emit provider.status_changed event"""
```

**Features**:
- ✅ Idempotent start/stop (check state before acting)
- ✅ PID tracking via `~/.agentos/ollama.pid`
- ✅ Process logging to `~/.agentos/ollama.log`
- ✅ Health probe via `GET /api/tags`
- ✅ Event emission on state changes
- ✅ SIGTERM → SIGKILL fallback for stop
- ✅ 3s startup wait (6 polls @ 0.5s)
- ✅ Comprehensive error handling

#### 2. API Endpoints

**File**: `agentos/webui/api/providers_control.py`

```python
@router.post("/api/providers/ollama/start", response_model=ControlResponse)
async def start_ollama():
    controller = OllamaController()
    result = controller.start()
    return ControlResponse(...)

@router.post("/api/providers/ollama/stop", response_model=ControlResponse)
async def stop_ollama():
    controller = OllamaController()
    result = controller.stop()
    return ControlResponse(...)
```

**Response Format**:
```json
{
  "ok": true,
  "provider": "ollama",
  "action": "start",
  "state": "READY",
  "pid": 12345,
  "message": "Ollama started successfully (PID: 12345)",
  "error": null
}
```

**Error Format**:
```json
{
  "ok": false,
  "provider": "ollama",
  "action": "start",
  "state": "DISCONNECTED",
  "pid": null,
  "message": "Ollama CLI not found. Please install Ollama first.",
  "error": {
    "code": "cli_not_found",
    "message": "Ollama CLI not found. Please install Ollama first.",
    "hint": "Install Ollama from https://ollama.com/download"
  }
}
```

---

## ✅ Testing

### Unit Tests (6 Tests)

**File**: `tests/webui/test_ollama_control_api.py`

```bash
pytest tests/webui/test_ollama_control_api.py -v
```

**Coverage**:
1. ✅ `test_start_when_not_running` - Start Ollama successfully
2. ✅ `test_start_when_already_running_idempotent` - Idempotent start
3. ✅ `test_start_when_cli_not_found` - CLI not installed error
4. ✅ `test_stop_when_running` - Stop Ollama successfully
5. ✅ `test_stop_when_already_stopped_idempotent` - Idempotent stop
6. ✅ `test_stop_when_pid_not_tracked` - External process error

**Result**: ✅ 6/6 passed

### Manual Validation

**File**: `tests/webui/validate_ollama_control.sh`

```bash
# Start WebUI server
python3 -m agentos.cli.main webui

# Run validation (in another terminal)
./tests/webui/validate_ollama_control.sh
```

**Test Sequence**:
1. POST /api/providers/ollama/start → ok=true, state=READY
2. POST /api/providers/ollama/start (再次) → ok=true (idempotent)
3. GET /api/providers/status → verify Ollama READY
4. POST /api/providers/ollama/stop → ok=true, state=DISCONNECTED
5. POST /api/providers/ollama/stop (再次) → ok=true (idempotent)
6. GET /api/providers/status → verify Ollama DISCONNECTED

---

## 🎯 Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `curl POST /api/providers/ollama/start` → ok=true + state=READY | ✅ |
| 2 | `curl POST /api/providers/ollama/start` (再次) → ok=true (幂等) | ✅ |
| 3 | `curl POST /api/providers/ollama/stop` → ok=true + state=DISCONNECTED | ✅ |
| 4 | `curl POST /api/providers/ollama/stop` (再次) → ok=true (幂等) | ✅ |
| 5 | WebSocket client 收到 `provider.status_changed` 事件 | ✅ |

---

## 🔧 Technical Details

### PID Tracking

**File**: `~/.agentos/ollama.pid`

```python
def get_pid(self) -> Optional[int]:
    if not self.pid_file.exists():
        return None

    pid = int(self.pid_file.read_text().strip())

    # Verify PID is still valid
    try:
        os.kill(pid, 0)  # Signal 0 doesn't kill, just checks
        return pid
    except OSError:
        # Stale PID file, clean up
        self.pid_file.unlink(missing_ok=True)
        return None
```

**Benefits**:
- ✅ Persistent across CLI invocations
- ✅ Automatic stale PID cleanup
- ✅ No external dependencies

### Process Management

**Start**:
```python
process = subprocess.Popen(
    ["ollama", "serve"],
    stdout=log_handle,
    stderr=subprocess.STDOUT,
    start_new_session=True,  # Detach from parent
)
```

**Stop**:
```python
# Try graceful shutdown first
os.kill(pid, signal.SIGTERM)
time.sleep(1.0)

# Force kill if needed
if still_running:
    os.kill(pid, signal.SIGKILL)
```

### Event Integration

**Emission Points**:
- Start: READY or DEGRADED
- Stop: DISCONNECTED
- Idempotent: Current state

**Example Event**:
```json
{
  "type": "provider.status_changed",
  "source": "core",
  "entity": {
    "kind": "provider",
    "id": "ollama"
  },
  "payload": {
    "state": "READY",
    "details": {
      "endpoint": "http://127.0.0.1:11434",
      "pid": 12345,
      "action": "control"
    }
  },
  "ts": "2026-01-27T15:30:00.000Z"
}
```

---

## 📊 Error Handling

### Error Codes

| Code | Scenario | Recovery |
|------|----------|----------|
| `cli_not_found` | Ollama CLI not installed | Install from ollama.com/download |
| `start_failed` | subprocess.Popen failed | Check logs at ~/.agentos/ollama.log |
| `start_timeout` | Endpoint not ready after 3s | Check logs, verify port 11434 |
| `pid_not_tracked` | Running but PID unknown | Stop Ollama manually |
| `stop_failed` | Kill signal failed | Try manual: `kill -9 <pid>` |

### Example Error Response

```json
{
  "ok": false,
  "provider": "ollama",
  "action": "start",
  "state": "ERROR",
  "pid": null,
  "message": "Failed to start Ollama: subprocess failed",
  "error": {
    "code": "start_failed",
    "message": "Failed to start Ollama: subprocess failed",
    "hint": "Check logs at ~/.agentos/ollama.log"
  }
}
```

---

## 🔍 Debugging

### Check Ollama Status

```bash
# Via API
curl http://localhost:8000/api/providers/status | jq '.providers[] | select(.id=="ollama")'

# Via PID file
cat ~/.agentos/ollama.pid
ps aux | grep ollama

# Via logs
tail -f ~/.agentos/ollama.log
```

### Monitor Events

Open `tests/webui/ws_events_client.html` in browser:
1. Connect to `ws://localhost:8000/ws/events`
2. Trigger start/stop via curl
3. Observe `provider.status_changed` events

---

## 📝 Integration Points

### With Sprint B Task #4 (Event Stream)

**Dependency**: OllamaController uses EventBus from Task #4

```python
from agentos.core.events import Event, get_event_bus

def _emit_status_event(self, state: str, pid: Optional[int]):
    event = Event.provider_status_changed(
        provider_id="ollama",
        state=state,
        details={"endpoint": self.endpoint, "pid": pid}
    )
    get_event_bus().emit(event)
```

**Verification**:
- ✅ Events broadcast to all WebSocket clients
- ✅ No coupling between Core and WebUI
- ✅ Fire-and-forget pattern (no await)

### With Existing Provider System

**No Changes Required**:
- ✅ `agentos/providers/ollama.py` remains unchanged
- ✅ OllamaController is separate lifecycle manager
- ✅ Provider.probe() continues to work independently

**Separation of Concerns**:
- `OllamaProvider`: Health checking (probe)
- `OllamaController`: Lifecycle management (start/stop)

---

## 🚀 Next Steps

### Sprint B Task #6 (Cloud API Key 配置)

**Waiting for**: User to provide "最小安全方案"

**Expected Scope**:
- Cloud provider API key storage
- Secure credential management
- WebUI configuration interface

---

## 📌 Commit Summary

**Files Created**:
- `agentos/providers/ollama_controller.py` (OllamaController)
- `agentos/webui/api/providers_control.py` (API endpoints)
- `tests/webui/test_ollama_control_api.py` (6 unit tests)
- `tests/webui/validate_ollama_control.sh` (manual validation)

**Files Modified**:
- `agentos/webui/app.py` (registered providers_control router)

**Test Results**:
- Unit tests: ✅ 6/6 passed
- Acceptance criteria: ✅ 5/5 met

---

## ✅ Task Closure

**Status**: READY TO COMMIT

Sprint B Task #5 is complete and ready for user approval.

**Deliverables**:
- ✅ OllamaController with start/stop
- ✅ WebUI API endpoints
- ✅ Idempotent operations
- ✅ PID tracking
- ✅ Event integration
- ✅ Unit tests (6/6 passed)
- ✅ Manual validation script
- ✅ Comprehensive documentation

**Dependencies Met**:
- ✅ Sprint B Task #4 (EventBus integration)
- ✅ W-P1-03 (Provider abstraction)

**Ready for**: User verification and git commit
