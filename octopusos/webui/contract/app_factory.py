"""Contract/runtime app factory with full router mounting."""

from __future__ import annotations

from fastapi import FastAPI

from octopusos.version import RELEASE_VERSION
from octopusos.webui.contract.router_registry import (
    iter_registered_routers,
    registry_consistency_errors,
)


def create_contract_app(include_contract_only: bool = False) -> FastAPI:
    errors = registry_consistency_errors()
    if errors:
        raise RuntimeError("; ".join(errors))

    app = FastAPI(title="OctopusOS WebUI API", version=RELEASE_VERSION)
    for entry, router in iter_registered_routers(include_contract_only=include_contract_only):
        if entry.include_prefix:
            app.include_router(router, prefix=entry.include_prefix)
        else:
            app.include_router(router)
    return app
