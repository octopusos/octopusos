from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple

from .models import DBEngine, DBInstance, Environment, ProviderStatus, SelectionIntent, SelectionResult


_ENV_KEYWORDS = {
    Environment.PROD: ("prod", "production", "线上", "生产"),
    Environment.STAGING: ("staging", "stage", "预发", "测试环境"),
    Environment.DEV: ("dev", "development", "开发"),
}

_ENGINE_KEYWORDS = {
    DBEngine.MYSQL: ("mysql",),
    DBEngine.POSTGRES: ("postgres", "postgresql", "pg"),
    DBEngine.SQLSERVER: ("sql server", "sqlserver", "mssql"),
    DBEngine.SQLITE: ("sqlite",),
    DBEngine.MONGODB: ("mongodb", "mongo"),
    DBEngine.REDIS: ("redis",),
    DBEngine.DYNAMODB: ("dynamodb",),
}


def parse_intent_from_text(text: str, action_id: str) -> SelectionIntent:
    lower = text.lower()

    env = next(
        (candidate for candidate, words in _ENV_KEYWORDS.items() if any(w in lower for w in words)),
        None,
    )
    engine = next(
        (candidate for candidate, words in _ENGINE_KEYWORDS.items() if any(w in lower for w in words)),
        None,
    )
    keywords = [tok for tok in re.split(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]+", lower) if len(tok) >= 3]

    return SelectionIntent(action_id=action_id, environment=env, engine=engine, target_keywords=keywords)


def _score_instance(intent: SelectionIntent, instance: DBInstance, last_used_id: Optional[str]) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    if intent.environment and instance.environment == intent.environment:
        score += 50
        reasons.append(f"environment={instance.environment.value}")

    if intent.engine and instance.engine == intent.engine:
        score += 40
        reasons.append(f"engine={instance.engine.value}")

    searchable = " ".join([instance.provider_id, instance.instance_id, instance.target, *instance.tags]).lower()
    keyword_hits = sum(1 for kw in intent.target_keywords if kw in searchable)
    if keyword_hits:
        score += keyword_hits * 8
        reasons.append(f"keyword_hits={keyword_hits}")

    if last_used_id and f"{instance.provider_id}/{instance.instance_id}" == last_used_id:
        score += 5
        reasons.append("last_used")

    return score, reasons


def select_instance(
    intent: SelectionIntent,
    instances: Iterable[DBInstance],
    *,
    last_used_id: Optional[str] = None,
) -> SelectionResult:
    all_instances = [
        instance
        for instance in instances
        if not (
            instance.capability_profile
            and instance.capability_profile.status == ProviderStatus.REJECTED
        )
    ]
    ranked: List[Tuple[int, DBInstance, List[str]]] = []

    for instance in all_instances:
        score, reasons = _score_instance(intent, instance, last_used_id)
        ranked.append((score, instance, reasons))

    ranked.sort(key=lambda x: x[0], reverse=True)
    selected = ranked[0][1] if ranked else None

    if not selected:
        return SelectionResult(selected=None, candidates=[], reason="no candidate instances")

    top_reasons = ", ".join(ranked[0][2]) if ranked[0][2] else "default ordering"
    reason = (
        f"selected {selected.provider_id}/{selected.instance_id} because {top_reasons}; "
        f"action={intent.action_id}"
    )
    return SelectionResult(selected=selected, candidates=[item[1] for item in ranked], reason=reason)
