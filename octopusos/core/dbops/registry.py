from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from .models import (
    CapabilityProfile,
    DBEngine,
    DBInstance,
    DBProvider,
    Environment,
    PrivilegeTier,
    ProviderStatus,
)


class DBProviderCatalog:
    """File-backed catalog for DB providers and multi-instance definitions."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.providers: Dict[str, DBProvider] = {}
        if self.path.exists():
            self.load()

    def load(self) -> None:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        providers = payload.get("providers", [])
        self.providers = {}

        for raw_provider in providers:
            instances: List[DBInstance] = []
            for raw_instance in raw_provider.get("instances", []):
                profile = raw_instance.get("capability_profile")
                capability_profile = None
                if profile:
                    capability_profile = CapabilityProfile(
                        privilege_tier=PrivilegeTier(profile["privilege_tier"]),
                        status=ProviderStatus(profile["status"]),
                        reason=profile.get("reason"),
                    )

                instances.append(
                    DBInstance(
                        provider_id=raw_provider["provider_id"],
                        instance_id=raw_instance["instance_id"],
                        engine=DBEngine(raw_instance["engine"]),
                        environment=Environment(raw_instance["environment"]),
                        target=raw_instance["target"],
                        secret_ref=raw_instance["secret_ref"],
                        tags=raw_instance.get("tags", []),
                        capability_profile=capability_profile,
                    )
                )

            self.providers[raw_provider["provider_id"]] = DBProvider(
                provider_id=raw_provider["provider_id"],
                enabled=raw_provider.get("enabled", True),
                instances=instances,
            )

    def save(self) -> None:
        providers_payload = []
        for provider in self.providers.values():
            providers_payload.append(
                {
                    "provider_id": provider.provider_id,
                    "enabled": provider.enabled,
                    "instances": [asdict(instance) for instance in provider.instances],
                }
            )
        self.path.write_text(
            json.dumps({"providers": providers_payload}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def upsert_provider(self, provider: DBProvider) -> None:
        self.providers[provider.provider_id] = provider

    def get_instance(self, provider_id: str, instance_id: str) -> Optional[DBInstance]:
        provider = self.providers.get(provider_id)
        if not provider:
            return None
        for instance in provider.instances:
            if instance.instance_id == instance_id:
                return instance
        return None

    def list_instances(self, include_rejected: bool = False) -> List[DBInstance]:
        items: List[DBInstance] = []
        for provider in self.providers.values():
            if not provider.enabled:
                continue
            for instance in provider.instances:
                if not include_rejected and instance.capability_profile:
                    if instance.capability_profile.status == ProviderStatus.REJECTED:
                        continue
                items.append(instance)
        return items
