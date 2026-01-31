# Quick Reference: gate_no_implicit_external_io.py

## Purpose
Enforce explicit external I/O patterns in Chat core - all web search/fetch must go through `/comm` commands.

## Run the Gate
```bash
python3 scripts/gates/gate_no_implicit_external_io.py
```

## What It Checks

### ❌ FORBIDDEN (Will Fail Gate)

```python
# In engine.py or service.py
class ChatEngine:
    def handle_message(self, query):
        # FORBIDDEN: Implicit external I/O
        results = self.comm_adapter.search(query, session_id, task_id)
        return results
```

```python
# In engine.py or service.py
from agentos.core.communication.connectors.web_search import WebSearchConnector

class ChatEngine:
    def __init__(self):
        # FORBIDDEN: Direct connector import
        self.search = WebSearchConnector()
```

```python
# In engine.py or service.py
class ChatEngine:
    async def search(self, query):
        # FORBIDDEN: Direct service.execute()
        result = await self.service.execute("search", {"query": query})
        return result
```

### ✅ ALLOWED (Will Pass Gate)

```python
# In comm_commands.py (command handler)
class CommCommandHandler:
    async def handle_search(self, query, session_id, task_id):
        # ALLOWED: In command handler
        result = await self.comm_adapter.search(query, session_id, task_id)
        return result
```

```python
# In engine.py
class ChatEngine:
    def handle_message(self, query):
        # ALLOWED: Suggest explicit command
        if needs_search(query):
            return "To search the web, use: /comm search <query>"
        return process_message(query)
```

## Critical Files Checked

1. `agentos/core/chat/engine.py` - Chat Engine (orchestration only)
2. `agentos/core/chat/service.py` - Chat Service (persistence only)
3. `agentos/core/chat/context_builder.py` - Context Builder (local context only)
4. `agentos/core/chat/models.py` - Chat Models (data structures only)

## Whitelisted Files (Allowed External I/O)

- `agentos/core/chat/comm_commands.py` - Command handlers (ONLY sanctioned channel)
- `agentos/core/chat/communication_adapter.py` - Adapter initialization
- `agentos/core/chat/slash_command_router.py` - Command routing
- `tests/*` - Test files

## Fix Violations

### Before (WRONG)
```python
# engine.py
class ChatEngine:
    def process(self, user_input):
        if "search" in user_input:
            # Implicit I/O - BAD!
            results = self.comm_adapter.search(user_input, "session1", "task1")
            return format_results(results)
```

### After (CORRECT)
```python
# engine.py
class ChatEngine:
    def process(self, user_input):
        if "search" in user_input:
            # Explicit command suggestion - GOOD!
            return {
                "type": "suggestion",
                "message": "To search the web, use the command:",
                "command": f"/comm search {user_input}"
            }
```

## Exit Codes

- **0**: PASS - No implicit external I/O detected
- **1**: FAIL - Violations found (see detailed report)

## Integration

### In Gate Suite
```bash
bash scripts/gates/run_all_gates.sh
```

### In CI/CD
Add to `.github/workflows/`:
```yaml
- name: Check External I/O
  run: python3 scripts/gates/gate_no_implicit_external_io.py
```

### Pre-commit Hook
```bash
# .git/hooks/pre-commit
python3 scripts/gates/gate_no_implicit_external_io.py || exit 1
```

## Common Scenarios

### Scenario 1: Need to Add Search Feature

**❌ WRONG Approach:**
```python
# engine.py
def handle_user_question(self, question):
    # Don't do this!
    web_results = self.comm_adapter.search(question, session, task)
    return summarize(web_results)
```

**✅ CORRECT Approach:**
```python
# engine.py
def handle_user_question(self, question):
    # Detect need, suggest command
    if requires_external_info(question):
        return ExternalInfoDeclaration(
            reason="Need web search to answer",
            suggested_command=f"/comm search {extract_query(question)}"
        )
    return answer_from_context(question)
```

### Scenario 2: URL Fetch in Response

**❌ WRONG Approach:**
```python
# service.py
async def generate_response(self, message):
    if contains_url(message):
        # Don't do this!
        content = await self.comm_adapter.fetch(extract_url(message), session, task)
        return process_content(content)
```

**✅ CORRECT Approach:**
```python
# service.py
def generate_response(self, message):
    if contains_url(message):
        url = extract_url(message)
        # Suggest explicit command
        return {
            "message": "To fetch this URL, use:",
            "command": f"/comm fetch {url}"
        }
    return process_message(message)
```

### Scenario 3: Background Research

**❌ WRONG Approach:**
```python
# context_builder.py
def build_context(self, query):
    # Don't do this!
    background = self.comm_adapter.search(
        f"background: {query}", session, task
    )
    return merge_context(background, local_context)
```

**✅ CORRECT Approach:**
```python
# context_builder.py
def build_context(self, query):
    # Only use local context
    return build_from_local_sources(query)

# Let user decide if they need external info
# User can type: /comm search background: <topic>
```

## Performance

- **Execution Time**: ~1-2 seconds
- **Files Scanned**: 4 critical files
- **Analysis Method**: AST-based (static analysis)

## Troubleshooting

### Gate Fails on My Code

1. Read the violation report carefully
2. Identify the forbidden pattern
3. Refactor to use `/comm` commands
4. Re-run the gate to verify

### False Positive?

Check if:
1. Your file is a critical file (engine.py, service.py, etc.)
2. You're calling `comm_adapter.search()` or `.fetch()`
3. You're importing web connectors directly

If you believe it's a false positive:
1. Verify your code pattern
2. Check if file should be whitelisted
3. Report issue if gate logic is incorrect

### Need to Bypass (Emergency Only)

```bash
# Local bypass (NOT recommended)
git commit --no-verify

# CI cannot be bypassed - must fix code
```

After emergency bypass:
1. Create issue documenting the bypass
2. Create task to fix properly
3. Notify team

## Architecture Principle

**Explicit over Implicit**: All external information needs must be declared explicitly through user commands, not embedded implicitly in code.

This enables:
- User awareness and control
- Audit trail of all external I/O
- Security and privacy protection
- Clear system boundaries

## Related Documentation

- Full summary: `GATE_NO_IMPLICIT_EXTERNAL_IO_SUMMARY.md`
- ADR: `docs/adr/ADR-EXTERNAL-INFO-DECLARATION-001.md`
- Gate system: `docs/GATE_SYSTEM.md`
- Gate README: `scripts/gates/README.md`

---

**Remember**: If the LLM needs external info, it should **ask the user** to run a `/comm` command, not do it implicitly!
