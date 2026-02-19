from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from octopusos.core.mcp.config import MCPConfigManager
from octopusos.core.mcp.client import MCPClient

from ..contracts.models import (
    SkillApprovalPolicy,
    SkillBudget,
    SkillContract,
    SkillDispatchTarget,
    SkillEnabledConditions,
    SkillMode,
    SkillRiskTier,
)

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Registry for SkillContracts (SoT)."""

    def __init__(self, *, load_mcp: bool = True) -> None:
        self._skills: Dict[str, SkillContract] = {}
        self._load_builtin()
        if load_mcp:
            try:
                self.refresh_mcp_tools()
            except Exception as exc:
                logger.warning("Failed to refresh MCP tools", extra={"error": str(exc)})
        try:
            self.export_snapshot(Path("reports") / "skill_registry_snapshot.json")
        except Exception:
            pass

    def _load_builtin(self) -> None:
        # Seed with minimal built-in contracts (example).
        builtin = SkillContract(
            skill_id="skill.shell.run",
            name="Shell Run",
            version="1.0.0",
            input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
            output_schema={"type": "object"},
            risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
            required_permissions=["system.exec"],
            budget=SkillBudget(max_tokens=200, max_runtime_ms=10000, max_network_calls=0),
            enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
            audit_tags=["side_effect:system.exec"],
            approval_policy=SkillApprovalPolicy(),
            dispatch=SkillDispatchTarget(
                dispatch_type="extension",
                tool_id="ext:system.shell:run",
                extension_id="system.shell",
                action_id="run",
                runner="shell_direct",
            ),
            origin="builtin",
        )
        self.register(builtin)

        fs_write = SkillContract(
            skill_id="skill.fs.write",
            name="Filesystem Write",
            version="1.0.0",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            output_schema={"type": "object"},
            risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
            required_permissions=["filesystem.write"],
            budget=SkillBudget(max_tokens=200, max_runtime_ms=5000, max_network_calls=0),
            enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
            audit_tags=["side_effect:filesystem.write"],
            approval_policy=SkillApprovalPolicy(),
            dispatch=SkillDispatchTarget(
                dispatch_type="extension",
                tool_id="ext:system.fs:write",
                extension_id="system.fs",
                action_id="write",
                runner="fs",
            ),
            origin="builtin",
        )
        self.register(fs_write)

        dbops = SkillContract(
            skill_id="skill.db_ops",
            name="DB Ops",
            version="1.0.0",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
            required_permissions=["database.write"],
            budget=SkillBudget(max_tokens=200, max_runtime_ms=30000, max_network_calls=0),
            enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
            audit_tags=["side_effect:database.write"],
            approval_policy=SkillApprovalPolicy(),
            dispatch=SkillDispatchTarget(
                dispatch_type="extension",
                tool_id="ext:db_ops:execute",
                extension_id="db_ops",
                action_id="execute",
                runner="dbops",
            ),
            origin="builtin",
        )
        self.register(dbops)

        db_query = SkillContract(
            skill_id="skill.db_query",
            name="DB NLQ Query",
            version="1.0.0",
            input_schema={
                "type": "object",
                "properties": {
                    "user_query": {"type": "string"},
                    "db_path": {"type": "string"},
                    "max_rows": {"type": "integer"},
                },
                "required": ["user_query"],
            },
            output_schema={"type": "object"},
            risk_tier=SkillRiskTier.SILENT,
            required_permissions=["db:read"],
            budget=SkillBudget(max_tokens=800, max_runtime_ms=30000, max_network_calls=0),
            enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
            audit_tags=["db", "nlq", "readonly", "evidence"],
            approval_policy=SkillApprovalPolicy(
                require_confirmation_for=[SkillRiskTier.EXPLAIN_CONFIRM, SkillRiskTier.HARD_BLOCK]
            ),
            dispatch=SkillDispatchTarget(
                dispatch_type="extension",
                tool_id="ext:db_nlq:query",
                extension_id="db_nlq",
                action_id="query",
                runner="nlq",
            ),
            origin="builtin",
        )
        self.register(db_query)
        self._load_kb_contracts()

    def _load_kb_contracts(self) -> None:
        kb_extension_id = "kb.orchestrator"
        kb_budget = SkillBudget(max_tokens=2000, max_runtime_ms=120000, max_network_calls=200)
        connector_input_schema = {
            "type": "object",
            "properties": {
                "connection_id": {"type": "string"},
                "source": {"type": "string"},
                "prefix": {"type": "string"},
                "recursive": {"type": "boolean"},
                "filters": {"type": "object"},
                "checkpoint_token": {"type": "string"},
                "dry_run": {"type": "boolean"},
            },
            "required": ["connection_id", "source"],
        }
        connector_output_schema = {
            "type": "object",
            "properties": {
                "objects": {"type": "array"},
                "checkpoint_token": {"type": "string"},
                "estimated_cost": {"type": "number"},
            },
        }
        ingest_input_schema = {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "connection_id": {"type": "string"},
                "path": {"type": "string"},
                "filters": {"type": "object"},
                "schedule": {"type": "string"},
                "once": {"type": "boolean"},
                "dry_run": {"type": "boolean"},
            },
            "required": ["source", "connection_id"],
        }
        ingest_output_schema = {
            "type": "object",
            "properties": {
                "ingest_id": {"type": "string"},
                "status": {"type": "string"},
                "estimated_cost": {"type": "number"},
                "session_id": {"type": "string"},
                "run_id": {"type": "string"},
            },
        }
        query_input_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer"},
                "filters": {"type": "object"},
                "mode": {"type": "string", "enum": ["precheck", "enrichment", "user_query"]},
                "query_purpose": {"type": "string"},
            },
            "required": ["query"],
        }
        query_output_schema = {
            "type": "object",
            "properties": {
                "results": {"type": "array"},
                "session_id": {"type": "string"},
                "run_id": {"type": "string"},
            },
        }
        self.register(
            SkillContract(
                skill_id="kb.connector.s3",
                name="KB Connector S3",
                version="1.0.0",
                input_schema=connector_input_schema,
                output_schema=connector_output_schema,
                risk_tier=SkillRiskTier.SILENT,
                required_permissions=["network.access", "kb.connector.read"],
                budget=kb_budget,
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "connector", "s3", "read_only"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:connector_s3",
                    extension_id=kb_extension_id,
                    action_id="connector_s3",
                    runner="default",
                ),
                origin="builtin",
            )
        )
        self.register(
            SkillContract(
                skill_id="kb.connector.onedrive",
                name="KB Connector OneDrive",
                version="1.0.0",
                input_schema=connector_input_schema,
                output_schema=connector_output_schema,
                risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
                required_permissions=["network.access", "kb.connector.read"],
                budget=kb_budget,
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "connector", "onedrive", "read_only"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:connector_onedrive",
                    extension_id=kb_extension_id,
                    action_id="connector_onedrive",
                    runner="default",
                ),
                origin="builtin",
            )
        )
        self.register(
            SkillContract(
                skill_id="kb.connector.googledrive",
                name="KB Connector GoogleDrive",
                version="1.0.0",
                input_schema=connector_input_schema,
                output_schema=connector_output_schema,
                risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
                required_permissions=["network.access", "kb.connector.read"],
                budget=kb_budget,
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "connector", "googledrive", "read_only"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:connector_googledrive",
                    extension_id=kb_extension_id,
                    action_id="connector_googledrive",
                    runner="default",
                ),
                origin="builtin",
            )
        )
        self.register(
            SkillContract(
                skill_id="kb.connector.sharepoint",
                name="KB Connector SharePoint",
                version="1.0.0",
                input_schema=connector_input_schema,
                output_schema=connector_output_schema,
                risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
                required_permissions=["network.access", "kb.connector.read"],
                budget=kb_budget,
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "connector", "sharepoint", "read_only"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:connector_sharepoint",
                    extension_id=kb_extension_id,
                    action_id="connector_sharepoint",
                    runner="default",
                ),
                origin="builtin",
            )
        )
        self.register(
            SkillContract(
                skill_id="kb.connector.ftp",
                name="KB Connector FTP",
                version="1.0.0",
                input_schema=connector_input_schema,
                output_schema=connector_output_schema,
                risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
                required_permissions=["network.access", "kb.connector.read"],
                budget=kb_budget,
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "connector", "ftp", "read_only"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:connector_ftp",
                    extension_id=kb_extension_id,
                    action_id="connector_ftp",
                    runner="default",
                ),
                origin="builtin",
            )
        )
        self.register(
            SkillContract(
                skill_id="kb.connector.smb",
                name="KB Connector SMB",
                version="1.0.0",
                input_schema=connector_input_schema,
                output_schema=connector_output_schema,
                risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
                required_permissions=["network.access", "kb.connector.read"],
                budget=kb_budget,
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "connector", "smb", "read_only"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:connector_smb",
                    extension_id=kb_extension_id,
                    action_id="connector_smb",
                    runner="default",
                ),
                origin="builtin",
            )
        )
        self.register(
            SkillContract(
                skill_id="kb.connector.sftp",
                name="KB Connector SFTP",
                version="1.0.0",
                input_schema=connector_input_schema,
                output_schema=connector_output_schema,
                risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
                required_permissions=["network.access", "kb.connector.read"],
                budget=kb_budget,
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "connector", "sftp", "read_only"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:connector_sftp",
                    extension_id=kb_extension_id,
                    action_id="connector_sftp",
                    runner="default",
                ),
                origin="builtin",
            )
        )
        self.register(
            SkillContract(
                skill_id="kb.api.query",
                name="KB API Query",
                version="1.0.0",
                input_schema=query_input_schema,
                output_schema=query_output_schema,
                risk_tier=SkillRiskTier.SILENT,
                required_permissions=["kb.query"],
                budget=SkillBudget(max_tokens=2000, max_runtime_ms=30000, max_network_calls=10),
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "api", "query", "read_only"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:api_query",
                    extension_id=kb_extension_id,
                    action_id="api_query",
                    runner="default",
                ),
                origin="builtin",
            )
        )
        self.register(
            SkillContract(
                skill_id="kb.api.ingest",
                name="KB API Ingest",
                version="1.0.0",
                input_schema=ingest_input_schema,
                output_schema=ingest_output_schema,
                risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
                required_permissions=["kb.ingest", "network.access"],
                budget=SkillBudget(max_tokens=4000, max_runtime_ms=300000, max_network_calls=400),
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "api", "ingest", "write", "provenance"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:api_ingest",
                    extension_id=kb_extension_id,
                    action_id="api_ingest",
                    runner="default",
                ),
                origin="builtin",
            )
        )
        self.register(
            SkillContract(
                skill_id="kb.api.reindex",
                name="KB API Reindex",
                version="1.0.0",
                input_schema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "connection_id": {"type": "string"},
                        "path": {"type": "string"},
                        "filters": {"type": "object"},
                        "dry_run": {"type": "boolean"},
                    },
                },
                output_schema=ingest_output_schema,
                risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
                required_permissions=["kb.reindex", "network.access"],
                budget=SkillBudget(max_tokens=4000, max_runtime_ms=300000, max_network_calls=400),
                enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
                audit_tags=["kb", "api", "reindex", "write", "provenance"],
                approval_policy=SkillApprovalPolicy(),
                dispatch=SkillDispatchTarget(
                    dispatch_type="extension",
                    tool_id="ext:kb.orchestrator:api_reindex",
                    extension_id=kb_extension_id,
                    action_id="api_reindex",
                    runner="default",
                ),
                origin="builtin",
            )
        )

    def register(self, contract: SkillContract) -> None:
        contract.validate()
        self._skills[contract.skill_id] = contract

    def get(self, skill_id: str) -> Optional[SkillContract]:
        return self._skills.get(skill_id)

    def list(self) -> List[SkillContract]:
        return list(self._skills.values())

    def ensure_extension_skill(
        self,
        *,
        skill_id: str,
        extension_id: str,
        action_id: str,
        name: Optional[str] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        risk_tier: SkillRiskTier = SkillRiskTier.EXPLAIN_CONFIRM,
        audit_tags: Optional[List[str]] = None,
        required_permissions: Optional[List[str]] = None,
    ) -> SkillContract:
        existing = self.get(skill_id)
        if existing:
            return existing
        contract = SkillContract(
            skill_id=skill_id,
            name=name or skill_id,
            version="1.0.0",
            input_schema=input_schema or {"type": "object", "properties": {}},
            output_schema=output_schema or {"type": "object"},
            risk_tier=risk_tier,
            required_permissions=required_permissions or [],
            budget=SkillBudget(),
            enabled_conditions=SkillEnabledConditions(mode=SkillMode.LOCAL_LOCKED),
            audit_tags=audit_tags or ["side_effect:unspecified"],
            approval_policy=SkillApprovalPolicy(),
            dispatch=SkillDispatchTarget(
                dispatch_type="extension",
                tool_id=f"ext:{extension_id}:{action_id}",
                extension_id=extension_id,
                action_id=action_id,
            ),
            origin="extension",
        )
        self.register(contract)
        return contract

    def refresh_mcp_tools(self, timeout_s: Optional[float] = None) -> None:
        manager = MCPConfigManager()
        servers = list(manager.get_enabled_servers())
        for server in servers:
            try:
                tools = self._probe_server_tools(server, timeout_s=timeout_s)
            except Exception as exc:
                logger.warning("Failed to list MCP tools", extra={"server_id": server.id, "error": str(exc)})
                continue
            for tool in tools:
                name = str(tool.get("name") or "").strip()
                if not name:
                    continue
                if not manager.is_tool_allowed(server.id, name):
                    continue
                side_effects = tool.get("side_effect_tags") if isinstance(tool.get("side_effect_tags"), list) else []
                if side_effects and manager.is_side_effect_denied(server.id, side_effects):
                    continue
                self.register_mcp_tool(server, tool)

    def probe_mcp_server(self, server, timeout_s: Optional[float] = None) -> List[Dict[str, Any]]:
        return self._probe_server_tools(server, timeout_s=timeout_s)

    def register_mcp_tool(self, server, tool: Dict[str, Any]) -> Optional[SkillContract]:
        name = str(tool.get("name") or "").strip()
        if not name:
            return None
        if server.deny_side_effect_tags:
            side_effects = tool.get("side_effect_tags") if isinstance(tool.get("side_effect_tags"), list) else []
            if any(effect in server.deny_side_effect_tags for effect in side_effects):
                return None
        skill_id = f"mcp.{server.id}.{name}"
        if skill_id in self._skills:
            return self._skills[skill_id]
        input_schema = tool.get("inputSchema") if isinstance(tool.get("inputSchema"), dict) else {}
        output_schema = tool.get("outputSchema") if isinstance(tool.get("outputSchema"), dict) else {}
        tags = ["network"]
        deny_tags = list(server.deny_side_effect_tags or [])
        if deny_tags:
            tags.extend([f"deny:{t}" for t in deny_tags])
        contract = SkillContract(
            skill_id=skill_id,
            name=str(tool.get("title") or tool.get("name") or skill_id),
            version="1.0.0",
            input_schema=input_schema or {"type": "object", "properties": {}},
            output_schema=output_schema or {"type": "object"},
            risk_tier=SkillRiskTier.EXPLAIN_CONFIRM,
            required_permissions=["network.access"],
            budget=SkillBudget(max_network_calls=10),
            enabled_conditions=SkillEnabledConditions(mode=SkillMode.OPEN),
            audit_tags=tags or ["network"],
            approval_policy=SkillApprovalPolicy(),
            dispatch=SkillDispatchTarget(
                dispatch_type="mcp",
                tool_id=f"mcp:{server.id}:{name}",
                mcp_server_id=server.id,
                mcp_tool_name=name,
            ),
            origin=f"mcp:{server.id}",
        )
        self.register(contract)
        return contract

    @staticmethod
    def _probe_server_tools(server, timeout_s: Optional[float] = None) -> List[Dict[str, Any]]:
        async def _call() -> List[Dict[str, Any]]:
            client = MCPClient(server)
            try:
                await client.connect()
                return await client.list_tools()
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass
        import asyncio
        if timeout_s and timeout_s > 0:
            return asyncio.run(asyncio.wait_for(_call(), timeout=timeout_s))
        return asyncio.run(_call())

    def export_snapshot(self, path: Path) -> None:
        snapshot = {
            "skills": [self._snapshot_entry(skill) for skill in self.list()],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _snapshot_entry(skill: SkillContract) -> Dict[str, Any]:
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "version": skill.version,
            "risk_tier": skill.risk_tier.value,
            "required_permissions": list(skill.required_permissions or []),
            "budget": asdict(skill.budget),
            "enabled_conditions": {
                "mode": skill.enabled_conditions.mode.value,
                "trust_tier": skill.enabled_conditions.trust_tier,
                "feature_flags": list(skill.enabled_conditions.feature_flags or []),
            },
            "audit_tags": list(skill.audit_tags or []),
            "approval_policy": {
                "require_confirmation_for": [tier.value for tier in skill.approval_policy.require_confirmation_for],
            },
            "dispatch": {
                "dispatch_type": skill.dispatch.dispatch_type,
                "tool_id": skill.dispatch.tool_id,
                "extension_id": skill.dispatch.extension_id,
                "action_id": skill.dispatch.action_id,
                "runner": skill.dispatch.runner,
                "mcp_server_id": skill.dispatch.mcp_server_id,
                "mcp_tool_name": skill.dispatch.mcp_tool_name,
            },
            "origin": skill.origin,
        }
