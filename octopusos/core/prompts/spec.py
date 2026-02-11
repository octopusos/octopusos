"""Prompt specification primitives with deterministic rendering."""

from __future__ import annotations

import hashlib
import json
import string
from dataclasses import dataclass, field
from typing import Any

import jsonschema


class PromptSpecError(Exception):
    """Base prompt spec error."""


class PromptVarsValidationError(PromptSpecError):
    """Raised when prompt render vars fail schema validation."""


@dataclass(frozen=True)
class RenderedPrompt:
    """Rendered prompt with governance metadata."""

    text: str
    render_hash: str
    vars_used: dict[str, Any]
    spec_id: str
    version: str
    spec_hash: str
    vars_hash: str


@dataclass(frozen=True)
class PromptSpec:
    """Governed prompt asset."""

    id: str
    name: str
    version: str
    template: str
    vars_schema: dict[str, Any]
    defaults: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def render(self, vars: dict[str, Any]) -> RenderedPrompt:
        vars_merged = {**self.defaults, **vars}
        self._validate_vars(vars_merged)
        self._validate_required_template_vars(vars_merged)

        text = self.template.format(**vars_merged)
        spec_hash = self.spec_hash()
        vars_hash = self._vars_hash(vars_merged)
        render_hash = self._render_hash(vars_merged)

        return RenderedPrompt(
            text=text,
            render_hash=render_hash,
            vars_used=vars_merged,
            spec_id=self.id,
            version=self.version,
            spec_hash=spec_hash,
            vars_hash=vars_hash,
        )

    def spec_hash(self) -> str:
        canonical = json.dumps(
            {
                "id": self.id,
                "name": self.name,
                "version": self.version,
                "template": self.template,
                "vars_schema": self.vars_schema,
                "defaults": self.defaults,
                "tags": self.tags,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _render_hash(self, vars_merged: dict[str, Any]) -> str:
        canonical = json.dumps(
            {
                "spec_id": self.id,
                "version": self.version,
                "template": self.template,
                "vars": vars_merged,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _vars_hash(self, vars_merged: dict[str, Any]) -> str:
        canonical = json.dumps(
            vars_merged,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _validate_vars(self, vars_merged: dict[str, Any]) -> None:
        validator = jsonschema.Draft202012Validator(self.vars_schema)
        errors = sorted(validator.iter_errors(vars_merged), key=lambda err: list(err.path))
        if not errors:
            return

        messages = []
        for err in errors[:20]:
            path = "/" + "/".join(str(part) for part in err.absolute_path)
            path = path if path != "/" else "<root>"
            messages.append(f"{path}: {err.message}")
        raise PromptVarsValidationError("; ".join(messages))

    def _validate_required_template_vars(self, vars_merged: dict[str, Any]) -> None:
        formatter = string.Formatter()
        required_fields = {
            field_name
            for _, field_name, _, _ in formatter.parse(self.template)
            if field_name
        }
        missing = sorted(field for field in required_fields if field not in vars_merged)
        if missing:
            raise PromptVarsValidationError(
                "Missing template variables: " + ", ".join(missing)
            )
