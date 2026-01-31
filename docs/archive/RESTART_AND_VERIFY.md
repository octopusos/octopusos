# Restart WebUI and Verify Fix

## Issue Fixed

Route conflict between `/api/extensions/execute` and `/api/extensions/{extension_id}` has been resolved by reordering router registration in `agentos/webui/app.py`.

## Steps to Verify

### 1. Stop Current WebUI

```bash
pkill -f "uvicorn agentos.webui.app"
```

### 2. Start WebUI

```bash
python -m agentos.webui.app
```

Or with custom port:

```bash
uvicorn agentos.webui.app:app --host 127.0.0.1 --port 9090
```

### 3. Wait for Startup (3-5 seconds)

```bash
# Check if running
ps aux | grep "uvicorn agentos.webui.app" | grep -v grep

# Or check health endpoint
curl http://localhost:9090/api/health
```

### 4. Run Acceptance Tests

```bash
python test_acceptance_webui.py
```

### Expected Output

```
================================================================================
TASK #8: WEBUI API ACCEPTANCE TEST
================================================================================
Testing against: http://localhost:9090

================================================================================
TEST 1: WebUI Health Check
================================================================================
✅ PASSED: WebUI is running
   Status: ok

================================================================================
TEST 2: Extension List API
================================================================================
📊 Found 1 extensions
   - tools.test (Test Extension) - Enabled: True

✅ PASSED: Test extension found
   ID: tools.test
   Name: Test Extension
   Version: 1.0.0
   Enabled: True
   Status: INSTALLED

================================================================================
TEST 3: Execute Extension Command
================================================================================
Executing: /test hello
   Run ID: run_abc123...
   Initial Status: PENDING
   Status: SUCCEEDED (after 0.52s)

📊 Output:
   Hello from Test Extension! 🎉

✅ PASSED: Correct output received
✅ PASSED: Response time < 3s

================================================================================
TEST 4: Execute Status Command
================================================================================
   Run ID: run_def456...

📊 Output (first 500 chars):
System Status Report:

Environment:
- Platform: Darwin 25.2.0
- Architecture: arm64
- Python Version: 3.13.11
- Current Time: 2026-01-30 14:30:00

Execution Context:
- Session ID: acceptance-test-status
- Extension ID: tools.test
- Work Directory: /Users/pangge/PycharmProjects/AgentOS/store/extensions/tools.test

Status: ✅ All systems operational

✅ PASSED: Status command returned expected information

================================================================================
TEST 5: Performance Test (5 executions)
================================================================================
   Run 1: 0.523s
   Run 2: 0.487s
   Run 3: 0.501s
   Run 4: 0.495s
   Run 5: 0.512s

📊 Performance Statistics:
   Average: 0.504s
   Fastest: 0.487s
   Slowest: 0.523s
✅ PASSED: Average response time < 2s

================================================================================
TEST 6: Error Handling
================================================================================
Testing: /nonexist hello
   ✓ Correctly returned error status: 404
✅ PASSED: Error handling works (no crashes)

================================================================================
TEST SUMMARY
================================================================================
✅ PASSED: WebUI Health
✅ PASSED: Extension List API
✅ PASSED: Execute /test hello
✅ PASSED: Execute /test status
✅ PASSED: Performance
✅ PASSED: Error Handling

📊 Overall: 6/6 tests passed (100.0%)

🎉 ALL TESTS PASSED - WebUI API is working correctly!
```

## Manual Verification (Optional)

### Test Execute API

```bash
# Execute /test hello
curl -X POST http://localhost:9090/api/extensions/execute \
  -H "Content-Type: application/json" \
  -d '{"session_id":"manual-test","command":"/test hello","dry_run":false}'

# Expected response:
# {"run_id":"run_abc123def456","status":"PENDING"}
```

### Check Run Status

```bash
# Replace run_xxx with actual run_id from above
curl http://localhost:9090/api/runs/run_xxx

# Expected response:
# {
#   "run_id":"run_abc123def456",
#   "extension_id":"tools.test",
#   "action_id":"hello",
#   "status":"SUCCEEDED",
#   "progress_pct":100,
#   "stdout":"Hello from Test Extension! 🎉",
#   "stderr":"",
#   "error":null,
#   ...
# }
```

### Test in WebUI (Browser)

1. Open http://localhost:9090
2. Navigate to chat interface
3. Type: `/test hello`
4. Expected: "Hello from Test Extension! 🎉"

## Troubleshooting

### WebUI Won't Start

```bash
# Check for port conflicts
lsof -i :9090

# Kill conflicting process
kill -9 <PID>

# Try different port
uvicorn agentos.webui.app:app --port 9091
```

### Tests Fail After Restart

```bash
# Check WebUI is actually running
curl http://localhost:9090/api/health

# Check WebUI logs for errors
tail -f webui.log  # if running in background

# Verify extensions are registered
curl http://localhost:9090/api/extensions | python3 -m json.tool
```

### Execute API Still Returns 405

If the execute API still returns 405 after restart:

1. Verify the fix was applied:
   ```bash
   grep -A 5 "Extensions Execution API" agentos/webui/app.py
   # Should show extensions_execute.router BEFORE extensions.router
   ```

2. Check router order in running server:
   ```bash
   curl http://localhost:9090/openapi.json | grep -A 2 "/api/extensions/execute"
   ```

3. Force reload:
   ```bash
   pkill -9 -f uvicorn
   sleep 2
   python -m agentos.webui.app
   ```

## Success Criteria

✅ All 6 acceptance tests pass
✅ `/test hello` returns greeting message
✅ `/test status` returns system information
✅ Average execution time < 2 seconds
✅ No errors in WebUI logs

## Next Steps After Verification

Once all tests pass:

1. **Commit the fix:**
   ```bash
   git add agentos/webui/app.py
   git commit -m "fix(webui): resolve route conflict for extension execute API

   Moved extensions_execute.router registration before extensions.router
   to prevent /api/extensions/execute from being matched by
   /api/extensions/{extension_id} pattern."
   ```

2. **Review PR-E acceptance report:**
   ```bash
   cat PR_E_FINAL_ACCEPTANCE_REPORT.md
   ```

3. **Prepare for merge:**
   - All tests passing ✅
   - Documentation complete ✅
   - Critical bug fixed ✅
   - Ready for production ✅

4. **Deploy to production** (if approved)

---

**Report Date:** 2026-01-30
**Fix Applied:** Router order correction in app.py
**Verification Required:** WebUI restart + test run
