from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

from octopusos.core.audit import log_audit_event, EXT_RUN_STARTED, EXT_RUN_FINISHED
from octopusos.extensions.runtime import ExtensionRuntime
from octopusos.core.mcp.client import MCPClient
from octopusos.core.mcp.config import MCPConfigManager
from octopusos.core.capabilities.capability_models import ToolInvocation


@dataclass(frozen=True)
class DispatchResult:
    ok: bool
    payload: Dict[str, Any]
    error: Optional[str] = None


class ExtensionDispatcher:
    def __init__(self) -> None:
        self._runtime = ExtensionRuntime()

    def dispatch(
        self,
        *,
        extension_id: str,
        action_id: str,
        invocation: ToolInvocation,
        decision_context: Dict[str, Any],
    ) -> DispatchResult:
        log_audit_event(
            event_type=EXT_RUN_STARTED,
            task_id=invocation.task_id,
            metadata={
                "extension_id": extension_id,
                "action_id": action_id,
                "invocation_id": invocation.invocation_id,
            },
        )
        result = self._runtime.run(
            extension_id=extension_id,
            action_id=action_id,
            args=invocation.inputs,
            decision_context=decision_context,
        )
        out = DispatchResult(ok=result.success, payload={"output": result.output}, error=result.error)
        log_audit_event(
            event_type=EXT_RUN_FINISHED,
            task_id=invocation.task_id,
            metadata={
                "extension_id": extension_id,
                "action_id": action_id,
                "invocation_id": invocation.invocation_id,
                "ok": out.ok,
            },
        )
        return out


class McpDispatcher:
    def __init__(self) -> None:
        self._tool_router = None

    def dispatch(self, *, tool_id: str, invocation, decision_context: Dict[str, Any]) -> DispatchResult:
        async def _call() -> DispatchResult:
            parts = tool_id.split(":", 2)
            if len(parts) != 3 or parts[0] != "mcp":
                return DispatchResult(ok=False, payload={}, error=f"Invalid MCP tool_id: {tool_id}")
            server_id = parts[1]
            tool_name = parts[2]
            manager = MCPConfigManager()
            server_cfg = manager.get_server_config(server_id)
            if not server_cfg or not server_cfg.enabled:
                return DispatchResult(ok=False, payload={}, error=f"MCP server disabled: {server_id}")
            client = MCPClient(server_cfg)
            await client.connect()
            try:
                skill_context = {
                    "skill_id": decision_context.get("skill_id"),
                    "risk_tier": decision_context.get("risk_tier"),
                    "audit_tags": decision_context.get("audit_tags"),
                }
                result = await client.call_tool(tool_name, invocation.inputs, skill_context=skill_context)
                return DispatchResult(ok=True, payload={"payload": result})
            finally:
                await client.disconnect()

        try:
            return asyncio.run(_call())
        except RuntimeError:
            return asyncio.get_event_loop().run_until_complete(_call())
