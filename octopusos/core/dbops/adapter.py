from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .models import DBEngine


@dataclass(slots=True)
class AdapterDispatch:
    action_id: str
    engine: DBEngine
    tool_name: str
    template: str


_ACTION_TOOL_MAP = {
    "db.readonly.inspect": "db_inspect",
    "db.readonly.query_sample": "db_query_sample",
    "db.safe.maintenance.refresh_stats": "db_refresh_stats",
    "db.migration.apply": "db_apply_migration",
    "db.data.mutation.high_risk.delete_with_predicate": "db_delete_with_predicate",
}

_TEMPLATE_BY_ENGINE = {
    DBEngine.MYSQL: "mysql::{tool}",
    DBEngine.POSTGRES: "postgres::{tool}",
    DBEngine.SQLSERVER: "sqlserver::{tool}",
    DBEngine.SQLITE: "sqlite::{tool}",
    DBEngine.MONGODB: "mongodb::{tool}",
    DBEngine.REDIS: "redis::{tool}",
    DBEngine.DYNAMODB: "dynamodb::{tool}",
}


def build_dispatch(action_id: str, engine: DBEngine) -> AdapterDispatch:
    tool_name = _ACTION_TOOL_MAP.get(action_id)
    if not tool_name:
        raise ValueError(f"unsupported action_id: {action_id}")

    template = _TEMPLATE_BY_ENGINE[engine].format(tool=tool_name)
    return AdapterDispatch(action_id=action_id, engine=engine, tool_name=tool_name, template=template)


def supported_actions() -> List[str]:
    return sorted(_ACTION_TOOL_MAP.keys())


def supported_engines() -> List[str]:
    return [engine.value for engine in DBEngine]
