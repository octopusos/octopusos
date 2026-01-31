# Voice Sidecar Quick Reference

**Version**: 1.0
**Last Updated**: 2026-02-01

---

## 🚀 Quick Start

### Start Sidecar (Auto)

```python
from agentos.core.communication.voice.worker_client import VoiceWorkerClient

client = VoiceWorkerClient(auto_start=True)
await client.start()
```

### Start Sidecar (Manual)

```bash
python3.13 -m agentos.core.communication.voice.sidecar.main --port 50051
```

---

## 📊 Health Check

### Via grpcurl

```bash
grpcurl -plaintext localhost:50051 agentos.voice.VoiceWorker/HealthCheck
```

### Via Python

```python
if client.is_healthy:
    print("✅ Healthy")
else:
    print("❌ Unhealthy")
```

---

## 🔧 Configuration

| Variable                  | Default | Description              |
|---------------------------|---------|--------------------------|
| `VOICE_SIDECAR_PORT`      | 50051   | gRPC server port         |
| `VOICE_SIDECAR_LOG_LEVEL` | INFO    | Logging level            |

---

## 📈 Key Metrics

| Metric            | Alert Threshold       |
|-------------------|-----------------------|
| Active Sessions   | ≥ 10 (at capacity)    |
| Memory Usage      | > 500MB               |
| Health Check Fail | ≥ 3 consecutive       |
| Latency (p99)     | > 100ms               |

---

## 🧪 Test Commands

```bash
# Run all tests
pytest tests/unit/communication/voice/test_grpc_session_creation.py \
       tests/unit/communication/voice/test_audio_streaming.py \
       tests/unit/communication/voice/test_health_check.py \
       tests/unit/communication/voice/test_fallback_logic.py \
       tests/integration/voice/test_sidecar_lifecycle.py \
       tests/integration/voice/test_main_to_sidecar_roundtrip.py

# Run with coverage
pytest ... --cov=agentos.core.communication.voice.sidecar

# Run single test file
pytest tests/unit/communication/voice/test_grpc_session_creation.py -v
```

---

## 🐛 Common Issues

### Port Already in Use

```bash
# Find process
lsof -i :50051

# Kill it
kill -9 <PID>
```

### Python 3.13 Not Found

```bash
# Check if installed
python3.13 --version

# Specify full path
VoiceWorkerClient(python_path="/usr/local/bin/python3.13")
```

### Health Check Fails

```bash
# Check if running
ps aux | grep voice.sidecar.main

# Restart
await client.stop()
await client.start()
```

---

## 🛑 Emergency Stop

```bash
# Find PID
pgrep -f "voice.sidecar.main"

# Force kill
kill -9 <PID>
```

---

## 📚 Documentation Links

- **ADR**: `/docs/adr/ADR-015-voice-sidecar-grpc.md`
- **Runbook**: `/docs/voice/SIDECAR_RUNBOOK.md`
- **Tests**: `/tests/unit/communication/voice/test_*`

---

## 🎯 Resource Limits

| Limit                   | Value |
|-------------------------|-------|
| Max Buffer per Session  | 10MB  |
| Max Concurrent Sessions | 10    |
| Health Check Interval   | 10s   |
| Graceful Shutdown       | 5s    |

---

## 📦 Test Coverage

| Test File                         | Tests | Coverage                    |
|-----------------------------------|-------|-----------------------------|
| test_grpc_session_creation.py     | 9     | Session creation & limits   |
| test_audio_streaming.py           | 11    | Audio processing & buffers  |
| test_health_check.py              | 12    | Health monitoring           |
| test_fallback_logic.py            | 12    | Error recovery              |
| test_sidecar_lifecycle.py         | 11    | Process management          |
| test_main_to_sidecar_roundtrip.py | 9     | End-to-end flows            |
| **TOTAL**                         | **64**| **Full functionality**      |

---

## 🔑 Status Codes

| Status      | Meaning                   | Action                    |
|-------------|---------------------------|---------------------------|
| `OK`        | Operating normally        | None                      |
| `DEGRADED`  | At capacity (10 sessions) | Consider scaling          |
| `UNHEALTHY` | Error or unresponsive     | Restart sidecar           |

---

## 📞 Support

- **Owner**: Voice Team
- **Slack**: #voice-support
- **On-Call**: voice-oncall@example.com
