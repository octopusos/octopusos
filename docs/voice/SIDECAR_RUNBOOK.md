# Voice Sidecar Operational Runbook

**Version**: 1.0
**Last Updated**: 2026-02-01
**Owner**: Voice Team

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Starting the Sidecar](#starting-the-sidecar)
4. [Stopping the Sidecar](#stopping-the-sidecar)
5. [Configuration](#configuration)
6. [Health Checks](#health-checks)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Performance Tuning](#performance-tuning)
10. [Emergency Procedures](#emergency-procedures)

---

## Overview

The Voice Worker Sidecar is a Python 3.13 process that handles voice processing (STT/TTS) while the main AgentOS process runs on Python 3.14. It communicates with the main process via gRPC on localhost.

**Architecture**:
- **Main Process**: Python 3.14, manages lifecycle, sends audio, receives events
- **Sidecar Process**: Python 3.13, processes audio, runs faster-whisper
- **Communication**: gRPC over localhost (default port 50051)

---

## Prerequisites

### System Requirements

- Python 3.13 installed and accessible in PATH as `python3.13`
- Minimum 2GB RAM per sidecar instance
- Minimum 1 CPU core per sidecar instance
- Port 50051 available (or configured alternative)

### Python Dependencies (Sidecar)

```bash
pip install grpcio>=1.60.0 protobuf>=4.25.0 faster-whisper>=1.0.0
```

### Python Dependencies (Main Process)

```bash
pip install grpcio>=1.60.0 protobuf>=4.25.0
```

### Verify Installation

```bash
# Check Python 3.13 availability
python3.13 --version
# Expected: Python 3.13.x

# Check faster-whisper installation
python3.13 -c "import faster_whisper; print(faster_whisper.__version__)"
# Expected: Version number (e.g., 1.0.3)

# Check gRPC installation
python3.13 -c "import grpc; print(grpc.__version__)"
# Expected: Version number (e.g., 1.60.1)
```

---

## Starting the Sidecar

### Automatic Start (Recommended)

The main AgentOS process automatically starts the sidecar when needed:

```python
from agentos.core.communication.voice.worker_client import VoiceWorkerClient

client = VoiceWorkerClient(
    python_path="python3.13",
    port=50051,
    auto_start=True,  # Automatically start sidecar
    fallback_to_embedded=True  # Fall back if sidecar fails
)

await client.start()
```

**Logs to Monitor**:
```
[INFO] Voice Worker Sidecar starting on port 50051
[INFO] Sidecar started (PID=12345)
[INFO] Sidecar ready (status=OK)
```

### Manual Start

For debugging or standalone testing:

```bash
# Basic start
python3.13 -m agentos.core.communication.voice.sidecar.main --port 50051

# With debug logging
python3.13 -m agentos.core.communication.voice.sidecar.main \
  --port 50051 \
  --log-level DEBUG
```

**Expected Output**:
```
============================================================
Voice Worker Sidecar
============================================================
Python version: 3.13.0
gRPC port: 50051
Log level: INFO
============================================================
2026-02-01 10:00:00 [INFO] VoiceWorkerServicer initialized: worker-12345
2026-02-01 10:00:00 [INFO] Voice Worker gRPC server started on port 50051
```

### Start with Environment Variables

```bash
# Set port via environment variable
export VOICE_SIDECAR_PORT=50052
export VOICE_SIDECAR_LOG_LEVEL=DEBUG

python3.13 -m agentos.core.communication.voice.sidecar.main
```

---

## Stopping the Sidecar

### Graceful Shutdown (Recommended)

The main process automatically stops the sidecar:

```python
await client.stop()
```

**Shutdown Process**:
1. Main process sends SIGTERM to sidecar
2. Sidecar flushes pending audio buffers
3. Sidecar closes active sessions
4. Sidecar shuts down gRPC server
5. Process exits (within 5 seconds)

**Logs to Monitor**:
```
[INFO] Received signal SIGTERM, shutting down gracefully...
[INFO] Stopped session: session-123 (reason=shutdown, flushed=2048 bytes)
[INFO] Voice Worker gRPC server stopped
```

### Manual Stop

If sidecar was started manually:

```bash
# Send SIGTERM (graceful)
kill -TERM <PID>

# Send SIGINT (graceful)
kill -INT <PID>

# Force kill (not recommended)
kill -9 <PID>
```

### Emergency Stop

If sidecar is unresponsive:

```bash
# Find PID
ps aux | grep "voice.sidecar.main"

# Force kill
kill -9 <PID>
```

---

## Configuration

### Environment Variables

| Variable                  | Default | Description                          |
|---------------------------|---------|--------------------------------------|
| `VOICE_SIDECAR_PORT`      | 50051   | gRPC server port                     |
| `VOICE_SIDECAR_LOG_LEVEL` | INFO    | Logging level (DEBUG/INFO/WARNING/ERROR) |

### Command-Line Arguments

```bash
python3.13 -m agentos.core.communication.voice.sidecar.main --help
```

**Options**:
- `--port`: gRPC server port (default: 50051)
- `--log-level`: Logging level (default: INFO)

### Resource Limits (Hardcoded)

| Limit                    | Value    | Rationale                          |
|--------------------------|----------|------------------------------------|
| Max Buffer per Session   | 10MB     | Prevents memory exhaustion         |
| Max Concurrent Sessions  | 10       | Prevents resource overload         |
| Health Check Interval    | 10s      | Early failure detection            |
| Graceful Shutdown Timeout| 5s       | Balance between clean stop and hang|

**Note**: These limits are hardcoded in `worker_service.py`. To change them, modify:
- `VoiceWorkerServicer.MAX_BUFFER_BYTES`
- `VoiceWorkerServicer.MAX_CONCURRENT_SESSIONS`

---

## Health Checks

### Manual Health Check

Using `grpcurl` (install: `go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest`):

```bash
grpcurl -plaintext \
  -import-path agentos/core/communication/voice/sidecar \
  -proto voice_worker.proto \
  localhost:50051 \
  agentos.voice.VoiceWorker/HealthCheck
```

**Expected Response (Healthy)**:
```json
{
  "status": "OK",
  "active_sessions": 2,
  "memory_usage_bytes": 4096000,
  "uptime_seconds": 120,
  "metrics": {
    "worker_id": "worker-12345",
    "max_sessions": "10"
  }
}
```

**Expected Response (Degraded)**:
```json
{
  "status": "DEGRADED",
  "active_sessions": 10,
  "memory_usage_bytes": 100000000,
  "uptime_seconds": 3600,
  "metrics": {
    "worker_id": "worker-12345",
    "max_sessions": "10"
  }
}
```

### Automated Health Check (from Main Process)

```python
# Health check runs automatically every 10 seconds
if client.is_healthy:
    print("Sidecar is healthy")
else:
    print("Sidecar is unhealthy - check logs")
```

### Health Status Codes

| Status     | Meaning                                      | Action                          |
|------------|----------------------------------------------|---------------------------------|
| `OK`       | Sidecar operating normally                   | None                            |
| `DEGRADED` | At capacity (10 sessions) but functional     | Consider scaling horizontally   |
| `UNHEALTHY`| Error detected or unresponsive               | Restart sidecar, check logs     |

---

## Monitoring

### Key Metrics to Monitor

| Metric                 | Source                     | Alert Threshold           |
|------------------------|----------------------------|---------------------------|
| Active Sessions        | Health check response      | ≥ 10 (at capacity)        |
| Memory Usage           | Health check response      | > 500MB (per sidecar)     |
| Uptime                 | Health check response      | < 60s (recent restart)    |
| Health Check Failures  | Main process logs          | ≥ 3 consecutive failures  |
| gRPC Error Rate        | Main process logs          | > 5% of requests          |
| Roundtrip Latency      | Application metrics        | > 100ms (p99)             |

### Log Locations

**Main Process Logs**:
```
# Check main process logs for sidecar lifecycle events
grep "VoiceWorkerClient" /var/log/agentos/main.log

# Check for health check failures
grep "Health check failed" /var/log/agentos/main.log
```

**Sidecar Logs** (if redirected to file):
```bash
# Redirect sidecar output to file
python3.13 -m agentos.core.communication.voice.sidecar.main \
  > /var/log/agentos/sidecar.log 2>&1
```

**Log Patterns to Monitor**:

✅ **Healthy**:
```
[INFO] Created session: abc-123 (project=test, stt=whisper_local)
[INFO] Stopped session: abc-123 (reason=user_requested, flushed=0 bytes)
```

⚠️ **Warning**:
```
[WARNING] Max concurrent sessions reached: 10
[WARNING] Buffer limit exceeded for session: abc-123
```

❌ **Error**:
```
[ERROR] Failed to load Whisper: No module named 'faster_whisper'
[ERROR] Error in ProcessAudio: Session not found
```

### Prometheus Metrics (Future Work)

The following metrics are planned for future implementation:

```
# HELP voice_sidecar_sessions_active Number of active voice sessions
# TYPE voice_sidecar_sessions_active gauge
voice_sidecar_sessions_active{worker_id="worker-12345"} 3

# HELP voice_sidecar_memory_bytes Memory usage in bytes
# TYPE voice_sidecar_memory_bytes gauge
voice_sidecar_memory_bytes{worker_id="worker-12345"} 8388608

# HELP voice_sidecar_uptime_seconds Uptime in seconds
# TYPE voice_sidecar_uptime_seconds counter
voice_sidecar_uptime_seconds{worker_id="worker-12345"} 3600
```

---

## Troubleshooting

### Problem: Sidecar Fails to Start

**Symptoms**:
```
[ERROR] Failed to find Python 3.13: [Errno 2] No such file or directory: 'python3.13'
```

**Solutions**:
1. Verify Python 3.13 installation:
   ```bash
   python3.13 --version
   ```
2. Check PATH includes Python 3.13:
   ```bash
   which python3.13
   ```
3. Specify full path:
   ```python
   client = VoiceWorkerClient(python_path="/usr/local/bin/python3.13")
   ```

---

### Problem: Port Already in Use

**Symptoms**:
```
[ERROR] Failed to bind to port 50051: Address already in use
```

**Solutions**:
1. Check what's using the port:
   ```bash
   lsof -i :50051
   ```
2. Kill the conflicting process:
   ```bash
   kill -9 <PID>
   ```
3. Use a different port:
   ```python
   client = VoiceWorkerClient(port=50052)
   ```

---

### Problem: Health Check Failures

**Symptoms**:
```
[ERROR] Health check failed: StatusCode.UNAVAILABLE
```

**Solutions**:
1. Check if sidecar is running:
   ```bash
   ps aux | grep "voice.sidecar.main"
   ```
2. Check port connectivity:
   ```bash
   nc -zv localhost 50051
   ```
3. Check sidecar logs for errors
4. Restart sidecar

---

### Problem: High Memory Usage

**Symptoms**:
```
[WARNING] Memory usage: 900MB (active sessions: 8)
```

**Solutions**:
1. Check for stuck sessions:
   ```bash
   grpcurl -plaintext localhost:50051 agentos.voice.VoiceWorker/HealthCheck
   ```
2. Stop old sessions:
   ```python
   await client.stop_session(session_id, force=True)
   ```
3. Restart sidecar to reclaim memory
4. Reduce concurrent session limit (requires code change)

---

### Problem: Slow STT Processing

**Symptoms**:
- STT results take > 5 seconds to return
- High CPU usage on sidecar process

**Solutions**:
1. Check CPU usage:
   ```bash
   top -p <sidecar-pid>
   ```
2. Reduce concurrent sessions
3. Use smaller Whisper model (future work: configurable model size)
4. Add more CPU cores
5. Scale horizontally (run multiple sidecars)

---

### Problem: Session Not Found Errors

**Symptoms**:
```
[ERROR] ProcessAudio: Session not found: abc-123
```

**Solutions**:
1. Ensure `CreateSession` was called before `ProcessAudio`
2. Check session ID matches between calls
3. Verify session wasn't stopped prematurely
4. Check for sidecar restart (sessions lost on restart)

---

### Problem: Buffer Limit Exceeded

**Symptoms**:
```
[ERROR] Buffer limit exceeded for session: abc-123
```

**Solutions**:
1. Client is sending too much audio without waiting for processing
2. Check client-side throttling logic
3. Increase buffer limit (requires code change to `MAX_BUFFER_BYTES`)
4. Process audio in smaller chunks

---

## Performance Tuning

### Latency Optimization

**Target**: < 50ms roundtrip latency

**Tuning Steps**:
1. **Reduce audio chunk size**: Smaller chunks = lower latency but higher overhead
   ```python
   # Instead of 1 second chunks
   chunk_size = 0.5 * sample_rate * 2  # 0.5 seconds
   ```
2. **Use localhost**: Never use remote sidecar for latency-critical workloads
3. **Pin to CPU cores**: Reduce context switching
   ```bash
   taskset -c 0-3 python3.13 -m agentos.core.communication.voice.sidecar.main
   ```

### Throughput Optimization

**Target**: > 100 messages/second

**Tuning Steps**:
1. **Batch audio chunks**: Send multiple chunks per gRPC call
2. **Increase concurrent sessions**: Scale to 10 concurrent (max supported)
3. **Scale horizontally**: Run multiple sidecars on different ports

### Memory Optimization

**Target**: < 10MB per session

**Tuning Steps**:
1. **Flush buffers aggressively**: Process audio as soon as threshold is reached
2. **Reduce buffer limits**: Lower `MAX_BUFFER_BYTES` (requires code change)
3. **Monitor for leaks**: Check memory usage over time
   ```bash
   watch -n 5 'ps aux | grep voice.sidecar.main'
   ```

---

## Emergency Procedures

### Procedure: Sidecar Crash Loop

**Detection**:
- Sidecar repeatedly crashes and restarts
- Logs show continuous startup/shutdown

**Steps**:
1. **Stop auto-restart**: Disable `auto_start` in client configuration
2. **Check logs**: Identify crash cause
3. **Fix root cause**: Install missing dependencies, fix configuration
4. **Test manually**: Start sidecar manually to verify fix
5. **Re-enable auto-restart**: Once stable

---

### Procedure: Memory Leak

**Detection**:
- Memory usage continuously increases
- No corresponding increase in active sessions

**Steps**:
1. **Capture heap dump** (requires `memory_profiler`):
   ```bash
   python3.13 -m memory_profiler -m agentos.core.communication.voice.sidecar.main
   ```
2. **Stop all sessions**: Force-stop all active sessions
3. **Restart sidecar**: Reclaim memory
4. **Report bug**: File issue with heap dump

---

### Procedure: Sidecar Hang

**Detection**:
- Health checks timeout
- Sidecar process exists but doesn't respond

**Steps**:
1. **Capture stack trace**:
   ```bash
   kill -SIGUSR1 <sidecar-pid>  # If signal handler added
   # Or use py-spy:
   py-spy dump --pid <sidecar-pid>
   ```
2. **Force kill**:
   ```bash
   kill -9 <sidecar-pid>
   ```
3. **Restart sidecar**
4. **Report bug**: File issue with stack trace

---

### Procedure: Port Conflict

**Detection**:
- Sidecar fails to start with "Address already in use"

**Steps**:
1. **Identify conflicting process**:
   ```bash
   lsof -i :50051
   ```
2. **Kill or migrate**: Either kill conflict or use different port
3. **Update configuration**: If using different port, update client config
4. **Restart sidecar**

---

## Appendix

### Useful Commands

```bash
# Check if sidecar is running
pgrep -f "voice.sidecar.main"

# View sidecar resource usage
ps aux | grep voice.sidecar.main

# Send test audio to sidecar (requires grpcurl)
echo "test audio data" | grpcurl -plaintext -d @ localhost:50051 \
  agentos.voice.VoiceWorker/ProcessAudio

# List all gRPC methods
grpcurl -plaintext localhost:50051 list

# Get service description
grpcurl -plaintext localhost:50051 describe agentos.voice.VoiceWorker
```

### Debugging with grpcurl

Install grpcurl:
```bash
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
```

Create a session:
```bash
grpcurl -plaintext -d '{
  "session_id": "debug-session",
  "project_id": "debug-project",
  "stt_provider": "whisper_local"
}' localhost:50051 agentos.voice.VoiceWorker/CreateSession
```

Stop a session:
```bash
grpcurl -plaintext -d '{
  "session_id": "debug-session",
  "reason": "manual_debug",
  "force": false
}' localhost:50051 agentos.voice.VoiceWorker/StopSession
```

---

## Contact

**Owner**: Voice Team
**Slack**: #voice-support
**On-Call**: voice-oncall@example.com

---

## Changelog

| Date       | Version | Changes                              |
|------------|---------|--------------------------------------|
| 2026-02-01 | 1.0     | Initial version                      |
