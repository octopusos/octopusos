from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DBEngine(str, Enum):
    MYSQL = "mysql"
    POSTGRES = "postgres"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    REDIS = "redis"
    DYNAMODB = "dynamodb"


class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class ProviderStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    REJECTED = "REJECTED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    CONFIRM = "CONFIRM"
    BLOCK = "BLOCK"


class PrivilegeTier(str, Enum):
    READONLY = "READONLY"
    LIMITED_WRITE = "LIMITED_WRITE"
    DBA = "DBA"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class CapabilityProbe:
    """Runtime probe snapshot returned by MCP/provider health check."""

    can_read_data: bool = True
    can_write_data: bool = False
    can_manage_schema: bool = False
    is_superuser: bool = False
    raw_privileges: List[str] = field(default_factory=list)


@dataclass(slots=True)
class CapabilityProfile:
    privilege_tier: PrivilegeTier
    status: ProviderStatus
    reason: Optional[str] = None


@dataclass(slots=True)
class DBInstance:
    provider_id: str
    instance_id: str
    engine: DBEngine
    environment: Environment
    target: str
    secret_ref: str
    tags: List[str] = field(default_factory=list)
    capability_profile: Optional[CapabilityProfile] = None


@dataclass(slots=True)
class DBProvider:
    provider_id: str
    enabled: bool = True
    instances: List[DBInstance] = field(default_factory=list)


@dataclass(slots=True)
class SelectionIntent:
    action_id: str
    environment: Optional[Environment] = None
    engine: Optional[DBEngine] = None
    target_keywords: List[str] = field(default_factory=list)


@dataclass(slots=True)
class SelectionResult:
    selected: Optional[DBInstance]
    candidates: List[DBInstance]
    reason: str


@dataclass(slots=True)
class OperationRequest:
    action_id: str
    reason: str
    parameters: Dict[str, Any]
    requested_by: str
    dry_run: bool = True


@dataclass(slots=True)
class RiskAssessment:
    risk_level: RiskLevel
    decision: Decision
    reason: str
    requires_confirmation: bool
    estimated_rows: Optional[int] = None
    rollback_possible: Optional[bool] = None


@dataclass(slots=True)
class OperationPlan:
    instance: DBInstance
    request: OperationRequest
    risk: RiskAssessment
    query_shape: str
    why_this_instance: str
