"""WebUI middleware package."""

from octopusos.webui.middleware.audit import AuditMiddleware
from octopusos.webui.middleware.csrf import CSRFProtectionMiddleware

__all__ = ["AuditMiddleware", "CSRFProtectionMiddleware"]
