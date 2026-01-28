"""
WebUI Middleware

v0.3.2 Closeout - Security and privacy hardening
"""

from agentos.webui.middleware.sanitize import sanitize_response, mask_sensitive_fields

__all__ = ["sanitize_response", "mask_sensitive_fields"]
