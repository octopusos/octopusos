# Provider Configuration Guide

Configuration file: `~/.agentos/config/providers.json`

## Structure

```json
{
  "providers": {
    "provider_id": {
      "enabled": true,
      "instances": [
        {
          "id": "instance_id",
          "base_url": "http://...",
          "enabled": true,
          "launch": {  // Optional: for locally-managed services
            "bin": "binary_name",
            "args": {
              "key": "value"
            }
          }
        }
      ]
    }
  }
}
```

## Examples

### Multiple llama.cpp Instances

```json
{
  "providers": {
    "llamacpp": {
      "enabled": true,
      "instances": [
        {
          "id": "glm47flash-q8",
          "base_url": "http://127.0.0.1:11434",
          "enabled": true,
          "launch": {
            "bin": "llama-server",
            "args": {
              "model": "/Users/pangge/.cache/model/GLM-4.7-Flash-UD-Q8_K_XL.gguf",
              "host": "127.0.0.1",
              "port": 11434,
              "ngl": 99,
              "threads": 8,
              "ctx": 8192
            }
          }
        },
        {
          "id": "llama3-8b",
          "base_url": "http://127.0.0.1:8081",
          "enabled": true,
          "launch": {
            "bin": "llama-server",
            "args": {
              "model": "/path/to/llama3-8b.gguf",
              "host": "127.0.0.1",
              "port": 8081,
              "ngl": 99,
              "threads": 4,
              "ctx": 4096
            }
          }
        }
      ]
    }
  }
}
```

### Custom Ollama Endpoint

```json
{
  "providers": {
    "ollama": {
      "enabled": true,
      "instances": [
        {
          "id": "default",
          "base_url": "http://127.0.0.1:11435",
          "enabled": true
        }
      ]
    }
  }
}
```

## Provider Instance IDs

Each provider instance gets a unique ID:
- Single instance with id="default": `ollama`
- Multiple instances: `llamacpp:glm47flash-q8`, `llamacpp:llama3-8b`

## Fingerprint Detection

AgentOS uses protocol fingerprints instead of port numbers to identify services:

- **Ollama**: GET `/api/tags` returns `{"models": [...]}`
- **OpenAI-compatible** (LM Studio, llama.cpp OpenAI mode): GET `/v1/models` returns `{"data": [...]}`
- **llama.cpp native**: GET `/health` or root endpoint with specific markers

This prevents false positives when multiple services run on standard ports.

## Launch Configuration

For locally-managed services (like llama-server), the `launch` config specifies:

### Required Fields
- `bin`: Binary name (e.g., "llama-server", "ollama")
- `args`: Dictionary of command-line arguments

### Common Arguments (llama-server)

| Key | Flag | Description | Example |
|-----|------|-------------|---------|
| `model` | `-m` | Model file path | `/path/to/model.gguf` |
| `host` | `--host` | Bind host | `127.0.0.1` |
| `port` | `--port` | Bind port | `11434` |
| `ngl` | `-ngl` | GPU layers | `99` |
| `threads` | `-t` | CPU threads | `8` |
| `ctx` | `-c` | Context size | `8192` |
| `extra_args` | (appended) | Additional flags | `["-fa", "--mlock"]` |

## API Endpoints

### Start Instance
```bash
POST /api/providers/{provider_id}/instances/start
{
  "instance_id": "glm47flash-q8",
  "launch_config": {...}  // Optional override
}
```

### Stop Instance
```bash
POST /api/providers/{provider_id}/instances/stop
{
  "instance_id": "glm47flash-q8",
  "force": false
}
```

### Check Status
```bash
GET /api/providers/{provider_id}/instances/{instance_id}/status
```

### Get Logs
```bash
GET /api/providers/{provider_id}/instances/{instance_id}/output?lines=100
```

### Install Provider (brew)
```bash
POST /api/providers/{provider_id}/install
```

Supported:
- `ollama`: `brew install ollama`
- `llamacpp`: `brew install llama.cpp`

### Check CLI
```bash
GET /api/providers/{provider_id}/cli-check
```

### Open LM Studio
```bash
POST /api/providers/lmstudio/open-app
```

## Port Conflict Resolution

When starting an instance, AgentOS:
1. Checks if port is available
2. If occupied, runs fingerprint detection
3. Reports which service is using the port

Error response example:
```json
{
  "detail": "Port occupied by ollama (expected llama.cpp)"
}
```

## Status Codes

New reason codes for provider issues:
- `PORT_OCCUPIED_BY_OTHER_PROVIDER`: Port in use by different service
- `FINGERPRINT_MISMATCH`: Service doesn't match expected protocol
- `SERVICE_CONFLICT`: Multiple services detected
- `CLI_NOT_FOUND`: Binary not in PATH
