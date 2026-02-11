from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from .models import CapabilityProbe, CapabilityProfile, PrivilegeTier, ProviderStatus


PROHIBITED_PRIVILEGES: Dict[str, Set[str]] = {
    "mysql": {
        "SUPER",
        "SYSTEM_USER",
        "FILE",
        "SHUTDOWN",
        "RELOAD",
        "GRANT OPTION",
        "ALL PRIVILEGES",
    },
    "postgres": {"SUPERUSER", "CREATEDB", "CREATEROLE", "REPLICATION", "BYPASSRLS"},
    "sqlserver": {"sysadmin", "securityadmin", "serveradmin", "db_owner"},
    "sqlite": {"all"},
    "mongodb": {"root", "dbOwner", "userAdminAnyDatabase"},
    "redis": {"@all", "+@all", "CONFIG", "ACL SETUSER"},
    "dynamodb": {"dynamodb:*", "iam:PassRole"},
}


READONLY_MINIMUMS: Dict[str, List[str]] = {
    "mysql": ["SELECT", "SHOW VIEW"],
    "postgres": ["CONNECT", "USAGE (schema)", "SELECT (tables/views)"],
    "sqlserver": ["CONNECT", "SELECT", "VIEW DEFINITION"],
    "sqlite": ["read-only file mode"],
    "mongodb": ["find", "listCollections"],
    "redis": ["+@read", "-@write", "-@dangerous"],
    "dynamodb": ["GetItem", "Query", "Scan", "DescribeTable"],
}


@dataclass(slots=True)
class QualificationResult:
    profile: CapabilityProfile
    readonly_checklist: List[str]


def qualify_instance(engine: str, probe: CapabilityProbe) -> QualificationResult:
    privileges = {p.strip() for p in probe.raw_privileges if p and p.strip()}
    prohibited = PROHIBITED_PRIVILEGES.get(engine, set())

    if probe.is_superuser or privileges.intersection(prohibited):
        return QualificationResult(
            profile=CapabilityProfile(
                privilege_tier=PrivilegeTier.DBA,
                status=ProviderStatus.REJECTED,
                reason="PRIVILEGE_TOO_HIGH",
            ),
            readonly_checklist=READONLY_MINIMUMS.get(engine, []),
        )

    if probe.can_write_data or probe.can_manage_schema:
        return QualificationResult(
            profile=CapabilityProfile(
                privilege_tier=PrivilegeTier.LIMITED_WRITE,
                status=ProviderStatus.ACTIVE,
                reason="WRITE_CAPABILITY_DETECTED",
            ),
            readonly_checklist=READONLY_MINIMUMS.get(engine, []),
        )

    if probe.can_read_data:
        return QualificationResult(
            profile=CapabilityProfile(
                privilege_tier=PrivilegeTier.READONLY,
                status=ProviderStatus.ACTIVE,
            ),
            readonly_checklist=READONLY_MINIMUMS.get(engine, []),
        )

    return QualificationResult(
        profile=CapabilityProfile(
            privilege_tier=PrivilegeTier.UNKNOWN,
            status=ProviderStatus.REJECTED,
            reason="NO_SUPPORTED_PRIVILEGES",
        ),
        readonly_checklist=READONLY_MINIMUMS.get(engine, []),
    )
