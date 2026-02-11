"""
Capability executors

Base class and concrete implementations for different runner types.
"""

import logging
import re
import os
import json
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any

from .exceptions import ExecutionError, ToolNotFoundError
from .models import (
    CommandRoute,
    ExecutionContext,
    ExecutionResult,
)
from .response_store import get_response_store
from .tool_executor import ToolExecutor
from .permissions import Permission, get_permission_checker
from octopusos.core.executor.audit_logger import AuditLogger
from octopusos.core.schemas.output_parser import SchemaOutputParser, ParseResult
from octopusos.core.prompts import (
    get_prompt_registry,
    register_default_prompt_specs,
    PromptVarsValidationError,
    RenderedPrompt,
)

logger = logging.getLogger(__name__)


class BaseExecutor(ABC):
    """
    Base class for capability executors

    Each executor implements a specific runner type (exec, analyze, etc.)
    """

    @abstractmethod
    def execute(
        self,
        route: CommandRoute,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a capability

        Args:
            route: Command route with execution details
            context: Execution context

        Returns:
            ExecutionResult with output and metadata
        """
        pass

    @abstractmethod
    def supports_runner(self, runner: str) -> bool:
        """
        Check if this executor supports a runner type

        Args:
            runner: Runner type string (e.g., "exec.postman_cli")

        Returns:
            True if supported, False otherwise
        """
        pass


class ExecToolExecutor(BaseExecutor):
    """
    Execute command-line tools (exec.xxx runner type)

    Handles runner types like:
    - exec.postman_cli
    - exec.curl
    - exec.ffmpeg
    """

    RUNNER_PREFIX = "exec."

    def __init__(self, tool_executor: Optional[ToolExecutor] = None):
        """
        Initialize executor

        Args:
            tool_executor: Tool executor instance (created if not provided)
        """
        self.tool_executor = tool_executor or ToolExecutor()
        self.response_store = get_response_store()

    def supports_runner(self, runner: str) -> bool:
        """Check if runner starts with 'exec.'"""
        return runner.startswith(self.RUNNER_PREFIX)

    def execute(
        self,
        route: CommandRoute,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a command-line tool

        Process:
        1. Check permissions (exec_shell required for tool execution)
        2. Extract tool name from runner (exec.postman_cli -> postman)
        3. Build command arguments from route
        4. Execute tool in controlled environment
        5. Store response for potential follow-up commands
        6. Return formatted result

        Args:
            route: Command route
            context: Execution context

        Returns:
            ExecutionResult
        """
        # Step 1: Check permissions before execution
        declared_permissions = getattr(route, 'permissions', [])
        if not declared_permissions:
            # Try to get from metadata
            declared_permissions = route.metadata.get('permissions', [])

        if declared_permissions:
            checker = get_permission_checker()
            granted, reason = checker.has_all_permissions(
                ext_id=route.extension_id,
                permissions=[Permission.EXEC_SHELL],
                declared_permissions=declared_permissions
            )

            if not granted:
                error_msg = f"Permission denied: {reason}"
                logger.error(
                    f"Extension execution denied: {route.extension_id}",
                    extra={
                        "extension_id": route.extension_id,
                        "action": route.action_id,
                        "reason": reason,
                        "required_permission": "exec_shell",
                        "audit_event": "EXT_RUN_DENIED"
                    }
                )
                return ExecutionResult(
                    success=False,
                    output="",
                    error=error_msg,
                    metadata={
                        "denial_reason": reason,
                        "required_permission": "exec_shell"
                    }
                )

        # Step 2: Extract tool name from runner
        tool_name = self._extract_tool_name(route.runner)

        logger.info(
            f"Executing tool: {tool_name}",
            extra={
                "extension_id": route.extension_id,
                "action": route.action_id,
                "runner": route.runner
            }
        )

        # Build command arguments
        # route.action_id = "get"
        # route.args = ["https://api.example.com"]
        # -> postman get https://api.example.com
        command_args = [route.action_id] + route.args

        # Add flags if present
        for flag_name, flag_value in route.flags.items():
            if isinstance(flag_value, bool):
                if flag_value:
                    command_args.append(f"--{flag_name}")
            else:
                command_args.extend([f"--{flag_name}", str(flag_value)])

        # Execute tool
        try:
            result = self.tool_executor.execute_tool(
                tool_name=tool_name,
                args=command_args,
                work_dir=context.work_dir,
                timeout=context.timeout
            )

            # Store last response for potential follow-up commands
            if result.success and result.stdout:
                self._save_last_response(
                    context.session_id,
                    result.stdout,
                    {
                        "extension_id": route.extension_id,
                        "command": route.command_name,
                        "action": route.action_id,
                        "tool": tool_name
                    }
                )

            # Return result
            return ExecutionResult(
                success=result.success,
                output=result.output,
                error=result.stderr if not result.success else None,
                metadata={
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                    "command": result.command,
                    "tool": tool_name
                },
                raw_data=result
            )

        except ToolNotFoundError as e:
            logger.error(f"Tool not found: {tool_name}", exc_info=True)
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                metadata={"tool": tool_name}
            )

        except Exception as e:
            logger.error(
                f"Tool execution failed: {tool_name}",
                exc_info=True
            )
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution failed: {str(e)}",
                metadata={"tool": tool_name}
            )

    def _extract_tool_name(self, runner: str) -> str:
        """
        Extract tool name from runner string

        Examples:
            exec.postman_cli -> postman
            exec.curl -> curl
            exec.ffmpeg -> ffmpeg

        Args:
            runner: Runner string

        Returns:
            Tool name
        """
        if not runner.startswith(self.RUNNER_PREFIX):
            raise ValueError(f"Invalid runner format: {runner}")

        tool_spec = runner[len(self.RUNNER_PREFIX):]

        # Handle suffixes like _cli, _tool
        tool_name = tool_spec.replace("_cli", "").replace("_tool", "")

        return tool_name

    def _save_last_response(
        self,
        session_id: str,
        response: str,
        metadata: dict
    ) -> None:
        """
        Save the last response for a session

        Args:
            session_id: Session identifier
            response: Response content
            metadata: Response metadata
        """
        try:
            self.response_store.save(session_id, response, metadata)
            logger.debug(
                f"Saved last response for session {session_id} "
                f"({len(response)} bytes)"
            )
        except Exception as e:
            logger.warning(
                f"Failed to save last response: {e}",
                exc_info=True
            )


class AnalyzeResponseExecutor(BaseExecutor):
    """
    Analyze output using LLM (analyze.response runner type)

    Handles analysis of previous command outputs or provided data.
    """

    RUNNER_TYPE = "analyze.response"

    def __init__(self, llm_client=None):
        """
        Initialize executor

        Args:
            llm_client: LLM client for analysis (optional)
        """
        self.llm_client = llm_client
        self.response_store = get_response_store()

    def supports_runner(self, runner: str) -> bool:
        """Check if runner is 'analyze.response'"""
        return runner == self.RUNNER_TYPE

    def execute(
        self,
        route: CommandRoute,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Analyze response using LLM

        Process:
        1. Get content to analyze (last_response or provided data)
        2. Build analysis prompt with usage documentation
        3. Call LLM for analysis
        4. Return formatted result

        Args:
            route: Command route
            context: Execution context

        Returns:
            ExecutionResult
        """
        logger.info(
            "Analyzing response with LLM",
            extra={
                "extension_id": route.extension_id,
                "action": route.action_id
            }
        )

        # Get content to analyze
        content = self._get_content_to_analyze(route, context)

        if not content:
            return ExecutionResult(
                success=False,
                output="",
                error=(
                    "No content to analyze. Either run a command first or "
                    "provide data to analyze."
                )
            )

        # Build analysis prompt
        prompt = self._build_analysis_prompt(
            content=content,
            usage_doc=context.usage_doc,
            action_description=route.description or "Analyze the response"
        )

        # Call LLM for analysis
        try:
            if self.llm_client is None:
                # If no LLM client, provide a simple analysis
                analysis = self._simple_analysis(content)
            else:
                analysis = self.llm_client.complete(prompt)

            return ExecutionResult(
                success=True,
                output=analysis,
                metadata={
                    "analyzed_content_length": len(content),
                    "analysis_type": "llm" if self.llm_client else "simple"
                }
            )

        except Exception as e:
            logger.error("Analysis failed", exc_info=True)
            return ExecutionResult(
                success=False,
                output="",
                error=f"Analysis failed: {str(e)}"
            )

    def _get_content_to_analyze(
        self,
        route: CommandRoute,
        context: ExecutionContext
    ) -> Optional[str]:
        """
        Get the content to analyze

        Args:
            route: Command route
            context: Execution context

        Returns:
            Content string or None
        """
        # Check if "last_response" is in args
        if "last_response" in route.args or "last" in route.args:
            content = self.response_store.get(context.session_id)
            if content:
                logger.debug(
                    f"Retrieved last response for analysis "
                    f"({len(content)} bytes)"
                )
                return content
            else:
                logger.warning(
                    f"No last response found for session {context.session_id}"
                )
                return None

        # Otherwise, use provided args as content
        if route.args:
            content = " ".join(route.args)
            logger.debug(f"Using provided content for analysis ({len(content)} bytes)")
            return content

        # Check if context has last_response
        if context.last_response:
            return context.last_response

        return None

    def _build_analysis_prompt(
        self,
        content: str,
        usage_doc: Optional[str],
        action_description: str
    ) -> str:
        """
        Build LLM prompt for analysis

        Args:
            content: Content to analyze
            usage_doc: Usage documentation from extension
            action_description: Description of the analysis task

        Returns:
            Formatted prompt
        """
        prompt = f"""You are helping the user understand an API response or data structure.

Task: {action_description}

"""

        if usage_doc:
            prompt += f"""Usage Guide:
{usage_doc}

"""

        prompt += f"""Content to analyze:
```
{content}
```

Please explain:
1. The structure and format of this response
2. Key fields and their meanings
3. Any notable patterns or insights
4. Potential issues or warnings (if any)

Be concise but thorough. Focus on what's most useful for the user.
"""

        return prompt

    def _simple_analysis(self, content: str) -> str:
        """
        Provide a simple analysis without LLM

        Args:
            content: Content to analyze

        Returns:
            Analysis string
        """
        lines = content.split("\n")
        char_count = len(content)
        line_count = len(lines)

        # Try to detect format
        format_type = "text"
        if content.strip().startswith("{") or content.strip().startswith("["):
            format_type = "JSON"
        elif content.strip().startswith("<"):
            format_type = "XML/HTML"

        analysis = f"""Response Analysis:

Format: {format_type}
Size: {char_count} characters, {line_count} lines

"""

        # Add first few lines as preview
        preview_lines = min(10, line_count)
        analysis += f"Preview (first {preview_lines} lines):\n"
        analysis += "\n".join(lines[:preview_lines])

        if line_count > preview_lines:
            analysis += f"\n\n... ({line_count - preview_lines} more lines)"

        return analysis


class AnalyzeSchemaExecutor(BaseExecutor):
    """
    Analyze JSON schema (analyze.schema runner type)

    Parse and validate structured output against JSON Schema.
    """

    RUNNER_TYPE = "analyze.schema"
    DEFAULT_SCHEMA_ID = "inline"

    def __init__(self, llm_client=None, schema_resolver=None):
        self.llm_client = llm_client
        self.schema_resolver = schema_resolver
        self.parser = SchemaOutputParser(schema_resolver=schema_resolver)
        register_default_prompt_specs()
        self.prompt_registry = get_prompt_registry()

    def supports_runner(self, runner: str) -> bool:
        return runner == self.RUNNER_TYPE

    def execute(
        self,
        route: CommandRoute,
        context: ExecutionContext
    ) -> ExecutionResult:
        raw = self._get_raw_text(route, context)
        if not raw:
            return ExecutionResult(
                success=False,
                output="",
                error="No content to parse for analyze.schema",
                metadata={"failure_type": "output_parse_error"},
            )

        try:
            schema, schema_id = self._resolve_schema(route)
        except Exception as exc:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Schema resolution failed: {exc}",
                metadata={"failure_type": "output_parse_error"},
            )

        parse_result = self.parser.parse(schema, raw)
        parse_metadata = self._build_parse_metadata(schema_id, parse_result)
        repair_prompt_hash = None
        repair_render_hash = None
        repair_prompt_spec_id = None
        repair_prompt_version = None
        repair_output_excerpt = None
        repair_attempted = False

        if parse_result.ok:
            result = ExecutionResult(
                success=True,
                output=json.dumps(parse_result.data, ensure_ascii=False),
                metadata={
                    **parse_metadata,
                    "analysis_type": "schema_parse",
                    "repair_attempted": False,
                },
            )
            self._write_schema_run_tape(
                route=route,
                context=context,
                parse_result=parse_result,
                result=result,
                repair_attempted=False,
                repair_prompt_hash=None,
                repair_render_hash=None,
                repair_prompt_spec_id=None,
                repair_prompt_version=None,
                repair_output_excerpt=None,
                repair_parse_result=None,
            )
            return result

        repair_result: Optional[ParseResult] = None
        if self.llm_client is not None:
            repair_attempted = True
            rendered_prompt = self._render_repair_prompt(schema, parse_result, raw)
            repair_prompt_hash = hashlib.sha256(rendered_prompt.text.encode("utf-8")).hexdigest()
            repair_render_hash = rendered_prompt.render_hash
            repair_prompt_spec_id = rendered_prompt.spec_id
            repair_prompt_version = rendered_prompt.version
            self._write_prompt_render_event(
                route=route,
                context=context,
                rendered_prompt=rendered_prompt,
                prompt_vars=rendered_prompt.vars_used,
            )
            repair_raw = self.llm_client.complete(rendered_prompt.text)
            repair_output_excerpt = self._truncate_text(repair_raw, 500)
            repair_result = self.parser.parse(schema, repair_raw)

            if repair_result.ok:
                repaired_metadata = self._build_parse_metadata(schema_id, repair_result)
                result = ExecutionResult(
                    success=True,
                    output=json.dumps(repair_result.data, ensure_ascii=False),
                    metadata={
                        **repaired_metadata,
                        "analysis_type": "schema_parse",
                        "repair_attempted": True,
                        "repair_prompt_hash": repair_prompt_hash,
                        "repair_render_hash": repair_render_hash,
                        "prompt_spec_id": repair_prompt_spec_id,
                        "prompt_version": repair_prompt_version,
                        "prompt_render_hash": repair_render_hash,
                        "repair_parse_ok": True,
                    },
                )
                self._write_schema_run_tape(
                    route=route,
                    context=context,
                    parse_result=parse_result,
                    result=result,
                    repair_attempted=True,
                    repair_prompt_hash=repair_prompt_hash,
                    repair_render_hash=repair_render_hash,
                    repair_prompt_spec_id=repair_prompt_spec_id,
                    repair_prompt_version=repair_prompt_version,
                    repair_output_excerpt=repair_output_excerpt,
                    repair_parse_result=repair_result,
                )
                return result

        failure_type = self._classify_failure(parse_result, repair_result)
        final_result = ExecutionResult(
            success=False,
            output="",
            error=self._format_parse_error(parse_result, repair_result),
            metadata={
                **parse_metadata,
                "failure_type": failure_type,
                "repair_attempted": repair_attempted,
                "repair_prompt_hash": repair_prompt_hash,
                "repair_render_hash": repair_render_hash,
                "prompt_spec_id": repair_prompt_spec_id,
                "prompt_version": repair_prompt_version,
                "prompt_render_hash": repair_render_hash,
                "repair_output_excerpt": repair_output_excerpt,
                "repair_parse_ok": bool(repair_result and repair_result.ok),
            },
        )
        self._write_schema_run_tape(
            route=route,
            context=context,
            parse_result=parse_result,
            result=final_result,
            repair_attempted=repair_attempted,
            repair_prompt_hash=repair_prompt_hash,
            repair_render_hash=repair_render_hash,
            repair_prompt_spec_id=repair_prompt_spec_id,
            repair_prompt_version=repair_prompt_version,
            repair_output_excerpt=repair_output_excerpt,
            repair_parse_result=repair_result,
        )
        return final_result

    def _resolve_schema(self, route: CommandRoute) -> tuple[dict[str, Any], str]:
        schema_value = route.flags.get("schema")
        if isinstance(schema_value, dict):
            return schema_value, str(schema_value.get("$id") or schema_value.get("title") or self.DEFAULT_SCHEMA_ID)

        schema_json = route.flags.get("schema_json")
        if isinstance(schema_json, str) and schema_json.strip():
            schema_dict = json.loads(schema_json)
            return schema_dict, str(schema_dict.get("$id") or schema_dict.get("title") or self.DEFAULT_SCHEMA_ID)

        schema_id = route.flags.get("schema_id")
        if isinstance(schema_id, str) and schema_id.strip():
            if self.schema_resolver is None:
                raise ValueError("schema_id provided but no schema_resolver configured")
            return self.schema_resolver(schema_id), schema_id

        raise ValueError("analyze.schema requires route.flags['schema'] or route.flags['schema_json'] or route.flags['schema_id']")

    def _get_raw_text(self, route: CommandRoute, context: ExecutionContext) -> Optional[str]:
        if route.args:
            return " ".join(str(arg) for arg in route.args)
        if context.last_response:
            return context.last_response
        return None

    def _build_parse_metadata(self, schema_id: str, parse_result: ParseResult) -> dict[str, Any]:
        return {
            "schema_id": schema_id,
            "schema_hash": parse_result.schema_hash,
            "parse_ok": parse_result.ok,
            "parse_strategy": parse_result.parse_strategy,
            "candidate_index": parse_result.candidate_index,
            "parse_errors": [err.__dict__ for err in parse_result.errors[:10]],
            "raw_excerpt": parse_result.raw_excerpt,
        }

    def _render_repair_prompt(self, schema: dict[str, Any], parse_result: ParseResult, raw_text: str) -> RenderedPrompt:
        required = schema.get("required", [])
        required_text = ", ".join(required) if required else "(none)"
        schema_compact = self._truncate_text(json.dumps(schema, ensure_ascii=False, sort_keys=True), 1500)
        errors_compact = "\n".join(
            f"- [{err.stage}] {err.path or '<root>'}: {err.message}"
            for err in parse_result.errors[:5]
        ) or "- unknown parse error"
        source_fragment = parse_result.json_candidate or parse_result.raw_excerpt or self._truncate_text(raw_text, 500)
        rules = (
            "1) Output a single JSON object/array only.\n"
            "2) No markdown fences or commentary.\n"
            f"3) Include required fields: {required_text}.\n"
            "4) Respect schema types and enums.\n"
        )
        spec = self.prompt_registry.get("analyze.schema.repair.v1")
        try:
            return spec.render(
                {
                    "rules": rules,
                    "schema_compact": schema_compact,
                    "errors_compact": errors_compact,
                    "json_candidate": self._truncate_text(source_fragment, 500),
                    "raw_excerpt": self._truncate_text(raw_text, 500),
                }
            )
        except PromptVarsValidationError as exc:
            raise ExecutionError(f"Prompt vars validation failed: {exc}") from exc

    def _format_parse_error(self, parse_result: ParseResult, repair_result: Optional[ParseResult]) -> str:
        current = repair_result if repair_result is not None else parse_result
        if not current.errors:
            return "Schema parse failed without detailed errors"
        first = current.errors[0]
        path = first.path or "<root>"
        return f"[{first.stage}] {path}: {first.message}"

    def _classify_failure(self, parse_result: ParseResult, repair_result: Optional[ParseResult]) -> str:
        if repair_result is not None:
            if any(err.stage in {"extract", "parse"} for err in repair_result.errors):
                return "output_repair_failed"
            if any(err.stage == "validate" for err in repair_result.errors):
                return "output_contract_violation"
            return "output_repair_failed"

        if any(err.stage in {"extract", "parse"} for err in parse_result.errors):
            return "output_parse_error"
        if any(err.stage == "validate" for err in parse_result.errors):
            return "output_contract_violation"
        return "output_parse_error"

    def _write_schema_run_tape(
        self,
        route: CommandRoute,
        context: ExecutionContext,
        parse_result: ParseResult,
        result: ExecutionResult,
        repair_attempted: bool,
        repair_prompt_hash: Optional[str],
        repair_render_hash: Optional[str],
        repair_prompt_spec_id: Optional[str],
        repair_prompt_version: Optional[str],
        repair_output_excerpt: Optional[str],
        repair_parse_result: Optional[ParseResult],
    ) -> None:
        try:
            run_tape_path_raw = os.getenv("OCTOPUSOS_SCHEMA_RUN_TAPE_PATH")
            if run_tape_path_raw:
                run_tape_path = Path(run_tape_path_raw)
            else:
                run_tape_path = context.work_dir / "run_tape.jsonl"

            audit_logger = AuditLogger(run_tape_path)
            audit_logger.log_event(
                event_type="analyze_schema",
                operation_id=f"{route.extension_id}:{route.action_id}",
                details={
                    "schema_id": result.metadata.get("schema_id"),
                    "schema_hash": result.metadata.get("schema_hash"),
                    "parse_ok": parse_result.ok,
                    "parse_strategy": parse_result.parse_strategy,
                    "candidate_index": parse_result.candidate_index,
                    "errors": [err.__dict__ for err in parse_result.errors[:10]],
                    "failure_type": result.metadata.get("failure_type"),
                    "repair_attempted": repair_attempted,
                    "repair_prompt_hash": repair_prompt_hash,
                    "repair_render_hash": repair_render_hash,
                    "prompt_spec_id": repair_prompt_spec_id,
                    "prompt_version": repair_prompt_version,
                    "repair_output_excerpt": repair_output_excerpt,
                    "repair_parse_ok": bool(repair_parse_result and repair_parse_result.ok),
                },
            )
        except Exception as exc:
            logger.warning("Failed to write analyze.schema run tape: %s", exc)

    def _write_prompt_render_event(
        self,
        route: CommandRoute,
        context: ExecutionContext,
        rendered_prompt: RenderedPrompt,
        prompt_vars: dict[str, Any],
    ) -> None:
        try:
            run_tape_path_raw = os.getenv("OCTOPUSOS_SCHEMA_RUN_TAPE_PATH")
            if run_tape_path_raw:
                run_tape_path = Path(run_tape_path_raw)
            else:
                run_tape_path = context.work_dir / "run_tape.jsonl"

            audit_logger = AuditLogger(run_tape_path)
            audit_logger.log_event(
                event_type="prompt_render",
                operation_id=f"{route.extension_id}:{route.action_id}",
                details={
                    "spec_id": rendered_prompt.spec_id,
                    "version": rendered_prompt.version,
                    "spec_hash": rendered_prompt.spec_hash,
                    "render_hash": rendered_prompt.render_hash,
                    "vars_hash": rendered_prompt.vars_hash,
                    "vars_keys": sorted(prompt_vars.keys()),
                    "context": "analyze_schema_repair",
                },
            )
        except Exception as exc:
            logger.warning("Failed to write prompt_render run tape: %s", exc)

    def _truncate_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "...(truncated)"
