from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class SkillExtensionManifest:
    """Minimal SkillOS extension manifest.

    Allowed fields only:
    - extension_id
    - skill_id
    - operations
    - side_effect_tags
    """

    extension_id: str
    skill_id: str
    operations: List[str]
    side_effect_tags: List[str]

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "SkillExtensionManifest":
        if not isinstance(payload, dict):
            raise ValueError("manifest must be an object")
        allowed = {"extension_id", "skill_id", "operations", "side_effect_tags"}
        extra = set(payload.keys()) - allowed
        if extra:
            raise ValueError(f"unexpected fields: {sorted(extra)}")
        missing = [k for k in allowed if k not in payload]
        if missing:
            raise ValueError(f"missing required fields: {missing}")

        extension_id = str(payload.get("extension_id") or "").strip()
        skill_id = str(payload.get("skill_id") or "").strip()
        operations = payload.get("operations")
        side_effect_tags = payload.get("side_effect_tags")

        if not extension_id:
            raise ValueError("extension_id is required")
        if not skill_id:
            raise ValueError("skill_id is required")
        if not isinstance(operations, list) or not all(isinstance(v, str) and v.strip() for v in operations):
            raise ValueError("operations must be a list of non-empty strings")
        if not isinstance(side_effect_tags, list) or not all(isinstance(v, str) and v.strip() for v in side_effect_tags):
            raise ValueError("side_effect_tags must be a list of non-empty strings")

        return SkillExtensionManifest(
            extension_id=extension_id,
            skill_id=skill_id,
            operations=[str(v).strip() for v in operations],
            side_effect_tags=[str(v).strip() for v in side_effect_tags],
        )
