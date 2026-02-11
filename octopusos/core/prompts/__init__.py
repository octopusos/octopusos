"""Prompt governance package."""

from .spec import (
    PromptSpec,
    RenderedPrompt,
    PromptSpecError,
    PromptVarsValidationError,
)
from .registry import (
    PromptRegistry,
    PromptRegistryError,
    PromptSpecNotFoundError,
    get_prompt_registry,
)


def register_default_prompt_specs() -> None:
    """Register built-in prompt specs used by core executors."""
    registry = get_prompt_registry()
    if registry.maybe_get("analyze.schema.repair.v1") is None:
        registry.register(
            PromptSpec(
                id="analyze.schema.repair.v1",
                name="Analyze Schema Repair",
                version="1.0.0",
                template=(
                    "Your previous output did not conform to the JSON schema.\\n"
                    "Return ONLY valid JSON. No markdown, no explanation.\\n\\n"
                    "Rules:\\n{rules}\\n\\n"
                    "Schema (compact):\\n{schema_compact}\\n\\n"
                    "Validation/parse errors:\\n{errors_compact}\\n\\n"
                    "JSON candidate:\\n{json_candidate}\\n\\n"
                    "Raw excerpt:\\n{raw_excerpt}\\n"
                ),
                vars_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "rules",
                        "schema_compact",
                        "errors_compact",
                        "json_candidate",
                        "raw_excerpt",
                    ],
                    "properties": {
                        "rules": {"type": "string"},
                        "schema_compact": {"type": "string"},
                        "errors_compact": {"type": "string"},
                        "json_candidate": {"type": "string"},
                        "raw_excerpt": {"type": "string"},
                    },
                },
                defaults={
                    "json_candidate": "(none)",
                },
                tags=["analyze", "schema", "repair"],
            )
        )


__all__ = [
    "PromptSpec",
    "RenderedPrompt",
    "PromptSpecError",
    "PromptVarsValidationError",
    "PromptRegistry",
    "PromptRegistryError",
    "PromptSpecNotFoundError",
    "get_prompt_registry",
    "register_default_prompt_specs",
]
