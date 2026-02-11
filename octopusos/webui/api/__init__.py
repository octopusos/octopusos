"""WebUI API routers."""

from .frontdesk import router as frontdesk_router
from .agents import router as agents_router
from .dispatch import router as dispatch_router
from .sessions import router as sessions_router
from .external_facts_schema import router as external_facts_schema_router
from .external_facts_providers import router as external_facts_providers_router
from .external_facts_bindings import router as external_facts_bindings_router
from .external_facts_registry import router as external_facts_registry_router
from .connectors import router as connectors_router
from .calls import router as calls_router
from .tasks import router as tasks_router
from .repos import router as repos_router
from .growth import router as growth_router
from .inbox import router as inbox_router
from . import mode_monitoring
from . import knowledge
from . import voice
from . import voice_twilio
from . import providers_errors
from . import providers_models
from . import providers_lifecycle

__all__ = [
    "frontdesk_router",
    "agents_router",
    "dispatch_router",
    "sessions_router",
    "external_facts_schema_router",
    "external_facts_providers_router",
    "external_facts_bindings_router",
    "external_facts_registry_router",
    "connectors_router",
    "calls_router",
    "tasks_router",
    "repos_router",
    "growth_router",
    "inbox_router",
    "mode_monitoring",
    "knowledge",
    "voice",
    "voice_twilio",
    "providers_errors",
    "providers_models",
    "providers_lifecycle",
]
