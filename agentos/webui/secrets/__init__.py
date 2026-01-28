"""
Secrets Management Module

Sprint B Task #6: Cloud API Key Configuration

This module provides secure storage for provider API keys with:
- File-based storage at ~/.agentos/secrets.json
- 0600 permission enforcement
- Key redaction in logs/errors
- Last-4 digits tracking for UI display
"""

from .store import SecretStore, SecretInfo

__all__ = ["SecretStore", "SecretInfo"]
