"""Idempotency and caching system for OctopusOS.

This module provides:
- IdempotencyStore: Manages idempotency keys for request deduplication
- LLMOutputCache: Caches and reuses LLM outputs to save tokens
- ToolLedger: Records and replays tool executions

Design Goals:
1. Reduce token consumption through LLM output caching
2. Avoid redundant tool executions through replay mechanism
3. Enable safe retries with idempotency guarantees
4. Track cache hit rates for optimization

Example:
    from octopusos.core.idempotency import IdempotencyStore, LLMOutputCache, ToolLedger

    # Check idempotency before expensive operation
    store = IdempotencyStore()
    if result := store.check(key):
        return result

    # Cache LLM outputs
    cache = LLMOutputCache()
    output = cache.get_or_generate(prompt, model, lambda: call_llm(prompt))

    # Record tool execution
    ledger = ToolLedger()
    result = ledger.execute_or_replay(tool, command, lambda: run_tool(command))
"""

from octopusos.core.idempotency.store import IdempotencyStore
from octopusos.core.idempotency.llm_cache import LLMOutputCache
from octopusos.core.idempotency.tool_ledger import ToolLedger

__all__ = [
    "IdempotencyStore",
    "LLMOutputCache",
    "ToolLedger",
]
