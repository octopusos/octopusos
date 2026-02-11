"""
Self-check module for OctopusOS

Provides comprehensive system health checks for:
- Runtime (version, paths, permissions)
- Providers (local & cloud)
- Context (memory, RAG, session binding)
- Chat pipeline

Sprint B Task #7 implementation
"""

from octopusos.selfcheck.runner import SelfCheckRunner

__all__ = ["SelfCheckRunner"]
