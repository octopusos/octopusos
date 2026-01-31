# CommunicationOS Deployment Guide

**Version**: 1.0
**Last Updated**: 2026-02-01
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Deployment](#deployment)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Security](#security)

---

## Overview

CommunicationOS is a secure, extensible system for managing external communication channels (WhatsApp, Telegram, Slack, etc.) with AgentOS. This guide covers production deployment and configuration.

### Key Features

- **Multi-Channel Support**: WhatsApp, Telegram, Slack, and extensible to new channels
- **Session Management**: Isolated conversation contexts with persistent storage
- **Security Policies**: Network mode control, phase gates, execute blocking
- **Message Deduplication**: Webhook replay protection
- **Audit Trail**: Complete logging of all communications

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CommunicationOS                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   WhatsApp   │  │  Telegram    │  │    Slack     │      │
│  │   Adapter    │  │   Adapter    │  │   Adapter    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│         └──────────────────┼──────────────────┘               │
│                            │                                  │
│                    ┌───────▼────────┐                        │
│                    │  MessageBus    │                        │
│                    │  + Middleware  │                        │
│                    └───────┬────────┘                        │
│                            │                                  │
│         ┌──────────────────┼──────────────────┐              │
│         │                  │                  │              │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐      │
│  │   Session    │  │   Command    │  │  Security    │      │
│  │   Manager    │  │  Processor   │  │   Policy     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS, or Windows Server
- **Python**: 3.11 or higher
- **Database**: SQLite 3.x (included) or PostgreSQL (optional)
- **Memory**: 512 MB minimum, 2 GB recommended
- **Disk Space**: 1 GB minimum, 10 GB recommended

### Software Dependencies

```bash
# Python packages (see requirements.txt)
agentos>=0.1.0
twilio>=8.0.0         # For WhatsApp Twilio adapter
python-telegram-bot>=20.0  # For Telegram adapter
slack-sdk>=3.0.0      # For Slack adapter
pytest>=7.0.0         # For testing
```

### External Services

- **Twilio Account** (for WhatsApp integration)
- **Telegram Bot Token** (for Telegram integration)
- **Slack App Credentials** (for Slack integration)

---

## Installation

### Step 1: Install AgentOS

```bash
# Clone repository
git clone https://github.com/your-org/agentos.git
cd agentos

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install AgentOS
pip install -e .
```

### Step 2: Initialize Database

```bash
# Run database migrations
agentos db migrate

# Verify database schema
agentos db check
```

### Step 3: Verify Installation

```bash
# Run E2E tests
pytest tests/e2e/communicationos/test_e2e.py -v

# Expected output: All tests pass ✅
```

---

## Configuration

### Configuration Files

CommunicationOS uses the following configuration files:

1. **Environment Variables** (`.env`)
2. **Channel Manifests** (`store/channels/*/manifest.json`)
3. **Security Policies** (`config/security_policy.json`)

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=sqlite:///store/agentos.db

# Security
NETWORK_MODE=on  # Options: on, readonly, off
EXECUTION_PHASE=execution  # Options: planning, execution

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+14155238886

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Slack
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_BOT_TOKEN=xoxb-your-bot-token

# Logging
LOG_LEVEL=INFO
AUDIT_LOG_ENABLED=true
```

### Channel Configuration

#### WhatsApp Twilio Adapter

Create `store/channels/whatsapp_twilio/manifest.json`:

```json
{
  "name": "WhatsApp (Twilio)",
  "id": "whatsapp_twilio",
  "version": "1.0.0",
  "adapter_class": "agentos.communicationos.channels.whatsapp_twilio.WhatsAppTwilioAdapter",
  "description": "WhatsApp integration via Twilio",
  "capabilities": ["text", "images", "audio"],
  "webhook_url": "/webhooks/whatsapp/twilio",
  "configuration_schema": {
    "account_sid": {"type": "string", "required": true},
    "auth_token": {"type": "string", "required": true, "secret": true},
    "phone_number": {"type": "string", "required": true}
  },
  "setup_guide": "README.md"
}
```

#### Telegram Adapter (Example)

Create `store/channels/telegram/manifest.json`:

```json
{
  "name": "Telegram",
  "id": "telegram",
  "version": "1.0.0",
  "adapter_class": "agentos.communicationos.channels.telegram.TelegramAdapter",
  "description": "Telegram bot integration",
  "capabilities": ["text", "images", "documents"],
  "webhook_url": "/webhooks/telegram",
  "configuration_schema": {
    "bot_token": {"type": "string", "required": true, "secret": true}
  },
  "setup_guide": "README.md"
}
```

### Security Policy Configuration

Create `config/security_policy.json`:

```json
{
  "network_mode": {
    "default": "on",
    "allowed_modes": ["on", "readonly", "off"],
    "mode_change_requires_approval": true
  },
  "phase_gates": {
    "planning": {
      "comm_commands_allowed": false,
      "external_fetch_allowed": false
    },
    "execution": {
      "comm_commands_allowed": true,
      "external_fetch_allowed": true
    }
  },
  "rate_limits": {
    "max_requests_per_user": 100,
    "time_window_seconds": 60,
    "dedupe_window_seconds": 300
  },
  "blocked_operations": [
    "execute",
    "shell",
    "system"
  ]
}
```

---

## Deployment

### Development Environment

```bash
# Start AgentOS in development mode
agentos serve --host 0.0.0.0 --port 8080 --reload

# Start ngrok for webhook testing (if needed)
ngrok http 8080
```

### Production Environment

#### Option 1: Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  agentos:
    image: agentos:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=sqlite:///data/agentos.db
      - NETWORK_MODE=on
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./config:/app/config
      - ./store:/app/store
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Deploy:

```bash
# Build image
docker build -t agentos:latest .

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

#### Option 2: Systemd Service

Create `/etc/systemd/system/agentos.service`:

```ini
[Unit]
Description=AgentOS CommunicationOS Service
After=network.target

[Service]
Type=simple
User=agentos
Group=agentos
WorkingDirectory=/opt/agentos
Environment="PATH=/opt/agentos/venv/bin"
ExecStart=/opt/agentos/venv/bin/agentos serve --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable agentos

# Start service
sudo systemctl start agentos

# Check status
sudo systemctl status agentos
```

#### Option 3: Kubernetes Deployment

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentos-communicationos
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentos
  template:
    metadata:
      labels:
        app: agentos
    spec:
      containers:
      - name: agentos
        image: agentos:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          value: "sqlite:///data/agentos.db"
        - name: NETWORK_MODE
          value: "on"
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: config
          mountPath: /app/config
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: agentos-data
      - name: config
        configMap:
          name: agentos-config
```

Deploy:

```bash
# Apply configuration
kubectl apply -f k8s/

# Check pods
kubectl get pods -l app=agentos

# Check logs
kubectl logs -l app=agentos -f
```

### Webhook Configuration

#### Twilio Webhook Setup

1. Log in to Twilio Console
2. Navigate to: Messaging → Services → WhatsApp sandbox
3. Set webhook URL: `https://your-domain.com/webhooks/whatsapp/twilio`
4. Save configuration

#### Telegram Webhook Setup

```bash
# Set webhook via API
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your-domain.com/webhooks/telegram"

# Verify webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

---

## Monitoring

### Health Checks

```bash
# Check service health
curl http://localhost:8080/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2026-02-01T12:00:00Z",
  "components": {
    "database": "healthy",
    "network_mode": "on",
    "channels": ["whatsapp_twilio", "telegram"]
  }
}
```

### Metrics and Logging

#### Application Logs

```bash
# View logs (systemd)
sudo journalctl -u agentos -f

# View logs (Docker)
docker-compose logs -f agentos

# View logs (Kubernetes)
kubectl logs -l app=agentos -f
```

#### Key Metrics to Monitor

1. **Message Processing Latency**
   - Target: < 50ms average
   - Alert if: > 100ms P95

2. **Message Throughput**
   - Target: > 50 msg/sec
   - Alert if: < 20 msg/sec

3. **Error Rate**
   - Target: < 1%
   - Alert if: > 5%

4. **Webhook Success Rate**
   - Target: > 99%
   - Alert if: < 95%

5. **Database Performance**
   - Query latency < 10ms
   - Connection pool utilization < 80%

### Prometheus Metrics (Optional)

Add Prometheus exporter:

```python
# In agentos/webui/app.py
from prometheus_client import Counter, Histogram, make_asgi_app

message_counter = Counter('communicationos_messages_total', 'Total messages processed')
message_latency = Histogram('communicationos_message_latency_seconds', 'Message processing latency')

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Webhook Not Receiving Messages

**Symptoms**: Messages sent via WhatsApp/Telegram don't trigger webhook

**Diagnosis**:
```bash
# Check webhook registration
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Check firewall
sudo ufw status

# Check logs
tail -f /var/log/agentos/webhook.log
```

**Solutions**:
- Verify webhook URL is publicly accessible
- Check firewall allows inbound HTTPS (port 443)
- Verify SSL certificate is valid
- Check Twilio/Telegram webhook configuration

#### Issue 2: Message Deduplication Not Working

**Symptoms**: Duplicate messages processed multiple times

**Diagnosis**:
```bash
# Check MessageBus middleware is active
agentos debug middleware-status

# Check rate limiter configuration
agentos config get rate_limits
```

**Solutions**:
- Enable MessageBus middleware in production
- Verify dedupe_window_seconds is set (default: 300)
- Check message_id is properly extracted from webhooks

#### Issue 3: Security Policy Blocking Commands

**Symptoms**: `/comm` commands return "blocked" error

**Diagnosis**:
```bash
# Check network mode
agentos config get network_mode

# Check execution phase
agentos config get execution_phase
```

**Solutions**:
- Verify network_mode is "on" (not "off" or "readonly")
- Verify execution_phase is "execution" (not "planning")
- Review security policy configuration

#### Issue 4: High Latency

**Symptoms**: Message processing takes > 100ms

**Diagnosis**:
```bash
# Run performance benchmark
pytest tests/e2e/communicationos/test_e2e.py::TestPerformance -v

# Check database performance
agentos db analyze

# Check system resources
top
df -h
```

**Solutions**:
- Optimize database queries (add indexes)
- Increase system resources (RAM, CPU)
- Enable database connection pooling
- Consider Redis for session caching

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG
export DEBUG=true

# Restart service
sudo systemctl restart agentos

# View debug logs
tail -f /var/log/agentos/debug.log
```

### Support

For additional support:
- **Documentation**: https://docs.agentos.ai/communicationos
- **Issues**: https://github.com/your-org/agentos/issues
- **Community**: https://community.agentos.ai
- **Email**: support@agentos.ai

---

## Security

### Security Best Practices

1. **Webhook Signature Verification**
   - Always verify Twilio signatures
   - Validate Telegram updates with bot token
   - Reject unsigned requests

2. **Secret Management**
   - Store credentials in environment variables or secret managers
   - Never commit secrets to version control
   - Rotate credentials regularly

3. **Network Security**
   - Use HTTPS for all webhooks
   - Configure firewall to allow only necessary ports
   - Use VPN or private networks for internal communication

4. **Access Control**
   - Implement role-based access control (RBAC)
   - Require authentication for admin endpoints
   - Audit all admin actions

5. **Data Protection**
   - Encrypt sensitive data at rest
   - Use TLS 1.3 for data in transit
   - Implement data retention policies

### Security Checklist

- [ ] Webhook signature verification enabled
- [ ] Secrets stored in environment variables
- [ ] HTTPS enabled with valid certificate
- [ ] Firewall configured properly
- [ ] Network mode set appropriately
- [ ] Execute operations blocked by default
- [ ] Audit logging enabled
- [ ] Regular security updates applied
- [ ] Backup and disaster recovery plan in place

### Compliance

CommunicationOS supports compliance with:
- **GDPR**: Data protection and right to be forgotten
- **HIPAA**: Healthcare data security (with additional configuration)
- **SOC 2**: Security and availability controls
- **ISO 27001**: Information security management

Consult with your compliance team for specific requirements.

---

## Backup and Recovery

### Backup Procedures

```bash
# Backup database
sqlite3 store/agentos.db ".backup store/backups/agentos-$(date +%Y%m%d).db"

# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/ .env

# Backup channel manifests
tar -czf channels-backup-$(date +%Y%m%d).tar.gz store/channels/
```

### Automated Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/agentos"
DATE=$(date +%Y%m%d-%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
sqlite3 /opt/agentos/store/agentos.db ".backup $BACKUP_DIR/agentos-$DATE.db"

# Backup configuration
tar -czf "$BACKUP_DIR/config-$DATE.tar.gz" -C /opt/agentos config/ .env

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Add to cron:

```bash
# Run daily at 2 AM
0 2 * * * /opt/agentos/scripts/backup.sh >> /var/log/agentos/backup.log 2>&1
```

### Recovery Procedures

```bash
# Restore database
cp store/backups/agentos-20260201.db store/agentos.db

# Restore configuration
tar -xzf config-backup-20260201.tar.gz

# Restart service
sudo systemctl restart agentos

# Verify restoration
agentos db check
agentos health
```

---

## Appendix A: Configuration Reference

### Complete Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///store/agentos.db` | Database connection string |
| `NETWORK_MODE` | `on` | Network access mode (on/readonly/off) |
| `EXECUTION_PHASE` | `execution` | Execution phase (planning/execution) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `AUDIT_LOG_ENABLED` | `true` | Enable audit logging |
| `RATE_LIMIT_MAX_REQUESTS` | `100` | Max requests per time window |
| `RATE_LIMIT_TIME_WINDOW` | `60` | Rate limit time window (seconds) |
| `DEDUPE_WINDOW` | `300` | Message deduplication window (seconds) |
| `TWILIO_ACCOUNT_SID` | - | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | - | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | - | Twilio WhatsApp number |
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token |
| `SLACK_APP_TOKEN` | - | Slack app token |
| `SLACK_BOT_TOKEN` | - | Slack bot token |

---

## Appendix B: API Reference

### Webhook Endpoints

#### POST /webhooks/whatsapp/twilio

Receives WhatsApp messages via Twilio.

**Headers**:
- `X-Twilio-Signature`: Twilio signature for verification

**Body** (form-encoded):
```
MessageSid=SM123
From=whatsapp:+1234567890
To=whatsapp:+14155238886
Body=Hello world
NumMedia=0
ProfileName=John Doe
```

**Response**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Message received</Message>
</Response>
```

#### POST /webhooks/telegram

Receives Telegram updates.

**Headers**:
- `Content-Type`: `application/json`

**Body**:
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {"id": 987654321, "first_name": "John"},
    "chat": {"id": 987654321, "type": "private"},
    "text": "Hello bot"
  }
}
```

**Response**:
```json
{
  "status": "ok"
}
```

### Admin API Endpoints

#### GET /api/network-mode

Get current network mode.

**Response**:
```json
{
  "mode": "on",
  "updated_at": "2026-02-01T12:00:00Z",
  "updated_by": "admin"
}
```

#### POST /api/network-mode

Set network mode (requires admin auth).

**Body**:
```json
{
  "mode": "readonly",
  "reason": "Maintenance window"
}
```

**Response**:
```json
{
  "previous_mode": "on",
  "new_mode": "readonly",
  "changed": true,
  "timestamp": "2026-02-01T12:00:00Z"
}
```

---

*End of Deployment Guide*
