"""Git module - Git operations and credential management"""

from octopusos.core.git.credentials import (
    AuthProfile,
    AuthProfileType,
    TokenProvider,
    ValidationStatus,
    CredentialsManager,
)
from octopusos.core.git.client import GitClientWithAuth, ProbeResult
from octopusos.core.git.ignore import GitignoreManager
from octopusos.core.git.guard_rails import (
    ChangeGuardRails,
    Violation,
    ValidationResult,
    create_default_guard_rails,
    create_strict_guard_rails,
)

__all__ = [
    "AuthProfile",
    "AuthProfileType",
    "TokenProvider",
    "ValidationStatus",
    "CredentialsManager",
    "GitClientWithAuth",
    "ProbeResult",
    "GitignoreManager",
    "ChangeGuardRails",
    "Violation",
    "ValidationResult",
    "create_default_guard_rails",
    "create_strict_guard_rails",
]
