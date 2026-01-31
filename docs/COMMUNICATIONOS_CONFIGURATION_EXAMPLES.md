# CommunicationOS Configuration Examples

**Quick Reference for Common Configurations**

---

## Table of Contents

1. [WhatsApp Setup](#whatsapp-setup)
2. [Telegram Setup](#telegram-setup)
3. [Slack Setup](#slack-setup)
4. [Security Policies](#security-policies)
5. [Performance Tuning](#performance-tuning)
6. [Multi-Channel Deployment](#multi-channel-deployment)

---

## WhatsApp Setup

### Basic WhatsApp (Twilio) Configuration

**.env file**:
```bash
# Twilio Account
TWILIO_ACCOUNT_SID=YOUR_TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+14155238886

# Database
DATABASE_URL=sqlite:///store/agentos.db

# Security
NETWORK_MODE=on
EXECUTION_PHASE=execution
```

**Channel Manifest** (`store/channels/whatsapp_twilio/manifest.json`):
```json
{
  "name": "WhatsApp (Twilio)",
  "id": "whatsapp_twilio",
  "version": "1.0.0",
  "adapter_class": "agentos.communicationos.channels.whatsapp_twilio.WhatsAppTwilioAdapter",
  "description": "WhatsApp integration via Twilio",
  "capabilities": ["text", "images", "audio", "video"],
  "webhook_url": "/webhooks/whatsapp/twilio",
  "configuration_schema": {
    "account_sid": {
      "type": "string",
      "required": true,
      "description": "Twilio Account SID"
    },
    "auth_token": {
      "type": "string",
      "required": true,
      "secret": true,
      "description": "Twilio Auth Token"
    },
    "phone_number": {
      "type": "string",
      "required": true,
      "pattern": "^\\+[1-9]\\d{1,14}$",
      "description": "WhatsApp number (E.164 format)"
    }
  },
  "metadata": {
    "author": "AgentOS Team",
    "license": "MIT",
    "homepage": "https://docs.agentos.ai/channels/whatsapp"
  }
}
```

**Twilio Webhook Configuration**:
1. Go to: https://console.twilio.com/
2. Navigate to: Messaging → Services → WhatsApp sandbox
3. Set "When a message comes in": `https://your-domain.com/webhooks/whatsapp/twilio`
4. HTTP Method: `POST`
5. Save configuration

---

## Telegram Setup

### Basic Telegram Bot Configuration

**.env file**:
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhooks/telegram

# Database
DATABASE_URL=sqlite:///store/agentos.db

# Security
NETWORK_MODE=on
```

**Channel Manifest** (`store/channels/telegram/manifest.json`):
```json
{
  "name": "Telegram",
  "id": "telegram",
  "version": "1.0.0",
  "adapter_class": "agentos.communicationos.channels.telegram.TelegramAdapter",
  "description": "Telegram bot integration",
  "capabilities": ["text", "images", "documents", "stickers"],
  "webhook_url": "/webhooks/telegram",
  "configuration_schema": {
    "bot_token": {
      "type": "string",
      "required": true,
      "secret": true,
      "description": "Telegram Bot Token from @BotFather"
    },
    "allowed_users": {
      "type": "array",
      "items": {"type": "integer"},
      "description": "List of allowed Telegram user IDs (optional)"
    }
  }
}
```

**Set Telegram Webhook**:
```bash
# Set webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/webhooks/telegram"}'

# Verify webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

---

## Slack Setup

### Basic Slack App Configuration

**.env file**:
```bash
# Slack App
SLACK_APP_TOKEN=xapp-1-A123B456-7890-C123D456E789F012G345H678
SLACK_BOT_TOKEN=xoxb-YOUR-BOT-TOKEN-HERE
SLACK_SIGNING_SECRET=abc123def456ghi789jkl012mno345pq

# Database
DATABASE_URL=sqlite:///store/agentos.db
```

**Channel Manifest** (`store/channels/slack/manifest.json`):
```json
{
  "name": "Slack",
  "id": "slack",
  "version": "1.0.0",
  "adapter_class": "agentos.communicationos.channels.slack.SlackAdapter",
  "description": "Slack workspace integration",
  "capabilities": ["text", "files", "threads", "reactions"],
  "webhook_url": "/webhooks/slack/events",
  "configuration_schema": {
    "app_token": {
      "type": "string",
      "required": true,
      "secret": true,
      "description": "Slack App Token"
    },
    "bot_token": {
      "type": "string",
      "required": true,
      "secret": true,
      "description": "Slack Bot Token"
    },
    "signing_secret": {
      "type": "string",
      "required": true,
      "secret": true,
      "description": "Slack Signing Secret"
    }
  }
}
```

**Slack App Configuration** (https://api.slack.com/apps):
1. Create new app or select existing
2. OAuth & Permissions → Add scopes:
   - `chat:write`
   - `im:read`
   - `im:history`
3. Event Subscriptions → Enable Events
4. Request URL: `https://your-domain.com/webhooks/slack/events`
5. Subscribe to bot events:
   - `message.im`
   - `app_mention`
6. Install app to workspace

---

## Security Policies

### Strict Security (Production)

**config/security_policy.json**:
```json
{
  "network_mode": {
    "default": "readonly",
    "allowed_modes": ["on", "readonly", "off"],
    "mode_change_requires_approval": true,
    "approval_timeout_seconds": 300
  },
  "phase_gates": {
    "planning": {
      "comm_commands_allowed": false,
      "external_fetch_allowed": false,
      "execute_allowed": false
    },
    "execution": {
      "comm_commands_allowed": true,
      "external_fetch_allowed": true,
      "execute_allowed": false,
      "require_confirmation": true
    }
  },
  "rate_limits": {
    "max_requests_per_user": 50,
    "time_window_seconds": 60,
    "dedupe_window_seconds": 300,
    "burst_allowance": 10
  },
  "blocked_operations": [
    "execute",
    "shell",
    "system",
    "eval",
    "exec",
    "subprocess"
  ],
  "allowed_domains": [
    "*.wikipedia.org",
    "*.github.com",
    "docs.python.org",
    "stackoverflow.com"
  ],
  "blocked_domains": [
    "*.onion",
    "localhost",
    "127.0.0.1",
    "192.168.*",
    "10.*"
  ]
}
```

### Development Environment (Relaxed)

**config/security_policy.json**:
```json
{
  "network_mode": {
    "default": "on",
    "allowed_modes": ["on", "readonly", "off"],
    "mode_change_requires_approval": false
  },
  "phase_gates": {
    "planning": {
      "comm_commands_allowed": false,
      "external_fetch_allowed": false
    },
    "execution": {
      "comm_commands_allowed": true,
      "external_fetch_allowed": true,
      "require_confirmation": false
    }
  },
  "rate_limits": {
    "max_requests_per_user": 1000,
    "time_window_seconds": 60,
    "dedupe_window_seconds": 60
  },
  "blocked_operations": [
    "execute"
  ]
}
```

### Read-Only Mode (Monitoring)

**Set via API or CLI**:
```bash
# Via CLI
agentos network-mode set readonly --reason "Scheduled maintenance"

# Via API
curl -X POST http://localhost:8080/api/network-mode \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{
    "mode": "readonly",
    "reason": "Monitoring mode for incident investigation"
  }'
```

---

## Performance Tuning

### High-Throughput Configuration

**.env file**:
```bash
# Database connection pool
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

# Message processing
MESSAGE_WORKER_THREADS=10
MESSAGE_QUEUE_SIZE=1000
MESSAGE_BATCH_SIZE=50

# Caching
REDIS_URL=redis://localhost:6379/0
SESSION_CACHE_TTL=3600
MESSAGE_CACHE_TTL=300

# Performance
ENABLE_QUERY_CACHE=true
ENABLE_MESSAGE_BATCHING=true
ASYNC_MESSAGE_PROCESSING=true
```

**Performance Tuning Settings** (`config/performance.json`):
```json
{
  "database": {
    "connection_pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "enable_wal_mode": true,
    "synchronous": "NORMAL",
    "journal_mode": "WAL"
  },
  "message_processing": {
    "worker_threads": 10,
    "queue_size": 1000,
    "batch_size": 50,
    "batch_timeout_ms": 100
  },
  "caching": {
    "enable_redis": true,
    "session_ttl": 3600,
    "message_ttl": 300,
    "query_cache_size_mb": 100
  },
  "http": {
    "connection_timeout": 10,
    "read_timeout": 30,
    "max_connections": 100,
    "keepalive": true
  }
}
```

### Low-Resource Configuration (< 512 MB RAM)

**.env file**:
```bash
# Minimal resource usage
DATABASE_POOL_SIZE=2
MESSAGE_WORKER_THREADS=2
MESSAGE_QUEUE_SIZE=100
ENABLE_MESSAGE_BATCHING=false
LOG_LEVEL=WARNING
```

**Low-Resource Settings** (`config/performance.json`):
```json
{
  "database": {
    "connection_pool_size": 2,
    "max_overflow": 1,
    "pool_timeout": 10
  },
  "message_processing": {
    "worker_threads": 2,
    "queue_size": 100,
    "batch_size": 10
  },
  "caching": {
    "enable_redis": false,
    "in_memory_cache_size_mb": 10
  }
}
```

---

## Multi-Channel Deployment

### Example: WhatsApp + Telegram + Slack

**.env file**:
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/agentos

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=AC123...
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+14155238886

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABC...
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhooks/telegram

# Slack
SLACK_APP_TOKEN=xapp-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=abc123...

# Security
NETWORK_MODE=on
EXECUTION_PHASE=execution

# Performance
MESSAGE_WORKER_THREADS=15
DATABASE_POOL_SIZE=30
```

**Multi-Channel Routing** (`config/routing.json`):
```json
{
  "channels": [
    {
      "id": "whatsapp_twilio",
      "enabled": true,
      "priority": 1,
      "rate_limit": {
        "max_requests": 100,
        "window_seconds": 60
      }
    },
    {
      "id": "telegram",
      "enabled": true,
      "priority": 2,
      "rate_limit": {
        "max_requests": 200,
        "window_seconds": 60
      }
    },
    {
      "id": "slack",
      "enabled": true,
      "priority": 3,
      "rate_limit": {
        "max_requests": 100,
        "window_seconds": 60
      }
    }
  ],
  "routing_rules": [
    {
      "condition": "user.role == 'admin'",
      "channels": ["slack"]
    },
    {
      "condition": "user.region == 'US'",
      "channels": ["whatsapp_twilio", "slack"]
    },
    {
      "condition": "default",
      "channels": ["telegram", "whatsapp_twilio"]
    }
  ]
}
```

---

## Load Balancer Configuration

### Nginx Load Balancer

**nginx.conf**:
```nginx
upstream agentos_backend {
    least_conn;
    server 127.0.0.1:8081 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8082 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8083 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Webhook endpoints
    location /webhooks/ {
        proxy_pass http://agentos_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Webhook-specific settings
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
        proxy_buffering off;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://agentos_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
    }

    # Health check
    location /health {
        proxy_pass http://agentos_backend;
        access_log off;
    }
}

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```

---

## Docker Compose Example

**docker-compose.yml** (Multi-Channel):
```yaml
version: '3.8'

services:
  agentos:
    image: agentos:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/agentos
      - REDIS_URL=redis://redis:6379/0
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
      - TWILIO_PHONE_NUMBER=${TWILIO_PHONE_NUMBER}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - NETWORK_MODE=on
      - LOG_LEVEL=INFO
    volumes:
      - ./config:/app/config
      - ./store:/app/store
    depends_on:
      - db
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=agentos
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/letsencrypt:ro
    depends_on:
      - agentos
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

**Start services**:
```bash
# Create .env file with credentials
cat > .env <<EOF
TWILIO_ACCOUNT_SID=AC123...
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+14155238886
TELEGRAM_BOT_TOKEN=123456789:ABC...
SLACK_BOT_TOKEN=xoxb-...
EOF

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f agentos

# Check health
curl http://localhost:8080/health
```

---

## Monitoring Configuration

### Prometheus Metrics

**prometheus.yml**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'agentos'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
```

### Grafana Dashboard

**Import dashboard** (grafana-dashboard.json):
```json
{
  "dashboard": {
    "title": "CommunicationOS Metrics",
    "panels": [
      {
        "title": "Message Throughput",
        "targets": [
          {
            "expr": "rate(communicationos_messages_total[5m])"
          }
        ]
      },
      {
        "title": "Message Processing Latency (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, communicationos_message_latency_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Active Sessions",
        "targets": [
          {
            "expr": "communicationos_active_sessions"
          }
        ]
      }
    ]
  }
}
```

---

## Troubleshooting Commands

### Quick Diagnostic Commands

```bash
# Check service status
systemctl status agentos

# View recent logs
journalctl -u agentos -n 100 --no-pager

# Test webhook endpoint
curl -X POST http://localhost:8080/webhooks/whatsapp/twilio \
  -d "MessageSid=SM123&From=whatsapp:+1234567890&Body=test"

# Check database
sqlite3 store/agentos.db "SELECT COUNT(*) FROM sessions;"

# Check network mode
curl http://localhost:8080/api/network-mode

# Test rate limiter
for i in {1..10}; do
  curl http://localhost:8080/api/test-endpoint
  sleep 0.1
done

# Database vacuum (performance)
sqlite3 store/agentos.db "VACUUM;"

# Check disk space
df -h store/

# Check memory usage
ps aux | grep agentos
```

---

*End of Configuration Examples*
