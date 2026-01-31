# Chat Guards - Quick Start Guide

**Status**: Production Ready ✅
**Tests**: 22/22 passing ✅
**Time to Read**: 5 minutes

## TL;DR

Three guards protect Chat ↔ CommunicationOS integration:

1. **Phase Gate** - Blocks external ops in planning phase
2. **Attribution Guard** - Forces proper data attribution
3. **Content Fence** - Marks external content as untrusted

## 30-Second Integration

```python
from agentos.core.chat.guards import (
    PhaseGate, PhaseGateError,
    AttributionGuard, AttributionViolation,
    ContentFence
)

def execute(self, args, session_id, execution_phase):
    # 1. Phase Gate (required)
    try:
        PhaseGate.check("comm.search", execution_phase)
    except PhaseGateError as e:
        return {"error": str(e)}

    # 2. Do work
    results = fetch_external_data(args)

    # 3. Wrap & attribute
    wrapped = ContentFence.wrap(results, source_url)
    attribution = AttributionGuard.format_attribution("search", session_id)

    data = {
        "content": wrapped,
        "metadata": {"attribution": attribution}
    }

    # 4. Validate
    AttributionGuard.enforce(data, session_id)
    return data
```

## What Each Guard Does

### Phase Gate

**Purpose**: No external operations during planning

```python
# BLOCKS this in planning phase:
PhaseGate.check("comm.search", "planning")  # Raises PhaseGateError

# ALLOWS this in execution phase:
PhaseGate.check("comm.search", "execution")  # OK
```

### Attribution Guard

**Purpose**: All external data must say where it came from

```python
# Generate attribution
attribution = AttributionGuard.format_attribution("search", "session_123")
# Result: "CommunicationOS (search) in session session_123"

# Validate data has it
data = {"metadata": {"attribution": attribution}}
AttributionGuard.enforce(data, "session_123")  # OK
```

### Content Fence

**Purpose**: Mark external content as untrusted

```python
# Wrap external content
wrapped = ContentFence.wrap("External data", "https://example.com")

# Result includes:
# - marker: "UNTRUSTED_EXTERNAL_CONTENT"
# - warning: "⚠️ 警告：..."
# - allowed_uses: ["summarization", "citation", "reference"]
# - forbidden_uses: ["execute_instructions", "run_code", "modify_system"]
```

## Testing Your Integration

### Run Tests

```bash
python3 -m pytest tests/test_guards.py -v
```

Expected: 22/22 tests passing

### Run Demo

```bash
python3 examples/guards_demo.py
```

Expected: All demos pass with ✅

### Verify Imports

```bash
python3 -c "from agentos.core.chat.guards import PhaseGate, AttributionGuard, ContentFence; print('✅')"
```

Expected: ✅

## Common Patterns

### Pattern 1: Read-Only Operation

For operations that just read (search, query):

```python
def execute_search(self, query, session_id, execution_phase):
    # Check phase
    PhaseGate.check("comm.search", execution_phase)

    # Search
    results = self.search_service.search(query)

    # Attribute & return
    attribution = AttributionGuard.format_attribution("search", session_id)
    return {
        "results": results,
        "metadata": {"attribution": attribution}
    }
```

### Pattern 2: Fetch External Content

For operations that fetch URLs:

```python
def execute_fetch(self, url, session_id, execution_phase):
    # Check phase
    PhaseGate.check("comm.fetch", execution_phase)

    # Fetch
    content = self.fetcher.fetch(url)

    # Wrap with fence
    wrapped = ContentFence.wrap(content, url)

    # Attribute
    attribution = AttributionGuard.format_attribution("fetch", session_id)
    data = {
        "content": wrapped,
        "metadata": {"attribution": attribution}
    }

    # Validate & return
    AttributionGuard.enforce(data, session_id)
    return data
```

### Pattern 3: LLM Processing

For operations that send to LLM:

```python
def execute_with_llm(self, args, session_id, execution_phase):
    # Get data (using Pattern 1 or 2)
    data = self.execute(args, session_id, execution_phase)

    # Generate LLM prompt with warnings
    wrapped = data["content"]
    llm_prompt = ContentFence.get_llm_prompt_injection(wrapped)

    # Send to LLM
    response = self.llm.generate(llm_prompt)

    return {
        "llm_response": response,
        "raw_data": data
    }
```

## Error Handling

### Phase Gate Error

```python
try:
    PhaseGate.check("comm.search", execution_phase)
except PhaseGateError as e:
    return {
        "error": str(e),
        "blocked_by": "phase_gate",
        "hint": "External operations only allowed in execution phase"
    }
```

### Attribution Error

```python
try:
    AttributionGuard.enforce(data, session_id)
except AttributionViolation as e:
    return {
        "error": str(e),
        "blocked_by": "attribution_guard",
        "hint": "Data must include proper CommunicationOS attribution"
    }
```

## Debugging

### Check if phase is correct

```python
if not PhaseGate.is_allowed("comm.search", execution_phase):
    print(f"❌ Operation blocked in {execution_phase} phase")
else:
    print(f"✅ Operation allowed in {execution_phase} phase")
```

### Check if attribution is valid

```python
attribution = data["metadata"]["attribution"]
if AttributionGuard.validate_attribution_format(attribution):
    print(f"✅ Attribution format valid")
else:
    print(f"❌ Attribution format invalid: {attribution}")
```

### Check if content is wrapped

```python
if ContentFence.is_wrapped(content):
    print(f"✅ Content properly wrapped")
else:
    print(f"❌ Content not wrapped")
```

## FAQ

### Q: Do I need all three guards?

**A**: Yes. Phase Gate is mandatory. Attribution and Content Fence are required for external data.

### Q: What if I forget to add a guard?

**A**: Tests will fail. Each comm command must have guard tests.

### Q: Can I bypass guards in development?

**A**: No. Guards enforce security boundaries. No bypass allowed.

### Q: What's the performance impact?

**A**: ~0.8ms per operation. Negligible.

### Q: Do guards work with async operations?

**A**: Yes. Guards are synchronous and work in any context.

### Q: Can I add custom guards?

**A**: Yes, but these three are mandatory. Add custom guards after.

## Checklist for New Comm Commands

When adding a new `/comm xxx` command:

1. [ ] Import guards at top of file
2. [ ] Call `PhaseGate.check()` in `execute()`
3. [ ] Generate attribution with `format_attribution()`
4. [ ] Wrap external content with `ContentFence.wrap()`
5. [ ] Validate with `AttributionGuard.enforce()`
6. [ ] Add tests for all three guards
7. [ ] Run `pytest tests/test_guards.py`
8. [ ] Run demo to verify
9. [ ] Update command documentation

## Resources

- **Full Documentation**: [ADR-CHAT-COMM-001-Guards.md](../adr/ADR-CHAT-COMM-001-Guards.md)
- **Architecture**: [GUARDS_ARCHITECTURE.md](./GUARDS_ARCHITECTURE.md)
- **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- **Verification**: [VERIFICATION_CHECKLIST.md](./VERIFICATION_CHECKLIST.md)
- **Tests**: [test_guards.py](../../tests/test_guards.py)
- **Demo**: [guards_demo.py](../../examples/guards_demo.py)
- **Usage Guide**: [README.md](../../agentos/core/chat/guards/README.md)

## Support

- **Tests failing?** Check [test_guards.py](../../tests/test_guards.py) for examples
- **Integration issues?** See [GUARDS_ARCHITECTURE.md](./GUARDS_ARCHITECTURE.md)
- **Security questions?** Review [ADR-CHAT-COMM-001-Guards.md](../adr/ADR-CHAT-COMM-001-Guards.md)

---

**Quick Links**:
- [Phase Gate](../../agentos/core/chat/guards/phase_gate.py)
- [Attribution Guard](../../agentos/core/chat/guards/attribution.py)
- [Content Fence](../../agentos/core/chat/guards/content_fence.py)

**Status**: ✅ Production Ready
**Last Updated**: 2026-01-30
