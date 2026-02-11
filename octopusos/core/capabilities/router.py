"""
Tool Router - Routes tool invocations to appropriate executors

This module provides the ToolRouter class that dispatches tool invocations
to the correct executor based on the tool's source type (Extension or MCP).

Features:
- Unified invocation interface
- Source-based routing (extension vs MCP)
- Error handling and result normalization
- Integration with policy engine (PR-3)

Example:
    from octopusos.core.capabilities import CapabilityRegistry, ToolRouter
    from octopusos.core.capabilities.capability_models import ToolInvocation

    registry = CapabilityRegistry(ext_registry)
    router = ToolRouter(registry)

    invocation = ToolInvocation(
        invocation_id="inv_123",
        tool_id="ext:tools.postman:get",
        inputs={"url": "https://api.example.com"},
        actor="user@example.com",
        timestamp=datetime.now()
    )

    result = await router.invoke_tool("ext:tools.postman:get", invocation)
"""

import logging
import json
import hashlib
import time
import uuid
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

import jsonschema
from octopusos.core.capabilities.registry import CapabilityRegistry
from octopusos.core.capabilities.capability_models import (
    ToolInvocation,
    ToolResult,
    ToolSource,
    PolicyDecision,
)
from octopusos.core.capabilities.audit import (
    emit_tool_invocation_start,
    emit_tool_invocation_end,
    emit_provenance_snapshot,
)
from octopusos.core.capabilities.policy import ToolPolicyEngine
from octopusos.core.capabilities.governance_models.provenance import (
    ProvenanceStamp,
    get_current_env,
)

logger = logging.getLogger(__name__)


class ToolRouterError(Exception):
    """Base exception for tool router errors"""
    pass


class ToolNotFoundError(ToolRouterError):
    """Raised when a tool is not found"""
    pass


class PolicyViolationError(ToolRouterError):
    """Raised when a tool invocation violates policy"""
    pass


class ToolRouter:
    """
    Tool invocation router

    Routes tool invocations to the appropriate executor based on source type.
    Handles policy checks, auditing, and result normalization.
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        policy_engine: Optional[ToolPolicyEngine] = None,
        quota_manager: Optional['QuotaManager'] = None
    ):
        """
        Initialize tool router

        Args:
            registry: CapabilityRegistry instance
            policy_engine: ToolPolicyEngine instance (optional, for PR-3)
            quota_manager: QuotaManager instance (optional, for PR-A)
        """
        self.registry = registry

        # Import QuotaManager here to avoid circular import
        if quota_manager is None:
            from octopusos.core.capabilities.quota_manager import QuotaManager
            quota_manager = QuotaManager()

        self.quota_manager = quota_manager
        self.policy_engine = policy_engine or ToolPolicyEngine(quota_manager=quota_manager)

    async def invoke_tool(
        self,
        tool_id: str,
        invocation: ToolInvocation,
        admin_token: Optional[str] = None
    ) -> ToolResult:
        """
        Invoke a tool by ID with complete security gate checks

        Security flow:
        1. Get tool descriptor
        2. Run 6-layer policy gate checks
        3. Emit before audit
        4. Execute tool
        5. Emit after audit

        Args:
            tool_id: Tool identifier
            invocation: ToolInvocation request
            admin_token: Admin token for high-risk operations (optional)

        Returns:
            ToolResult

        Raises:
            ToolNotFoundError: If tool not found
            PolicyViolationError: If policy check fails
            ToolRouterError: For other errors
        """
        start_time = time.time()
        started_at = datetime.now()
        tool = None  # Initialize for error handling
        self._ensure_invocation_id(invocation)
        run_tape_status = "runtime_error"
        run_tape_error = None

        try:
            # Step 1: Get tool descriptor
            tool = self.registry.get_tool(tool_id)
            if not tool:
                raise ToolNotFoundError(f"Tool not found: {tool_id}")

            # Step 1.5: Generate Provenance Stamp (PR-C)
            provenance = ProvenanceStamp(
                capability_id=tool.tool_id,
                tool_id=tool.name,
                capability_type=tool.source_type.value,
                source_id=tool.source_id,
                source_version=tool.source_version,
                execution_env=get_current_env(),
                trust_tier=tool.trust_tier.value,
                timestamp=datetime.now(),
                invocation_id=invocation.invocation_id,
                task_id=invocation.task_id,
                project_id=invocation.project_id,
                spec_hash=invocation.spec_hash
            )

            # Step 2: Policy check (6-layer gates)
            allowed, reason, decision = self.policy_engine.check_allowed(
                tool, invocation, admin_token
            )

            # Step 3: Handle policy violation
            if not allowed:
                from octopusos.core.capabilities.audit import emit_policy_violation
                emit_policy_violation(invocation, tool, decision, reason)

                # Return error result with provenance
                duration_ms = int((time.time() - start_time) * 1000)
                denied_result = ToolResult(
                    invocation_id=invocation.invocation_id,
                    success=False,
                    payload=None,
                    declared_side_effects=[],
                    error=f"Policy violation: {reason}",
                    duration_ms=duration_ms,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    provenance=provenance,
                    metadata={
                        "failure_type": "policy_denied",
                        "policy_reason": reason,
                        "policy_requires_approval": decision.requires_approval,
                    },
                )
                run_tape_status = "policy_denied"
                self._write_run_tape_event(
                    invocation=invocation,
                    tool=tool,
                    status=run_tape_status,
                    started_at=started_at,
                    duration_ms=duration_ms,
                    result=denied_result,
                    error=denied_result.error,
                )
                return denied_result

            # Step 4: Emit before audit
            from octopusos.core.capabilities.audit import (
                emit_tool_invocation_start,
                emit_tool_invocation_end
            )
            emit_tool_invocation_start(invocation, tool)

            # Step 5: Update quota - increment concurrent count
            quota_id = f"tool:{tool_id}"
            self.quota_manager.update_quota(quota_id, 0, 0, increment_concurrent=1)

            # Step 6: Route to appropriate executor
            try:
                if tool.source_type == ToolSource.EXTENSION:
                    result = await self._invoke_extension_tool(tool_id, invocation)
                elif tool.source_type == ToolSource.MCP:
                    result = await self._invoke_mcp_tool(tool_id, invocation)
                else:
                    raise ToolRouterError(f"Unknown source type: {tool.source_type}")
            finally:
                # Step 7: Update quota - decrement concurrent count and add runtime
                duration_ms = int((time.time() - start_time) * 1000)
                self.quota_manager.update_quota(
                    quota_id,
                    runtime_ms=duration_ms,
                    increment_concurrent=-1
                )

            # Step 8: Add timing information and provenance
            result = self._validate_output_contract(tool, result)
            run_tape_status = "success" if result.success else result.metadata.get("failure_type", "runtime_error")
            result.duration_ms = duration_ms
            result.started_at = started_at
            result.completed_at = datetime.now()
            result.provenance = provenance
            result.metadata.setdefault("capability_version", tool.source_version)
            result.metadata.setdefault("schema_hash", self._schema_hash(tool.output_schema))

            # Step 9: Emit after audit (including provenance snapshot)
            emit_tool_invocation_end(result, tool, invocation.task_id)
            emit_provenance_snapshot(provenance)
            self._write_run_tape_event(
                invocation=invocation,
                tool=tool,
                status=run_tape_status,
                started_at=started_at,
                duration_ms=duration_ms,
                result=result,
                error=result.error,
            )

            logger.info(f"Tool invocation completed: {tool_id} in {duration_ms}ms")
            return result

        except ToolNotFoundError as e:
            # Tool not found error
            duration_ms = int((time.time() - start_time) * 1000)
            error_result = ToolResult(
                invocation_id=invocation.invocation_id,
                success=False,
                payload=None,
                declared_side_effects=[],
                error=str(e),
                duration_ms=duration_ms,
                started_at=started_at,
                completed_at=datetime.now()
            )
            # Don't emit audit for tool not found
            raise

        except ToolRouterError as e:
            # Known router errors
            duration_ms = int((time.time() - start_time) * 1000)
            error_result = ToolResult(
                invocation_id=invocation.invocation_id,
                success=False,
                payload=None,
                declared_side_effects=[],
                error=str(e),
                duration_ms=duration_ms,
                started_at=started_at,
                completed_at=datetime.now()
            )
            # Emit audit if we have tool info
            if tool:
                from octopusos.core.capabilities.audit import emit_tool_invocation_end
                emit_tool_invocation_end(error_result, tool, invocation.task_id)
            run_tape_error = str(e)
            if tool:
                self._write_run_tape_event(
                    invocation=invocation,
                    tool=tool,
                    status=run_tape_status,
                    started_at=started_at,
                    duration_ms=duration_ms,
                    result=error_result,
                    error=run_tape_error,
                )
            raise

        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error invoking tool {tool_id}: {e}", exc_info=True)
            duration_ms = int((time.time() - start_time) * 1000)
            error_result = ToolResult(
                invocation_id=invocation.invocation_id,
                success=False,
                payload=None,
                declared_side_effects=[],
                error=f"Unexpected error: {e}",
                duration_ms=duration_ms,
                started_at=started_at,
                completed_at=datetime.now()
            )
            # Emit audit if we have tool info
            if tool:
                from octopusos.core.capabilities.audit import emit_tool_invocation_end
                emit_tool_invocation_end(error_result, tool, invocation.task_id)
                self._write_run_tape_event(
                    invocation=invocation,
                    tool=tool,
                    status=run_tape_status,
                    started_at=started_at,
                    duration_ms=duration_ms,
                    result=error_result,
                    error=str(e),
                )
            raise ToolRouterError(f"Failed to invoke tool: {e}") from e

    async def _invoke_extension_tool(
        self,
        tool_id: str,
        invocation: ToolInvocation
    ) -> ToolResult:
        """
        Invoke an extension tool

        This is a placeholder implementation for PR-1.
        Full implementation will integrate with the existing extension runner.

        Args:
            tool_id: Tool identifier
            invocation: ToolInvocation request

        Returns:
            ToolResult
        """
        try:
            # Parse tool_id: "ext:<extension_id>:<command>"
            parts = tool_id.split(":", 2)
            if len(parts) != 3 or parts[0] != "ext":
                raise ToolRouterError(f"Invalid extension tool_id format: {tool_id}")

            extension_id = parts[1]
            action_id = parts[2]
            dispatch = self._resolve_extension_dispatch(invocation.inputs)

            if dispatch["mode"] == "capability_runner":
                return self._invoke_via_capability_runner(
                    extension_id=extension_id,
                    action_id=action_id,
                    invocation=invocation,
                    runner_type=dispatch["runner_type"],
                )

            return self._invoke_via_runner_base(
                extension_id=extension_id,
                action_id=action_id,
                invocation=invocation,
                runner_type=dispatch["runner_type"],
                runner_kwargs=dispatch["runner_kwargs"],
            )

        except Exception as e:
            logger.error(f"Failed to invoke extension tool {tool_id}: {e}", exc_info=True)
            return ToolResult(
                invocation_id=invocation.invocation_id,
                success=False,
                payload=None,
                error=str(e),
                duration_ms=0,  # Will be set by caller
                metadata={"failure_type": "runtime_error"},
            )

    async def _invoke_mcp_tool(
        self,
        tool_id: str,
        invocation: ToolInvocation
    ) -> ToolResult:
        """
        Invoke an MCP tool

        Args:
            tool_id: Tool identifier (format: mcp:<server_id>:<tool_name>)
            invocation: ToolInvocation request

        Returns:
            ToolResult
        """
        start_time = datetime.now()

        try:
            logger.info(f"Invoking MCP tool: {tool_id}")

            # Parse tool_id: mcp:<server_id>:<tool_name>
            parts = tool_id.split(":", 2)
            if len(parts) != 3 or parts[0] != "mcp":
                raise ValueError(f"Invalid MCP tool_id format: {tool_id}")

            server_id = parts[1]
            tool_name = parts[2]

            logger.debug(f"MCP server: {server_id}, tool: {tool_name}")

            # Hardened guard: disabled servers must never be invokable even with stale cache.
            manager = getattr(self.registry, "mcp_config_manager", None)
            if manager:
                server_cfg = manager.get_server_config(server_id)
                if not server_cfg or not server_cfg.enabled:
                    raise RuntimeError(f"MCP server is disabled: {server_id}")

            # Get MCP client from registry
            client = self.registry.mcp_clients.get(server_id)
            if not client:
                raise RuntimeError(f"MCP server not connected: {server_id}")

            if not client.is_alive():
                raise RuntimeError(f"MCP server not alive: {server_id}")

            # Import adapter
            from octopusos.core.mcp import MCPAdapter

            # Call tool
            mcp_result = await client.call_tool(tool_name, invocation.inputs)

            # Calculate duration
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Convert result
            adapter = MCPAdapter()
            result = adapter.mcp_result_to_tool_result(
                invocation_id=invocation.invocation_id,
                mcp_result=mcp_result,
                duration_ms=duration_ms
            )

            logger.info(
                f"MCP tool invocation completed: {tool_id} "
                f"(success={result.success}, duration={duration_ms}ms)"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to invoke MCP tool {tool_id}: {e}", exc_info=True)
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return ToolResult(
                invocation_id=invocation.invocation_id,
                success=False,
                payload=None,
                declared_side_effects=[],
                error=str(e),
                duration_ms=duration_ms
            )

    def sync_invoke_tool(
        self,
        tool_id: str,
        invocation: ToolInvocation
    ) -> ToolResult:
        """
        Synchronous wrapper for invoke_tool

        This is provided for compatibility with synchronous code.
        Uses asyncio.run() internally.

        Args:
            tool_id: Tool identifier
            invocation: ToolInvocation request

        Returns:
            ToolResult
        """
        import asyncio
        return asyncio.run(self.invoke_tool(tool_id, invocation))

    def _resolve_extension_dispatch(self, inputs: dict[str, Any]) -> dict[str, Any]:
        runner_type = (
            inputs.get("__runner__")
            or inputs.get("runner")
            or "simulated"
        )
        if runner_type.startswith("exec.") or runner_type.startswith("analyze."):
            return {"mode": "capability_runner", "runner_type": runner_type, "runner_kwargs": {}}

        runner_kwargs = {}
        if runner_type == "simulated":
            runner_kwargs["delay_per_stage"] = 0.0
        if "extensions_dir" in inputs:
            runner_kwargs["extensions_dir"] = Path(inputs["extensions_dir"])

        return {"mode": "runner_base", "runner_type": runner_type, "runner_kwargs": runner_kwargs}

    def _invoke_via_capability_runner(
        self,
        extension_id: str,
        action_id: str,
        invocation: ToolInvocation,
        runner_type: str,
    ) -> ToolResult:
        from octopusos.core.capabilities.models import CommandRoute, ExecutionContext
        from octopusos.core.capabilities.runner import CapabilityRunner

        args = invocation.inputs.get("args", [])
        if not isinstance(args, list):
            args = [str(args)]
        flags = invocation.inputs.get("flags", {})
        if not isinstance(flags, dict):
            flags = {}

        work_dir_raw = invocation.inputs.get("work_dir")
        if work_dir_raw:
            work_dir = Path(work_dir_raw)
        else:
            work_dir = Path.cwd()

        route = CommandRoute(
            command_name=f"/{action_id}",
            extension_id=extension_id,
            action_id=action_id,
            runner=runner_type,
            args=args,
            flags=flags,
            metadata={"invocation_id": invocation.invocation_id},
        )
        context = ExecutionContext(
            session_id=invocation.session_id or "tool_router",
            user_id=invocation.user_id or invocation.actor,
            extension_id=extension_id,
            work_dir=work_dir,
            timeout=max(1, int(invocation.inputs.get("timeout", 300))),
        )

        runner = CapabilityRunner(base_dir=work_dir)
        capability_result = runner.execute(route, context)

        metadata = dict(capability_result.metadata or {})
        metadata.update(
            {
                "source": "extension",
                "extension_id": extension_id,
                "action_id": action_id,
                "runner_type": runner_type,
            }
        )
        if not capability_result.success:
            metadata.setdefault("failure_type", "runtime_error")

        return ToolResult(
            invocation_id=invocation.invocation_id,
            success=capability_result.success,
            payload={
                "output": capability_result.output,
                "artifacts": [str(p) for p in capability_result.artifacts],
            },
            declared_side_effects=[],
            error=capability_result.error,
            duration_ms=0,
            metadata=metadata,
        )

    def _invoke_via_runner_base(
        self,
        extension_id: str,
        action_id: str,
        invocation: ToolInvocation,
        runner_type: str,
        runner_kwargs: dict[str, Any],
    ) -> ToolResult:
        from octopusos.core.capabilities.runner_base import Invocation as RunnerInvocation, get_runner

        args = invocation.inputs.get("args", [])
        if not isinstance(args, list):
            args = [str(args)]
        flags = invocation.inputs.get("flags", {})
        if not isinstance(flags, dict):
            flags = {}

        runner = get_runner(runner_type, **runner_kwargs)
        runner_invocation = RunnerInvocation(
            extension_id=extension_id,
            action_id=action_id,
            session_id=invocation.session_id or "tool_router",
            user_id=invocation.user_id or invocation.actor,
            args=args,
            flags=flags,
            metadata={
                "invocation_id": invocation.invocation_id,
                "tool_id": invocation.tool_id,
            },
            timeout=max(1, int(invocation.inputs.get("timeout", 300))),
        )
        run_result = runner.run(runner_invocation)

        metadata = dict(run_result.metadata or {})
        metadata.update(
            {
                "source": "extension",
                "extension_id": extension_id,
                "action_id": action_id,
                "runner_type": runner_type,
            }
        )
        if not run_result.success:
            metadata.setdefault("failure_type", "runtime_error")

        return ToolResult(
            invocation_id=invocation.invocation_id,
            success=run_result.success,
            payload={"output": run_result.output},
            declared_side_effects=[],
            error=run_result.error,
            duration_ms=0,
            metadata=metadata,
        )

    def _validate_output_contract(self, tool, result: ToolResult) -> ToolResult:
        if not tool.output_schema or not result.success:
            return result
        validator = jsonschema.Draft202012Validator(tool.output_schema)
        errors = sorted(validator.iter_errors(result.payload), key=lambda e: e.path)
        if not errors:
            return result

        messages = []
        for err in errors[:3]:
            path = ".".join(str(p) for p in err.absolute_path) or "<root>"
            messages.append(f"{path}: {err.message}")

        result.success = False
        result.error = f"Output contract violation: {'; '.join(messages)}"
        result.metadata["failure_type"] = "contract_violation"
        result.metadata["contract_errors"] = messages
        return result

    def _schema_hash(self, schema: Optional[dict[str, Any]]) -> Optional[str]:
        if not schema:
            return None
        canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _ensure_invocation_id(self, invocation: ToolInvocation) -> None:
        if invocation.invocation_id:
            return
        invocation.invocation_id = f"inv_{uuid.uuid4().hex[:12]}"

    def _write_run_tape_event(
        self,
        invocation: ToolInvocation,
        tool,
        status: str,
        started_at: datetime,
        duration_ms: int,
        result: Optional[ToolResult],
        error: Optional[str],
    ) -> None:
        try:
            from octopusos.core.executor.audit_logger import AuditLogger

            run_tape_path_raw = os.getenv("OCTOPUSOS_TOOL_RUN_TAPE_PATH")
            if run_tape_path_raw:
                run_tape_path = Path(run_tape_path_raw)
            else:
                run_tape_path = Path.home() / ".octopusos" / "audit" / "tool_router_run_tape.jsonl"
            logger_instance = AuditLogger(run_tape_path)
            logger_instance.log_event(
                event_type="tool_invocation",
                operation_id=invocation.invocation_id,
                details={
                    "status": status,
                    "tool_id": tool.tool_id,
                    "source_type": tool.source_type.value,
                    "actor": invocation.actor,
                    "task_id": invocation.task_id,
                    "project_id": invocation.project_id,
                    "started_at": started_at.isoformat(),
                    "duration_ms": duration_ms,
                    "failure_type": (result.metadata.get("failure_type") if result else None),
                    "policy_reason": (result.metadata.get("policy_reason") if result else None),
                    "capability_version": (result.metadata.get("capability_version") if result else None),
                    "schema_hash": (result.metadata.get("schema_hash") if result else None),
                    "input_summary": self._truncate_json(invocation.inputs),
                    "output_summary": self._truncate_json(result.payload if result else None),
                    "error": error,
                },
            )
        except Exception as write_error:
            logger.warning("Failed to write run_tape event: %s", write_error)

    def _truncate_json(self, payload: Any, max_len: int = 400) -> Optional[str]:
        if payload is None:
            return None
        text = json.dumps(payload, ensure_ascii=False, default=str)
        if len(text) <= max_len:
            return text
        return text[:max_len] + "...(truncated)"
