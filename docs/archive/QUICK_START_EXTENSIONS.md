# Quick Start: AgentOS Extension System

Get up and running with the AgentOS Extension System in 5 minutes.

## Prerequisites

- Python 3.11+
- AgentOS installed
- Terminal/Command Prompt

## Step 1: Initialize Database (30 seconds)

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python3 -c "from agentos.store import init_db; init_db()"
```

Expected output:
```
Database initialized successfully
```

## Step 2: Start Server (10 seconds)

```bash
python3 -m agentos.webui.server
```

Expected output:
```
INFO:     Started server process
INFO:     Uvicorn running on http://localhost:8000
```

**Keep this terminal open!**

## Step 3: Create Sample Extensions (20 seconds)

Open a **new terminal**:

```bash
cd /Users/pangge/PycharmProjects/AgentOS/examples/extensions
python3 create_extensions.py
```

Expected output:
```
============================================================
Extension Package Creator
============================================================

Creating hello extension...
✓ Created: hello-extension.zip
Creating postman extension...
✓ Created: postman-extension.zip

============================================================
✓ Extension packages created successfully!
============================================================
```

## Step 4: Run Acceptance Tests (60 seconds)

```bash
python3 e2e_acceptance_test.py --verbose
```

Expected output:
```
============================================================
Extension System Acceptance Tests
============================================================

Test 1: Server health check
✓ Server is healthy

Test 2: List extensions (initial)
✓ Listed 0 extensions

Test 3: Install extension from hello-extension.zip
✓ Installation request accepted (install_id: inst_abc123)

Test 4: Monitor installation progress
✓ Installation completed (extension_id: demo.hello)

Test 5: Get extension detail
✓ Retrieved extension details for demo.hello

Test 6: Enable extension
✓ Extension demo.hello enabled

Test 7: Disable extension
✓ Extension demo.hello disabled

Test 8: Uninstall extension
✓ Extension demo.hello uninstalled

Test 9: List extensions (final verification)
✓ Extension count matches initial state (uninstall verified)

============================================================
Test Summary
============================================================
Total: 9
Passed: 9
Failed: 0
Success Rate: 100.0%
============================================================

✓ ALL TESTS PASSED!
```

## Step 5: Try It Yourself! (2 minutes)

### Option A: Web Interface

1. Open browser: http://localhost:8000/extensions
2. Click "Install Extension"
3. Select `hello-extension.zip`
4. Watch the progress bar
5. Once installed, go to: http://localhost:8000/chat
6. Type: `/hello`
7. See the response: "Hello, World!"

### Option B: Command Line

```bash
# Install extension
curl -X POST http://localhost:8000/api/extensions/install \
  -F "file=@hello-extension.zip"

# Get install ID from response, then check progress
curl http://localhost:8000/api/extensions/install/{install_id}

# List installed extensions
curl http://localhost:8000/api/extensions | jq

# Enable extension
curl -X POST http://localhost:8000/api/extensions/demo.hello/enable

# Test in chat (this would be done in the UI or via chat API)
```

## Common Commands

### Check Server Health
```bash
curl http://localhost:8000/health
```

### List Extensions
```bash
curl http://localhost:8000/api/extensions | jq
```

### View Extension Details
```bash
curl http://localhost:8000/api/extensions/demo.hello | jq
```

### Enable Extension
```bash
curl -X POST http://localhost:8000/api/extensions/demo.hello/enable | jq
```

### Disable Extension
```bash
curl -X POST http://localhost:8000/api/extensions/demo.hello/disable | jq
```

### Uninstall Extension
```bash
curl -X DELETE http://localhost:8000/api/extensions/demo.hello | jq
```

## Troubleshooting

### "Server not running" Error

**Problem:**
```
✗ Cannot connect to server
```

**Solution:**
```bash
# Check if server is running
ps aux | grep "agentos.webui.server"

# If not, start it
python3 -m agentos.webui.server
```

### "Extension not found" Error

**Problem:**
```
✗ Extension package not found: hello-extension.zip
```

**Solution:**
```bash
# Create the extensions
cd /Users/pangge/PycharmProjects/AgentOS/examples/extensions
python3 create_extensions.py
```

### "Database not initialized" Error

**Problem:**
```
FileNotFoundError: Database not initialized
```

**Solution:**
```bash
# Initialize database
cd /Users/pangge/PycharmProjects/AgentOS
python3 -c "from agentos.store import init_db; init_db()"
```

### Port Already in Use

**Problem:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
python3 -m agentos.webui.server --port 8001
```

## Next Steps

### Learn More
- Read the [User Guide](examples/extensions/README.md)
- Check the [Testing Guide](examples/extensions/TESTING_GUIDE.md)
- Review [System Documentation](EXTENSION_SYSTEM_SUMMARY.md)

### Create Your Own Extension

1. **Create directory structure:**
   ```bash
   mkdir -p my-extension/{install,commands,docs}
   ```

2. **Write manifest.json:**
   ```json
   {
     "id": "my.extension",
     "name": "My Extension",
     "version": "1.0.0",
     "description": "My first extension",
     "capabilities": [
       {
         "type": "slash_command",
         "name": "/mycommand",
         "description": "My custom command"
       }
     ],
     "install": {
       "mode": "agentos_managed",
       "plan": "install/plan.yaml"
     }
   }
   ```

3. **Write install/plan.yaml:**
   ```yaml
   steps:
     - action: detect_platform
       description: "Detect OS"
     - action: write_config
       config_namespace: "my.extension"
       data:
         enabled: true
   ```

4. **Write commands/commands.yaml:**
   ```yaml
   commands:
     - name: /mycommand
       description: My custom command
       entrypoint: commands/handler.sh
   ```

5. **Write commands/handler.sh:**
   ```bash
   #!/bin/bash
   echo "Hello from my extension!"
   ```

6. **Package:**
   ```bash
   cd my-extension
   zip -r ../my-extension.zip .
   ```

7. **Test:**
   ```bash
   cd ..
   python3 e2e_acceptance_test.py --extension my-extension.zip
   ```

### Try Sample Extensions

#### Hello Extension (Minimal)
```bash
# Install
curl -X POST http://localhost:8000/api/extensions/install \
  -F "file=@hello-extension.zip"

# Use in chat
# Go to http://localhost:8000/chat
# Type: /hello AgentOS
```

#### Postman Extension (Advanced)
```bash
# Install
curl -X POST http://localhost:8000/api/extensions/install \
  -F "file=@postman-extension.zip"

# Use in chat
# Go to http://localhost:8000/chat
# Type: /postman list collections
```

## Full Demo Script

Want to see everything in action? Run the full demo:

```bash
cd /Users/pangge/PycharmProjects/AgentOS/examples/extensions
./quick_demo.sh
```

This will:
1. ✅ Check prerequisites
2. ✅ Create extensions
3. ✅ Initialize database
4. ✅ Start server
5. ✅ Run all tests
6. ✅ Show manual testing instructions

## Architecture Overview

```
Extension ZIP (Declarative metadata only)
     ↓
 [Core: Installer]
     ↓
  Validate manifest
     ↓
  Extract to user directory
     ↓
 [Core: Engine]
     ↓
Execute plan steps (Core-controlled)
     ↓
 [Core: Registry]
     ↓
  Register extension
     ↓
  Ready!
```

**Important:** Extensions provide declarations (manifest.json, plan.yaml, commands.yaml). The Core system validates, parses, and executes all operations. No extension code is run.

## Key Concepts

### Extension
A packaged set of **declarative capability definitions** (no executable code). Extensions describe what they provide through structured metadata that Core uses to enable functionality.

### Manifest
The `manifest.json` file describing the extension's metadata and capabilities. This is a pure data file, not executable code.

### Installation Plan
The `install/plan.yaml` file defining how to install the extension. **Core executes these steps**—the extension provides declarations, not code. Default installation to user directory (.agentos/tools), no sudo; manual action required for system-level operations.

### Capability
A feature provided by an extension (slash command, tool, prompt template). These are declared in the manifest, not dynamically generated.

### Slash Command
A command that starts with `/` in the chat interface (e.g., `/hello`). Commands are registered from the extension's commands.yaml, with handlers executed by Core.

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/extensions` | List all extensions |
| GET | `/api/extensions/{id}` | Get extension details |
| POST | `/api/extensions/install` | Upload and install ZIP |
| GET | `/api/extensions/install/{id}` | Get install progress |
| POST | `/api/extensions/{id}/enable` | Enable extension |
| POST | `/api/extensions/{id}/disable` | Disable extension |
| DELETE | `/api/extensions/{id}` | Uninstall extension |
| GET | `/api/extensions/{id}/config` | Get configuration |
| PUT | `/api/extensions/{id}/config` | Update configuration |

## Cheat Sheet

```bash
# One-time setup
python3 -c "from agentos.store import init_db; init_db()"

# Start server
python3 -m agentos.webui.server

# Create sample extensions
cd examples/extensions && python3 create_extensions.py

# Run tests
python3 e2e_acceptance_test.py

# Install extension
curl -X POST http://localhost:8000/api/extensions/install \
  -F "file=@hello-extension.zip"

# List extensions
curl http://localhost:8000/api/extensions | jq

# Enable extension
curl -X POST http://localhost:8000/api/extensions/demo.hello/enable | jq

# Test in chat
# Open: http://localhost:8000/chat
# Type: /hello
```

## Video Tutorial

(Coming soon: https://youtube.com/agentos-extensions-tutorial)

## Community

- **GitHub**: https://github.com/agentos/agentos
- **Discord**: https://discord.gg/agentos
- **Docs**: https://docs.agentos.org/extensions

## Support

Need help? Try these resources:

1. **Documentation**
   - [README](examples/extensions/README.md)
   - [Testing Guide](examples/extensions/TESTING_GUIDE.md)
   - [System Summary](EXTENSION_SYSTEM_SUMMARY.md)

2. **Examples**
   - Look at `hello-extension.zip`
   - Study `postman-extension.zip`
   - Check test files

3. **Logs**
   ```bash
   tail -f logs/agentos.log
   ```

4. **Community**
   - Ask on Discord
   - Open GitHub issue
   - Check discussions

## Success!

You've successfully set up and tested the AgentOS Extension System!

You can now:
- ✅ Install extensions
- ✅ Create your own extensions
- ✅ Use slash commands
- ✅ Manage extension lifecycle

Happy extending! 🎉

---

**Quick Links:**
- [Full Documentation](EXTENSION_SYSTEM_SUMMARY.md)
- [Testing Guide](examples/extensions/TESTING_GUIDE.md)
- [API Reference](examples/extensions/README.md#api-testing-with-curl)
- [Sample Code](examples/extensions/)

**Version:** 1.0.0
**Last Updated:** 2026-01-30
