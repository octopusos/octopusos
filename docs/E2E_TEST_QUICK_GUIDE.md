# End-to-End Memory Integration Test - Quick Guide

## Quick Start

Run the comprehensive E2E acceptance test:

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python3 scripts/e2e_test_memory_integration.py
```

## Expected Output

```
╔═══════════════════════════════════════════════════════════╗
║   AgentOS Memory Integration E2E Acceptance Test           ║
╚═══════════════════════════════════════════════════════════╝

============================================================
SCENARIO A: Preferred Name Memory Flow
============================================================

✅ Step 1: PASS - Session created
✅ Step 2: PASS - Message saved
✅ Step 3: PASS - Extraction triggered, 1 memories extracted
✅ Step 4: PASS - Memory found (confidence: 0.9)
✅ Step 5: PASS - Session created
✅ Step 6: PASS - Memory loaded: 594 tokens
✅ Step 7: PASS - '胖哥' found in prompt (enforcement: True)
✅ Step 8: PASS - Memory Badge API endpoint exists
✅ Step 9: PASS - Message deduplication code present

🎉 OVERALL STATUS: ✅ ACCEPTANCE TEST PASSED
```

## What This Test Validates

### Complete User Journey
1. **User sends preference**: "以后请叫我胖哥"
2. **System extracts memory**: Background processing
3. **Memory persists**: Stored in database
4. **Memory recalls**: Available in new session
5. **AI uses memory**: "胖哥" in response

### Technical Coverage
- ✅ Memory extraction (rule-based patterns)
- ✅ Async processing (non-blocking)
- ✅ Storage (SQLite with JSON)
- ✅ Retrieval (scope-based filtering)
- ✅ Context injection (prompt assembly)
- ✅ Budget management (token allocation)
- ✅ API availability (memory status)
- ✅ UI integration (deduplication)

## Test Scenarios

### Scenario A: Preferred Name Flow
**Input**: "以后请叫我胖哥"
**Expected**:
- Memory extracted with type="preference"
- Memory key="preferred_name", value="胖哥"
- Confidence=0.9 (rule-based)
- Available in next session
- Injected into system prompt with MUST enforcement

## Exit Codes

- **0**: All tests passed ✅
- **1**: One or more tests failed ❌

## Troubleshooting

### Test Fails at Step 3 (Extraction)
**Symptom**: "Extraction triggered, 0 memories extracted"
**Cause**: Pattern matching failed or negative case detected
**Fix**: Check MemoryExtractor rules in `agentos/core/chat/memory_extractor.py`

### Test Fails at Step 4 (Memory Not Found)
**Symptom**: "Memory not found after extraction"
**Cause**: Database write failed or FTS issue
**Fix**:
1. Check database: `sqlite3 ~/.agentos/store.db "SELECT * FROM memory_items ORDER BY created_at DESC LIMIT 5;"`
2. Verify FTS index: `sqlite3 ~/.agentos/store.db "SELECT COUNT(*) FROM memory_fts;"`

### Test Fails at Step 6 (No Memory Loaded)
**Symptom**: "Memory loaded: 0 tokens"
**Cause**: Scope mismatch or confidence too low
**Fix**: Check ContextBuilder memory filtering in `agentos/core/chat/context_builder.py`

### Test Fails at Step 7 (Not in Prompt)
**Symptom**: "'胖哥' not found in prompt"
**Cause**: Memory not injected or formatting issue
**Fix**: Check `_build_system_prompt()` method in ContextBuilder

## Database Inspection

### Check Recent Memories
```bash
sqlite3 ~/.agentos/store.db \
  "SELECT id, type, content FROM memory_items
   WHERE type='preference'
   ORDER BY created_at DESC LIMIT 5;"
```

### Check Memory Count
```bash
sqlite3 ~/.agentos/store.db \
  "SELECT COUNT(*) FROM memory_items WHERE scope='global';"
```

### Check FTS Index
```bash
sqlite3 ~/.agentos/store.db \
  "SELECT COUNT(*) FROM memory_fts;"
```

## Manual Testing

If you want to test manually in the UI:

1. Start WebUI:
   ```bash
   python3 -m agentos.webui.app
   ```

2. Open browser: `http://localhost:5000`

3. Create new chat session

4. Send message: "以后请叫我胖哥"

5. Wait 2 seconds for extraction

6. Check Memory page: Should show preferred_name="胖哥"

7. Create new chat session

8. Send message: "你好"

9. AI should respond using "胖哥" in greeting

## Performance Benchmarks

### Expected Timings
- **Session creation**: < 50ms
- **Message save**: < 50ms
- **Memory extraction**: < 500ms (async)
- **Memory storage**: < 100ms
- **Memory retrieval**: < 50ms
- **Context building**: < 200ms

### Memory Usage
- **Memory item size**: ~200 bytes (JSON)
- **Context overhead**: ~600 tokens per preference
- **Database size**: ~1KB per 5 memories

## Related Documentation

- **Full Test Report**: [TASK11_E2E_ACCEPTANCE_REPORT.md](TASK11_E2E_ACCEPTANCE_REPORT.md)
- **Memory Extractor**: [MEMORY_EXTRACTOR_QUICK_REF.md](MEMORY_EXTRACTOR_QUICK_REF.md)
- **Prompt Injection**: [MEMORY_INJECTION_QUICK_REF.md](MEMORY_INJECTION_QUICK_REF.md)
- **Test Source**: `/Users/pangge/PycharmProjects/AgentOS/scripts/e2e_test_memory_integration.py`

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Run E2E Memory Test
  run: |
    python3 scripts/e2e_test_memory_integration.py
  timeout-minutes: 2
```

## Support

If tests fail unexpectedly:
1. Check database integrity: `sqlite3 ~/.agentos/store.db ".schema"`
2. Review logs: Look for "MemoryExtractor" or "ContextBuilder" in output
3. Run with debug: Set `LOGLEVEL=DEBUG` environment variable
4. Report issue: Include test output and database query results
