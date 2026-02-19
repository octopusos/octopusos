from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SkillRiskTier(str, Enum):
    SILENT = "Silent"
    EXPLAIN_CONFIRM = "ExplainConfirm"
    HARD_BLOCK = "HardBlock"


class SkillMode(str, Enum):
    LOCAL_LOCKED = "LocalLocked"
    OPEN = "Open"
    REMOTE_EXPOSED = "RemoteExposed"


@dataclass(frozen=True)
class SkillBudget:
    max_tokens: int = 800
    max_runtime_ms: int = 5000
    max_network_calls: int = 0


@dataclass(frozen=True)
class SkillEnabledConditions:
    mode: SkillMode = SkillMode.LOCAL_LOCKED
    trust_tier: Optional[str] = None
    feature_flags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillApprovalPolicy:
    require_confirmation_for: List[SkillRiskTier] = field(
        default_factory=lambda: [SkillRiskTier.EXPLAIN_CONFIRM, SkillRiskTier.HARD_BLOCK]
    )


@dataclass(frozen=True)
class SkillDispatchTarget:
    dispatch_type: str  # "extension" | "mcp"
    tool_id: str
    extension_id: Optional[str] = None
    action_id: Optional[str] = None
    runner: Optional[str] = None
    mcp_server_id: Optional[str] = None
    mcp_tool_name: Optional[str] = None


@dataclass(frozen=True)
class SkillContract:
    skill_id: str
    name: str
    version: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk_tier: SkillRiskTier
    required_permissions: List[str]
    budget: SkillBudget
    enabled_conditions: SkillEnabledConditions
    audit_tags: List[str]
    approval_policy: SkillApprovalPolicy
    dispatch: SkillDispatchTarget
    origin: Optional[str] = None

    def validate(self) -> None:
        missing = []
        if not self.skill_id:
            missing.append("skill_id")
        if not self.version:
            missing.append("version")
        if not isinstance(self.input_schema, dict):
            missing.append("input_schema")
        if not isinstance(self.output_schema, dict):
            missing.append("output_schema")
        if not self.risk_tier:
            missing.append("risk_tier")
        if self.required_permissions is None:
            missing.append("required_permissions")
        if not self.budget:
            missing.append("budget")
        if not self.enabled_conditions:
            missing.append("enabled_conditions")
        if not self.audit_tags:
            missing.append("audit_tags")
        if not self.approval_policy:
            missing.append("approval_policy")
        if missing:
            raise ValueError(f"SkillContract missing required fields: {', '.join(missing)}")
        if self.dispatch.dispatch_type not in {"extension", "mcp"}:
            raise ValueError(f"Invalid dispatch_type: {self.dispatch.dispatch_type}")
        if self.dispatch.dispatch_type == "extension" and not self.dispatch.extension_id:
            raise ValueError("Extension dispatch requires extension_id")
        if self.dispatch.dispatch_type == "mcp" and not self.dispatch.mcp_server_id:
            raise ValueError("MCP dispatch requires mcp_server_id")
        if self.dispatch.dispatch_type == "mcp" and "network.access" not in self.required_permissions:
            raise ValueError("MCP skills require network.access permission")
