"""
Authentication Module

Sprint B Task #7: Admin Token Auth (Minimal Security Gate)

This module provides minimal authentication for write operations.
NOT a full multi-user auth system - just a single admin token gate.
"""

from .simple_token import verify_admin_token, require_admin

__all__ = ["verify_admin_token", "require_admin"]
